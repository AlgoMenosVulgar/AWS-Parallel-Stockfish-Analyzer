import os
import sys
import time
import pathlib
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm  # For visually appealing progress bars

import chess
import chess.pgn
import chess.engine
import pandas as pd
from typing import List, Dict, Tuple, Any, Optional

# Specify exactly which PGN headers to include in the output
HEADERS_TO_KEEP = [    
    "Date",
    "White",
    "Black",
    "WhiteElo",
    "BlackElo",
    "ECO"    
]

# Global variables for the Stockfish engine instance and analysis limit.
ENGINE: Optional[chess.engine.SimpleEngine] = None
ENGINE_LIMIT: Optional[chess.engine.Limit] = None

def _cleanup_worker():
    """
    Cleanup function registered with atexit in each worker process to ensure
    the Stockfish engine subprocess is terminated.
    """
    global ENGINE
    try:
        if ENGINE:
            ENGINE.quit()
    except Exception:
        pass
    finally:
        ENGINE = None

def _init_worker(stockfish_path: str, hash_mb: int, depth: int) -> None:
    """
    Initialization function for each worker process in the multiprocessing pool.
    """
    global ENGINE, ENGINE_LIMIT
    import atexit
    atexit.register(_cleanup_worker)

    try:
        ENGINE = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        ENGINE.configure({"Threads": 1, "Hash": hash_mb})
        ENGINE_LIMIT = chess.engine.Limit(depth=depth)
    except Exception as e:
        print(f"[ERROR] Worker failed to initialize Stockfish engine: {e}", file=sys.stderr)
        ENGINE = None
        ENGINE_LIMIT = None

def _analyse_game(payload: Tuple[int, Dict[str, str], List[str]]) -> Dict[str, Any]:
    """
    Worker function that performs the analysis of a single chess game.
    Only keeps raw Scores and specified headers.
    """
    game_index, headers, fens = payload
    # Filter headers to only those we want
    filtered = {key: headers.get(key, None) for key in HEADERS_TO_KEEP}

    result_dict: Dict[str, Any] = {
        "Game_Index": game_index,
        **filtered,
        "Scores": [],
        "error": None,
    }

    if ENGINE is None or ENGINE_LIMIT is None:
        result_dict["error"] = "Stockfish engine not initialized in worker."
        return result_dict

    scores: List[int] = []
    try:
        for fen in fens:
            board = chess.Board(fen)
            if board.is_game_over():
                outcome = board.outcome()
                if outcome:
                    if outcome.result() == "1-0":
                        scores.append(10000)
                    elif outcome.result() == "0-1":
                        scores.append(-10000)
                    else:
                        scores.append(0)
                else:
                    scores.append(0)
            else:
                info = ENGINE.analyse(board, ENGINE_LIMIT)
                cp = info["score"].pov(chess.WHITE).score(mate_score=10000)
                scores.append(cp if cp is not None else 0)
    except Exception as e:
        result_dict["error"] = f"Exception during analysis: {e}"
        return result_dict

    # Only keep raw scores
    result_dict["Scores"] = scores
    return result_dict

# def build_payloads(pgn_path: pathlib.Path) -> List[Tuple[int, Dict[str, str], List[str]]]:
#     """
#     Parses a PGN file and constructs payloads for each game.
#     """
#     payloads: List[Tuple[int, Dict[str, str], List[str]]] = []
#     try:
#         with open(pgn_path, "r", encoding="utf-8", errors="ignore") as pgn_file:
#             idx = 1
#             while True:
#                 game = chess.pgn.read_game(pgn_file)
#                 if game is None:
#                     break
#                 headers = dict(game.headers)
#                 board = game.board()
#                 fens = [board.fen()]
#                 for move in game.mainline_moves():
#                     board.push(move)
#                     fens.append(board.fen())
#                 payloads.append((idx, headers, fens))
#                 idx += 1
#     except Exception as e:
#         print(f"[ERROR] Failed to parse PGN file: {e}", file=sys.stderr)
#     return payloads

def build_payloads(pgn_path: pathlib.Path) -> List[Tuple[int, Dict[str, str], List[str]]]:
    payloads: List[Tuple[int, Dict[str, str], List[str]]] = []
    try:
        with pgn_path.open(encoding="utf-8", errors="ignore") as pgn:
            for idx, game in enumerate(iter(lambda: chess.pgn.read_game(pgn), None), 1):
                board = game.board()
                fens = [board.fen()]
                push, fen = board.push, board.fen           # local bindings shave look-ups
                for mv in game.mainline_moves():
                    push(mv); fens.append(fen())
                payloads.append((idx, dict(game.headers), fens))
    except Exception as e:
        print(f"[ERROR] build_payloads: {e}", file=sys.stderr)

    return payloads


