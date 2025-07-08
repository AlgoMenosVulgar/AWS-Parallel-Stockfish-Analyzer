import pgn_utils as pu

import output  
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import os, time

# -- config lives ONLY here ---------------------------------------------------
ROOT            = Path(__file__).resolve().parent
PGN_PATH        = ROOT / "pgn"     / "lichess_tournament_2021.04.10_spring21_2021-spring-marathon.pgn"
CSV_PATH        = ROOT / "results" / "scores.csv"
STOCKFISH_PATH  = ROOT / "engine"  / "stockfish-windows-x86-64-avx2.exe"

DEPTH           = 12
HASH_MB         = 32
HEADERS_TO_KEEP = ["Date", "White", "Black", "WhiteElo", "BlackElo", "ECO"]
PROGRESS_EVERY  = 10

MAX_GAMES       = 50
MIN_WHITE_MOVES = 15
# ----------------------------------------------------------------------------

def main(): 
    t0 = time.time()

    games = pu.parse_pgn(
        PGN_PATH, HEADERS_TO_KEEP,
        MAX_GAMES, MIN_WHITE_MOVES
    )

    workers = max(1, round((os.cpu_count() or 2) / 2) - 1)
    chunks = pu.chunked(games, workers)

    all_results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(
                pu.analyse_chunk, chunk, wid+1,
                STOCKFISH_PATH, DEPTH, HASH_MB, PROGRESS_EVERY
            ): wid+1
            for wid, chunk in enumerate(chunks)
        }
        for fut in as_completed(future_map):
            wid = future_map[fut]
            all_results.extend(fut.result())
            print(f"✓ Chunk {wid}/{len(chunks)} done", flush=True)

    all_results.sort(key=lambda x: x[0])
    output.write_results(CSV_PATH, HEADERS_TO_KEEP, all_results)

    elapsed = time.time() - t0
    print(f"✅ Finished in {elapsed:.2f}s — {len(all_results)} games")

if __name__ == "__main__":
    main()
