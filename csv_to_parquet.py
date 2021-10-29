#!/usr/bin/env python

from pathlib import Path
import pandas as pd
from random import uniform


def load_csvs(glob, prep):
    return {
        f.stem.split("_")[0]: pd.read_csv(f, index_col=0, parse_dates=True).pipe(prep)
        for f in Path("data_raw").glob(glob)
    }


def prep_forecast(df):
    return df * 1000


def conf(df, direc):
    s = 1 if direc == "up" else -1
    power = uniform(0.4, 0.4)
    growth = s * uniform(0.01, 0.013)
    noise = s * 0.001

    for i, col in enumerate(df.columns):
        df[col] = df[col] * (1 + (i ** power) * uniform(growth, growth + noise))

    return df.clip(lower=0) * 1000


def prep_up(df):
    return conf(df, "up")


def prep_down(df):
    return conf(df, "down")


def prep_historic(df):
    return df.get(["volume_bcm", "tp_0"]).assign(volume_bcm=df.volume_bcm * 1000)


data = {
    "forecast": load_csvs("*_forecast.csv", prep_forecast),
    "forecast_up": load_csvs("*_forecast_up.csv", prep_up),
    "forecast_down": load_csvs("*_forecast_down.csv", prep_down),
    "historic": load_csvs("*_historic.csv", prep_historic),
}

for typ, dfs in data.items():
    for res, df in dfs.items():
        df.round(2).rename_axis("date").to_parquet(f"data/{res}_{typ}.pq")
