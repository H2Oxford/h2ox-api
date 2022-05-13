import datetime
from typing import Union, Optional

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
    value: float = Field(..., example=138)
    baseline: float = Field(..., example=120)


class Precip(BaseModel):
    date: datetime.date = Field(..., example=datetime.date(2022, 3, 12))
    value: float = Field(..., example=138)
    cumulative: float = Field(..., example=1250)
    cumulative_baseline: float = Field(..., example=1300)


class Reservoir(BaseModel):
    name: str = Field(..., example="Harangi")
    level: Level = Field(..., example=Level(date="2021-01-01", value=138, baseline=120))
    full_level: float = Field(..., example=190)
    geom: Optional[Geometry]


class LevelTimeseries(BaseModel):
    reservoir: str
    ref_date: datetime.date = Field(..., example=datetime.date(2022, 3, 12))
    timeseries: list[Level]


class PrecipTimeseries(BaseModel):
    reservoir: str
    ref_date: datetime.date = Field(..., example=datetime.date(2022, 3, 12))
    timeseries: list[Precip]


class ReservoirList(BaseModel):
    reservoirs: list[Reservoir]
