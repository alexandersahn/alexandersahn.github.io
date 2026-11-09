"""Answers from a label reader page into one CSV per set.

The page stores one db document per answer in collection "labels":
{set, <key fields>, code, guess, at}. Save them first with the ArtifactData
tool (action "list", collection "labels", query.limit 1000, out_dir <dir>;
follow next_cursor with the same out_dir until it is absent), then run this.
"?" ("can't tell") answers are dropped; X ("not a label") answers are kept,
since they are useful negative training examples. If an output CSV exists,
answers at the same key are replaced by the newer one.

Usage: python fetch_answers.py <out_dir from ArtifactData> <dest_dir> [--key sheet,px,py]
Writes <dest_dir>/hand_labels_<set>.csv with the key columns plus label.
"""
import argparse
import json
from pathlib import Path

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dest")
    ap.add_argument("--key", default="")
    a = ap.parse_args()
    keys = [k for k in a.key.split(",") if k]
    rows = []
    for f in Path(a.src).rglob("*.json"):
        d = json.loads(f.read_text())
        d = d.get("data", d)
        if d.get("code") and d["code"] != "?":
            rows.append({"set": str(d.get("set", d.get("year"))), **{k: d.get(k) for k in keys}, "label": d["code"]})
    df = pd.DataFrame(rows)
    if df.empty:
        print("no answers")
        return
    Path(a.dest).mkdir(parents=True, exist_ok=True)
    for s, g in df.groupby("set"):
        out = Path(a.dest) / f"hand_labels_{s}.csv"
        g = g.drop(columns="set")
        if out.exists() and keys:
            old = pd.read_csv(out)
            new_keys = set(map(tuple, g[keys].astype(str).to_numpy()))
            old = old[[tuple(r) not in new_keys for r in old[keys].astype(str).to_numpy()]]
            g = pd.concat([old, g], ignore_index=True)
        g.to_csv(out, index=False)
        print(f"{s}: {len(g)} answers ({(g.label != 'X').sum()} codes, {(g.label == 'X').sum()} not labels)")


if __name__ == "__main__":
    main()
