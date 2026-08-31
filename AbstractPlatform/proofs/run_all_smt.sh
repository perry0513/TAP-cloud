#!/bin/bash
# run_all_smt.sh <DIRECTORY> [TIMEOUT_PER_SOLVER] [JOBS]
# Solve every .smt file in DIRECTORY with the solver portfolio, JOBS at a time,
# and write results.csv there.
python3 ../scripts/run_smt_parallel.py "$@"
