import datetime as dt
import functools
import json
import os

import redis
from fastapi.encoders import jsonable_encoder
from google.cloud import bigquery
from google.oauth2 import service_account

from .models import Level, Reservoir, Timeseries, ReservoirList

bqclient = bigquery.Client(
    credentials=service_account.Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_CREDENTIALS"])
    )
)

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
REDIS_PW = os.environ.get("REDIS_PW", None)
CACHE_BUST = os.environ.get("REDIS_CACHE_BUST", False)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW)
redis_expiry = 60 * 60 * 24 * 2  # 2 days


def cache(prefix: str):
    def decorator_cache(func):
        @functools.wraps(func)
        def wrapper_cache(*args, **kwargs):
            if CACHE_BUST:
                data = func(*args, **kwargs)
            else:
                suffix = kwargs.get("reservoir", "")
                key = f"{prefix}.{suffix}"
                if data := r.get(key):
                    return json.loads(data)
                data = func(*args, **kwargs)
                r.set(key, json.dumps(jsonable_encoder(data)), ex=redis_expiry)
            return data

        return wrapper_cache

    return decorator_cache


@cache("forecast")
def get_prediction(*, reservoir: str) -> Timeseries:
    query = f"""
    SELECT date, forecast
    FROM `oxeo-main.wave2web.prediction`
    WHERE reservoir = "{reservoir}"
    ORDER BY date DESC, timestamp DESC
    LIMIT 1
    """
    job = bqclient.query(query)
    date, forecast = [row.values() for row in job][0]
    forecast = [
        Level(date=(date + dt.timedelta(days=i)).isoformat(), level=val)
        for i, val in enumerate(forecast)
    ]
    result = Timeseries(reservoir=reservoir, ref_date=date, timeseries=forecast)
    return result


@cache("historic")
def get_historic(*, reservoir: str) -> Timeseries:
    date = dt.datetime(2021, 9, 8)  # TODO this shouldn't be hardcoded
    start_date = date - dt.timedelta(days=365)
    query = f"""
    SELECT DATETIME, WATER_VOLUME * 1000
    FROM `oxeo-main.wave2web.reservoir-data`
    WHERE RESERVOIR_NAME = @reservoir
    AND DATETIME >= "{start_date.date().isoformat()}"
    AND DATETIME < "{date.date().isoformat()}"
    ORDER BY DATETIME
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("reservoir", "STRING", reservoir),
        ]
    )
    job = bqclient.query(query, job_config=job_config)
    historic = (row.values() for row in job)
    historic = [Level(date=row[0], level=row[1]) for row in historic]
    result = Timeseries(reservoir=reservoir, ref_date=date, timeseries=historic)
    return result


@cache("levels")
def get_reservoirs() -> ReservoirList:
    query = """
    SELECT
        historic.RESERVOIR_NAME,
        historic.DATETIME,
        historic.WATER_VOLUME * 1000,
    FROM (
        SELECT t1.RESERVOIR_NAME, t1.WATER_VOLUME, t1.DATETIME
        FROM `oxeo-main.wave2web.reservoir-data` t1
        WHERE t1.DATETIME = (
            SELECT MAX(t2.DATETIME)
            FROM `oxeo-main.wave2web.reservoir-data` t2
            WHERE t2.RESERVOIR_NAME = t1.RESERVOIR_NAME
        )
    ) AS historic
    """
    job = bqclient.query(query)
    data = [row.values() for row in job]
    result = ReservoirList(
        reservoirs=[
            Reservoir(name=row[0], level=Level(date=row[1], level=row[2]))
            for row in data
        ]
    )
    return result
