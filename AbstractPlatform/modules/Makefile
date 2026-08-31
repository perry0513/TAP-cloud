# ---------------------------------------------------------------------------
# The STAP model itself: verify every procedure's contract.
#
#   make tap        check with uclid directly
#   make tap-smt    emit SMT files to smt/ and solve them with the portfolio
#   make measure    the measurement module
#   make clean
#
# The proofs that build on this model live in ../proofs.
# ---------------------------------------------------------------------------

COMMON  = ../../Common/common-types.ucl
CPU     = $(COMMON) ./ap-types.ucl ./tap-mod-cache.ucl ./tap-mod-cpu.ucl

# Base TAP operations.
OPS     = ./tap-mod-destroy.ucl ./tap-mod-enter.ucl ./tap-mod-exit.ucl \
          ./tap-mod-launch.ucl ./tap-mod-pause.ucl ./tap-mod-resume.ucl \
          ./tap-mod-block-memory-region.ucl ./tap-mod-release-memory-region.ucl
# TAP-cloud operations: persistent storage and the KMS.
OPS    += ./tap-mod-load-storage.ucl ./tap-mod-store-storage.ucl ./tap-mod-kms.ucl \
          ./tap-mod-tamper-storage.ucl ./tap-mod-replay-storage.ucl

SOURCES = $(CPU) $(OPS) ./tap-mod.ucl ./tap-mod-control.ucl
MEASURE = ./measure.ucl

TIMEOUT ?= 60
JOBS    ?= 8

.PHONY: tap tap-smt measure clean

tap:
	uclid --main tap $(SOURCES)

# gen.time and results.csv here feed scripts/get_total_time.py.
tap-smt:
	rm -rf smt && mkdir smt
	/usr/bin/time -f "%U %S" -o smt/gen.time uclid -g smt/tap --main tap $(SOURCES)
	../proofs/run_all_smt.sh smt $(TIMEOUT) $(JOBS)

measure:
	rm -rf measure && mkdir measure
	/usr/bin/time -f "%U %S" -o measure/gen.time uclid -g measure/measure --main measure $(SOURCES) $(MEASURE)
	../proofs/run_all_smt.sh measure $(TIMEOUT) $(JOBS)

clean:
	rm -rf smt measure
