# District Label Reader

The page people used to read map labels by hand for the San Francisco zoning
atlas, kept with its crops and answers. It is also the starting point for
future label readers, including crowdsourced ones.

Each card shows a crop from a scanned map with the candidate boxed in red. The
reader presses a key for the district, and the next card comes up. Queues are
grouped by guessed code, so runs of the same answer go quickly.

## What is here

- `index.html`: the page. On this site it shows the saved answers, read-only.
- `label_data/`: `sets.json`, one `queue_<set>.json` per batch, and the crops as
  sprite sheets of 60.
- `answers.csv`: every answer with its set, guess, time and map position.
- `answers.json`: the same answers as item id to code, which the page reads.
- `tools/make_queue.py`: turns a CSV of candidates into crops and a queue.
- `tools/fetch_answers.py`: turns saved answers into one CSV per set.
- `tools/label_reader_template.html`: the page before project edits.

## Answer codes

A district code, `X`, or `?` ("can't tell"). `X` means "not a label" on the
label sets. On the `fill*` sets it means "no label in the box": those blocks
keep an inferred district. It does not mean the block has no district.

## Item ids

`<set>_<image>_<x>_<y>`. They stay the same when a queue is rebuilt or
reordered, so answers stay attached to their crops.

## Adapting it for crowdsourcing

The queue format, crops and keyboard flow can be reused. These parts change:

- **Saving answers.** The page saved to a private claude.ai database. A public
  version needs its own backend, one row per person per item.
- **Agreement.** Show each item to several people, and accept a code once enough
  of them agree. Send disagreements to an expert.
- **Quality checks.** Mix in items whose answer is known, and weight or drop
  people who miss them.
- **Abuse.** Rate-limit submissions and never let one person's answers decide an item.
- **Button wording.** Give each answer one meaning, on the button itself. `X`
  carried two meanings here and had to be clarified after the fact.
