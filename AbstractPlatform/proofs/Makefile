# ---------------------------------------------------------------------------
# TAP-cloud proof build.
#
#   make integrity-base    integrity-cloud    integrity-all
#   make conf-base         conf-cloud         conf-all
#   make measurement
#   make check-all                 measurement + integrity-all + conf-all
#
#   base   operations inherited from the original TAP
#   cloud  operations TAP-cloud adds (persistent storage and the KMS)
#   all    both
#
# Every target regenerates its case splits with uclid and discharges all of a
# split's obligations in parallel via run_all_smt.sh.  A target reports loudly
# and make exits non-zero if generation fails or any obligation comes back
# other than `unsat`.
#
# Obligations within a split already run in parallel; splits are independent,
# so `make -j` parallelises across them too:
#     make -j4 check-all
#
# Generated artifacts live in gen-chk/<proof>-<split>/ and are removed by
# `make clean`.  Each holds the emitted SMT files and a gen.log.
#
#   TIMEOUT   per-solver budget, seconds   (default 60)
#   JOBS      solver processes per split    (default 8)
#
# Both are passed straight through to run_all_smt.sh.  A run uses about
# (make -j) x JOBS cores, so on a 20-core box either of these fits:
#     make JOBS=20 check-all          # one split at a time, 20 solvers
#     make -j4 JOBS=5 check-all       # four splits at once, 5 solvers each
# ---------------------------------------------------------------------------

SHELL := /bin/bash
.ONESHELL:

# Per-solver budget handed to run_all_smt.sh, which fans the obligations of a
# split out across a portfolio (cvc5 under several quantifier configurations,
# and z3) and writes results.csv.  A portfolio matters: some obligations are
# closed only by --enum-inst or by z3.
TIMEOUT ?= 60
# Solver processes per split.  `make -jN` runs N splits at once, so the product
# N x JOBS is what lands on the CPU; keep it at or below `nproc`.
JOBS    ?= 8
GEN     := gen-chk

#---------------------------------------------------------------------------#
# Sources                                                                    #
#---------------------------------------------------------------------------#
MODULES  = ./../modules
INTG_DIR = $(MODULES)/tap-mod-integrity
CONF_DIR = $(MODULES)/tap-mod-conf

CPU_SOURCES = ../../Common/common-types.ucl $(MODULES)/ap-types.ucl \
              $(MODULES)/tap-mod-cache.ucl $(MODULES)/tap-mod-cpu.ucl

# Base TAP operations.
TAP_OP_SOURCE  = $(MODULES)/tap-mod-destroy.ucl $(MODULES)/tap-mod-enter.ucl \
                 $(MODULES)/tap-mod-exit.ucl $(MODULES)/tap-mod-launch.ucl \
                 $(MODULES)/tap-mod-pause.ucl $(MODULES)/tap-mod-resume.ucl \
                 $(MODULES)/tap-mod-block-memory-region.ucl \
                 $(MODULES)/tap-mod-release-memory-region.ucl
# TAP-cloud operations: persistent storage and the KMS.
TAP_OP_SOURCE += $(MODULES)/tap-mod-load-storage.ucl $(MODULES)/tap-mod-store-storage.ucl \
                 $(MODULES)/tap-mod-kms.ucl $(MODULES)/tap-mod-tamper-storage.ucl \
                 $(MODULES)/tap-mod-replay-storage.ucl

PROOF_SOURCES = $(CPU_SOURCES) $(TAP_OP_SOURCE) $(MODULES)/tap-mod.ucl ./proof-common.ucl

# An enclave-step split pairs with a stub init (the adversary step is not taken);
# an adversary-step split pairs with the real init.
INTEGRITY_NEXT = ./integrity-proof.ucl ./integrity-proof-init-stub.ucl \
                 ./integrity-proof-next.ucl $(MODULES)/tap-mod-integrity.ucl
INTEGRITY_FULL = ./integrity-proof.ucl ./integrity-proof-init.ucl \
                 ./integrity-proof-next.ucl $(MODULES)/tap-mod-integrity.ucl
MEM_CONF_NEXT  = $(MODULES)/tap-mod-conf.ucl ./mem-conf-proof.ucl ./mem-conf-proof-init-stub.ucl
MEM_CONF_FULL  = $(MODULES)/tap-mod-conf.ucl ./mem-conf-proof.ucl ./mem-conf-proof-init.ucl

MEASUREMENT = $(MODULES)/measure.ucl ./measurement-proof.ucl

#---------------------------------------------------------------------------#
# Case splits                                                               #
#---------------------------------------------------------------------------#
INTEGRITY_BASE  = enc-compute enc-exit enc-pause \
                  adv-launch adv-destroy adv-enter adv-exit adv-pause adv-resume \
                  adv-block adv-release adv-compute
INTEGRITY_CLOUD = enc-store enc-load enc-getkeytag enc-updatetag \
                  adv-createkey adv-deletekey adv-tamper adv-replay \
                  adv-store adv-load adv-getkeytag adv-updatetag
