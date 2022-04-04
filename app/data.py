import datetime as dt
import functools
import json
import os

import redis
from google.cloud import bigquery
from google.oauth2 import service_account

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


def cache(prefix):
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
                r.set(key, json.dumps(data), ex=redis_expiry)
            return data

        return wrapper_cache

    return decorator_cache


@cache("reservoirs")
def get_reservoir_list():
    query = """
    SELECT DISTINCT(reservoir) FROM `oxeo-main.wave2web.prediction`
    """
    job = bqclient.query(query)
    data = [row.values()[0] for row in job]
    return data


@cache("forecast")
def get_prediction(*, reservoir, date):
    reservoir = reservoir.split(" ")[0]  # naive prevent any injection!
    query = f"""
    SELECT forecast FROM `oxeo-main.wave2web.prediction`
    WHERE `reservoir` = "{reservoir}"
    AND `date` = "{date.date().isoformat()}"
    ORDER BY `timestamp` DESC
    LIMIT 1
    """
    job = bqclient.query(query)
    data = [row.values() for row in job][0][0]
    data = [
        {
            "x": (date + dt.timedelta(days=i)).isoformat(),
            "y": val,
        }
        for i, val in enumerate(data)
    ]
    return data


@cache("historic")
def get_historic(*, reservoir, date):
    start_date = date - dt.timedelta(days=365)
    query = f"""
    SELECT DATETIME, WATER_VOLUME * 1000 FROM `oxeo-main.wave2web.reservoir-data`
    WHERE `RESERVOIR_NAME` = "{reservoir}"
    AND `DATETIME` >= "{start_date.date().isoformat()}"
    AND `DATETIME` < "{date.date().isoformat()}"
    ORDER BY `DATETIME`
    """
    job = bqclient.query(query)
    data = (row.values() for row in job)
    data = [
        {
            "x": row[0].isoformat(),
            "volume": row[1],
            "precip": 0,
        }
        for row in data
    ]
    return data


@cache("levels")
def get_levels():
    query = """
    SELECT
        historic.RESERVOIR_NAME,
        historic.WATER_VOLUME * 1000,
    FROM (
        SELECT t1.RESERVOIR_NAME, t1.WATER_VOLUME
        FROM `oxeo-main.wave2web.reservoir-data` t1
        WHERE t1.DATETIME = (
            SELECT MAX(t2.DATETIME)
            FROM `oxeo-main.wave2web.reservoir-data` t2
            WHERE t2.RESERVOIR_NAME = t1.RESERVOIR_NAME
        )
    ) AS historic
    """
    job = bqclient.query(query)
    data = [dict(row) for row in job]
    return data
