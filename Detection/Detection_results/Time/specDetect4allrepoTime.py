from __future__ import annotations

import os
import ast
import json
import time
import traceback
import argparse
import statistics
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any


RULES_ROOT = Path(__file__).parent / "test_rules"


def discover_available_rules(rules_root: Path) -> list[str]:
    rule_ids: list[str] = []
    for sub in sorted(rules_root.iterdir()):
        if sub.is_dir() and sub.name.startswith("R"):
            rule_ids.append(sub.name)
    return rule_ids


def import_rule(rule_id: str) -> tuple[Any, Any]:
    mod_name = f"test_rules.{rule_id}.generated_rules_{rule_id}"
    module = __import__(mod_name, fromlist=[f"rule_{rule_id}"])
    func = getattr(module, f"rule_{rule_id}")
    return module, func


def analyze_file(filepath: str, selected_rules: list[str]) -> dict[str, list[str]]:
    try:
        source = Path(filepath).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=filepath)
    except Exception as e:
        return {"PARSE_ERROR": [f"Parse error: {e}"]}

    results: dict[str, list[str]] = {}

    for rid in selected_rules:
        module, rule_func = import_rule(rid)
        messages: list[str] = []

        def report(msg: str) -> None:
            messages.append(msg)

        saved_report = getattr(module, "report", None)
        module.report = report

        try:
            add_parent_info = getattr(module, "add_parent_info", None)
            if callable(add_parent_info):
                add_parent_info(tree)

            rule_func(tree)
        except Exception:
            messages.append(f"Execution error:\n{traceback.format_exc()}")
        finally:
            if saved_report is not None:
                module.report = saved_report

        if messages:
            results[rid] = messages

    return results


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0]
    if p <= 0:
        return vals[0]
    if p >= 100:
        return vals[-1]
    k = (p / 100.0) * (len(vals) - 1)
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    if f == c:
        return vals[f]
    d0 = vals[f] * (c - k)
    d1 = vals[c] * (k - f)
    return d0 + d1


def build_timing_summary(durations: List[float]) -> dict[str, float]:
    if not durations:
        return {
            "n_files": 0,
            "total_s": 0.0,
            "mean_s": 0.0,
            "median_s": 0.0,
            "p95_s": 0.0,
            "min_s": 0.0,
            "max_s": 0.0,
        }

    return {
        "n_files": float(len(durations)),
        "total_s": float(sum(durations)),
        "mean_s": float(statistics.fmean(durations)),
        "median_s": float(statistics.median(durations)),
        "p95_s": float(_percentile(durations, 95.0)),
        "min_s": float(min(durations)),
        "max_s": float(max(durations)),
    }


def analyze_project(
    root: Path,
    rules: list[str],
    verbose: bool = True,
) -> tuple[dict[str, dict[str, list[str]]], int, dict[str, float], dict[str, float]]:
    output: dict[str, dict[str, list[str]]] = {}
    total_py_files = 0

    per_file_seconds: Dict[str, float] = {}
    durations: List[float] = []

    for dirpath, _, files in os.walk(root):
        for fname in files:
            if not fname.endswith(".py"):
                continue

            total_py_files += 1
            full = Path(dirpath) / fname

            if verbose:
                print(f"Analyzing {full}")

            t0 = time.perf_counter()
            res = analyze_file(str(full), rules)
            dt = time.perf_counter() - t0

            per_file_seconds[str(full)] = float(dt)
            durations.append(float(dt))

            if res:
                output[str(full)] = res

    summary = build_timing_summary(durations)
    return output, total_py_files, per_file_seconds, summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run SpecDetect4LLM code smell detection on a Python project."
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=Path,
        required=False,
        help="Path to the root directory of Python files to analyze",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=Path,
        default=Path("specDetectllm_results.json"),
        help="Path to write JSON results (default: specDetectllm_results.json)",
    )
    parser.add_argument(
        "--rules",
        "-r",
        nargs="+",
        metavar="RULE_ID",
        help="List of rule IDs to run (e.g. R24 R26)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all available rules",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="RULE_ID",
        help="List of rule IDs to exclude when using --all",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print summary of results per rule",
    )
    parser.add_argument(
        "--list-rules",
        action="store_true",
        help="List all available rule IDs and exit",
    )
    parser.add_argument(
        "--timings-file",
        type=Path,
        default=None,
        help="Optional path to write timings JSON. Default is <output-file>_timings.json",
    )
    parser.add_argument(
        "--print-slowest",
        type=int,
        default=0,
        help="Print the N slowest files by analysis time",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable per-file progress printing",
    )

    args = parser.parse_args()
    print(f"Starting SpecDetect4LLM analysis on project: {args.input_dir} .")

    available = discover_available_rules(RULES_ROOT)
    if args.list_rules:
        print("Available rules:")
        for r in available:
            print(f"  {r}")
        raise SystemExit(0)

    if not args.input_dir:
        print("Error: --input-dir is required unless using --list-rules.")
        raise SystemExit(1)

    if args.all:
        selected = [r for r in available if not args.exclude or r not in args.exclude]
    elif args.rules:
        selected = args.rules
    else:
        print("Error: You must specify either --rules or --all.")
        raise SystemExit(1)

    invalid = [r for r in selected if r not in available]
    if invalid:
        print(f"Error: Unknown rule IDs: {invalid}\nUse --list-rules to see available rules.")
        raise SystemExit(1)

    print(f"Analyzing {args.input_dir} with rules: {selected}")
    print("_________")

    t_project_0 = time.perf_counter()
    results, total_files, per_file_seconds, timings_summary = analyze_project(
        args.input_dir,
        selected,
        verbose=not args.quiet,
    )
    t_project_total = time.perf_counter() - t_project_0

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    with args.output_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("           ")
    print(
        f"Results written to {args.output_file} ({len(results)} files with alerts out of {total_files} total .py files)"
    )
    print(f"Wall time (project): {t_project_total:.6f} s")
    print(
        f"Sum of per-file times: {timings_summary.get('total_s', 0.0):.6f} s "
        f"(mean {timings_summary.get('mean_s', 0.0):.6f} s, p95 {timings_summary.get('p95_s', 0.0):.6f} s)"
    )

    timings_path = args.timings_file
    if timings_path is None:
        timings_path = args.output_file.with_name(args.output_file.stem + "_timings.json")

    slowest = sorted(per_file_seconds.items(), key=lambda kv: kv[1], reverse=True)
    timings_payload = {
        "summary": timings_summary,
        "per_file_seconds": per_file_seconds,
        "slowest_files": [{"path": p, "seconds": s} for p, s in slowest[: min(50, len(slowest))]],
        "wall_time_project_s": float(t_project_total),
    }

    with timings_path.open("w", encoding="utf-8") as f:
        json.dump(timings_payload, f, indent=2, ensure_ascii=False)

    print(f"Timings written to {timings_path}")

    if args.print_slowest and args.print_slowest > 0:
        n = min(args.print_slowest, len(slowest))
        print(f"\nSlowest {n} files:")
        for p, s in slowest[:n]:
            print(f"  {s:.6f} s  {p}")

    if args.summary:
        print("\n___Summary by rule___")
        rule_counts = defaultdict(int)
        for file_res in results.values():
            for rule, messages in file_res.items():
                rule_counts[rule] += len(messages)
        for rule, count in sorted(rule_counts.items()):
            print(f"  {rule}: {count} alerts")