CONF_BASE       = e-compute e-exit e-pause \
                  block compute destroy enter exit launch pause release resume
CONF_CLOUD      = e-store e-load e-getkeytag e-updatetag \
                  create-key delete-key load-storage store-storage \
                  tamper-storage replay-storage get-key-and-tag update-tag

#--- integrity: enclave-step splits (full adversary step, stub init) ---#
FILES_integrity_enc-compute = $(INTG_DIR)/e-compute.ucl $(INTG_DIR)/full-adv-step.ucl $(INTEGRITY_NEXT)
FILES_integrity_enc-exit = $(INTG_DIR)/e-exit.ucl $(INTG_DIR)/full-adv-step.ucl $(INTEGRITY_NEXT)
FILES_integrity_enc-pause = $(INTG_DIR)/e-pause.ucl $(INTG_DIR)/full-adv-step.ucl $(INTEGRITY_NEXT)
FILES_integrity_enc-store = $(INTG_DIR)/e-store-storage.ucl $(INTG_DIR)/full-adv-step.ucl $(INTEGRITY_NEXT)
FILES_integrity_enc-load = $(INTG_DIR)/e-load-storage.ucl $(INTG_DIR)/full-adv-step.ucl $(INTEGRITY_NEXT)
FILES_integrity_enc-getkeytag = $(INTG_DIR)/e-get-key-and-tag.ucl $(INTG_DIR)/full-adv-step.ucl $(INTEGRITY_NEXT)
FILES_integrity_enc-updatetag = $(INTG_DIR)/e-update-tag.ucl $(INTG_DIR)/full-adv-step.ucl $(INTEGRITY_NEXT)

#--- integrity: adversary-step splits (full enclave step, real init) ---#
FILES_integrity_adv-launch = $(INTG_DIR)/adv-launch.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-destroy = $(INTG_DIR)/adv-destroy.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-enter = $(INTG_DIR)/adv-enter.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-exit = $(INTG_DIR)/adv-exit.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-pause = $(INTG_DIR)/adv-pause.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-resume = $(INTG_DIR)/adv-resume.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-block = $(INTG_DIR)/adv-block.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-release = $(INTG_DIR)/adv-release.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-compute = $(INTG_DIR)/adv-compute.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-createkey = $(INTG_DIR)/adv-create-key.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-deletekey = $(INTG_DIR)/adv-delete-key.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-tamper = $(INTG_DIR)/adv-tamper-storage.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-replay = $(INTG_DIR)/adv-replay-storage.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-store = $(INTG_DIR)/adv-store-storage.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-load = $(INTG_DIR)/adv-load-storage.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-getkeytag = $(INTG_DIR)/adv-get-key-and-tag.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)
FILES_integrity_adv-updatetag = $(INTG_DIR)/adv-update-tag.ucl $(INTG_DIR)/full-enc-step.ucl $(INTEGRITY_FULL)

#--- confidentiality: enclave-step splits (full observer step, stub init) ---#
FILES_conf_e-compute = $(CONF_DIR)/e-compute.ucl $(CONF_DIR)/full-obs-step.ucl $(MEM_CONF_NEXT)
FILES_conf_e-exit = $(CONF_DIR)/e-exit.ucl $(CONF_DIR)/full-obs-step.ucl $(MEM_CONF_NEXT)
FILES_conf_e-pause = $(CONF_DIR)/e-pause.ucl $(CONF_DIR)/full-obs-step.ucl $(MEM_CONF_NEXT)
FILES_conf_e-store = $(CONF_DIR)/e-store-storage.ucl $(CONF_DIR)/full-obs-step.ucl $(MEM_CONF_NEXT)
FILES_conf_e-load = $(CONF_DIR)/e-load-storage.ucl $(CONF_DIR)/full-obs-step.ucl $(MEM_CONF_NEXT)
FILES_conf_e-getkeytag = $(CONF_DIR)/e-get-key-and-tag.ucl $(CONF_DIR)/full-obs-step.ucl $(MEM_CONF_NEXT)
FILES_conf_e-updatetag = $(CONF_DIR)/e-update-tag.ucl $(CONF_DIR)/full-obs-step.ucl $(MEM_CONF_NEXT)

#--- confidentiality: observer-step splits (full enclave step, real init) ---#
FILES_conf_block = $(CONF_DIR)/obs-block.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_compute = $(CONF_DIR)/obs-compute.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_create-key = $(CONF_DIR)/obs-create-key.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_delete-key = $(CONF_DIR)/obs-delete-key.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_destroy = $(CONF_DIR)/obs-destroy.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_enter = $(CONF_DIR)/obs-enter.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_exit = $(CONF_DIR)/obs-exit.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_launch = $(CONF_DIR)/obs-launch.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_load-storage = $(CONF_DIR)/obs-load-storage.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_pause = $(CONF_DIR)/obs-pause.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_release = $(CONF_DIR)/obs-release.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_resume = $(CONF_DIR)/obs-resume.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_store-storage = $(CONF_DIR)/obs-store-storage.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_tamper-storage = $(CONF_DIR)/obs-tamper-storage.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_replay-storage = $(CONF_DIR)/obs-replay-storage.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_get-key-and-tag = $(CONF_DIR)/obs-get-key-and-tag.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)
FILES_conf_update-tag = $(CONF_DIR)/obs-update-tag.ucl $(CONF_DIR)/full-enc-step.ucl $(MEM_CONF_FULL)

