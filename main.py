#!/usr/bin/env python3
# Parallel PGN analysis with Stockfish — fully descriptive identifiers

import argparse, multiprocessing as mp, pathlib, sys, time

from pgn_utils import (
    build_payloads,
    run_parallel_analysis,
)

from output import (
    results_to_dataframe,
    save_dataframe
)

# ───────────────────────────────────────────────────────────────────────────────
# 1. PATHS
# ───────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT_DIRECTORY = pathlib.Path(__file__).resolve().parent
DEFAULT_PGN_FILE_PATH = PROJECT_ROOT_DIRECTORY / "pgn" / "short.pgn"
DEFAULT_STOCKFISH_ENGINE_PATH = (PROJECT_ROOT_DIRECTORY / "engine" / "stockfish-windows-x86-64-bmi2.exe")

#pip install stockfish
#coge el .exe y muevelo a nose que
#llamalo

DEFAULT_OUTPUT_FILE_PATH = (PROJECT_ROOT_DIRECTORY / "results" / "analysis_results.xlsx")

# ───────────────────────────────────────────────────────────────────────────────
# 2. DEFINITIONS (command-line interface)
# ───────────────────────────────────────────────────────────────────────────────
def create_argument_parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(
        description="Analyse PGN games in parallel using Stockfish",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    argument_parser.add_argument("--pgn", dest="pgn_file_path")
    argument_parser.add_argument("--stockfish", dest="stockfish_engine_path")
    argument_parser.add_argument("--depth", type=int, default=18)
    argument_parser.add_argument("--hash", type=int, default=500)
    argument_parser.add_argument("--workers", type=int, default=mp.cpu_count())
    argument_parser.add_argument("--out", dest="output_file_path")
    return argument_parser

# ───────────────────────────────────────────────────────────────────────────────
# 3. VARIABLE RESOLUTION (hash, depth, etc.)
# ───────────────────────────────────────────────────────────────────────────────
def resolve_runtime_variables(parsed_args: argparse.Namespace) -> dict[str, pathlib.Path | int]:
    resolved_variables = {
        "pgn_file_path": pathlib.Path(
            parsed_args.pgn_file_path or DEFAULT_PGN_FILE_PATH
        ).resolve(),
        "stockfish_engine_path": pathlib.Path(
            parsed_args.stockfish_engine_path or DEFAULT_STOCKFISH_ENGINE_PATH
        ).resolve(),
        "search_depth": parsed_args.depth,
        "hash_size_mb": parsed_args.hash,
        "worker_process_count": parsed_args.workers,
        "output_file_path": PROJECT_ROOT_DIRECTORY
        / pathlib.Path(parsed_args.output_file_path or DEFAULT_OUTPUT_FILE_PATH.name),
    }
    resolved_variables["output_file_path"].parent.mkdir(parents=True, exist_ok=True)
    return resolved_variables

# ───────────────────────────────────────────────────────────────────────────────
# 4. MAIN EXECUTION FUNCTION
# ───────────────────────────────────────────────────────────────────────────────
def main() -> None:
    mp.set_start_method("spawn", force=True)
    runtime_arguments = create_argument_parser().parse_args()
    config = resolve_runtime_variables(runtime_arguments)

    if not config["pgn_file_path"].is_file():
        sys.exit(f"PGN file not found: {config['pgn_file_path']}")
    if not config["stockfish_engine_path"].is_file():
        sys.exit(f"Stockfish executable not found: {config['stockfish_engine_path']}")

    # ───────────────────────────────────────────────────────────────────────────
    # 5. DISPLAY CONFIGURATION
    # ───────────────────────────────────────────────────────────────────────────
    print(
        f"""
        PGN file           : {config['pgn_file_path']}
        Stockfish engine   : {config['stockfish_engine_path']}
        Output file        : {config['output_file_path']}
        Search depth       : {config['search_depth']}
        Hash size (MB)     : {config['hash_size_mb']}
        Worker processes   : {config['worker_process_count']}
        """
    )

    overall_start_time = time.time()
    
    game_payloads = build_payloads(config["pgn_file_path"])
    if not game_payloads:
        sys.exit("No games found in PGN file.")

    print("[Debug Enzo] Build Paylods ends here")
    
    analysis_results = run_parallel_analysis(
        payloads=game_payloads,
        stockfish_path=config["stockfish_engine_path"],
        depth=config["search_depth"],
        hash_mb=config["hash_size_mb"],
        workers=config["worker_process_count"],
    )

    analysis_dataframe = results_to_dataframe(analysis_results)
    if analysis_dataframe.empty:
        print("Empty DataFrame — nothing saved.")
    else:
        save_dataframe(analysis_dataframe, config["output_file_path"].as_posix())
        print(f"Saved {len(analysis_dataframe)} analysed games → {config['output_file_path']}")

    print(f"Elapsed time: {(time.time() - overall_start_time) / 60:.2f} minutes")
    
    print(f"Games per second: {len(analysis_dataframe) / (time.time() - overall_start_time):.2f}")

# ───────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
