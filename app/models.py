from pydantic import BaseModel, Field


class HTTPError(BaseModel):
    detail: str

    class Config:
        schema_extra = {
            "example": {"detail": "HTTPException raised."},
        }


class Message(BaseModel):
    message: str


class Level(BaseModel):
    name: str = Field(..., example="Harangi")
    level: float = Field(..., example=138)


class Prediction(BaseModel):
    date: str = Field(..., example="2022-11-02")
    level: float = Field(..., example=138)


class Historic(BaseModel):
    date: str = Field(..., example="2022-11-02")
    level: float = Field(..., example=138)
    precip: float = Field(..., example=2.4)
