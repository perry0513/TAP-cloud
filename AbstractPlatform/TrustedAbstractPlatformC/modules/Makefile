COMMON_SOURCE=../../../Common/common-types.ucl
CACHE_SOURCE=./tap-mod-cache.ucl
AP_SOURCE=./ap-types.ucl
TAP_OP_SOURCES=./tap-mod-destroy.ucl ./tap-mod-enter.ucl ./tap-mod-exit.ucl ./tap-mod-launch.ucl ./tap-mod-pause.ucl ./tap-mod-resume.ucl ./tap-mod-block-memory-region.ucl ./tap-mod-release-memory-region.ucl
# TAP_OP_SOURCES+=./tap-mod-clone.ucl ./tap-mod-snapshot.ucl // Cerberus
TAP_OP_SOURCES+=./tap-mod-load-storage.ucl ./tap-mod-store-storage.ucl ./tap-mod-kms.ucl ./tap-mod-tamper-storage.ucl ./tap-mod-rollback-storage.ucl
CPU_SOURCES=$(COMMON_SOURCE) $(AP_SOURCE) $(CACHE_SOURCE) ./tap-mod-cpu.ucl
TAP_SOURCES=$(CPU_SOURCES) $(TAP_OP_SOURCES) ./tap-mod.ucl ./tap-mod-control.ucl
MEASURE=./measure.ucl

.PHONY: tap tap-printed measure clean

tap:
	uclid --main tap $(TAP_SOURCES)
tap-printed:
	rm -rf smt
	mkdir smt
	time uclid -g smt/tap --main tap $(TAP_SOURCES)
	python3 ../scripts/run_smt_parallel.py smt
	# ./run_all_smt.sh
measure:
	rm -rf measure
	mkdir measure
	uclid -g measure/measure --main measure $(TAP_SOURCES) $(MEASURE)
	python3 ../scripts/run_smt_parallel.py measure

clean:
	rm -rf smt
