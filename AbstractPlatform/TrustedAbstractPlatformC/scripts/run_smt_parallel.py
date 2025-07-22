import os
import sys
import time
import subprocess
import pandas as pd
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager
from threading import Lock

# === CONFIGURATION ===
COMMAND = "cvc4 -q --lang smt2 --force-logic=ALL --incremental"
MAX_WORKERS = 4
OUTPUT_CSV = "results.csv"
PROGRESS_UPDATE_INTERVAL = 0.5

# === Global lock and status tracking ===
lock = Lock()
last_print_lines = 0


def run_on_file(filepath):
    start_time = time.time()
    filepath = Path(filepath)

    try:
        proc = subprocess.run(
            f"{COMMAND} {str(filepath)}".split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300
        )
        output = proc.stdout.strip().splitlines()
        result = output[0] if output else "No output"
    except Exception as e:
        result = f"Error: {str(e)}"

    duration = time.time() - start_time
    return str(filepath), result, duration


def print_progress(statuses, total):
    global last_print_lines
    lines = []

    with lock:
        done = sum(1 for v in statuses.values() if v.startswith("finished"))
        lines.append(f"Progress: [{done}/{total}]")
        for file, status in list(statuses.items())[-10:]:
            lines.append(f"  {Path(file).name}: {status}")

    # Clear previous output
    for _ in range(last_print_lines):
        print("\x1b[F\x1b[2K", end='')  # Move up and clear line

    for line in lines:
        print(line)

    last_print_lines = len(lines)


def summarize_results(results, total_time):
    sat = sum(1 for (_, res, _) in results if res.strip().lower() == "sat")
    unsat = sum(1 for (_, res, _) in results if res.strip().lower() == "unsat")
    error = sum(1 for (_, res, _) in results if res.strip().lower() not in {"sat", "unsat"})
    print("\n=== Summary ===")
    print(f"  SAT    : {sat}")
    print(f"  UNSAT  : {unsat}")
    print(f"  Errors : {error}")
    print(f"  Total runtime: {total_time:.2f} seconds")


def main(directory):
    files = sorted(Path(directory).rglob("*.smt"))
    if not files:
        print("No .smt files found.")
        return

    total = len(files)
    print(f"Found {total} .smt files.\n")
    start_time = time.time()

    manager = Manager()
    statuses = manager.dict()
    results = manager.list()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(run_on_file, f): str(f) for f in files
        }
        last_update = time.time()

        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                file, result, duration = future.result()
            except Exception as e:
                file, result, duration = file_path, f"Error: {e}", 0.0

            with lock:
                results.append((file, result, duration))
                statuses[file] = f"finished in {duration:.2f}s"

            if time.time() - last_update >= PROGRESS_UPDATE_INTERVAL:
                print_progress(statuses, total)
                last_update = time.time()

        print_progress(statuses, total)  # Final update

    total_runtime = time.time() - start_time

    # Output results
    df = pd.DataFrame(list(results), columns=["file", "result", "time_sec"])
    save_path = Path(directory) / OUTPUT_CSV
    df.to_csv(save_path, index=False)

    summarize_results(results, total_runtime)
    print(f"\nDone. Results saved to {save_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_smt_parallel.py <directory>")
        sys.exit(1)
    main(sys.argv[1])

