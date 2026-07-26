#/*Copyright 2019-2021 T-Head Semiconductor Co., Ltd.
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
#*/

export SMART_RUN_ROOT := $(abspath .)

include ./setup/smart_cfg.mk
include ./setup/env_check.mk

################################################################################
# Simulation related
################################################################################
SIM = iverilog
DUMP = off
COV = off
COV_METRICS = line+cond+fsm+tgl+branch
COV_DIR = coverage.vdb
COV_REPORT_DIR = coverage_report
THREADS = 4
REBUILD = off
WORK_ROOT = ./work
DV_ROOT ?= $(abspath ../riscv-dv)
DV_TARGET ?= c910
DV_TESTLIST ?= $(DV_ROOT)/target/$(DV_TARGET)/testlist.yaml
DV_TEST ?=
SEED ?= 1
DV_CASE = dv_$(DV_TEST)_seed_$(SEED)
DV_BUILD_DIR = $(WORK_ROOT)/build/dv/$(DV_TARGET)
DV_RUN_DIR = $(WORK_ROOT)/runs/$(DV_CASE)
DV_GEN_DIR = $(DV_RUN_DIR)/.dv-gen
DV_SOURCE = $(DV_RUN_DIR)/$(DV_TEST)_seed_$(SEED).S
DV_TOHOST_HEX ?= 01ffffe0
DV_TESTS ?= all
RUNS_PER_TEST ?= 50
JOBS ?= 50
REPORT_JOBS ?= 8
SEED_BASE ?= 1
DV_TIMEOUT ?= 1800
ESTIMATED_CASE_MIB ?= 500
DRY_RUN ?= off
FORCE ?= off
WORKER_MAKE ?= $(MAKE)
REGRESS_ROOT ?= $(WORK_ROOT)/regress
BUILD_KEY = $(if $(filter $(CASE),debug_gpr debug_memory plic_int sleep),$(CASE),default)
BUILD_DIR = $(WORK_ROOT)/build/$(BUILD_KEY)
RUN_DIR = $(WORK_ROOT)/runs/$(if $(strip $(CASE)),$(CASE),compile)
BUILD_CONFIG = SIM=$(SIM) COV=$(COV) COV_METRICS=$(COV_METRICS) DUMP=$(DUMP) UPF=$(UPF) CODE_BASE_PATH=$(CODE_BASE_PATH)
CASE_SOURCE_DIR_ISA_AMO = ./tests/cases/ISA/ISA_AMO
CASE_SOURCE_DIR_smoke_bus = ./tests/cases/smoke/bus_smoke
CASE_SOURCE_DIR_debug_gpr = ./tests/cases/debug/debug_gpr
CASE_SOURCE_DIR_ISA_THEAD = ./tests/cases/ISA/ISA_THEAD
CASE_SOURCE_DIR_cache_op = ./tests/cases/cache/idcache_oper
CASE_SOURCE_DIR_debug_memory = ./tests/cases/debug/debug_memory
CASE_SOURCE_DIR_ISA_FP = ./tests/cases/ISA/ISA_FP
CASE_SOURCE_DIR_ISA_IMAC = ./tests/cases/ISA/ISA_IMAC
CASE_SOURCE_DIR_coremark = ./tests/cases/coremark
CASE_SOURCE_DIR_hello_world = ./tests/cases/hello_world
CASE_SOURCE_DIR_MMU = ./tests/cases/MMU
CASE_SOURCE_DIR_ISA_VECTOR = ./tests/cases/ISA/ISA_VECTOR/VECTOR_SMOKE
CASE_SOURCE_DIR_csr = ./tests/cases/csr
CASE_SOURCE_DIR_ISA_BARRIER = ./tests/cases/ISA/ISA_BARRIER
CASE_SOURCE_DIR_plic_int = ./tests/cases/interrupt/int_smoke
CASE_SOURCE_DIR_sleep = ./tests/cases/sleep
CASE_SOURCE_DIR = $(CASE_SOURCE_DIR_$(CASE))

