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


class TimeValue(BaseModel):
    date: datetime.date = Field(..., example=datetime.date(2022, 3, 12))
    value: float = Field(..., example=138)


class Reservoir(BaseModel):
    name: str = Field(..., example="Harangi")
    level: TimeValue = Field(..., example=TimeValue(date="2021-01-01", value=138))
    full_level: float = Field(..., example=190)
    geom: Geometry


class Timeseries(BaseModel):
    reservoir: str
    ref_date: datetime.date = Field(..., example=datetime.date(2022, 3, 12))
    timeseries: list[TimeValue]


class ReservoirList(BaseModel):
    reservoirs: list[Reservoir]
