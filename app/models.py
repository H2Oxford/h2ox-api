import datetime
from typing import Union

from pydantic import BaseModel, Field, conlist


class HTTPError(BaseModel):
    detail: str

    class Config:
        schema_extra = {
            "example": {"detail": "HTTPException raised."},
        }


# The geometry types below borrow heavily from
# https://github.com/developmentseed/geojson-pydantic
Point = tuple[float, float]
LinearRing = conlist(Point, min_items=4)
PolygonCoords = conlist(LinearRing, min_items=1)
MultiPolygonCoords = conlist(PolygonCoords, min_items=1)


class Geometry(BaseModel):
    type: str = Field(..., example="Polygon")
    coordinates: Union[PolygonCoords, MultiPolygonCoords] = Field(
        ..., example=[[[1, 3], [2, 2], [4, 4], [1, 3]]]
    )


class Level(BaseModel):
    date: datetime.date = Field(..., example=datetime.date(2022, 3, 12))
    level: float = Field(..., example=138)


class Reservoir(BaseModel):
    name: str = Field(..., example="Harangi")
    level: Level = Field(..., example=Level(date="2021-01-01", level=138))
    full_level: float = Field(..., example=190)
    geom: Geometry


class Timeseries(BaseModel):
    reservoir: str
    ref_date: datetime.date = Field(..., example=datetime.date(2022, 3, 12))
    timeseries: list[Level]


class ReservoirList(BaseModel):
    reservoirs: list[Reservoir]