# Generate C++ in executable form
VERILATOR_FLAGS += -cc --exe
# Generate makefile dependencies (not shown as complicates the Makefile)
#VERILATOR_FLAGS += -MMD
# Optimize
VERILATOR_FLAGS += -Os -x-assign 0
# lint-only
VERILATOR_FLAGS += -lint-only
# Warn abount lint issues; may not want this on less solid designs
VERILATOR_FLAGS += -Wno-fatal
# Make waveforms
#VERILATOR_FLAGS += --trace
## Check SystemVerilog assertions
#VERILATOR_FLAGS += --assert
## Generate coverage analysis
#VERILATOR_FLAGS += --coverage
# Run Verilator in debug mode
#VERILATOR_FLAGS += --debug
# Add this trace to get a backtrace in gdb
#VERILATOR_FLAGS += --gdbbt

# Generate C++ in executable form
VERILATOR_FLAGS += -cc --exe
# Generate makefile dependencies (not shown as complicates the Makefile)
#VERILATOR_FLAGS += -MMD
# Optimize
VERILATOR_FLAGS += -Os -x-assign 0
# lint-only
VERILATOR_FLAGS += -lint-only
# Warn abount lint issues; may not want this on less solid designs
VERILATOR_FLAGS += -Wno-fatal
# Make waveforms
#VERILATOR_FLAGS += --trace
## Check SystemVerilog assertions
#VERILATOR_FLAGS += --assert
## Generate coverage analysis
#VERILATOR_FLAGS += --coverage
# Run Verilator in debug mode
#VERILATOR_FLAGS += --debug
# Add this trace to get a backtrace in gdb
#VERILATOR_FLAGS += --gdbbt

ifeq ($(DUMP), on)
ifeq (${SIM}, verilator)
SIM_DUMP := --trace
else
SIM_DUMP :=
endif
else
ifeq (${SIM}, iverilog)
SIM_DUMP = -DNO_DUMP
else
SIM_DUMP := +define+NO_DUMP
endif
endif

ifeq ($(SIM), vcs)
TIMESCALE := -timescale=1ns/100fs
SIMULATOR_OPT := -sverilog -full64 -kdb -lca -debug_access +nospecify +notimingchecks +lint=TFIPC-L
SIMULATOR_DEF := +define+no_warning +define+TSMC_NO_WARNING
SIMULATOR_LOG := -l comp.vcs.log
ifeq ($(COV), on)
SIMULATOR_COV_OPT := -cm $(COV_METRICS) -cm_dir $(COV_DIR)
SIMV_COV_OPT := -cm $(COV_METRICS) -cm_dir $(COV_DIR)
endif
ifeq ($(UPF), on)
SIMULATOR_POWER_OPT := -upf $(SMART_RUN_ROOT)/impl/upf/example_cpu_power_spec.upf +define+UPF_INCLUDED
SIMV_POWER_OPT      := +fsdb+power +fsdb+all
else
SIMULATOR_POWER_OPT :=
SIMV_POWER_OPT      :=
endif
else
    ifeq ($(SIM), nc)
    TIMESCALE := -timescale 1ns/100fs
    SIMULATOR_OPT := +v2k -sysv +sv +access+wrc +notimingcheck -default_ext verilog -elaborate +tcl+../setup/nc.tcl
    SIMULATOR_DEF := +define+no_warning +define+TSMC_NO_WARNING +define+VMC +define+NC_SIM
    SIMULATOR_LOG := -l comp.nc.log
    else
        ifeq ($(SIM), iverilog)
          TIMESCALE :=
          SIMULATOR_OPT := -o xuantie_core.vvp -Diverilog=1 -g2012
          SIMULATOR_DEF := -DIVERILOG_SIM
          SIMULATOR_LOG :=
        else
            ifeq ($(SIM), verilator)
              SIMULATOR_OPT := -Os -x-assign 0 -Wno-fatal --threads ${THREADS}
              SIMULATOR_DEF := -cc --exe --top-module top
              SIMULATOR_LOG :=
            else
            endif
        endif
    endif
endif

