from app.domain_models.user import User, Role
from copy import deepcopy
import json

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload

from app.database_models.events.event_model import EventModel, event_tags
from app.database_models.location_model import LocationModel
from app.database_models.site_account.site_account_model import SiteAccountModel
from app.database_models.tags.tag_model import TagModel
from app.domain_models.events.event import Event
from app.domain_models.events.event_query import EventQuery


class SqlEventRepo:
    def __init__(self, session):
        self.session = session

    def create_event(self, event: Event) -> bool:
        model = EventModel()
        self._apply_event(model, event)
        self.session.add(model)
        self.session.commit()
        event.id = model.id
        return True

    def get_event_by_id(self, event_id: int) -> Event | None:
        model = self.session.get(EventModel, event_id)
        if model is None:
            return None
        return self._to_domain(model)

    def get_events(self, page: int, page_size: int) -> list[Event]:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        models = (
            self.session.query(EventModel)
            .options(selectinload(EventModel.tags), selectinload(EventModel.collaborators))
            .order_by(EventModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [self._to_domain(model) for model in models]

    def update_event(self, event: Event) -> bool:
        if event.id is None:
            return False
        model = self.session.get(EventModel, event.id)
        if model is None:
            return False
        self._apply_event(model, event)
        self.session.commit()
        return True

    def query_events(self, query: EventQuery, page: int, page_size: int, user: User | None = None) -> list[Event]:
        query.validate()
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        models = self.session.query(EventModel).options(
            selectinload(EventModel.tags), selectinload(EventModel.collaborators)
        )
        rank = user.role.value if user is not None and isinstance(user.role, Role) else (user.role if user is not None else -1)
        if rank < Role.MODERATOR.value:
            visible = EventModel.visible.is_(True)
            if user is not None:
                owned_accounts = select(SiteAccountModel.id).where(SiteAccountModel.creator_id == user.id)
                visible = visible | EventModel.owner_id.in_(owned_accounts)
            models = models.filter(visible)
        included = sorted(set(query.included_tags))
        if query.organizer_ids:
            models = models.filter(EventModel.owner_id.in_(query.organizer_ids))
        if query.collaborator_ids:
            models = models.filter(EventModel.collaborators.any(SiteAccountModel.id.in_(query.collaborator_ids)))
        if query.excluded_tags:
            models = models.filter(~EventModel.tags.any(TagModel.id.in_(query.excluded_tags)))
        if query.access:
            models = models.filter(cast(EventModel.access, JSONB).contains(query.access))
        if query.name:
            models = models.filter(EventModel.name.icontains(query.name, autoescape=True))
        if query.from_ is not None:
            models = models.filter(EventModel.till >= query.from_)
        if query.till is not None:
            models = models.filter(EventModel.from_ <= query.till)

        if query.place_id is not None or query.geofence is not None or query.radius_m is not None:
            models = models.join(LocationModel, EventModel.place_id == LocationModel.place_id)
            if query.place_id is not None:
                fence = select(LocationModel.geometry).where(
                    LocationModel.place_id == query.place_id
                ).correlate(None).scalar_subquery()
                models = models.filter(func.ST_Intersects(LocationModel.geometry, fence))
            if query.geofence is not None:
                fence = func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(query.geofence)), 4326)
                models = models.filter(func.ST_Intersects(LocationModel.geometry, fence))
            if query.radius_m is not None:
                point = func.ST_SetSRID(func.ST_MakePoint(query.longitude, query.latitude), 4326)
                models = models.filter(func.ST_DWithin(
                    cast(LocationModel.geometry, Geography(srid=4326)),
                    cast(point, Geography(srid=4326)), query.radius_m,
                ))

        if included:
            score = select(func.count()).select_from(event_tags).where(
                event_tags.c.event_id == EventModel.id,
                event_tags.c.tag_id.in_(included),
            ).correlate(EventModel).scalar_subquery()
            if not query.include_partial:
                models = models.filter(score > 0)
            models = models.order_by(score.desc())
            # The last selected tag has priority among equally strong matches:
            # [Gaming, Dogs] ranks both, then Dogs, then Gaming.
            for tag_id in reversed(list(dict.fromkeys(query.included_tags))):
                models = models.order_by(EventModel.tags.any(TagModel.id == tag_id).desc())
        models = models.order_by(EventModel.from_, EventModel.id)
        return [self._to_domain(model) for model in models.offset((page - 1) * page_size).limit(page_size).all()]

    def remove_event(self, event: Event) -> bool:
        if event.id is None:
            return False
        model = self.session.get(EventModel, event.id)
        if model is None:
            return False
        self.session.delete(model)
        self.session.commit()
        return True

    def _resolve_ids(self, model_class, ids: list[int]):
        unique_ids = sorted(set(ids))
        if not unique_ids:
            return []
        models = self.session.query(model_class).filter(model_class.id.in_(unique_ids)).all()
        missing = set(unique_ids) - {model.id for model in models}
        if missing:
            raise ValueError(f"Unknown {model_class.__name__} IDs: {sorted(missing)}")
        return models

    def _apply_event(self, model: EventModel, event: Event):
        # Resolve both collections before changing an existing model.
        tags = self._resolve_ids(TagModel, event.tags)
        collaborators = self._resolve_ids(SiteAccountModel, event.collaborators)
        model.visible = event.visible
        model.name = event.name
        model.description = event.description
        model.from_ = event.from_
        model.till = event.till
        model.place_id = event.place_id
        model.layout = event.layout
        model.data = deepcopy(event.data)
        model.owner_id = event.owner_id
        model.access = deepcopy(event.access)
        model.repeating = event.repeating
        model.detail_data = deepcopy(event.detail_data)
        model.tags = tags
        model.collaborators = collaborators

    @staticmethod
    def _to_domain(model: EventModel) -> Event:
        return Event(
            id=model.id,
            visible=model.visible,
            name=model.name,
            description=model.description,
            from_=model.from_,
            till=model.till,
            tags=sorted(tag.id for tag in model.tags),
            place_id=model.place_id,
            layout=model.layout,
            data=deepcopy(model.data),
            owner_id=model.owner_id,
            access=deepcopy(model.access),
            repeating=model.repeating,
            detail_data=deepcopy(model.detail_data),
            collaborators=sorted(account.id for account in model.collaborators),
        )
