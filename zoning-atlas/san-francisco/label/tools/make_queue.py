"""Build a hand-labelling queue for assets/label_reader.html.

Input: a CSV of candidates the automatic reader is unsure of, one row each:
  image   path to the source image (scan, sheet, page)
  x, y    candidate centre in image pixels
  w, h    candidate box size in pixels (the red box drawn on the crop)
  guess   the classifier's top answer (one of the codes, or X for "not a label")
  prob    its probability
  where   optional short text shown under the crop ("Sheet 3 · 1204, 880")
  flag    optional extra note ("in unlabelled land")
  + any further columns named with --key are stored with each answer, so the
    answer can be matched back to the candidate (e.g. sheet, px, py).

Writes into <out>/label_data/:
  queue_<set>.json   {set, codes, items:[{id, guess, prob, where, flag, key, sprite, col, row, cols, rows}]}
  <set>_sNN.jpg      sprite sheets of context crops (a publish takes at most 255 files)
  sets.json          every set with a queue in that folder

Order: code guesses before "not a label" guesses, the top --max surest kept,
then grouped by guessed code in --codes order, surest first within a code, so
the person labelling meets runs of the same answer and flips through quickly.
Item ids are <set>_<image stem>_<x>_<y>, so a rebuilt or reordered queue keeps
earlier answers attached.

Usage: python make_queue.py candidates.csv <set> <out_dir> --codes R-1,R-2,C-1 [--key sheet,px,py] [--max 400]
       [--ctx 600x384 for small patterns] [--labels 'R1=R1 hatch,...' button text]
       [--legend label_data/key_<set>.jpg: an image of the map's legend, shown above the crops]
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

THUMB_W, THUMB_H = 560, 358   # crop as shown on the page
SPRITE_COLS, SPRITE_N = 6, 60


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("set"); ap.add_argument("out")
    ap.add_argument("--codes", required=True)
    ap.add_argument("--key", default="")
    ap.add_argument("--max", type=int, default=400)
    ap.add_argument("--ctx", default="1000x640", help="context window in source px, WxH (keep the 560:358 shape)")
    ap.add_argument("--labels", default="", help="button text per code, e.g. 'R1=R1 hatch,C=C solid'")
    ap.add_argument("--legend", default="", help="legend image path as the page fetches it, e.g. label_data/key_1935p.jpg")
    a = ap.parse_args()
    codes = a.codes.split(",")
    ctx_w, ctx_h = (int(v) for v in a.ctx.lower().split("x"))
    labels = dict(kv.split("=", 1) for kv in a.labels.split(",") if "=" in kv)
    keys = [k for k in a.key.split(",") if k]
    out = Path(a.out) / "label_data"
    out.mkdir(parents=True, exist_ok=True)

    q = pd.read_csv(a.csv)
    q["id"] = [f"{a.set}_{Path(i).stem}_{int(round(x))}_{int(round(y))}" for i, x, y in zip(q.image, q.x, q.y)]
    q = q.drop_duplicates("id")
    q["code_guess"] = q.guess != "X"
    q = q.sort_values(["code_guess", "prob"], ascending=[False, False]).head(a.max)
    rank = {c: k for k, c in enumerate(codes)}
    q["rank"] = q.guess.map(rank).fillna(len(codes))
    q = q.sort_values(["rank", "prob"], ascending=[True, False])

    thumbs, items = {}, []
    for path, g in q.groupby("image", sort=False):
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        H, W = img.shape[:2]
        for r in g.itertuples():
            x0 = int(np.clip(r.x - ctx_w / 2, 0, max(0, W - ctx_w)))
            y0 = int(np.clip(r.y - ctx_h / 2, 0, max(0, H - ctx_h)))
            crop = img[y0:y0 + ctx_h, x0:x0 + ctx_w].copy()
            cv2.rectangle(crop, (int(r.x - r.w / 2 - x0 - 10), int(r.y - r.h / 2 - y0 - 10)),
                          (int(r.x + r.w / 2 - x0 + 10), int(r.y + r.h / 2 - y0 + 10)), (40, 40, 220), 4)
            thumbs[r.id] = cv2.resize(crop, (THUMB_W, THUMB_H), interpolation=cv2.INTER_AREA)
        del img
    for r in q.itertuples():
        items.append(dict(id=r.id, guess=r.guess, prob=round(float(r.prob), 2),
                          where=str(getattr(r, "where", "") or Path(r.image).stem),
                          flag=str(getattr(r, "flag", "") or "") if "flag" in q else "",
                          key={k: (v.item() if hasattr(v, "item") else v) for k, v in zip(keys, (getattr(r, k) for k in keys))}))

    for f in out.glob(f"{a.set}_s*.jpg"):
        f.unlink()
    rows = -(-SPRITE_N // SPRITE_COLS)
    for k in range(0, len(items), SPRITE_N):
        sheet = np.full((rows * THUMB_H, SPRITE_COLS * THUMB_W, 3), 255, np.uint8)
        name = f"{a.set}_s{k // SPRITE_N:02d}.jpg"
        for j, it in enumerate(items[k:k + SPRITE_N]):
            rr, cc = divmod(j, SPRITE_COLS)
            sheet[rr * THUMB_H:(rr + 1) * THUMB_H, cc * THUMB_W:(cc + 1) * THUMB_W] = thumbs[it["id"]]
            it.update(sprite=f"label_data/{name}", col=cc, row=rr, cols=SPRITE_COLS, rows=rows)
        cv2.imwrite(str(out / name), sheet, [cv2.IMWRITE_JPEG_QUALITY, 72])
    (out / f"queue_{a.set}.json").write_text(json.dumps({"set": a.set, "codes": codes, "labels": labels, "legend": a.legend, "items": items}))
    sets = sorted(f.stem.split("_", 1)[1] for f in out.glob("queue_*.json"))
    (out / "sets.json").write_text(json.dumps(sets))
    print(f"{a.set}: {len(items)} candidates queued, {int(q.code_guess.sum())} guessed as codes")


if __name__ == "__main__":
    main()