ifeq ($(SIM), iverilog)
    SIM_FILELIST := $(SIM_FILELIST) -f ${CODE_BASE_PATH}/gen_rtl/filelists/C910_asic_rtl.fl -c $(SMART_RUN_ROOT)/logical/filelists/smart.fl -c $(SMART_RUN_ROOT)/logical/filelists/tb.fl
else
    ifeq ($(SIM), verilator)
    SIM_FILELIST := $(SIM_FILELIST) -f $(SMART_RUN_ROOT)/logical/filelists/sim_verilator.fl
    else
    SIM_FILELIST := $(SIM_FILELIST) -f $(SMART_RUN_ROOT)/logical/filelists/sim.fl
    endif
endif

prepare-work:
	@mkdir -p "$(BUILD_DIR)" "$(RUN_DIR)"
	@rm -f "$(WORK_ROOT)/build/logical" "$(WORK_ROOT)/build/tests" "$(WORK_ROOT)/build/impl"
	@rm -f "$(WORK_ROOT)/runs/logical" "$(WORK_ROOT)/runs/tests" "$(WORK_ROOT)/runs/impl"

compile: prepare-work
	@echo "  [THead-smart] Compiling smart now ... "
	@echo "  [THead-smart] SIM = $(SIM)"
	@echo "  [THead-smart] BUILD_DIR = $(BUILD_DIR)"
ifeq ($(SIM), vcs)
	@current_config=$$(cat "$(BUILD_DIR)/.build-config" 2>/dev/null || true); \
	newer_source=$$(find ./logical ./setup "$(CODE_BASE_PATH)" -type f \
	  -newer "$(BUILD_DIR)/simv" -print -quit 2>/dev/null); \
	if [ "$(REBUILD)" = "on" ] || [ ! -x "$(BUILD_DIR)/simv" ] || \
	    [ "$$current_config" != "$(BUILD_CONFIG)" ] || [ -n "$$newer_source" ]; then \
	  $(MAKE) -s cleansim; \
	  printf '%s\n' '$(BUILD_CONFIG)' > "$(BUILD_DIR)/.build-config"; \
	  cd "$(BUILD_DIR)" && vcs $(SIMULATOR_OPT) $(TIMESCALE) $(SIMULATOR_DEF) $(SIM_FILELIST) $(SIM_DUMP) $(SIMULATOR_LOG) $(SIMULATOR_POWER_OPT) $(SIMULATOR_COV_OPT); \
	else \
	  echo "  [THead-smart] Reusing $(BUILD_DIR)/simv"; \
	fi
else
    ifeq ($(SIM), nc)
	@cd "$(BUILD_DIR)" && irun $(SIMULATOR_OPT) $(TIMESCALE) $(SIMULATOR_DEF) $(SIM_FILELIST) $(SIM_DUMP) $(SIMULATOR_LOG)
    else
        ifeq ($(SIM), iverilog)
	  @cd "$(BUILD_DIR)" && iverilog $(TIMESCALE) $(SIMULATOR_OPT) $(SIMULATOR_DEF) $(SIM_FILELIST) $(SIM_DUMP) $(SIMULATOR_LOG)
        else
            ifeq ($(SIM), verilator)
	      @cd "$(BUILD_DIR)" && verilator $(SIMULATOR_OPT) $(SIMULATOR_DEF) $(SIMULATOR_LOG) $(SIM_FILELIST) $(SIM_DUMP)
            else
	      @echo "  [THead-smart] Please specify SIM = vcs to use VCS, or SIM = nc ,or SIM = verilator to use irun ..."
            endif
        endif
    endif
endif

buildVerilator: prepare-work
	@cp ./logical/tb/Makefile_obj "$(BUILD_DIR)/Makefile_obj"
	@cd "$(BUILD_DIR)" && make -j -C obj_dir -f ../Makefile_obj
cleansim: prepare-work
	@cd "$(BUILD_DIR)" && rm -rf simv* csrc ucli.key *.vcs.log novas_dump.log *.fsdb $(COV_DIR) $(COV_REPORT_DIR) .build-config
cleanVerilator: prepare-work
	@cd "$(BUILD_DIR)" && rm -rf obj_dir/

