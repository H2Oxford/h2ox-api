import datetime as dt
import functools
import json
import os

import redis
import shapely.wkt
from fastapi.encoders import jsonable_encoder
from google.cloud import bigquery
from google.oauth2 import service_account

from .models import (
    Level,
    Precip,
    Geometry,
    Reservoir,
    PrecipTimeseries,
    ReservoirList,
    LevelTimeseries,
)

bqclient = bigquery.Client(
    credentials=service_account.Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_CREDENTIALS"])
    )
)

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
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
                suffix = "".join([f"{k}={v}_" for k, v in kwargs.items()])
                key = f"{prefix}.{suffix}"
                if data := r.get(key):
                    return json.loads(data)
                data = func(*args, **kwargs)
                r.set(key, json.dumps(jsonable_encoder(data)), ex=redis_expiry)
            return data

        return wrapper_cache

    return decorator_cache


@cache("prediction")
def get_prediction(*, reservoir: str) -> LevelTimeseries:
    query = """
    SELECT date, forecast
    FROM `oxeo-main.wave2web.prediction`
    WHERE reservoir = @reservoir
    ORDER BY date DESC, timestamp DESC
    LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("reservoir", "STRING", reservoir),
        ]
    )
    job = bqclient.query(query, job_config=job_config)
    date, forecast = [row.values() for row in job][0]
    forecast = [
        # convert from BCM to MCM
        Level(
            date=(date + dt.timedelta(days=i)).isoformat(), value=val * 1000, baseline=0
        )
        for i, val in enumerate(forecast)
    ]
    result = LevelTimeseries(reservoir=reservoir, ref_date=date, timeseries=forecast)
    return result


@cache("historic")
def get_historic(*, reservoir: str) -> LevelTimeseries:
    query = """
    WITH
    baseline AS (
        SELECT
            EXTRACT(DAYOFYEAR from DATETIME) AS doy,
            AVG(WATER_VOLUME) AS baseline_value
        FROM `oxeo-main.wave2web.reservoir-data`
        WHERE RESERVOIR_NAME = @reservoir
        GROUP BY EXTRACT(DAYOFYEAR from DATETIME)
    )

    SELECT
        DATETIME AS date,
        WATER_VOLUME * 1000 AS value,
        ROUND(baseline.baseline_value * 1000) AS baseline_value,
    FROM `oxeo-main.wave2web.reservoir-data`

    INNER JOIN baseline
    ON baseline.doy=EXTRACT(DAYOFYEAR from DATETIME)

    WHERE RESERVOIR_NAME = @reservoir
    ORDER BY DATETIME DESC
    LIMIT 365
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("reservoir", "STRING", reservoir),
        ]
    )
    job = bqclient.query(query, job_config=job_config)
    historic = [
        Level(date=row[0], value=row[1], baseline=row[2])
        for row in (row.values() for row in job)
    ]
    ref_date = historic[0].date
    result = LevelTimeseries(
        reservoir=reservoir, ref_date=ref_date, timeseries=historic
    )
    return result


@cache("precip")
def get_precip(*, reservoir: str) -> PrecipTimeseries:
    query = """
    WITH
    cum AS (
        SELECT
            date AS cum_date,
            SUM(value) OVER (PARTITION BY EXTRACT(YEAR from date) ORDER BY date) AS cum_value
        FROM `oxeo-main.wave2web.precipitation`
        WHERE reservoir = @reservoir
    ),
    avg_cum AS (
        SELECT
            EXTRACT(DAYOFYEAR from cum_date) AS doy,
            AVG(cum_value) AS avg_cum_value
        FROM cum
        GROUP BY EXTRACT(DAYOFYEAR from cum_date)
    )

    SELECT
        date,
        ROUND(value, 3) AS value,
        ROUND(cum.cum_value, 3) AS cum_value,
        ROUND(avg_cum.avg_cum_value, 3) AS avg_cum_value
    FROM `oxeo-main.wave2web.precipitation`

    INNER JOIN avg_cum
    ON avg_cum.doy=EXTRACT(DAYOFYEAR from date)

    INNER JOIN cum
    ON cum.cum_date=date

    WHERE reservoir = @reservoir
    ORDER BY date DESC
    LIMIT 365
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("reservoir", "STRING", reservoir),
        ]
    )
    job = bqclient.query(query, job_config=job_config)
    historic = [
        Precip(date=row[0], value=row[1], cumulative=row[2], cumulative_baseline=row[3])
        for row in (row.values() for row in job)
    ]
    ref_date = historic[0].date
    result = PrecipTimeseries(
        reservoir=reservoir, ref_date=ref_date, timeseries=historic
    )
    return result


@cache("reservoirs")
def get_reservoirs(*, include_geoms: bool = True) -> ReservoirList:
    query = """
    WITH
    historic AS (
        SELECT
            RESERVOIR_NAME,
            DATETIME,
            WATER_VOLUME,
            FULL_WATER_LEVEL
        FROM `oxeo-main.wave2web.reservoir-data` AS r1
        WHERE DATETIME = (
            SELECT MAX(DATETIME)
            FROM `oxeo-main.wave2web.reservoir-data` AS r2
            WHERE r1.RESERVOIR_NAME = r2.RESERVOIR_NAME
        )
        ORDER BY RESERVOIR_NAME, DATETIME
    )

    SELECT
        DISTINCT(pred.reservoir),
        historic.DATETIME,
        historic.WATER_VOLUME * 1000,
        historic.FULL_WATER_LEVEL,
        tracked.lake_geom
    FROM
        `oxeo-main.wave2web.prediction` AS pred

    INNER JOIN `oxeo-main.wave2web.tracked-reservoirs` AS tracked
    ON pred.reservoir=tracked.name

    INNER JOIN historic
    ON pred.reservoir=historic.RESERVOIR_NAME
    """
    job = bqclient.query(query)
    data = [row.values() for row in job]
    result = ReservoirList(
        reservoirs=[
            Reservoir(
                name=row[0],
                level=Level(date=row[1], value=row[2], baseline=0),
                full_level=row[3],
                geom=Geometry(**shapely.wkt.loads(row[4]).__geo_interface__)
                if include_geoms
                else None,
            )
            for row in data
        ]
    )
    return result
