import datetime

from pydantic import BaseModel, Field


class HTTPError(BaseModel):
    detail: str

    class Config:
        schema_extra = {
            "example": {"detail": "HTTPException raised."},
        }


class Level(BaseModel):
    date: datetime.date = Field(..., example=datetime.date(2022, 3, 12))
    level: float = Field(..., example=138)


class Reservoir(BaseModel):
    name: str = Field(..., example="Harangi")
    level: Level = Field(..., example=Level(date="2021-01-01", level=138))


class Timeseries(BaseModel):
    reservoir: str
    ref_date: datetime.date = Field(..., example=datetime.date(2022, 3, 12))
    timeseries: list[Level]


class ReservoirList(BaseModel):
    reservoirs: list[Reservoir]
