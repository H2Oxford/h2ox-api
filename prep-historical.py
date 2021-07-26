#!/usr/bin/env python

from pathlib import Path

import pandas as pd

text = ""
for f in Path("data").glob("*_historic.csv"):
    print(f.stem)
    df = pd.read_csv(f).dropna()
    df.columns = ["x", "y"]
    text += "const " + f.stem + " = "
    text += df.to_json(orient="records")
    text += "\n"

print(text)
