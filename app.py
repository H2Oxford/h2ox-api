import os
from datetime import datetime as dt
from datetime import timedelta
from pathlib import Path

import pandas as pd
from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS


def load_csvs(glob):
    return {
        f.stem.split("_")[0]: pd.read_csv(f, index_col=0, parse_dates=True)
        for f in Path("data").glob(glob)
    }


dfs_forecast = load_csvs("*_forecast.csv")
dfs_historic = load_csvs("*_historic.csv")
dfs_prec = load_csvs("*_prec.csv")

for reservoir in dfs_historic.keys():
    dfs_historic[reservoir] = (
        dfs_historic[reservoir]
        .assign(x=lambda df: df.index.astype(str))
        .rename(columns={"PRESENT_STORAGE_TMC": "y"})
    )
    dfs_prec[reservoir] = (
        dfs_prec[reservoir]
        .assign(x=lambda df: df.index.astype(str))
        .rename(columns={"tp": "y"})
    )

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
    if reservoir is None or reservoir not in dfs_historic.keys():
        return jsonify({"error": f"specify a reservoir from {dfs_historic.keys()}"})
    date = request.args.get("date")
    try:
        date = dt.strptime(date, "%Y-%m-%d")
    except Exception as e:
        return jsonify({"error": f"specify a date as YYYY-MM-DD: {e}"})

    try:
        forecast = [
            {"x": str(date + timedelta(days=int(kk.split(" ")[0])))[0:10], "y": vv}
            for kk, vv in dfs_forecast[reservoir].loc[date, :].to_dict().items()
        ]
        forecast_up = [
            {
                "x": str(date + timedelta(days=int(kk.split(" ")[0])))[0:10],
                "y": vv * 1.2,
            }
            for kk, vv in dfs_forecast[reservoir].loc[date, :].to_dict().items()
        ]
        forecast_down = [
            {
                "x": str(date + timedelta(days=int(kk.split(" ")[0])))[0:10],
                "y": vv * 0.8,
            }
            for kk, vv in dfs_forecast[reservoir].loc[date, :].to_dict().items()
        ]
        historic = (
            dfs_historic[reservoir]
            .fillna(0)
            .loc[
                (dfs_historic[reservoir].index > (date - timedelta(days=history)))
                & (dfs_historic[reservoir].index <= (date + timedelta(days=1))),
                ["x", "y"],
            ]
            .to_dict(orient="records")
        )
        prec = (
            dfs_prec[reservoir]
            .fillna(0)
            .loc[
                (dfs_prec[reservoir].index > (date - timedelta(days=history)))
                & (dfs_prec[reservoir].index <= (date + timedelta(days=1))),
                ["x", "y"],
            ]
            .to_dict(orient="records")
        )

        data = {
            "prec": prec,
            "historic": historic,
            "forecast": forecast,
            "forecastUp": forecast_up,
            "forecastDown": forecast_down,
        }
        return jsonify(data)

    except Exception as e:
        print("Error!", e)
        return jsonify({"Error": f"bad request: {e}"})


if __name__ == "__main__":
    app.run()