#---------------------------------------------------------------------------#
# One case split: generate, then solve every obligation in parallel.         #
#   $(1) proof (integrity|conf)   $(2) uclid main module   $(3) split name   #
#---------------------------------------------------------------------------#
define check_split
	dir=$(GEN)/$(1)-$(3)
	mkdir -p $(GEN)
	rm -rf $$dir && mkdir -p $$dir
	if ! uclid -g $$dir/x --main $(2) $(PROOF_SOURCES) $(FILES_$(1)_$(3)) > $$dir/gen.log 2>&1; then
	  printf '  %-22s GENERATION FAILED -- see %s/gen.log\n' '$(3)' "$$dir"
	  exit 1
	fi
	n=$$(ls $$dir/*.smt 2>/dev/null | wc -l)
	if [ "$$n" -eq 0 ]; then
	  printf '  %-22s NO OBLIGATIONS GENERATED\n' '$(3)'
	  exit 1
	fi
	./run_all_smt.sh $$dir $(TIMEOUT) $(JOBS) > $$dir/solve.log 2>&1
	bad=$$(python3 -c "import csv;print(sum(1 for r in csv.DictReader(open('$$dir/results.csv')) if r['result']!='unsat'))")
	if [ "$$bad" -eq 0 ]; then
	  printf '  %-22s %5d unsat\n' '$(3)' "$$n"
	else
	  printf '  %-22s %5d obligations, %d NOT unsat\n' '$(3)' "$$n" "$$bad"
	  exit 1
	fi
endef

check-integrity-%: ; @$(call check_split,integrity,integrity_proof,$*)
check-conf-%:      ; @$(call check_split,conf,mem_confidentiality_proof,$*)

#---------------------------------------------------------------------------#
# Groups                                                                     #
#---------------------------------------------------------------------------#
integrity-base:  ; @echo "=== integrity / base ==="  ; $(MAKE) -s $(addprefix check-integrity-,$(INTEGRITY_BASE))
integrity-cloud: ; @echo "=== integrity / cloud ===" ; $(MAKE) -s $(addprefix check-integrity-,$(INTEGRITY_CLOUD))
integrity-all:   ; @echo "=== integrity / all ==="   ; $(MAKE) -s $(addprefix check-integrity-,$(INTEGRITY_BASE) $(INTEGRITY_CLOUD))

conf-base:  ; @echo "=== confidentiality / base ==="  ; $(MAKE) -s $(addprefix check-conf-,$(CONF_BASE))
conf-cloud: ; @echo "=== confidentiality / cloud ===" ; $(MAKE) -s $(addprefix check-conf-,$(CONF_CLOUD))
conf-all:   ; @echo "=== confidentiality / all ==="   ; $(MAKE) -s $(addprefix check-conf-,$(CONF_BASE) $(CONF_CLOUD))

# Measurement is a single proof rather than a case split, but is checked the
# same way: emit the obligations, then solve them in parallel.
measurement:
	@echo "=== measurement ==="
	dir=$(GEN)/measurement
	mkdir -p $(GEN)
	rm -rf $$dir && mkdir -p $$dir
	if ! uclid -g $$dir/x --main measurement_proof $(PROOF_SOURCES) $(MEASUREMENT) > $$dir/gen.log 2>&1; then
	  echo "  GENERATION FAILED -- see $$dir/gen.log"; exit 1
	fi
	n=$$(ls $$dir/*.smt | wc -l)
	./run_all_smt.sh $$dir $(TIMEOUT) $(JOBS) > $$dir/solve.log 2>&1
	bad=$$(python3 -c "import csv;print(sum(1 for r in csv.DictReader(open('$$dir/results.csv')) if r['result']!='unsat'))")
	if [ "$$bad" -eq 0 ]; then printf '  %-22s %5d unsat\n' measurement "$$n"
	else printf '  %-22s %5d obligations, %d NOT unsat\n' measurement "$$n" "$$bad"; exit 1; fi

check-all: measurement integrity-all conf-all

help:
	@echo "Case-split checks (regenerate, solve in parallel, non-zero exit on failure):"
	@echo "  integrity-base   integrity-cloud   integrity-all"
	@echo "  conf-base        conf-cloud        conf-all"
	@echo "  measurement"
	@echo "  check-all        all of the above"
	@echo
	@echo "  TIMEOUT=<s>  per-solver budget       (default $(TIMEOUT))"
	@echo "  JOBS=<n>     solvers per split        (default $(JOBS))"
	@echo "  make -jN     runs splits concurrently"

clean:
	rm -rf $(GEN)

.PHONY: help check-all measurement clean \
        integrity-base integrity-cloud integrity-all \
        conf-base conf-cloud conf-all
