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
SOLVER_CONFIG = {
    "cvc5": {
        "exe": "cvc5 -q --lang smt2 --force-logic=ALL",
        # Below are all cvc5 options particularly relevant for quantifiers
        "options": [
            "",
            "--enum-inst",
            # "--cbqi-all-conflict",
            # "--mbqi",
            # "--decision internal --enum-inst --enum-inst-sum",
            # "--simplification none --enum-inst",
            # "--no-e-matching --enum-inst",
            # "--no-e-matching --enum-inst --enum-inst-sum",
            # "--relevant-triggers --enum-inst",
            # "--trigger-sel max --enum-inst",
            # "--enum-inst-interleave --enum-inst",
            # "--finite-model-find --decision internal",
            # "--finite-model-find --e-matching",
        ],
    },
    "z3": {
        "exe": "z3",
        "options": [
            # "",
        ],
    }
}

MAX_WORKERS = 8
OUTPUT_CSV = "results.csv"
PROGRESS_UPDATE_INTERVAL = 0.5
TIMEOUT = 10  # seconds

# === Global lock and status tracking ===
lock = Lock()
last_print_lines = 0


def run_on_file(filepath):
    start_time = time.time()
    filepath = Path(filepath)

    result = ""
    command = ""

    for solver_name, config in SOLVER_CONFIG.items():
        exe = config["exe"]
        options = config["options"]

        for opt in options:
            command = f"{exe} {opt}".strip()
            try:
                proc = subprocess.run(
                    f"{command} {str(filepath)}".split(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=TIMEOUT,
                )
                output = proc.stdout.strip().splitlines()
                result = output[0] if output else "No output"
            except Exception as e:
                result = f"Error: {str(e)}"
                if "timed out" in result:
                    result = "timeout"

            if result in ["sat", "unsat"]:
                break
        if result in ["sat", "unsat"]:
            break

    duration = time.time() - start_time
    return str(filepath), result, duration, command


def print_progress(statuses, total):
    global last_print_lines
    lines = []

    with lock:
        done = sum(1 for v in statuses.values() if v.startswith("finished"))
        lines.append(f"Progress [{done}/{total}]")
        for file, status in list(statuses.items())[-10:]:
            lines.append(f"  {Path(file).name}: {status}")

    # Clear previous output
    for _ in range(last_print_lines):
        print("\x1b[F\x1b[2K", end='')  # Move up and clear line

    for line in lines:
        print(line)

    last_print_lines = len(lines)


def summarize_results(results, total_time):
    sat = sum(1 for (res, _, _) in results.values() if res.strip().lower() == "sat")
    unsat = sum(1 for (res, _, _) in results.values() if res.strip().lower() == "unsat")
    unknown = sum(1 for (res, _, _) in results.values() if res.strip().lower() == "unknown")
    error = sum(1 for (res, _, _) in results.values() if res.strip().lower() not in {"sat", "unsat", "unknown"})
    cpu_time = sum(dur for (_, dur, _) in results.values() if dur > 0)
    print("\n=== Summary ===")
    print(f"  SAT    : {sat}")
    print(f"  UNSAT  : {unsat}")
    print(f"  UNKNOWN: {unknown}")
    print(f"  Errors : {error}")
    print(f"  Wall clock time: {total_time:.2f} seconds")
    print(f"  CPU time:        {cpu_time:.2f} seconds")

    if sat > 0 or unknown > 0 or error > 0:
        print()
        print(f"  SAT / UNKNOWN / ERROR instances:")
        for file, (res, dur, command) in results.items():
            if res.strip().lower() != "unsat":
                print(f"    {file} -> {res} ({dur:.2f}s with {command})")


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
    results = manager.dict()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(run_on_file, f): str(f) for f in files
        }
        last_update = time.time()

        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                file, result, duration, command = future.result()
            except Exception as e:
                file, result, duration, command = file_path, f"Error: {e}", 0.0, ""

            with lock:
                results[file] = (result, duration, command)
                statuses[file] = f"finished in {duration:.2f}s with {result} using `{command}`"

            if time.time() - last_update >= PROGRESS_UPDATE_INTERVAL:
                print_progress(statuses, total)
                last_update = time.time()

        print_progress(statuses, total)  # Final update


    total_runtime = time.time() - start_time

    # Output results
    results_list = [(f, res, dur, opt) for f, (res, dur, opt) in results.items()]
    df = pd.DataFrame(results_list, columns=["file", "result", "time_sec", "solver_option"])
    save_path = Path(directory) / OUTPUT_CSV
    df.to_csv(save_path, index=False)

    summarize_results(results, total_runtime)
    print(f"\nDone. Results saved to {save_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_smt_parallel.py <DIRECTORY> [TIMEOUT_PER_SOLVER]")
        sys.exit(1)
    if len(sys.argv) == 3:
        TIMEOUT = int(sys.argv[2])
    main(sys.argv[1])