################################################################################
# Cases related
################################################################################
showcase:
	@echo "  Case lists:" \
	@for case in $(CASE_LIST) ; do \
          echo "    $$case"; \
        done

buildcase: tool-chain-chk prepare-work
ifeq ($(CASE),)
	$(error Please specify CASE=xxx on the command line, like: \
        $(newline)   > make buildcase CASE=xxx... \
        $(newline)   The list of valid cases can be obtained by executing: \
        $(newline)   > make showcase ...)
endif
ifeq ($(findstring $(CASE), $(CASE_LIST)), $(CASE))
	@make -s cleancase
	@make -s $(CASE)_build
else
	$(error Argument CASE=xxx is not valid: \
        $(newline)   The list of valid cases can be obtained by executing: \
        $(newline)   > make showcase ...)
endif


cleancase: prepare-work
	@cd "$(RUN_DIR)" && rm -rf *.s *.S *.c *.o *.pat *.h *.lcf *.hex *.obj *.vh *.v *.report *.elf Makefile *.case.log $(COV_DIR) $(COV_REPORT_DIR) *.vcs.log run.meta

prunecase: prepare-work
	@cd "$(RUN_DIR)" && rm -rf *.o *.pat *.h *.lcf *.hex *.obj *.elf Makefile *.case.log cm.log ucli.key
	@find "$(RUN_DIR)" -maxdepth 1 -type f \( -name '*.c' -o -name '*.S' -o -name '*.s' -o -name '*.v' -o -name '*.vh' \) -delete
	@find "$(CASE_SOURCE_DIR)" -maxdepth 1 -type f \( -name '*.c' -o -name '*.S' -o -name '*.s' -o -name '*.v' -o -name '*.vh' \) -exec cp {} "$(RUN_DIR)" \;

################################################################################
# Combined flows
################################################################################
# Execute one case
runVerilator: prepare-work
	@cd "$(RUN_DIR)" && "$(abspath $(BUILD_DIR))/obj_dir/Vtop"

runcase: prepare-work
	@make cleanVerilator
ifeq ($(CASE),)
	$(error Please specify CASE=xxx on the command line, like: \
        $(newline)   > make buildcase CASE=xxx... \
        $(newline)   The list of valid cases can be obtained by executing: \
        $(newline)   > make showcase ...)
endif
ifeq ($(findstring $(CASE), $(CASE_LIST)), $(CASE))
	@make -s compile
	@make -s buildcase CASE=$(CASE)
ifeq ($(COV), on)
	@cp -a "$(BUILD_DIR)/$(COV_DIR)" "$(RUN_DIR)/$(COV_DIR)"
endif
ifeq ($(SIM), vcs)
	cd "$(RUN_DIR)" && "$(abspath $(BUILD_DIR))/simv" -l run.vcs.log $(SIMV_POWER_OPT) $(SIMV_COV_OPT)
else
        ifeq ($(SIM), nc)
		cd "$(RUN_DIR)" && irun -R -l run.irun.log
        else
            ifeq ($(SIM), verilator)
			make buildVerilator
			cd "$(RUN_DIR)" && "$(abspath $(BUILD_DIR))/obj_dir/Vtop"
            else
	        cd "$(RUN_DIR)" && vvp "$(abspath $(BUILD_DIR))/xuantie_core.vvp"
            endif
        endif
endif
	@printf '%s\n' \
	  'CASE=$(CASE)' \
	  'BUILD_KEY=$(BUILD_KEY)' \
	  'BUILD_CONFIG=$(BUILD_CONFIG)' \
	  "GIT_COMMIT=$$(git rev-parse HEAD 2>/dev/null || echo unknown)" \
	  > "$(RUN_DIR)/run.meta"
ifeq ($(COV), on)
	@$(MAKE) -s coverage CASE=$(CASE) SIM=$(SIM) COV=$(COV)
endif
	@$(MAKE) -s prunecase CASE=$(CASE)
else
	$(error Argument CASE=xxx is not valid: \
        $(newline)   The list of valid cases can be obtained by executing: \
        $(newline)   > make showcase ...)
endif

