# IP Readme

  Welcome to C910! Some key directories are shown below.
```
|--C910_RTL_FACTORY/
  |--gen_rtl/     ## Verilog source code of C910
  |--setup/       ## Script to set the environment variables
|--smart_run/     ## RTL simulation environment
  |--impl/        ## SDC file, scripts and file lists for implementation
  |--logical/     ## SoC demo and test bench to run the simulation
  |--setup/       ## GNU tool chain setting
  |--tests/       ## Test driver and test cases
  |--work/        ## Working directory for builds
  |--Makefile     ## Makefile for building and running sim targets
|--doc/           ## The user and integration manual of C910
```


## Usage

  Step1: Get Started

```
$ cd C910_RTL_FACTORY
$ source setup/setup.csh
$ cd ../smart_run
$ make help
To gain more information about how to use smart testbench.
```

  Step2: Download and install C/C++ Compiler

```
You can download the GNU tool chain compiled by T-HEAD from the url below:
https://occ.t-head.cn/community/download?id=3948120165480468480

$ cd ./smart_run
GNU tool chain (specific riscv version) must be installed and specified before
compiling *.c/*.v tests of the smart environment. Please refer to the following
setup file about how to specify it:
    ./smart_run/setup/example_setup.csh
```

### Generate and simulate riscv-dv tests

The `smart_run/Makefile` can generate C910 assembly tests with `riscv-dv`, run
them on the RTL with VCS, and create an URG coverage report. Before running the
commands below, initialize the `riscv-dv` submodule, configure the RISC-V GNU
toolchain as described above, and make sure `vcs` and `urg` are in `PATH`.

```sh
$ git submodule update --init riscv-dv
$ cd smart_run
```

List all available C910 generated tests:

```sh
$ make dv-show
```

Generate one test, build it, simulate it, and collect coverage:

```sh
$ make dv-runcase DV_TEST=c910_integer_arithmetic_test SEED=1
```

`DV_TEST` must be one of the names printed by `make dv-show`. `SEED` must be a
positive integer and defaults to `1`. The same test can be reproduced by using
the same seed.

Run selected tests with one or more seeds:

```sh
$ make dv-regress \
    DV_TESTS="c910_integer_arithmetic_test c910_load_store_test" \
    SEEDS="1 2"
```

Run every test in `riscv-dv/target/c910/testlist.yaml` with the default seed:

```sh
$ make dv-regress DV_TESTS=all
```

Run all 100 tests 50 times with globally unique seeds. Simulation uses 50
workers while URG report generation is limited to 8 workers to avoid saturating
the coverage-report disk. The two worker pools run as a pipeline: each passing
simulation is submitted to URG immediately while the remaining simulations
continue:

```sh
$ make dv-regress-parallel \
    DV_TESTS=all \
    RUNS_PER_TEST=50 \
    JOBS=50 \
    REPORT_JOBS=8 \
    SEED_BASE=1 \
    DV_TIMEOUT=600
```

The seed for test index `i` and run index `j` is
`SEED_BASE + i * RUNS_PER_TEST + j`, so the default run uses seeds `1` through
`5000`. Inspect the plan without compiling or running anything with
`DRY_RUN=on`:

```sh
$ make dv-regress-parallel DRY_RUN=on
```

Each batch writes `manifest.tsv`, per-stage logs, and `summary.tsv` below
`work/regress/`. Running the same command again resumes the same batch: complete
cases are skipped. A case is complete when its generated `.S` source,
`TEST PASS` result, `coverage.vdb`, and `coverage_report/dashboard.html` all
exist. Cases with a passing simulation and `coverage.vdb` but no dashboard only
rerun URG. Resume by running the same command with the same test selection,
run count, and seed base.

Force every selected `test+seed` pair through generation, simulation, and URG
again, even when complete artifacts already exist:

