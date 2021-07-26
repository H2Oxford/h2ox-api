#!/usr/bin/env python

from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

res = {}
for f in Path("data").glob("*_forecast.csv"):
    name = f.stem.split("_")[0]
    df = pd.read_csv(f, index_col=0)
    use = ["2020-01-01", "2020-04-01", "2020-07-01"]
    vals = df.loc[df.index.isin(use)]
    res[name] = {}
    for idx, row in vals.iterrows():
        row.index = [
            (
                datetime.strptime(idx, "%Y-%m-%d")
                + timedelta(days=int(x.split(" ")[0]))
            ).strftime("%Y-%m-%d")
            for x in row.index.tolist()
        ]
        row = pd.DataFrame(row).reset_index()
        row.columns = ["x", "y"]
        res[name][idx] = row.to_dict(orient="records")

print(f"const forecast = {res}")
