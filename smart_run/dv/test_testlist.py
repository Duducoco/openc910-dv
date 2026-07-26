#!/usr/bin/env python3

import pathlib
import re
import subprocess
import tempfile
import unittest

import yaml


TESTLIST = pathlib.Path(__file__).parents[2] / "riscv-dv/target/c910/testlist.yaml"
SMART_RUN = pathlib.Path(__file__).parents[1]
MAKEFILE = SMART_RUN / "Makefile"
LINKER_SCRIPT = SMART_RUN / "dv/c910.ld"
TESTBENCH = SMART_RUN / "logical/tb/tb.v"


class C910TestlistTest(unittest.TestCase):
    def setUp(self):
        self.tests = yaml.safe_load(TESTLIST.read_text(encoding="utf-8"))

    def test_covers_core_instruction_design_spaces(self):
        required = {
            "integer",
            "multiply_divide",
            "compressed",
            "branch_prediction",
            "load_store",
            "load_store_hazard",
            "unaligned",
            "atomic",
            "floating_point",
            "fence",
            "csr",
            "exception",
            "xthead_scalar",
            "xthead_memory",
            "cache",
            "synchronization",
            "mixed_random",
            "integer_corner",
            "shift",
            "logical",
            "compare",
            "jump",
            "loop",
            "call_return",
            "non_compressed",
            "hint",
            "single_load_store",
            "back_to_back_load_store",
            "multi_page_memory",
            "memory_region",
            "lr_sc",
            "amo",
            "floating_single",
            "floating_double",
            "floating_control_flow",
            "csr_stress",
            "illegal_csr",
            "ebreak",
            "instruction_misaligned",
            "illegal_instruction",
            "xthead_arithmetic",
            "xthead_logical",
            "xthead_register_offset",
            "xthead_pair_memory",
            "xthead_indexed_memory",
            "xthead_fp_memory",
            "dcache",
            "icache",
            "l2cache",
        }
        covered = {
            tag
            for test in self.tests
            for tag in test.get("coverage_tags", [])
        }
        self.assertEqual(set(), required - covered)
        self.assertGreaterEqual(len(self.tests), 40)

    def test_every_rtl_test_is_reproducible_and_c910_compatible(self):
        for test in self.tests:
            with self.subTest(test=test["test"]):
                self.assertIn("iterations", test)
                self.assertEqual(1, test["no_iss"])
                self.assertIn("-march=rv64imafdcxtheadc", test["gcc_opts"])
                self.assertIn("-mabi=lp64d", test["gcc_opts"])
                self.assertIn("+boot_mode=m", test["gen_opts"])
                if "hint" in test.get("coverage_tags", []):
                    self.assertNotIn("+hint_instr_ratio=0", test["gen_opts"])
                else:
                    self.assertIn("+hint_instr_ratio=0", test["gen_opts"])
                if "exception" in test.get("coverage_tags", []):
                    self.assertNotIn("+bare_program_mode=1", test["gen_opts"])
                else:
                    self.assertIn("+bare_program_mode=1", test["gen_opts"])
                if "illegal_instruction" in test.get("coverage_tags", []):
                    self.assertNotIn("+illegal_instr_ratio=0", test["gen_opts"])
                else:
                    self.assertIn("+illegal_instr_ratio=0", test["gen_opts"])

    def test_instruction_counts_provide_a_coverage_depth_ladder(self):
        expected_ladder = {
            "c910_coverage_ladder_tiny_test": 20,
            "c910_coverage_ladder_short_test": 100,
            "c910_coverage_ladder_medium_test": 1000,
            "c910_coverage_ladder_long_test": 5000,
            "c910_coverage_ladder_extended_test": 15000,
        }
        tests_by_name = {test["test"]: test for test in self.tests}
        common_options = None

        for name, expected_count in expected_ladder.items():
            with self.subTest(test=name):
                test = tests_by_name[name]
                match = re.search(r"\+instr_cnt=(\d+)", test["gen_opts"])
                self.assertIsNotNone(match)
                self.assertEqual(expected_count, int(match.group(1)))
                self.assertIn("coverage_ladder", test["coverage_tags"])
                options_without_count = re.sub(
                    r"\s*\+instr_cnt=\d+\s*", "\n", test["gen_opts"]
                ).strip()
                if common_options is None:
                    common_options = options_without_count
                else:
                    self.assertEqual(common_options, options_without_count)

    def test_compressed_smoke_test_has_bounded_control_flow(self):
        tests_by_name = {test["test"]: test for test in self.tests}
        compressed = tests_by_name["c910_compressed_instr_test"]
        options = compressed["gen_opts"]

        self.assertIn("compressed", compressed["coverage_tags"])
        self.assertIn("+march=RV32I,RV64I,RV32C,RV64C", options)
        self.assertIn("+num_of_sub_program=0", options)
        self.assertIn("+no_branch_jump=1", options)
        self.assertIn("+no_load_store=1", options)
        self.assertNotIn("+disable_compressed_instr=1", options)

    def test_load_store_smoke_test_has_bounded_control_flow(self):
        tests_by_name = {test["test"]: test for test in self.tests}
        load_store = tests_by_name["c910_load_store_test"]
        options = load_store["gen_opts"]

        self.assertIn("load_store", load_store["coverage_tags"])
        self.assertIn("+num_of_sub_program=0", options)
        self.assertIn("+no_branch_jump=1", options)
        self.assertNotIn("+no_load_store=1", options)

    def test_execution_domains_have_comparable_depth_ladders(self):
        domains = {
            "branch": ("branch_prediction", (200, 1000, 10000)),
            "load_store": ("load_store_hazard", (200, 1000, 5000, 10000)),
            "integer": ("multiply_divide", (200, 500, 1000, 2000, 5000, 10000)),
        }
        tests_by_name = {test["test"]: test for test in self.tests}

        for domain, (required_tag, expected_depths) in domains.items():
            common_options = None
            for depth in expected_depths:
                name = f"c910_{domain}_depth_{depth}_test"
                with self.subTest(domain=domain, depth=depth):
                    test = tests_by_name[name]
                    self.assertIn("execution_domain_ladder", test["coverage_tags"])
                    self.assertIn(required_tag, test["coverage_tags"])
                    self.assertIn(f"depth_{depth}", test["coverage_tags"])
                    self.assertIn(f"+instr_cnt={depth}", test["gen_opts"])
                    options_without_count = re.sub(
                        r"\s*\+instr_cnt=\d+\s*", "\n", test["gen_opts"]
                    ).strip()
                    if common_options is None:
                        common_options = options_without_count
                    else:
                        self.assertEqual(common_options, options_without_count)

    def test_diversity_expansion_reaches_one_hundred_distinct_tests(self):
        expected_groups = {
            "integer_control_expansion": 7,
            "memory_atomic_expansion": 8,
            "floating_point_expansion": 5,
            "csr_exception_expansion": 5,
            "compressed_mixed_expansion": 5,
            "xthead_expansion": 8,
        }
        expanded = [
            test
            for test in self.tests
            if "diversity_expansion" in test.get("coverage_tags", [])
        ]

        self.assertEqual(100, len(self.tests))
        self.assertEqual(sum(expected_groups.values()), len(expanded))
        for group, expected_count in expected_groups.items():
            with self.subTest(group=group):
                actual_count = sum(
                    group in test.get("coverage_tags", []) for test in expanded
                )
                self.assertEqual(expected_count, actual_count)

        signatures = {
            (test["gen_test"], test["gcc_opts"], test["gen_opts"])
            for test in expanded
        }
        self.assertEqual(len(expanded), len(signatures))

    def test_names_are_safe_for_run_directories(self):
        names = [test["test"] for test in self.tests]
        self.assertEqual(len(names), len(set(names)))
        for test in self.tests:
            with self.subTest(test=test["test"]):
                self.assertRegex(test["test"], r"^[a-z0-9_]+$")

    def test_make_interface_lists_dv_tests(self):
        result = subprocess.run(
            ["make", "-s", "dv-show"],
            cwd=SMART_RUN,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("c910_integer_arithmetic_test", result.stdout)
        self.assertIn("c910_xthead_cache_sync_test", result.stdout)

    def test_make_help_documents_dv_entrypoint(self):
        result = subprocess.run(
            ["make", "-s", "help"],
            cwd=SMART_RUN,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("dv-runcase DV_TEST=[test] SEED=[seed]", result.stdout)

    def test_parallel_regression_dry_run_builds_unique_seed_matrix(self):
        result = subprocess.run(
            [
                "make",
                "-s",
                "dv-regress-parallel",
                "DV_TESTS=c910_integer_arithmetic_test c910_branch_jump_test",
                "RUNS_PER_TEST=3",
                "JOBS=50",
                "REPORT_JOBS=8",
                "SEED_BASE=100",
                "DRY_RUN=on",
            ],
            cwd=SMART_RUN,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("Tests: 2", result.stdout)
        self.assertIn("Runs per test: 3", result.stdout)
        self.assertIn("Planned cases: 6", result.stdout)
        self.assertIn("Seed range: 100..105", result.stdout)
        self.assertIn("Simulation jobs: 50", result.stdout)
        self.assertIn("Report jobs: 8", result.stdout)
        self.assertIn("Stage timeout: 600s", result.stdout)

    def test_parallel_regression_writes_reproducible_manifest(self):
        with tempfile.TemporaryDirectory() as regress_root:
            result = subprocess.run(
                [
                    "make",
                    "-s",
                    "dv-regress-parallel",
                    "DV_TESTS=c910_integer_arithmetic_test c910_branch_jump_test",
                    "RUNS_PER_TEST=2",
                    "SEED_BASE=700",
                    "DRY_RUN=on",
                    f"REGRESS_ROOT={regress_root}",
                ],
                cwd=SMART_RUN,
                check=True,
                capture_output=True,
                text=True,
            )

            manifest_line = next(
                line for line in result.stdout.splitlines() if line.startswith("Manifest: ")
            )
            manifest = pathlib.Path(manifest_line.removeprefix("Manifest: "))
            self.assertEqual(pathlib.Path(regress_root), manifest.parent.parent)
            self.assertEqual(
                [
                    "test\tseed\tcase",
                    "c910_integer_arithmetic_test\t700\tdv_c910_integer_arithmetic_test_seed_700",
                    "c910_integer_arithmetic_test\t701\tdv_c910_integer_arithmetic_test_seed_701",
                    "c910_branch_jump_test\t702\tdv_c910_branch_jump_test_seed_702",
                    "c910_branch_jump_test\t703\tdv_c910_branch_jump_test_seed_703",
                ],
                manifest.read_text(encoding="utf-8").splitlines(),
            )

    def test_parallel_regression_skips_complete_case_unless_forced(self):
        test_name = "c910_integer_arithmetic_test"
        seed = 77
        with tempfile.TemporaryDirectory() as work_root:
            run_dir = pathlib.Path(work_root) / "runs" / f"dv_{test_name}_seed_{seed}"
            (run_dir / "coverage.vdb").mkdir(parents=True)
            (run_dir / "coverage_report").mkdir()
            (run_dir / f"{test_name}_seed_{seed}.S").write_text("", encoding="utf-8")
            (run_dir / "run_case.report").write_text("TEST PASS\n", encoding="utf-8")
            (run_dir / "coverage_report/dashboard.html").write_text("", encoding="utf-8")
            common_args = [
                "make",
                "-s",
                "dv-regress-parallel",
                f"DV_TESTS={test_name}",
                "RUNS_PER_TEST=1",
                f"SEED_BASE={seed}",
                "DRY_RUN=on",
                f"WORK_ROOT={work_root}",
                f"REGRESS_ROOT={work_root}/regress",
            ]

            resumed = subprocess.run(
                common_args,
                cwd=SMART_RUN,
                check=True,
                capture_output=True,
                text=True,
            )
            forced = subprocess.run(
                common_args + ["FORCE=on"],
                cwd=SMART_RUN,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("Cases to simulate: 0", resumed.stdout)
            self.assertIn("Force rerun: off", resumed.stdout)
            self.assertIn("Cases to simulate: 1", forced.stdout)
            self.assertIn("Force rerun: on", forced.stdout)

    def test_parallel_regression_reports_completed_case_while_simulations_continue(self):
        with tempfile.TemporaryDirectory() as work_root:
            helper = pathlib.Path(work_root) / "fake_make.py"
            helper.write_text(
                """#!/usr/bin/env python3
import pathlib
import sys
import time

work_root = pathlib.Path(sys.argv[sys.argv.index("--work-root") + 1])
target = next(
    arg for arg in sys.argv if arg in ("dv-preflight", "dv-simcase", "dv-reportcase")
)
values = dict(arg.split("=", 1) for arg in sys.argv if "=" in arg)
if target == "dv-preflight":
    raise SystemExit(0)

test = values["DV_TEST"]
seed = int(values["SEED"])
case = f"dv_{test}_seed_{seed}"
run_dir = work_root / "runs" / case
run_dir.mkdir(parents=True, exist_ok=True)
events = work_root / "events.log"

if target == "dv-simcase":
    time.sleep(0.1 if seed == 900 else 1.0)
    (run_dir / f"{test}_seed_{seed}.S").write_text("", encoding="utf-8")
    (run_dir / "coverage.vdb").mkdir(exist_ok=True)
    (run_dir / "run_case.report").write_text("TEST PASS\\n", encoding="utf-8")
    with events.open("a", encoding="utf-8") as event_file:
        event_file.write(f"sim:{seed}\\n")
else:
    with events.open("a", encoding="utf-8") as event_file:
        event_file.write(f"report:{seed}\\n")
    (run_dir / "coverage_report").mkdir(exist_ok=True)
    (run_dir / "coverage_report/dashboard.html").write_text("", encoding="utf-8")
""",
                encoding="utf-8",
            )
            make_command = f"python3 {helper} --work-root {work_root}"
            result = subprocess.run(
                [
                    "make",
                    "-s",
                    "dv-regress-parallel",
                    "DV_TESTS=c910_integer_arithmetic_test c910_branch_jump_test",
                    "RUNS_PER_TEST=1",
                    "JOBS=2",
                    "REPORT_JOBS=1",
                    "SEED_BASE=900",
                    "DV_TIMEOUT=10",
                    "ESTIMATED_CASE_MIB=1",
                    f"WORK_ROOT={work_root}",
                    f"REGRESS_ROOT={work_root}/regress",
                    f"WORKER_MAKE={make_command}",
                ],
                cwd=SMART_RUN,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

            events = (pathlib.Path(work_root) / "events.log").read_text().splitlines()
            self.assertLess(events.index("report:900"), events.index("sim:901"))

    def test_dv_completion_uses_tohost_bus_write(self):
        makefile = MAKEFILE.read_text(encoding="utf-8")
        testbench = TESTBENCH.read_text(encoding="utf-8")

        self.assertIn("--defsym=tohost=0x$(DV_TOHOST_HEX)", makefile)
        self.assertIn('+DV_TOHOST=$(DV_TOHOST_HEX)', makefile)
        self.assertIn('$value$plusargs("DV_TOHOST=%h"', testbench)
        self.assertIn("cpu_wdata[31:0] == 32'h1", testbench)
        self.assertNotIn("DV_DONE_PC", makefile + testbench)

    def test_dv_simulation_limits_retired_instructions(self):
        makefile = MAKEFILE.read_text(encoding="utf-8")
        testbench = TESTBENCH.read_text(encoding="utf-8")

        self.assertIn("DV_MAX_RETIRED ?= 1000000", makefile)
        self.assertIn("+DV_MAX_RETIRED=$(DV_MAX_RETIRED)", makefile)
        self.assertIn('$value$plusargs("DV_MAX_RETIRED=%d"', testbench)
        self.assertIn("retired-instruction limit", testbench)
        self.assertIn("`retire0_pc", testbench)
        self.assertIn('$fwrite(FILE,"TEST FAIL")', testbench)

    def test_linker_matches_testbench_memory_capacity(self):
        linker_script = LINKER_SCRIPT.read_text(encoding="utf-8")

        self.assertIn(
            "DMEM (rwx) : ORIGIN = 0x00040000, LENGTH = 0x00040000",
            linker_script,
        )


if __name__ == "__main__":
    unittest.main()
