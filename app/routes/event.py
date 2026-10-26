from dataclasses import replace
from datetime import datetime
import json

from flask import Blueprint, current_app, request
from sqlalchemy.exc import IntegrityError

from app import login_required, validate
from app.domain_models.events.event import Event
from app.domain_models.events.event_query import EventQuery
from app.domain_models.user import Role, User
from app.extensions import db


events = Blueprint("events", __name__)


def _error(message: str, status: int):
    return {"error": "not_found" if status == 404 else "validation", "message": message}, status


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _changes(data: dict) -> dict:
    fields = {}
    for key in ("name", "description", "till", "layout", "data", "access", "repeating", "collaborators", "visible"):
        if key in data:
            fields[key] = data[key]
    for external, internal in (("from", "from_"), ("place-id", "place_id"),
                               ("owner-id", "owner_id"), ("detail-data", "detail_data")):
        if external in data:
            fields[internal] = data[external]
    for key in ("from_", "till"):
        if key in fields:
            fields[key] = _date(fields[key])
    if "tags" in data:
        # Validate existing IDs before creating any of the supplied tag names.
        fields["tags"] = [tag for tag in data["tags"] if isinstance(tag, int)]
    return fields


def _site_permission(user: User, site_id: int):
    account = current_app.site_account_service.get_site_account_by_id(site_id)
    if account is None:
        return _error("Site account not found.", 404)
    if not current_app.site_account_service.has_authority(user, account):
        return _error("You do not have permission to manage events for this site account.", 401)
    return None


def _check_references(event: Event):
    for tag in event.tags:
        if current_app.tag_service.get_tag(tag) is None:
            return _error(f"Tag {tag} not found.", 404)
    for collaborator in event.collaborators:
        if current_app.site_account_service.get_site_account_by_id(collaborator) is None:
            return _error(f"Collaborating site account {collaborator} not found.", 404)
    return None


def _response(event: Event, accounts: dict | None = None, places: dict | None = None) -> dict:
    accounts = {} if accounts is None else accounts
    places = {} if places is None else places

    def account(site_id):
        if site_id not in accounts:
            accounts[site_id] = current_app.site_account_service.get_site_account_by_id(site_id)
        return accounts[site_id]

    owner = account(event.owner_id)
    if event.place_id not in places:
        location = current_app.location_service.get_location_data(event.place_id)
        details = location.details if location is not None else None
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except ValueError:
                pass
        places[event.place_id] = details
    result = event.to_dict()
    result.pop("place-id")
    result["place-data"] = places[event.place_id]
    result["owner-name"] = owner.name if owner else ""
    result["owner-picture"] = owner.picture if owner else ""
    result["collaborators"] = [
        {"collaborator-id": site.id, "collaborator-name": site.name, "collaborator-picture": site.picture}
        for site in (account(site_id) for site_id in event.collaborators) if site is not None
    ]
    if event.repeating is None:
        result.pop("repeating")
    return result


@events.route("", methods=["POST"])
@login_required(role=Role.USER)
@validate
def create_event(user: User):
    data = request.get_json()
    denied = _site_permission(user, data["owner-id"])
    if denied is not None:
        return denied
    try:
        value = Event(**_changes(data))
        missing = _check_references(value)
        if missing is not None:
            return missing
        value.tags = current_app.tag_service.resolve_tags(data["tags"])
        if current_app.event_service.create_event(value):
            return {"message": "Event created."}, 201
    except ValueError as exc:
        return _error(str(exc), 422)
    except IntegrityError:
        db.session.rollback()
        return _error("Event references could not be stored.", 422)
    return _error("Failed to create event.", 500)


@events.route("/<id>", methods=["GET"])
@login_required(optional=True)
@validate
def get_event(id: str, user: User | None):
    try:
        event_id = int(id)
    except ValueError:
        return _error("Event not found.", 404)
    value = current_app.event_service.get_event_by_id(event_id)
    if value is None or not current_app.event_service.can_view(user, value):
        return _error("Event not found.", 404)
    return _response(value), 200


@events.route("/<int:id>", methods=["PATCH"])
@login_required(role=Role.USER)
@validate
def update_event(user: User, id: int):
    value = current_app.event_service.get_event_by_id(id)
    if value is None:
        return _error("Event not found.", 404)
    denied = _site_permission(user, value.owner_id)
    if denied is not None:
        return denied
    data = request.get_json()
    if "owner-id" in data:
        denied = _site_permission(user, data["owner-id"])
        if denied is not None:
            return denied
    try:
        updated = replace(value, **_changes(data))
        missing = _check_references(updated)
        if missing is not None:
            return missing
        if "tags" in data:
            updated.tags = current_app.tag_service.resolve_tags(data["tags"])
        if current_app.event_service.update_event(updated):
            return {"message": "Event updated."}, 200
    except ValueError as exc:
        return _error(str(exc), 422)
    except IntegrityError:
        db.session.rollback()
        return _error("Event references could not be stored.", 422)
    return _error("Event not found.", 404)


@events.route("/<int:id>", methods=["DELETE"])
@login_required(role=Role.USER)
@validate
def delete_event(user: User, id: int):
    value = current_app.event_service.get_event_by_id(id)
    if value is None:
        return _error("Event not found.", 404)
    denied = _site_permission(user, value.owner_id)
    if denied is not None:
        return denied
    if current_app.event_service.remove_event(value):
        return {"message": "Event deleted."}, 200
    return _error("Event not found.", 404)


@events.route("", methods=["GET"])
@login_required(role=Role.USER)
@validate
def query_events(user: User):
    args = request.args
    try:
        query = EventQuery(
            included_tags=[int(value) for value in args.getlist("included_tags")],
            excluded_tags=[int(value) for value in args.getlist("excluded_tags")],
            access=args.getlist("access"), name=args.get("name"),
            from_=_date(args["from"]) if "from" in args else None,
            till=_date(args["till"]) if "till" in args else None,
            place_id=args.get("place-id"),
            longitude=float(args["long"]) if "long" in args else None,
            latitude=float(args["lat"]) if "lat" in args else None,
            radius_m=float(args["radius"]) if "radius" in args else None,
            include_partial=args.get("include-no-tag-matches", "false").lower() == "true",
            organizer_ids=[int(value) for value in args.getlist("organisers")],
        )
        values = current_app.event_service.query_events(
            query, page=int(args.get("page", 1)), page_size=int(args.get("size", 25)), user=user
        )
    except ValueError as exc:
        return _error(str(exc), 422)
    accounts, places = {}, {}
    return [_response(value, accounts, places) for value in values], 200
