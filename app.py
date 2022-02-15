import os
import datetime as dt
import functools
import json

from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_cors import CORS
from google.cloud import bigquery
from google.oauth2 import service_account
import redis
from werkzeug.security import generate_password_hash, check_password_hash

bqclient = bigquery.Client(
    credentials=service_account.Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_CREDENTIALS"])
    )
)

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
REDIS_PW = os.environ.get("REDIS_PW", None)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW)
redis_expiry = 60 * 60 * 24 * 2  # 2 days


def cache(prefix):
    def decorator_cache(func):
        @functools.wraps(func)
        def wrapper_cache(*args, **kwargs):
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
def get_forecast(*, reservoir, date):
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
    SELECT date, volume, precip FROM `oxeo-main.wave2web.historic`
    WHERE `reservoir` = "{reservoir}"
    AND `date` >= "{start_date.date().isoformat()}"
    AND `date` < "{date.date().isoformat()}"
    ORDER BY `date`
    """
    job = bqclient.query(query)
    data = (row.values() for row in job)
    data = [
        {
            "x": row[0].isoformat(),
            "volume": row[1],
            "precip": row[2],
        }
        for row in data
    ]
    return data


@cache("levels")
def get_levels():
    query = """
    SELECT
        historic.reservoir,
        historic.volume,
        prediction.forecast[
            ORDINAL(ARRAY_LENGTH(prediction.forecast))
        ] as forecast

    FROM (
        SELECT t1.reservoir, t1.volume
        FROM `oxeo-main.wave2web.historic` t1
        WHERE t1.date = (
            SELECT MAX(t2.date)
            FROM `oxeo-main.wave2web.historic` t2
            WHERE t2.reservoir = t1.reservoir
        )
    ) AS historic

    JOIN (
        SELECT t1.reservoir, t1.forecast
        FROM `oxeo-main.wave2web.prediction` t1
        WHERE t1.date = (
            SELECT MAX(t2.date)
            FROM `oxeo-main.wave2web.prediction` t2
            WHERE t2.reservoir = t1.reservoir
        )
    ) AS prediction

    ON historic.reservoir = prediction.reservoir
    """
    job = bqclient.query(query)
    data = [dict(row) for row in job]
    return data


app = Flask(__name__)
auth = HTTPBasicAuth()
CORS(app)
users = {os.environ["USERNAME"]: generate_password_hash(os.environ["USERPASSWORD"])}


@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username


@app.route("/")
def index():
    return "API is running"


@app.route("/api/levels")
@auth.login_required
def levels():
    levels = get_levels()
    return jsonify(levels)


@app.route("/api/forecasts")
@auth.login_required
def forecasts():
    date = request.args.get("date")

    try:
        date = dt.datetime.strptime(date, "%Y-%m-%d")
    except Exception as e:
        return jsonify({"error": f"specify a date as YYYY-MM-DD: {e}"})

    try:
        reservoirs = get_reservoir_list()
        data = [
            {"reservoir": res, "forecast": get_forecast(reservoir=res, date=date)}
            for res in reservoirs
        ]
        return jsonify(data)
    except Exception as e:
        print("Error!", e)
        return jsonify({"Error": f"bad request: {e}"})


@app.route("/api/forecast")
@auth.login_required
def forecast():
    reservoir = request.args.get("reservoir")
    date = request.args.get("date")

    try:
        date = dt.datetime.strptime(date, "%Y-%m-%d")
    except Exception as e:
        return jsonify({"error": f"specify a date as YYYY-MM-DD: {e}"})

    try:
        return jsonify(get_forecast(reservoir=reservoir, date=date))
    except Exception as e:
        print("Error!", e)
        return jsonify({"Error": f"bad request: {e}"})


@app.route("/api/historic")
@auth.login_required
def historic():
    reservoir = request.args.get("reservoir")
    date = request.args.get("date")

    try:
        date = dt.datetime.strptime(date, "%Y-%m-%d")
    except Exception as e:
        return jsonify({"error": f"specify a date as YYYY-MM-DD: {e}"})

    try:
        return jsonify(get_historic(reservoir=reservoir, date=date))
    except Exception as e:
        print("Error!", e)
        return jsonify({"Error": f"bad request: {e}"})


if __name__ == "__main__":
    app.run()
