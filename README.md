# Parallel Stockfish PGN Analysis

Evaluate large collections of chess games in **parallel** with the Stockfish
engine and export centipawn scores to a tidy CSV file.

## Contents

```
├── main.py          # orchestrates parsing, multiprocessing and CSV export
├── pgn_utils.py     # helpers for PGN reading, chunking and engine calls
├── output.py        # writes aggregated results to disk
└── requirement.txt  # Python dependency pin (this file)
```

## Prerequisites

| Requirement        | Notes                                                         |
|--------------------|---------------------------------------------------------------|
| Python ≥ 3.9       | `concurrent.futures` & `pathlib` are part of the stdlib       |
| Stockfish engine   | Grab a recent binary <https://stockfishchess.org/download>    |
| `python-chess`     | Installed via **pip** – wraps PGN/engine communication        |

## Installation

```bash
# 1. Clone / download the sources
cd your-project-folder

# 2. Set up a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install the single Python dependency
pip install -r requirement.txt
```

**Tip:**  Feel free to pin `python-chess` to an exact version once your
workflow is stable.

## Quick start

1. Place a `.pgn` file inside the **pgn/** directory (or adjust the path in
   `main.py`).
2. Download the Stockfish binary that matches your OS/CPU and point
   `STOCKFISH_PATH` in `main.py` to it.
3. Run:

```bash
python main.py
```

The script will:

* Parse each game, discarding those with fewer than the configured white
  moves.
* Spawn roughly **(CPU‑cores/2 − 1)** worker processes and split the games
  evenly between them.
* Query Stockfish at a fixed depth for **every single ply** (white & black)
  in every kept game.
* Dump a **scores.csv** to the **results/** folder containing:

  | Column        | Description                               |
  |---------------|-------------------------------------------|
  | `GameIndex`   | Sequential index in parsing order         |
  | PGN headers   | `Date`, `White`, `Black`, Elo, `ECO`, …   |
  | `Scores`      | JSON‑encoded list of centipawn evaluations|

Progress for each worker is printed as it goes, so you can keep an eye on
longue analyses.

## Customising the run

* **Depth / Hash size** – tweak `DEPTH` and `HASH_MB` in `main.py`.
* **Filters** – `MAX_GAMES`, `MIN_WHITE_MOVES`, and `HEADERS_TO_KEEP`.
* **CPU usage** – edit the formula that sets `workers` if you want full
  saturation or a single‑threaded run.

## Performance notes

* With light PGNs (few moves) and modern CPUs, disk I/O tends to dominate.
* If you hit diminishing returns, try raising the chunk size or pinning each
  worker to a physical core.
* For millions of positions, persisting intermediate results per chunk can
  avoid data loss on crashes.

---
