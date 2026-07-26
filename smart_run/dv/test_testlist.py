#!/usr/bin/env python3

import pathlib
import subprocess
import unittest

import yaml


TESTLIST = pathlib.Path(__file__).parents[2] / "riscv-dv/target/c910/testlist.yaml"
SMART_RUN = pathlib.Path(__file__).parents[1]


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
        }
        covered = {
            tag
            for test in self.tests
            for tag in test.get("coverage_tags", [])
        }
        self.assertEqual(set(), required - covered)

    def test_every_rtl_test_is_reproducible_and_c910_compatible(self):
        for test in self.tests:
            with self.subTest(test=test["test"]):
                self.assertEqual(1, test["iterations"])
                self.assertEqual(1, test["no_iss"])
                self.assertIn("-march=rv64imafdcxtheadc", test["gcc_opts"])
                self.assertIn("-mabi=lp64d", test["gcc_opts"])
                self.assertIn("+boot_mode=m", test["gen_opts"])
                self.assertIn("+hint_instr_ratio=0", test["gen_opts"])
                if "exception" in test.get("coverage_tags", []):
                    self.assertNotIn("+bare_program_mode=1", test["gen_opts"])
                    self.assertNotIn("+illegal_instr_ratio=0", test["gen_opts"])
                else:
                    self.assertIn("+bare_program_mode=1", test["gen_opts"])
                    self.assertIn("+illegal_instr_ratio=0", test["gen_opts"])

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


if __name__ == "__main__":
    unittest.main()
