import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .data import get_reservoirs, get_prediction, get_historic, get_precip
from .models import HTTPError, PrecipTimeseries, LevelTimeseries, ReservoirList


app = FastAPI()

security = HTTPBasic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware)

USERNAME = os.environ["USERNAME"]
PASSWORD = os.environ["PASSWORD"]


def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


requires_auth = [Depends(authenticate)]
other_responses = {
    401: {"model": HTTPError, "description": "Unauthorized"},
    400: {"model": HTTPError, "description": "Parameter error"},
}


@app.get(
    "/",
    response_model=str,
)
async def index():
    return "API is running"


@app.get(
    "/api/reservoirs",
    dependencies=requires_auth,
    response_model=ReservoirList,
    responses=other_responses,
)
async def reservoirs():
    try:
        data = get_reservoirs()
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/api/prediction",
    dependencies=requires_auth,
    response_model=LevelTimeseries,
    responses=other_responses,
)
async def prediction(reservoir: str):
    try:
        data = get_prediction(reservoir=reservoir)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/api/historic",
    dependencies=requires_auth,
    response_model=LevelTimeseries,
    responses=other_responses,
)
async def historic(reservoir: str):
    try:
        data = get_historic(reservoir=reservoir)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/api/precip",
    dependencies=requires_auth,
    response_model=PrecipTimeseries,
    responses=other_responses,
)
async def precip(reservoir: str):
    try:
        data = get_precip(reservoir=reservoir)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
