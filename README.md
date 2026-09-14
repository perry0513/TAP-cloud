# STAP

This repository provides the formal models, machine-checked proofs, and supplementary materials for the paper "A Formal Foundation for Secure Stateful Remote Execution of Enclaves in the Cloud."

## Directory Structure

* `AbstractPlatform`: Formal model and machine-checked proofs for STAP extended from TAP
* `Common`: Some common definitions for the formal model
* `natural_deudction_proof.pdf`: Fitch-style proof for Theorem 2 in the paper.

## Running the Proof
To run the proof, you need to have the following installed:
1. [UCLID5](https://github.com/uclid-org/uclid)
2. [cvc5](https://github.com/cvc5/cvc5)

Check out the repositories for installation instructions.

The model gives the KMS calls their own steps, so `storePS` and `updateTag` are
no longer a single atomic operation and the window between them is part of the
model. Freshness tags commit to the *content* of the stored state rather than to
its position in the sequence, the KMS commit is a conditional append, and the
adversary has an explicit archive it can replay a previously observed ciphertext
from. `AbstractPlatform/proofs/regression/` holds a variant of the model in
which tags certify position only; it is there to show which obligations the
content-binding tags are actually carrying.

The proof consists of four parts. Every target below regenerates its SMT
obligations with UCLID5 and discharges them through a solver portfolio; a target
exits non-zero if any obligation comes back other than `unsat`. Two knobs are
common to all of them: `TIMEOUT=<seconds>` is the per-solver budget (default 60)
and `JOBS=<n>` the number of solver processes (default 8). The case-split
targets are independent, so `make -jN` parallelises across them as well; a run
uses about `N x JOBS` cores.

1. To run procedural verification for each operation (procedure) in the formal model:
   ```bash
   cd AbstractPlatform/modules
   make tap-smt          # emit the obligations and solve them in parallel
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
both case-split proofs in one go. Generated artifacts land in
`AbstractPlatform/proofs/gen-chk/<proof>-<split>/` -- the emitted SMT files, a
`gen.log`, and a `results.csv` giving the result and solver for each obligation
-- and `make clean` removes them. `make help` lists the targets.
