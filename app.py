import os
import json
import datetime as dt
from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

bqclient = bigquery.Client(
    credentials=service_account.Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_CREDENTIALS"])
    )
)


def load_parquets(glob):
    return {f.stem.split("_")[0]: pd.read_parquet(f) for f in Path("data").glob(glob)}


def prep_historic(dfs, y_col):
    return {
        k: df.assign(x=lambda df: df.index.astype(str)).rename(columns={y_col: "y"})
        for k, df in dfs.items()
    }


def get_forecast(reservoir, ref_date):
    reservoir = reservoir.split(" ")[0]  # naive prevent any injection!
    query = f"""
    SELECT forecast FROM `oxeo-main.wave2web.h2ox-forecast`
    WHERE `reservoir` = "{reservoir}"
    AND `date` = "{ref_date.date().isoformat()}"
    ORDER BY `timestamp` DESC
    LIMIT 1
    """
    job = bqclient.query(query)
    data = [row.values() for row in job][0][0]
    data = [
        {"x": ref_date + dt.timedelta(days=i), "y": val} for i, val in enumerate(data)
    ]
    return data


def historic2dict(dfs, reservoir, date, history):
    return (
        dfs[reservoir]
        .fillna(0)
        .loc[
            (dfs[reservoir].index > (date - dt.timedelta(days=history)))
            & (dfs[reservoir].index <= (date + dt.timedelta(days=1))),
            ["x", "y"],
        ]
        .to_dict(orient="records")
    )


dfs_historic = load_parquets("*_historic.pq")
dfs_historic = prep_historic(dfs_historic, y_col="volume_bcm")
dfs_prec = prep_historic(dfs_historic, y_col="tp_0")

app = Flask(__name__)
auth = HTTPBasicAuth()
CORS(app)
users = {os.environ["USERNAME"]: generate_password_hash(os.environ["USERPASSWORD"])}


@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username


@app.route("/api/")
@auth.login_required
def index():
    reservoir = request.args.get("reservoir")
    history = int(request.args.get("history")) or 180
    date = request.args.get("date")

    if reservoir is None or reservoir not in dfs_historic.keys():
        return jsonify({"error": f"specify a reservoir from {dfs_historic.keys()}"})
    try:
        date = dt.datetime.strptime(date, "%Y-%m-%d")
    except Exception as e:
        return jsonify({"error": f"specify a date as YYYY-MM-DD: {e}"})

    try:
        return jsonify(
            {
                "forecast": get_forecast(reservoir, date),
                "historic": historic2dict(dfs_historic, reservoir, date, history),
                "prec": historic2dict(dfs_prec, reservoir, date, history),
            }
        )
    except Exception as e:
        print("Error!", e)
        return jsonify({"Error": f"bad request: {e}"})


if __name__ == "__main__":
    app.run()
