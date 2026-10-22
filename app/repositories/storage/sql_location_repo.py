import json

from app.database_models.location_model import LocationModel
from app.domain_models.Location import Location
from app.repositories.interfaces.storage.location_storage_protocol import LocationStorageProtocol


class SQLLocationRepo:
    def __init__(self, session):
        self.session = session

    def add_location(self, location: Location) -> bool:
        if self.get_location(location.id):
            return False
        details = location.details if isinstance(location.details, str) else json.dumps(location.details)
        db_model = LocationModel(place_id=location.place_id, details=details, geometry=location.geometry)
        self.session.add(db_model)
        self.session.commit()
        location.id = db_model.id
        return True

    def remove_location(self, location: Location) -> bool:
        db_model = self.session.query(LocationModel).filter(LocationModel.id == location.id).first()
        if db_model:
            self.session.delete(db_model)
            self.session.commit()
            return True
        return False

    def get_location_by_place_id(self, place_id: str) -> Location | None:
        db_model = self.session.query(LocationModel).filter(LocationModel.place_id == place_id).first()
        if db_model:
            return Location(id=db_model.id, place_id=db_model.place_id, details=db_model.details, geometry=db_model.geometry)
        return None

    def get_location(self, location_id: int) -> Location | None:
        db_model = self.session.query(LocationModel).filter(LocationModel.id == location_id).first()
        if db_model:
            return Location(id=db_model.id, place_id=db_model.place_id, details=db_model.details, geometry=db_model.geometry)
        return None

    def update_location(self, location: Location) -> bool:
        db_model = self.session.query(LocationModel).filter(LocationModel.id == location.id).first()
        if db_model:
            db_model.place_id = location.place_id
            db_model.details = location.details if isinstance(location.details, str) else json.dumps(location.details)
            db_model.geometry = location.geometry
            self.session.commit()
            return True
        return False
