import datetime as dt

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .data import get_levels, get_reservoir_list, get_prediction, get_historic


app = FastAPI()
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


@app.get("/")
def index():
    return "API is running"


@app.get("/api/levels")
def levels():
    levels = get_levels()
    return levels


@app.get("/api/predictions")
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


@app.get("/api/prediction")
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


@app.get("/api/historic")
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
