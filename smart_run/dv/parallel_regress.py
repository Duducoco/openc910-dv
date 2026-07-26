#!/usr/bin/env python3

import argparse
import concurrent.futures
import csv
import dataclasses
import hashlib
import os
import pathlib
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time

import yaml


MAX_SEED = 2_147_483_647
SMART_RUN = pathlib.Path(__file__).resolve().parents[1]
ACTIVE_PROCESSES = set()
ACTIVE_LOCK = threading.Lock()
STOP_REQUESTED = threading.Event()


@dataclasses.dataclass(frozen=True)
class Case:
    test: str
    seed: int
    name: str


@dataclasses.dataclass(frozen=True)
class CommandResult:
    case: Case
    returncode: int
    elapsed: float
    detail: str


def positive_int(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_args():
    parser = argparse.ArgumentParser(description="Run OpenC910 DV cases in parallel")
    parser.add_argument("--testlist", type=pathlib.Path, required=True)
    parser.add_argument("--tests", default="all")
    parser.add_argument("--runs-per-test", type=positive_int, default=50)
    parser.add_argument("--jobs", type=positive_int, default=50)
    parser.add_argument("--report-jobs", type=positive_int, default=8)
    parser.add_argument("--seed-base", type=positive_int, default=1)
    parser.add_argument("--timeout", type=positive_int, default=1800)
    parser.add_argument("--estimated-case-mib", type=positive_int, default=500)
    parser.add_argument("--work-root", type=pathlib.Path, required=True)
    parser.add_argument("--regress-root", type=pathlib.Path, required=True)
    parser.add_argument("--make-command", default="make")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def load_tests(testlist, selection):
    configured = [entry["test"] for entry in yaml.safe_load(testlist.read_text())]
    requested = configured if selection.strip() in ("", "all") else selection.split()
    unknown = sorted(set(requested) - set(configured))
    if unknown:
        raise ValueError("unknown tests: " + ", ".join(unknown))
    if len(requested) != len(set(requested)):
        raise ValueError("test selection contains duplicates")
    return requested


def case_state(case, work_root):
    run_dir = work_root / "runs" / case.name
    source = run_dir / f"{case.test}_seed_{case.seed}.S"
    try:
        passed = (run_dir / "run_case.report").read_text().strip() == "TEST PASS"
    except OSError:
        passed = False
    simulated = passed and source.is_file() and (run_dir / "coverage.vdb").is_dir()
    reported = simulated and (run_dir / "coverage_report/dashboard.html").is_file()
    return simulated, reported


def terminate_process(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def request_stop(_signum=None, _frame=None):
    STOP_REQUESTED.set()
    with ACTIVE_LOCK:
        processes = tuple(ACTIVE_PROCESSES)
    for process in processes:
        terminate_process(process)


def run_make(case, target, args, log_path):
    if STOP_REQUESTED.is_set():
        return CommandResult(case, 130, 0.0, "cancelled")

    command = shlex.split(args.make_command) + [
        "-s",
        target,
        f"DV_TEST={case.test}",
        f"SEED={case.seed}",
    ]
    if target == "dv-simcase":
        command.append("DV_PREBUILT=on")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log_file:
        try:
            process = subprocess.Popen(
                command,
                cwd=SMART_RUN,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
        except OSError as error:
            log_file.write(f"failed to start command: {error}\n")
            return CommandResult(
                case, 127, time.monotonic() - started, f"start failed: {error}"
            )
        with ACTIVE_LOCK:
            ACTIVE_PROCESSES.add(process)
        try:
            process.wait(timeout=args.timeout)
            returncode = process.returncode
            detail = "pass" if returncode == 0 else f"exit {returncode}"
        except subprocess.TimeoutExpired:
            terminate_process(process)
            returncode = 124
            detail = f"timeout after {args.timeout}s"
        finally:
            with ACTIVE_LOCK:
                ACTIVE_PROCESSES.discard(process)

    return CommandResult(case, returncode, time.monotonic() - started, detail)


def run_phase(cases, jobs, target, log_suffix, args, batch_dir):
    results = {}
    if not cases:
        return results

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = {
            executor.submit(
                run_make,
                case,
                target,
                args,
                batch_dir / "logs" / f"{case.name}.{log_suffix}.log",
            ): case
            for case in cases
        }
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
            except Exception as error:
                case = futures[future]
                result = CommandResult(case, 1, 0.0, f"worker failed: {error}")
            results[result.case.name] = result
            completed += 1
            print(
                f"[{target} {completed}/{len(cases)}] "
                f"{result.case.name}: {result.detail} ({result.elapsed:.1f}s)",
                flush=True,
            )
    return results


def write_summary(path, cases, statuses):
    with path.open("w", encoding="utf-8", newline="") as summary_file:
        writer = csv.writer(summary_file, delimiter="\t", lineterminator="\n")
        writer.writerow(("test", "seed", "case", "simulation", "report", "result"))
        for case in cases:
            simulation, report, result = statuses[case.name]
            writer.writerow((case.test, case.seed, case.name, simulation, report, result))


def main():
    args = parse_args()
    args.work_root.mkdir(parents=True, exist_ok=True)
    try:
        tests = load_tests(args.testlist, args.tests)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    case_count = len(tests) * args.runs_per_test
    last_seed = args.seed_base + case_count - 1
    if last_seed > MAX_SEED:
        print(f"error: final seed {last_seed} exceeds {MAX_SEED}", file=sys.stderr)
        return 2

    cases = []
    for test_index, test in enumerate(tests):
        first_seed = args.seed_base + test_index * args.runs_per_test
        for iteration in range(args.runs_per_test):
            seed = first_seed + iteration
            cases.append(Case(test, seed, f"dv_{test}_seed_{seed}"))

    selection_hash = hashlib.sha256("\n".join(tests).encode()).hexdigest()[:12]
    batch_name = (
        f"s{args.seed_base}-{last_seed}_r{args.runs_per_test}_{selection_hash}"
    )
    batch_dir = args.regress_root / batch_name
    batch_dir.mkdir(parents=True, exist_ok=True)
    manifest = batch_dir / "manifest.tsv"
    with manifest.open("w", encoding="utf-8", newline="") as manifest_file:
        writer = csv.writer(manifest_file, delimiter="\t", lineterminator="\n")
        writer.writerow(("test", "seed", "case"))
        writer.writerows((case.test, case.seed, case.name) for case in cases)

    print(f"Tests: {len(tests)}")
    print(f"Runs per test: {args.runs_per_test}")
    print(f"Planned cases: {case_count}")
    print(f"Seed range: {args.seed_base}..{last_seed}")
    print(f"Simulation jobs: {args.jobs}")
    print(f"Report jobs: {args.report_jobs}")
    print(f"Manifest: {manifest.resolve()}")

    states = {case.name: case_state(case, args.work_root) for case in cases}
    simulation_count = sum(
        args.force or not simulated for simulated, _reported in states.values()
    )
    report_only_count = sum(
        not args.force and simulated and not reported
        for simulated, reported in states.values()
    )
    estimated_count = simulation_count + report_only_count
    estimated_bytes = estimated_count * args.estimated_case_mib * 1024 * 1024
    available_bytes = shutil.disk_usage(args.work_root).free
    print(f"Force rerun: {'on' if args.force else 'off'}")
    print(f"Cases to simulate: {simulation_count}")
    print(f"Cases needing report only: {report_only_count}")
    print(f"Estimated new storage: {estimated_bytes / 1024**4:.2f} TiB")
    print(f"Available storage: {available_bytes / 1024**4:.2f} TiB")

    if args.dry_run:
        return 0
    if available_bytes < estimated_bytes:
        print("error: insufficient free storage for estimated case output", file=sys.stderr)
        return 2

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    statuses = {}
    simulation_queue = []
    report_queue = []
    for case in cases:
        simulated, reported = states[case.name]
        if args.force:
            statuses[case.name] = ("pending", "pending", "pending")
            simulation_queue.append(case)
        elif reported:
            statuses[case.name] = ("skipped", "skipped", "pass")
        elif simulated:
            statuses[case.name] = ("reused", "pending", "pending")
            report_queue.append(case)
        else:
            statuses[case.name] = ("pending", "pending", "pending")
            simulation_queue.append(case)

    if simulation_queue:
        first_case = simulation_queue[0]
        preflight_log = batch_dir / "preflight.log"
        print("Running serial preflight build", flush=True)
        preflight = run_make(first_case, "dv-preflight", args, preflight_log)
        if preflight.returncode != 0:
            for case in simulation_queue:
                statuses[case.name] = (preflight.detail, "not-run", "fail")
            for case in report_queue:
                statuses[case.name] = ("reused", "not-run", "fail")
            summary = batch_dir / "summary.tsv"
            write_summary(summary, cases, statuses)
            print(
                f"error: preflight failed ({preflight.detail}); see {preflight_log}",
                file=sys.stderr,
            )
            print(f"Summary: {summary.resolve()}", file=sys.stderr)
            return 1

    print(
        f"Simulation phase: {len(simulation_queue)} queued, "
        f"{len(cases) - len(simulation_queue)} reusable",
        flush=True,
    )
    simulation_results = run_phase(
        simulation_queue, args.jobs, "dv-simcase", "sim", args, batch_dir
    )
    for case in simulation_queue:
        result = simulation_results[case.name]
        simulated, _reported = case_state(case, args.work_root)
        if result.returncode == 0 and simulated:
            statuses[case.name] = ("pass", "pending", "pending")
            report_queue.append(case)
        else:
            statuses[case.name] = (result.detail, "not-run", "fail")

    print(f"Report phase: {len(report_queue)} queued", flush=True)
    report_results = run_phase(
        report_queue, args.report_jobs, "dv-reportcase", "report", args, batch_dir
    )
    for case in report_queue:
        result = report_results[case.name]
        _simulated, reported = case_state(case, args.work_root)
        simulation = statuses[case.name][0]
        if result.returncode == 0 and reported:
            statuses[case.name] = (simulation, "pass", "pass")
        else:
            statuses[case.name] = (simulation, result.detail, "fail")

    summary = batch_dir / "summary.tsv"
    write_summary(summary, cases, statuses)
    passed = sum(status[2] == "pass" for status in statuses.values())
    failed = len(cases) - passed
    print(f"Passed cases: {passed}")
    print(f"Failed cases: {failed}")
    print(f"Summary: {summary.resolve()}")
    return 1 if failed or STOP_REQUESTED.is_set() else 0


if __name__ == "__main__":
    sys.exit(main())
