import datetime as dt
import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .data import get_levels, get_reservoir_list, get_prediction, get_historic


app = FastAPI()

security = HTTPBasic()

origins = [
    "http://localhost:3000",
    "https://h2ox.org/",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
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


@app.get("/")
def index() -> str:
    return "API is running"


@app.get("/api/levels", dependencies=requires_auth)
def levels():
    levels = get_levels()
    return levels


@app.get("/api/predictions", dependencies=requires_auth)
def predictions(date: str):
    try:
        date = dt.datetime.strptime(date, "%Y-%m-%d")
    except Exception as e:
        return {"error": f"specify a date as YYYY-MM-DD: {e}"}

    try:
        reservoirs = get_reservoir_list()
        data = [
            {"reservoir": res, "prediction": get_prediction(reservoir=res, date=date)}
            for res in reservoirs
        ]
        return data
    except Exception as e:
        print("Error!", e)
        return {"Error": f"bad request: {e}"}


@app.get("/api/prediction", dependencies=requires_auth)
def prediction(reservoir: str, date: str):
    try:
        date = dt.datetime.strptime(date, "%Y-%m-%d")
    except Exception as e:
        return {"error": f"specify a date as YYYY-MM-DD: {e}"}

    try:
        return get_prediction(reservoir=reservoir, date=date)
    except Exception as e:
        print("Error!", e)
        return {"Error": f"bad request: {e}"}


@app.get("/api/historic", dependencies=requires_auth)
def historic(reservoir: str, date: str):
    try:
        date = dt.datetime.strptime(date, "%Y-%m-%d")
    except Exception as e:
        return {"error": f"specify a date as YYYY-MM-DD: {e}"}

    try:
        return get_historic(reservoir=reservoir, date=date)
    except Exception as e:
        print("Error!", e)
        return {"Error": f"bad request: {e}"}
