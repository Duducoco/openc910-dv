#!/usr/bin/env python3

import argparse
import pathlib

import yaml


def load_tests(path):
    entries = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {entry["test"]: entry for entry in entries if "test" in entry}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("testlist", type=pathlib.Path)
    parser.add_argument("test", nargs="?")
    args = parser.parse_args()

    tests = load_tests(args.testlist)
    if args.test is None:
        print("\n".join(tests))
        return
    if args.test not in tests:
        parser.error(f"unknown DV test: {args.test}")


if __name__ == "__main__":
    main()