# Execute all cases
regress: prepare-work
	rm -rf ./tests/regress/regress_result/*
	@(for case in $(CASE_LIST) ; do \
	 make -s runcase CASE=$$case; \
	 cp ./work/runs/$$case/run_case.report ./tests/regress/regress_result/$$case.report; \
	 done)
	cd ./tests/regress && perl report_gen.pl
	cat ./tests/regress/regress_report

################################################################################
# riscv-dv generated cases
################################################################################
dv-show:
	@python3 ./dv/testlist.py "$(DV_TESTLIST)"

check-dv-args:
	@test -n "$(DV_TEST)" || { echo "DV_TEST is required; run 'make dv-show'" >&2; exit 2; }
	@printf '%s' "$(DV_TEST)" | grep -Eq '^[a-z0-9_]+$$' || { echo "Invalid DV_TEST: $(DV_TEST)" >&2; exit 2; }
	@printf '%s' "$(SEED)" | grep -Eq '^[1-9][0-9]*$$' || { echo "SEED must be a positive integer" >&2; exit 2; }
	@python3 ./dv/testlist.py "$(DV_TESTLIST)" "$(DV_TEST)"

dv-compile:
	@mkdir -p "$(DV_BUILD_DIR)"
	@current_config=$$(cat "$(DV_BUILD_DIR)/.build-config" 2>/dev/null || true); \
	dv_source_hash=$$({ \
	  find "$(DV_ROOT)/src" "$(DV_ROOT)/target/$(DV_TARGET)" \
	    "$(DV_ROOT)/user_extension" "$(DV_ROOT)/yaml" -type f -print0; \
	  printf '%s\0' "$(DV_ROOT)/run.py"; \
	} | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1); \
	wanted_config="DV_COMMIT=$$(git -C "$(DV_ROOT)" rev-parse HEAD) DV_SOURCE=$$dv_source_hash TARGET=$(DV_TARGET)"; \
	if [ "$(REBUILD)" = "on" ] || [ ! -x "$(DV_BUILD_DIR)/vcs_simv" ] || [ "$$current_config" != "$$wanted_config" ]; then \
	  rm -rf "$(DV_BUILD_DIR)/vcs_simv" "$(DV_BUILD_DIR)/vcs_simv.daidir" "$(DV_BUILD_DIR)/vcs_simv.csrc"; \
	  cd "$(DV_ROOT)" && python3 run.py \
	    --custom_target "target/$(DV_TARGET)" \
	    --test all --simulator vcs --steps gen --co \
	    --isa rv64imafdcxtheadc --mabi lp64d \
	    --output "$(abspath $(DV_BUILD_DIR))"; \
	  printf '%s\n' "$$wanted_config" > "$(abspath $(DV_BUILD_DIR))/.build-config"; \
	else \
	  echo "  [riscv-dv] Reusing $(DV_BUILD_DIR)/vcs_simv"; \
	fi

DV_GENERATE_DEPS = check-dv-args dv-compile
ifeq ($(DV_PREBUILT),on)
DV_GENERATE_DEPS = check-dv-args check-dv-prebuilt
endif

check-dv-prebuilt:
	@test -x "$(WORK_ROOT)/build/default/simv" || { echo "Missing prebuilt RTL simulator" >&2; exit 2; }
	@test -d "$(WORK_ROOT)/build/default/$(COV_DIR)" || { echo "Missing prebuilt coverage database" >&2; exit 2; }
	@test -x "$(DV_BUILD_DIR)/vcs_simv" || { echo "Missing prebuilt riscv-dv generator" >&2; exit 2; }
	@grep -q 'SIM=vcs COV=on' "$(WORK_ROOT)/build/default/.build-config" || { \
	  echo "RTL simulator was not compiled with VCS coverage" >&2; exit 2; }

dv-preflight: check-dv-args
	@$(MAKE) -s compile CASE="$(DV_CASE)" SIM=vcs COV=on
	@$(MAKE) -s dv-compile
	@$(MAKE) -s check-dv-prebuilt

dv-generate: $(DV_GENERATE_DEPS)
	@rm -rf "$(DV_RUN_DIR)"
	@mkdir -p "$(DV_GEN_DIR)"
	@ln -s "$(abspath $(DV_BUILD_DIR))/vcs_simv" "$(DV_GEN_DIR)/vcs_simv"
	@if [ -d "$(DV_BUILD_DIR)/vcs_simv.daidir" ]; then \
	  ln -s "$(abspath $(DV_BUILD_DIR))/vcs_simv.daidir" "$(DV_GEN_DIR)/vcs_simv.daidir"; \
	fi
	@cd "$(DV_ROOT)" && python3 run.py \
	  --custom_target "target/$(DV_TARGET)" \
	  --test "$(DV_TEST)" --simulator vcs --steps gen --so \
	  --seed "$(SEED)" --isa rv64imafdcxtheadc --mabi lp64d \
	  --output "$(abspath $(DV_GEN_DIR))"
	@cp "$(DV_GEN_DIR)/asm_test/$(DV_TEST)_0.S" "$(DV_SOURCE)"
	@cp "$(DV_GEN_DIR)/sim_$(DV_TEST)_0.log" "$(DV_RUN_DIR)/dv-generate.log"
	@if [ "$(DV_TEST)" = "c910_compressed_instr_test" ]; then \
	  python3 "$(DV_ROOT)/target/$(DV_TARGET)/check_generated_asm.py" \
	    --group bounded-compressed "$(DV_SOURCE)"; \
	fi

dv-buildcase: check-dv-args tool-chain-chk
	@test -f "$(DV_SOURCE)" || { echo "Missing generated source: $(DV_SOURCE)" >&2; exit 2; }
	@cd "$(DV_RUN_DIR)" && "$(TOOL_EXTENSION)/riscv64-unknown-elf-gcc" \
	  -static -mcmodel=medany -fvisibility=hidden -nostdlib -nostartfiles \
	  -I"$(DV_ROOT)/target/$(DV_TARGET)" -I"$(DV_ROOT)/user_extension" \
	  -T"$(abspath ./dv/c910.ld)" -march=rv64imafdcxtheadc -mabi=lp64d \
	  -Wl,--defsym=tohost=0x$(DV_TOHOST_HEX) \
	  "$(notdir $(DV_SOURCE))" -o dv_test.elf
	@cd "$(DV_RUN_DIR)" && "$(TOOL_EXTENSION)/riscv64-unknown-elf-nm" dv_test.elf | \
	  awk '$$3 == "tohost" { print substr($$1, length($$1) - 7) }' > dv_tohost.addr
	@test "$$(cat "$(DV_RUN_DIR)/dv_tohost.addr")" = "$(DV_TOHOST_HEX)" || { \
	  echo "Generated ELF has an unexpected tohost address" >&2; exit 2; }
	@cd "$(DV_RUN_DIR)" && "$(TOOL_EXTENSION)/riscv64-unknown-elf-objcopy" \
	  -O srec dv_test.elf inst.hex -j .text -j .rodata
	@cd "$(DV_RUN_DIR)" && "$(TOOL_EXTENSION)/riscv64-unknown-elf-objcopy" \
	  -O srec dv_test.elf data.hex -j .data -j .test_data -j .bss
	@cd "$(DV_RUN_DIR)" && "$(abspath ./tests/bin/Srec2vmem)" inst.hex inst.pat
	@cd "$(DV_RUN_DIR)" && "$(abspath ./tests/bin/Srec2vmem)" data.hex data.pat

dv-simcase: check-dv-args check-dv-prebuilt
	@$(MAKE) -s dv-generate DV_TEST="$(DV_TEST)" SEED="$(SEED)"
	@$(MAKE) -s dv-buildcase DV_TEST="$(DV_TEST)" SEED="$(SEED)"
	@rm -rf "$(DV_RUN_DIR)/$(COV_DIR)"
	@cp -a "$(WORK_ROOT)/build/default/$(COV_DIR)" "$(DV_RUN_DIR)/$(COV_DIR)"
	@cd "$(DV_RUN_DIR)" && "$(abspath $(WORK_ROOT)/build/default)/simv" \
	  -l run.vcs.log -cm $(COV_METRICS) -cm_dir $(COV_DIR) \
	  +DV_TOHOST=$(DV_TOHOST_HEX)
	@test "$$(cat "$(DV_RUN_DIR)/run_case.report" 2>/dev/null)" = "TEST PASS" || { \
	  echo "riscv-dv case failed: $(DV_CASE)" >&2; exit 1; }
	@printf '%s\n' \
	    'CASE=$(DV_CASE)' \
	    'DV_TEST=$(DV_TEST)' \
	    'SEED=$(SEED)' \
	    'DV_TOHOST=0x$(DV_TOHOST_HEX)' \
	    "OPENC910_COMMIT=$$(git rev-parse HEAD)" \
	    "RISCV_DV_COMMIT=$$(git -C "$(DV_ROOT)" rev-parse HEAD)" \
	    > "$(DV_RUN_DIR)/run.meta"
	@rm -rf "$(DV_GEN_DIR)" "$(DV_RUN_DIR)/dv_test.elf" \
	  "$(DV_RUN_DIR)/inst.hex" "$(DV_RUN_DIR)/data.hex" \
	  "$(DV_RUN_DIR)/inst.pat" "$(DV_RUN_DIR)/data.pat" \
	  "$(DV_RUN_DIR)/dv_tohost.addr" "$(DV_RUN_DIR)/cm.log" \
	  "$(DV_RUN_DIR)/ucli.key"

dv-reportcase: check-dv-args
	@test "$$(cat "$(DV_RUN_DIR)/run_case.report" 2>/dev/null)" = "TEST PASS" || { \
	  echo "Cannot report failed case: $(DV_CASE)" >&2; exit 1; }
	@test -d "$(DV_RUN_DIR)/$(COV_DIR)" || { echo "Missing coverage database: $(DV_CASE)" >&2; exit 2; }
	@rm -rf "$(DV_RUN_DIR)/$(COV_REPORT_DIR)"
	@$(MAKE) -s coverage CASE="$(DV_CASE)" SIM=vcs COV=on

dv-runcase: check-dv-args
	@$(MAKE) -s dv-preflight DV_TEST="$(DV_TEST)" SEED="$(SEED)"
	@$(MAKE) -s dv-simcase DV_TEST="$(DV_TEST)" SEED="$(SEED)" DV_PREBUILT=on
	@$(MAKE) -s dv-reportcase DV_TEST="$(DV_TEST)" SEED="$(SEED)"

dv-regress:
	@tests="$(DV_TESTS)"; \
	if [ -z "$$tests" ] || [ "$$tests" = "all" ]; then tests="$$(python3 ./dv/testlist.py "$(DV_TESTLIST)")"; fi; \
	seeds="$(SEEDS)"; if [ -z "$$seeds" ]; then seeds=1; fi; \
	for test in $$tests; do \
	  for seed in $$seeds; do \
	    $(MAKE) -s dv-runcase DV_TEST="$$test" SEED="$$seed" || exit $$?; \
	  done; \
	done

dv-regress-parallel:
	@python3 ./dv/parallel_regress.py \
	  --testlist "$(DV_TESTLIST)" \
	  --tests "$(DV_TESTS)" \
	  --runs-per-test "$(RUNS_PER_TEST)" \
	  --jobs "$(JOBS)" \
	  --report-jobs "$(REPORT_JOBS)" \
	  --seed-base "$(SEED_BASE)" \
	  --timeout "$(DV_TIMEOUT)" \
	  --estimated-case-mib "$(ESTIMATED_CASE_MIB)" \
	  --work-root "$(abspath $(WORK_ROOT))" \
	  --regress-root "$(abspath $(REGRESS_ROOT))" \
	  --make-command "$(WORKER_MAKE)" \
	  $(if $(filter on,$(DRY_RUN)),--dry-run,) \
	  $(if $(filter on,$(FORCE)),--force,)

################################################################################
# Misc
################################################################################
.DEFAULT_GOAL := help

memlist:
	@make -s compile
	${VERDI_HOME}/share/VIA/Apps/Bin/findInstDefWild.pl -dbdir "$(BUILD_DIR)/simv.daidir" -pattern "ct_spsram*" -scope "tb.x_soc.x_cpu_sub_system_axi.x_rv_integration_platform.x_cpu_top" -dump_def_name -outlog "$(BUILD_DIR)/memlist.verdi.log"
	perl impl/memlist/memlist.pl

coverage: prepare-work
ifeq ($(CASE),)
	$(error Please specify CASE=xxx to select a run directory)
endif
ifeq ($(SIM), vcs)
ifeq ($(COV), on)
	@cd "$(RUN_DIR)" && urg -full64 -dir $(COV_DIR) -report $(COV_REPORT_DIR)
	@echo "  [THead-smart] Coverage report: $(RUN_DIR)/$(COV_REPORT_DIR)/dashboard.html"
else
	$(error Coverage is disabled. Re-run with SIM=vcs COV=on)
endif
else
	$(error Coverage reporting is supported only with SIM=vcs)
endif

clean:
	@rm -rf "$(WORK_ROOT)/build" "$(WORK_ROOT)/runs" "$(WORK_ROOT)/regress"

help:
	@echo "  ########## Smart Help Info ##########"
	@echo "  This Makefile is the entrance of T-Head Smart simulation environment"
	@echo "  Usage: make [target] [arguments]"
	@echo "  Available targets:"
	@echo "    compile                         : compile the RTL and Smart testbench"
	@echo "    showcase                        : list all valid cases"
	@echo "    buildcase CASE=[casename]       : compile a C/assembly case"
	@echo "    runcase CASE=[casename]         : compile and run a case; report coverage when COV=on"
	@echo "    regress                         : run all cases and summarize results"
	@echo "    dv-show                         : list OpenC910 riscv-dv tests"
	@echo "    dv-runcase DV_TEST=[test] SEED=[seed] : generate, simulate, and report coverage"
	@echo "    dv-regress DV_TESTS=[tests] SEEDS=[seeds] : run generated coverage cases"
	@echo "    dv-regress-parallel              : run resumable parallel DV coverage regression"
	@echo "    coverage                        : generate the VCS coverage report"
	@echo "    memlist                         : generate the SRAM list with VCS/Verdi"
	@echo "    cleansim / cleancase / clean    : remove generated files"
	@echo "  Optional arguments:"
	@echo "    SIM=                            : vcs / nc / iverilog / verilator"
	@echo "    CASE=                           : one of the cases printed by 'make showcase'"
	@echo "    DUMP=                           : on / off"
	@echo "    COV=                            : on / off (VCS only)"
	@echo "    REBUILD=                        : on / off (force simulator rebuild)"
	@echo "    THREADS=                        : Verilator thread count"
	@echo "    RUNS_PER_TEST=                  : parallel runs per DV test (default: 50)"
	@echo "    JOBS= / REPORT_JOBS=            : simulation/report concurrency (defaults: 50/8)"
	@echo "    SEED_BASE= / DV_TIMEOUT=         : first seed and per-stage timeout in seconds"
	@echo "    DRY_RUN=on                      : write and display the parallel plan only"
	@echo "    FORCE=on                        : rerun complete test+seed cases"
	@echo "  Examples:"
	@echo "    make runcase CASE=hello_world SIM=vcs"
	@echo "    make runcase CASE=hello_world SIM=vcs COV=on"
	@echo "    make coverage CASE=hello_world SIM=vcs COV=on"
	@echo "    make dv-runcase DV_TEST=c910_integer_arithmetic_test SEED=1"
	@echo "    make dv-regress-parallel DV_TESTS=all RUNS_PER_TEST=50 JOBS=50"
	@echo "    make runcase CASE=coremark SIM=verilator THREADS=8"

.PHONY: prepare-work compile buildVerilator cleansim cleanVerilator showcase \
	buildcase cleancase prunecase runVerilator runcase regress memlist coverage \
	dv-show check-dv-args check-dv-prebuilt dv-preflight dv-compile dv-generate \
	dv-buildcase dv-simcase dv-reportcase dv-runcase dv-regress \
	dv-regress-parallel \
	clean help
