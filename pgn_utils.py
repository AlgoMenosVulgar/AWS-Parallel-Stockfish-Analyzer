import sys, math
from pathlib import Path
import chess
import chess.pgn
import chess.engine



# 1) PGN parsing

def parse_pgn(pgn_path, headers_to_keep, max_games=None, min_white_moves=0):

    if not Path(pgn_path).is_file():
        sys.exit(f"PGN not found: {pgn_path}")

    raw = kept = 0
    games = []

    with open(pgn_path, encoding="utf-8", errors="ignore") as f:
        idx = 1
        while max_games is None or idx <= max_games:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            raw += 1
            board = game.board()
            fens = [board.fen()]
            white_moves = 0
            for ply, mv in enumerate(game.mainline_moves()):
                board.push(mv)
                fens.append(board.fen())
                if ply % 2 == 0:
                    white_moves += 1

            if white_moves >= min_white_moves:
                headers = {k: v for k, v in game.headers.items()
                           if k in headers_to_keep}
                games.append((idx, headers, fens))
                kept += 1
            idx += 1

    print(f"📂 Raw games read: {raw}")
    print(f"✅ Games kept after filter (≥{min_white_moves} white moves): {kept}")
    if not games:
        sys.exit("No games matched the criteria.")
    return games



# 2) Per-chunk Stockfish evaluation

def analyse_chunk(chunk, wid, stockfish_path, depth, hash_mb, progress_every):

    engine = chess.engine.SimpleEngine.popen_uci(str(stockfish_path))
    engine.configure({"Threads": 1, "Hash": hash_mb})
    limit = chess.engine.Limit(depth=depth)

    results = []
    total = len(chunk)
    print(f"[Worker {wid}] starting with {total} games", flush=True)

    try:
        for gnum, (idx, headers, fens) in enumerate(chunk, 1):
            scores = []
            for fen in fens:
                info = engine.analyse(chess.Board(fen), limit)
                sc = info["score"].white()
                scores.append(
                    1000 if sc.is_mate() and sc.mate() > 0 else
                    -1000 if sc.is_mate() else
                    sc.score()
                )
            results.append((idx, headers, scores))

            if gnum % progress_every == 0 or gnum == total:
                print(f"[Worker {wid}] {gnum}/{total} games analysed", flush=True)
    finally:
        engine.quit()
    return results



# 3) Utility: split a list into roughly equal chunks

def chunked(lst, n_chunks):
    if n_chunks <= 0:
        raise ValueError("n_chunks must be > 0")
    size = math.ceil(len(lst) / n_chunks)
    return [lst[i*size : min(len(lst), (i+1)*size)]
            for i in range(n_chunks) if i*size < len(lst)]
