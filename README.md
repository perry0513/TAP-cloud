# STAP

## Directory Structure

* `AbstractPlatform`: A formal model for STAP extended from TAP
* `Common`: Some common definitions for the formal model

## Running the Proof
To run the proof, you need to have the following installed:
1. [UCLID5](https://github.com/uclid-org/uclid)
2. [cvc5](https://github.com/cvc5/cvc5)
Check out the repositories for installation instructions.

The proof consists of four parts. Below are the commands to run each part:
1. To run procedural verification for each operations and procedures in the model:
   ```bash
   cd AbstractPlatform/modules
   make tap-printed
   ```

2. To run the secure measurement proof:
   ```bash
   cd AbstractPlatform/proofs
   make measurement-proof-printed
   ```
   Note that you can enable case splitting by uncommenting relevant lines in [measurement-proof.ucl](AbstractPlatform/proofs/measurement-proof.ucl) to speed up the proof.

3. To run the integrity proof:
    ```bash
    cd AbstractPlatform/proofs
    make integrity-case-split       # Checks the original operations in TAP
    make integrity-case-split-new   # Checks the new operations introduced by STAP
    ```

4. To run the confidentiality proof:
    ```bash
    cd AbstractPlatform/proofs
    make mem-conf-case-split        # Checks the original operations in TAP
    make mem-conf-case-split-new    # Checks the new operations introduced by STAP
    ```
    Note that only memory confidentiality is proved in this work while cache and page-table confidentiality are not.
