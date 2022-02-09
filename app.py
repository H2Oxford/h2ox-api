import os
import json
import datetime as dt

from google.cloud import bigquery
from google.oauth2 import service_account
from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

bqclient = bigquery.Client(
    credentials=service_account.Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_CREDENTIALS"])
    )
)


def get_forecast(reservoir, ref_date):
    reservoir = reservoir.split(" ")[0]  # naive prevent any injection!
    query = f"""
    SELECT forecast FROM `oxeo-main.wave2web.prediction`
    WHERE `reservoir` = "{reservoir}"
    AND `date` = "{ref_date.date().isoformat()}"
    ORDER BY `timestamp` DESC
    LIMIT 1
    """
    job = bqclient.query(query)
    data = [row.values() for row in job][0][0]
    data = [
        {
            "x": ref_date + dt.timedelta(days=i),
            "y": val,
        }
        for i, val in enumerate(data)
    ]
    return data


def get_historic(reservoir, date, history):
    start_date = date - dt.timedelta(days=history)
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


@app.route("/api/timeseries")
@auth.login_required
def timeseries():
    reservoir = request.args.get("reservoir")
    history = int(request.args.get("history")) or 180
    date = request.args.get("date")

    try:
        date = dt.datetime.strptime(date, "%Y-%m-%d")
    except Exception as e:
        return jsonify({"error": f"specify a date as YYYY-MM-DD: {e}"})

    try:
        return jsonify(
            {
                "forecast": get_forecast(reservoir, date),
                "historic": get_historic(reservoir, date, history),
            }
        )
    except Exception as e:
        print("Error!", e)
        return jsonify({"Error": f"bad request: {e}"})


if __name__ == "__main__":
    app.run()
