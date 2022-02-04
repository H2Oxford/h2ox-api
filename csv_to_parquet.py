#!/usr/bin/env python

from pathlib import Path
import pandas as pd


def load_csvs(glob, prep):
    return {
        f.stem.split("_")[0]: pd.read_csv(f, index_col=0, parse_dates=True).pipe(prep)
        for f in Path("data_raw").glob(glob)
    }


def prep_historic(df):
    return df.get(["volume_bcm", "tp_0"]).assign(volume_bcm=df.volume_bcm * 1000)


data = {
    "historic": load_csvs("*_historic.csv", prep_historic),
}

for typ, dfs in data.items():
    for res, df in dfs.items():
        df.round(2).rename_axis("date").to_parquet(f"data/{res}_{typ}.pq")
