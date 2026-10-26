import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import json
from app.domain_models.messages.notify_message import NotifyMessage
from app.domain_models.user import User, Role
from app.domain_models.subscriptions.event_subscription import EventSubscription
from app.repositories.interfaces.storage.subscriptions.event_subscription_repo_protocol import EventSubscriptionRepoProtocol
from copy import deepcopy
from app.metrics.operation_metrics import monitored

from app.domain_models.events.event import Event
from app.domain_models.events.event_query import EventQuery
from app.repositories.interfaces.storage.events.event_repo_protocol import EventRepoProtocol
from app.services.image_service import ImageService
from app.services.location_service import LocationService


# Editable templates; placeholders: event_name, changes.
EVENT_CHANGED_TITLE = 'Es gab Änderungen beim Event „{event_name}“'
EVENT_CHANGED_BODY = 'Es gab Änderungen beim Event „{event_name}“:\n{changes}'
EVENT_CANCELLED_TITLE = 'Event „{event_name}“ abgesagt'
EVENT_CANCELLED_BODY = 'Das Event „{event_name}“ wurde abgesagt und ist nicht mehr verfügbar.'
EVENT_CHANGE_LABELS = {
    "name": "Name", "description": "Beschreibung", "from_": "Beginn", "till": "Ende",
    "place_id": "Ort", "data": "Inhalt",
    "owner_id": "Veranstalter", "access": "Zugang", "detail_data": "Details",
    "repeating": "Wiederholung", "collaborators": "Mitveranstalter",
}
logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, event_repo: EventRepoProtocol, location_service: LocationService, image_service: ImageService,
                 subscription_repo: EventSubscriptionRepoProtocol | None = None,
                 message_service=None, user_repo=None, site_account_service=None):
        self.subscription_repo = subscription_repo
        self.message_service = message_service
        self.user_repo = user_repo
        self.site_account_service = site_account_service
        self.event_repo = event_repo
        self.location_service = location_service
        self.image_service = image_service

    def _prepare(self, event: Event) -> Event:
        for value in (event.from_, event.till):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("Event dates must include a timezone")
        if event.from_ > event.till:
            raise ValueError("Event start must not be after its end")
        prepared = deepcopy(event)
        if self.location_service.get_location_data(prepared.place_id) is None:
            raise ValueError("Event location could not be resolved")
        prepared.data = self.image_service.replace_event_images(prepared.data)
        prepared.detail_data = self.image_service.replace_event_images(prepared.detail_data)
        return prepared

    @monitored("event", "create")
    def create_event(self, event: Event) -> bool:
        prepared = self._prepare(event)
        if not self.event_repo.create_event(prepared):
            return False
        event.id = prepared.id
        event.data = prepared.data
        event.detail_data = prepared.detail_data
        if prepared.visible:
            self._notify_publication(prepared)
        return True

    @monitored("event", "get")
    def get_event_by_id(self, event_id: int) -> Event | None:
        return self.event_repo.get_event_by_id(event_id)

    @monitored("event", "update")
    def update_event(self, event: Event) -> bool:
        if event.id is None:
            return False
        previous = self.event_repo.get_event_by_id(event.id)
        if previous is None:
            return False
        prepared = self._prepare(event)
        if not self.event_repo.update_event(prepared):
            return False
        event.data = prepared.data
        event.detail_data = prepared.detail_data
        if not previous.visible and prepared.visible:
            self._notify_publication(prepared)
        elif previous.visible and not prepared.visible:
            self._notify_event(prepared, EVENT_CANCELLED_TITLE, EVENT_CANCELLED_BODY)
        elif previous.visible and prepared.visible:
            if any(getattr(previous, field) != getattr(prepared, field) for field in EVENT_CHANGE_LABELS):
                self._notify_event(prepared, EVENT_CHANGED_TITLE, EVENT_CHANGED_BODY, previous=previous)
        return True

    @monitored("event", "delete")
    def remove_event(self, event: Event) -> bool:
        previous = self.event_repo.get_event_by_id(event.id) if event.id is not None else None
        if previous is None:
            return False
        recipients = self._notification_users(previous.id) if previous.visible else []
        if not self.event_repo.remove_event(event):
            return False
        if previous.visible:
            self._notify_event(previous, EVENT_CANCELLED_TITLE, EVENT_CANCELLED_BODY, recipients=recipients)
        return True

    @monitored("event", "query")
    def query_events(self, query: EventQuery | None = None, page: int = 1, page_size: int = 25, user: User | None = None) -> list[Event]:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        query = query or EventQuery()
        query.validate()
        if query.place_id is not None and self.location_service.get_location_data(query.place_id) is None:
            raise ValueError("Query location could not be resolved")
        if user is None:
            return self.event_repo.query_events(query, page, page_size)
        return self.event_repo.query_events(query, page, page_size, user=user)

    def can_view(self, user: User | None, event: Event) -> bool:
        if event.visible:
            return True
        if user is None:
            return False
        rank = user.role.value if isinstance(user.role, Role) else user.role
        if rank >= Role.MODERATOR.value:
            return True
        if self.site_account_service is None:
            return False
        owner = self.site_account_service.get_site_account_by_id(event.owner_id)
        return owner is not None and owner.creator_id == user.id

    def get_event_subscription(self, user: User, event_id: int) -> EventSubscription | None:
        """Look up only the authenticated user's subscription to this target."""
        subscription = self.subscription_repo.get_by_user_and_event_id(user.id, event_id)
        if subscription is None or subscription.user_id != user.id:
            return None
        return subscription

    def get_event_subscriptions(self, user: User, page: int = 1, page_size: int = 25) -> list[EventSubscription] | None:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        return self.subscription_repo.get_by_user_id(user.id, page, page_size)

    def subscribe_to_event(self, user: User, event_id: int) -> bool | None:
        """Return None for a missing target, otherwise the write result."""
        if self.event_repo.get_event_by_id(event_id) is None:
            return None
        if self.get_event_subscription(user, event_id) is not None:
            return True
        return self.subscription_repo.create(EventSubscription(user_id=user.id, event_id=event_id))

    def unsubscribe_from_event(self, user: User, event_id: int) -> bool | None:
        subscription = self.get_event_subscription(user, event_id)
        if subscription is None or subscription.user_id != user.id:
            return None
        return self.subscription_repo.delete(subscription)

    def set_event_notifications(self, user: User, event_id: int, notify: bool) -> bool | None:
        if not isinstance(notify, bool):
            raise ValueError("notify must be a boolean")
        subscription = self.get_event_subscription(user, event_id)
        if subscription is None or subscription.user_id != user.id:
            return None
        subscription.notifications_enabled = notify
        return self.subscription_repo.update(subscription)
    def _describe_changes(self, previous: Event, updated: Event, recipient_timezone: str = "UTC") -> str:
        try:
            zone = ZoneInfo(recipient_timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            zone = timezone.utc

        def display(field, value):
            if isinstance(value, datetime):
                # Older SQLite/naive database timestamps represent UTC.
                value = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
                return value.astimezone(zone).strftime("%d.%m.%Y um %H:%M %Z")
            if field == "place_id":
                location = self.location_service.get_location_data(value)
                details = location.details if location is not None else {}
                if isinstance(details, str):
                    try:
                        details = json.loads(details)
                    except ValueError:
                        details = {}
                if isinstance(details, dict):
                    if details.get("formatted"):
                        return details["formatted"]
                    lat, lon = details.get("lat"), details.get("lon")
                    if lat is not None and lon is not None:
                        return f"{lat}, {lon}"
                return "Unbekannter Ort"
            if field in ("owner_id", "collaborators"):
                ids = value if isinstance(value, list) else [value]
                names = []
                for site_id in ids:
                    site = self.site_account_service.get_site_account_by_id(site_id) if self.site_account_service else None
                    names.append(site.name if site is not None else "Unbekannter Veranstalter")
                return ", ".join(names) or "Keine"
            if isinstance(value, list):
                return ", ".join(str(item) for item in value) or "Keine"
            return str(value) if value is not None and value != "" else "Keine Angabe"

        changes = []
        content_changed = False
        for field, label in EVENT_CHANGE_LABELS.items():
            before, after = getattr(previous, field), getattr(updated, field)
            if field in ("collaborators", "access") and set(before) == set(after):
                continue
            if before == after:
                continue
            if field in ("data", "detail_data"):
                content_changed = True
            else:
                changes.append(f"{label}: {display(field, before)} → {display(field, after)}")
        if content_changed:
            changes.append("Inhalte haben sich geändert.")
        return "\n".join(changes)

    def _notify_publication(self, event: Event):
        if self.site_account_service is not None:
            try:
                self.site_account_service.notify_new_event(event)
            except Exception:
                logger.exception("Failed to announce event %s", event.id)

    def _notification_users(self, event_id: int) -> list[User]:
        if self.message_service is None or self.subscription_repo is None or self.user_repo is None:
            return []
        users, seen = [], set()
        try:
            page = 1
            while True:
                subscriptions = self.subscription_repo.get_by_event_id(event_id, page, 100)
                if subscriptions is None:
                    logger.error("Could not load event notification recipients")
                    return users
                for subscription in subscriptions:
                    if not subscription.notifications_enabled or subscription.user_id in seen:
                        continue
                    seen.add(subscription.user_id)
                    user = self.user_repo.get_user(subscription.user_id)
                    if user is not None:
                        users.append(user)
                if len(subscriptions) < 100:
                    return users
                page += 1
        except Exception:
            logger.exception("Failed to load notification recipients for event %s", event_id)
        return users

    def _notify_event(self, event: Event, title: str, body: str, *, changes: str = "", recipients=None, previous: Event | None = None):
        if self.message_service is None:
            return
        users = self._notification_users(event.id) if recipients is None else recipients
        for user in users:
            try:
                user_changes = self._describe_changes(previous, event, getattr(user, "timezone", "UTC")) if previous is not None else changes
                if previous is not None and not user_changes:
                    continue
                notification = NotifyMessage(title.format(event_name=event.name, changes=user_changes),
                                             body.format(event_name=event.name, changes=user_changes))
                if not self.message_service.send_message(notification, user):
                    logger.error("Failed to notify user %s about event %s", user.id, event.id)
            except Exception:
                logger.exception("Failed to notify user %s about event %s", user.id, event.id)