# def run_parallel_analysis(
#         payloads       : List[Tuple[int, Dict[str, str], List[str]]],
#         stockfish_path : pathlib.Path,
#         depth          : int,
#         hash_mb        : int,
#         workers        : int
#     ) -> List[Dict[str, Any]]:
#     """
#     Manages the parallel execution of game analysis tasks using a ProcessPoolExecutor.
#     """
#     all_results: List[Dict[str, Any]] = []
#     total_games = len(payloads)
#     if total_games == 0:
#         print("No game payloads to analyze. Skipping parallel analysis.", file=sys.stderr)
#         return []

#     print(f"[DEBUG] About to start ProcessPoolExecutor with {workers} workers")
#     with ProcessPoolExecutor(
#             max_workers=workers,
#             initializer=_init_worker,
#             initargs=(str(stockfish_path), hash_mb, depth)
#         ) as pool:

#         print(f"[DEBUG] Created executor, submitting {total_games} tasks")
#         futures = {pool.submit(_analyse_game, p): p for p in payloads}

#         print(f"[DEBUG] All tasks submitted, waiting for completion")
#         completed_count = 0
#         for future in tqdm(as_completed(futures), total=total_games, desc="Analyzing games"):
#             try:
#                 result = future.result(timeout=300)
#                 completed_count += 1
#                 print(f"[DEBUG] Completed task {completed_count}/{total_games}")
#                 if result.get("error"):
#                     print(f"\n⚠️  Game {result.get('Game_Index','?')} failed: {result['error']}", file=sys.stderr)
#                 else:
#                     all_results.append(result)
#             except Exception as e:
#                 print(f"\n❌ Unexpected error retrieving result: {e}", file=sys.stderr)
#                 import traceback; traceback.print_exc(file=sys.stderr)

#         print(f"[DEBUG] All tasks completed, cleaning up engine processes...")
#         try:
#             import psutil
#             for proc in psutil.process_iter(['name']):
#                 if proc.info['name'] and 'stockfish' in proc.info['name'].lower():
#                     proc.kill()
#         except ImportError:
#             os.system(f"taskkill /f /im {stockfish_path.name} /T >nul 2>&1")
#         except Exception as kill_e:
#             print(f"[DEBUG] Error killing Stockfish processes: {kill_e}", file=sys.stderr)

#     print(f"[DEBUG] Executor shutdown cleanly, {len(all_results)} results collected")
#     time.sleep(2)
#     return all_results

def run_parallel_analysis(
        payloads       : List[Tuple[int, Dict[str, str], List[str]]],
        stockfish_path : pathlib.Path,
        depth          : int,
        hash_mb        : int,
        workers        : int
    ) -> List[Dict[str, Any]]:
    """
    Manages the parallel execution of game analysis tasks using a ProcessPoolExecutor.
    """
    all_results: List[Dict[str, Any]] = []
    total_games = len(payloads)
    if total_games == 0:
        print("No game payloads to analyze. Skipping parallel analysis.", file=sys.stderr)
        return []

    print(f"[DEBUG] About to start ProcessPoolExecutor with {workers} workers")
    with ProcessPoolExecutor(
            max_workers=workers,
            initializer=_init_worker,
            initargs=(str(stockfish_path), hash_mb, depth)
        ) as pool:

        print(f"[DEBUG] Created executor, submitting {total_games} tasks")
        futures = {pool.submit(_analyse_game, p): p for p in payloads}

        print(f"[DEBUG] All tasks submitted, waiting for completion")
        completed_count = 0
        for future in as_completed(futures): # Removed tqdm
            try:
                result = future.result(timeout=300)
                completed_count += 1
                # Print just the count
                print(f"{completed_count}", end=" ", flush=True) # Added end=" " and flush=True
                if result.get("error"):
                    print(f"\n⚠️  Game {result.get('Game_Index','?')} failed: {result['error']}", file=sys.stderr)
                else:
                    all_results.append(result)
            except Exception as e:
                print(f"\n❌ Unexpected error retrieving result: {e}", file=sys.stderr)
                import traceback; traceback.print_exc(file=sys.stderr)

        print("\n[DEBUG] All tasks completed, cleaning up engine processes...") # Newline after printing counts
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and 'stockfish' in proc.info['name'].lower():
                    proc.kill()
        except ImportError:
            os.system(f"taskkill /f /im {stockfish_path.name} /T >nul 2>&1")
        except Exception as kill_e:
            print(f"[DEBUG] Error killing Stockfish processes: {kill_e}", file=sys.stderr)

    print(f"[DEBUG] Executor shutdown cleanly, {len(all_results)} results collected")
    time.sleep(2)
    return all_results