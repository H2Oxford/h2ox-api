#!/usr/bin/env python

from pathlib import Path

import pandas as pd

res = {}
for f in Path("data").glob("*_historic.csv"):
    name = f.stem.split("_")[0]
    df = pd.read_csv(f).dropna()
    df.columns = ["x", "y"]
    res[name] = df.to_dict(orient="records")

print(f"const historic = {res}")
