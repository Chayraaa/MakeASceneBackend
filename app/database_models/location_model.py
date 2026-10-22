from geoalchemy2 import Geometry
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class LocationModel(db.Model):
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    place_id: Mapped[str] = mapped_column(nullable=False, unique=True)
    details: Mapped[str] = mapped_column(nullable=False)
    geometry: Mapped[object] = mapped_column(
        Geometry(
            geometry_type="GEOMETRY",
            srid=4326,
        ),
        nullable=True,
    )