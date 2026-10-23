# STAP

This repository provides the formal models, machine-checked proofs, and supplementary materials for the paper "A Formal Foundation for Secure Stateful Remote Execution of Enclaves in the Cloud."

## Directory Structure

* `AbstractPlatform`: Formal model and machine-checked proofs for STAP extended from TAP
  * `modules`: the model itself, and the per-operation step files for the case splits
  * `proofs`: the measurement, integrity and confidentiality proofs, and the proof build
  * `scripts`: the solver dispatcher and the model-statistics script
* `Common`: Some common definitions for the formal model

## Running the Proof

### Dependencies

1. [UCLID5](https://github.com/uclid-org/uclid)
2. [cvc5](https://github.com/cvc5/cvc5)
3. [Z3](https://github.com/Z3Prover/z3)
4. Python 3 with [pandas](https://pandas.pydata.org/)
5. GNU `time`, at `/usr/bin/time`

All five need to be on `PATH`. Check out the repositories for installation
instructions; the numbers below were produced with UCLID5 0.9.5, cvc5 1.0.3 and
Z3 4.12.2.
Both solvers are required to run the portfolio.

### Proof commands

The proof consists of four parts. Every target regenerates its SMT obligations
with UCLID5 and discharges them through the solver portfolio.

Two knobs are common to all of them: `TIMEOUT=<seconds>` is the per-solver
budget (default 60) and `JOBS=<n>` the number of solver processes (default 8).
The case-split targets are independent, so `make -jN` parallelises across them
as well -- be mindful that a run then uses about `N x JOBS` cores.

1. To run procedural verification for each operation (procedure) in the formal model:
   ```bash
   cd AbstractPlatform/modules
   make tap-smt          # emit the obligations and solve them in parallel
   make measure
   ```
   `make tap` verifies the same contracts with UCLID5 driving the solver
   in-process. That is a single process and needs several GB of memory; prefer
   `tap-smt` unless you want UCLID5's own output.

2. To run the secure measurement proof:
   ```bash
   cd AbstractPlatform/proofs
   make measurement
   ```
   Note that you can enable case splitting by uncommenting relevant lines in [measurement-proof.ucl](AbstractPlatform/proofs/measurement-proof.ucl) to speed up the proof.

3. To run the integrity proof:
    ```bash
    cd AbstractPlatform/proofs
    make integrity-base     # Checks the original operations in TAP
    make integrity-cloud    # Checks the new operations introduced by STAP
    make integrity-all      # Both
    ```
    `integrity-cloud` covers the granular KMS calls (`getKeyTag`, `updateTag`)
    and the operation that gives the adversary its replay archive
    (`replayStorage`) alongside the storage operations, in both the enclave-step
    and the adversary-step splits.

4. To run the confidentiality proof:
    ```bash
    cd AbstractPlatform/proofs
    make conf-base          # Checks the original operations in TAP
    make conf-cloud         # Checks the new operations introduced by STAP
    make conf-all           # Both
    ```
    Note that only memory confidentiality is proved in this work while cache and page-table confidentiality are not.

`make check-all` in `AbstractPlatform/proofs` runs the measurement proof and
both case-split proofs in one go.

```bash
make -C AbstractPlatform/proofs help     # list the proof targets
make clean    # remove the generated obligations, logs and results
```

### Expected results

Every obligation comes back `unsat`. Part 1 prints a summary block in which
`UNSAT` equals the number of obligations and `SAT`, `UNKNOWN` and `Errors` are
all zero. Parts 2-4 print one summary line per split instead:

```
  adv-replay               230 unsat
```

A split that does not close reports `N obligations, M NOT unsat` on that line.
With UCLID5 0.9.5 the obligation counts are 5535 for `tap-smt`, 30 for
`measure`, 395 for `measurement`, 5704 for `integrity-all` and 5392 for
`conf-all`. The `measurement` count is 287 obligations for
`measurement_proof` plus part 1's 54, which UCLID5 emits twice.

## Model and Verification Statistics

`AbstractPlatform/scripts/model_stats.py` reproduces the model-statistics
table in the paper: per model and proof, the number of procedures,
uninterpreted functions, annotations (postconditions and loop/global
invariants) and non-blank lines, together with verification time. Verification
time is SMT generation time plus solver time, read from the run artifacts, so
run the proof first -- the script warns if a row's artifacts are older than its
sources, or missing.

```bash
cd AbstractPlatform
make -C proofs check-all && make -C modules tap-smt
python3 scripts/model_stats.py             # LaTeX table body
python3 scripts/model_stats.py --plain     # aligned text, plus obligation counts
python3 scripts/model_stats.py --verbose   # per-file and per-split detail
```

The script's header comment records the counting conventions, including which
files each row covers and why the proof rows report zero procedures.