```sh
$ make dv-regress-parallel \
    DV_TESTS=all \
    RUNS_PER_TEST=50 \
    JOBS=50 \
    REPORT_JOBS=8 \
    SEED_BASE=1 \
    FORCE=on
```

`DV_TIMEOUT` limits each simulation or report command in seconds.
`DV_MAX_RETIRED` defaults to 1,000,000 and fails a DV case that keeps retiring
instructions without reaching `tohost`; override it for intentionally long-running tests.
The preflight estimates 500 MiB per incomplete case by default; override this
with `ESTIMATED_CASE_MIB` when measured report sizes differ. Failed or timed-out
cases remain in `summary.tsv` and are retried by the next non-forced run.

Run the same RV64IMC stimulus configuration at five instruction depths to
compare how coverage grows from a tiny baseline to an extended run:

```sh
$ make dv-regress \
    DV_TESTS="c910_coverage_ladder_tiny_test \
              c910_coverage_ladder_short_test \
              c910_coverage_ladder_medium_test \
              c910_coverage_ladder_long_test \
              c910_coverage_ladder_extended_test" \
    SEEDS=1
```

The ladder uses `instr_cnt` values `20`, `100`, `1000`, `5000`, and `15000`.
Additional execution-domain ladders use the depth points retained after an
OpenC910 VCS coverage saturation run:

```text
Integer:    200, 500, 1000, 2000, 5000, 10000
Branch:     200, 1000, 10000
Load/store: 200, 1000, 5000, 10000
```

Their test names follow `c910_<domain>_depth_<count>_test`, where `<domain>` is
`integer`, `branch`, or `load_store`.

Floating-point behavior remains covered by the feature-oriented tests. Its
depth ladder is not enabled because the 200-instruction VCS pilot did not
complete on the current OpenC910 RTL flow.

The C910 list contains 100 tests in total. The diversity expansion adds 38
focused variants: 7 integer/control-flow, 8 memory/atomic, 5 floating-point,
5 CSR/exception, 5 compressed/mixed, and 8 XThead tests. Run `make dv-show`
to list their exact names.

The flow can also be run in separate stages when debugging generation or
linking. `dv-buildcase` expects the source produced by `dv-generate` for the
same test and seed.

```sh
$ make dv-compile
$ make dv-generate DV_TEST=c910_integer_arithmetic_test SEED=1
$ make dv-buildcase DV_TEST=c910_integer_arithmetic_test SEED=1
```

Generated artifacts use the following layout:

```text
smart_run/work/
|-- build/
|   |-- default/                 # Shared OpenC910 RTL/VCS build
|   `-- dv/c910/                 # Shared riscv-dv generator build
|-- regress/                       # Parallel manifests, logs, and summaries
`-- runs/
    `-- dv_<test>_seed_<seed>/
        |-- <test>_seed_<seed>.S # Generated test source
        |-- coverage.vdb/        # VCS coverage database
        |-- coverage_report/     # URG HTML coverage report
        |-- run.vcs.log          # RTL simulation log
        |-- run_case.report      # TEST PASS/FAIL result
        |-- run.meta             # Test, seed, and Git revisions
        `-- dv-generate.log      # riscv-dv generation log
```

The shared builds are reused between cases. Use `REBUILD=on` to force a rebuild:

```sh
$ make dv-runcase DV_TEST=c910_integer_arithmetic_test SEED=1 REBUILD=on
```


## Notes

```
The testbench supports Verilator(version is better newer than 4.215),iverilog, vcs and irun to run simulation and you can use Gtkwave or verdi
to open the waveform under ./smart_run/work/ directory.

You can get the debugger, IDE and SDK from the url:https://occ.t-head.cn/community/download?id=575997419775328256
```


## Discussion
    If you are interested in participating in discussions or improving the "openXuantie" cores, you can scan the DingDing QR code below to join the discussion group.
<img src="https://github.com/T-head-Semi/opene902/blob/main/doc/QR_code_openXuantie.png" />


/*Copyright 2019-2021 T-Head Semiconductor Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

*/
