#!/usr/bin/env python3

import pathlib
import re
import subprocess
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

    def test_names_are_safe_for_run_directories(self):
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

    def test_dv_completion_uses_tohost_bus_write(self):
        makefile = MAKEFILE.read_text(encoding="utf-8")
        testbench = TESTBENCH.read_text(encoding="utf-8")

        self.assertIn("--defsym=tohost=0x$(DV_TOHOST_HEX)", makefile)
        self.assertIn('+DV_TOHOST=$(DV_TOHOST_HEX)', makefile)
        self.assertIn('$value$plusargs("DV_TOHOST=%h"', testbench)
        self.assertIn("cpu_wdata[31:0] == 32'h1", testbench)
        self.assertNotIn("DV_DONE_PC", makefile + testbench)

    def test_linker_matches_testbench_memory_capacity(self):
        linker_script = LINKER_SCRIPT.read_text(encoding="utf-8")

        self.assertIn(
            "DMEM (rwx) : ORIGIN = 0x00040000, LENGTH = 0x00040000",
            linker_script,
        )


if __name__ == "__main__":
    unittest.main()
