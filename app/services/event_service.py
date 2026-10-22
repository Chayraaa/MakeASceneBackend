from copy import deepcopy
from app.metrics.operation_metrics import monitored

from app.domain_models.events.event import Event
from app.domain_models.events.event_query import EventQuery
from app.repositories.interfaces.storage.events.event_repo_protocol import EventRepoProtocol
from app.services.image_service import ImageService
from app.services.location_service import LocationService


class EventService:
    def __init__(self, event_repo: EventRepoProtocol, location_service: LocationService, image_service: ImageService):
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
        return True

    @monitored("event", "get")
    def get_event_by_id(self, event_id: int) -> Event | None:
        return self.event_repo.get_event_by_id(event_id)

    @monitored("event", "update")
    def update_event(self, event: Event) -> bool:
        if event.id is None or self.event_repo.get_event_by_id(event.id) is None:
            return False
        prepared = self._prepare(event)
        if not self.event_repo.update_event(prepared):
            return False
        event.data = prepared.data
        event.detail_data = prepared.detail_data
        return True

    @monitored("event", "delete")
    def remove_event(self, event: Event) -> bool:
        return self.event_repo.remove_event(event)

    @monitored("event", "query")
    def query_events(self, query: EventQuery | None = None, page: int = 1, page_size: int = 25) -> list[Event]:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        query = query or EventQuery()
        query.validate()
        if query.place_id is not None and self.location_service.get_location_data(query.place_id) is None:
            raise ValueError("Query location could not be resolved")
        return self.event_repo.query_events(query, page, page_size)
