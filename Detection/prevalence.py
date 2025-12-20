#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Any, Set, Tuple

RULE_MIN = 25
RULE_MAX = 33


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Error: file not found: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"Error: invalid JSON in {path}: {e}")


def extract_project_id(file_path: str) -> str:
    """
    Heuristic for your local layout:
    /.../repos/<project_folder>/...
    Returns <project_folder> when possible, otherwise returns empty string.
    """
    p = file_path.replace("\\", "/")
    token = "/repos/"
    if token not in p:
        return ""
    tail = p.split(token, 1)[1]
    parts = [x for x in tail.split("/") if x]
    return parts[0] if parts else ""


def count_instances(instances: Any) -> int:
    if instances is None:
        return 0
    if isinstance(instances, list):
        return len(instances)
    if isinstance(instances, str):
        return 1
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Prevalence study from SpecDetect4LLM-style JSON output")
    parser.add_argument("input", nargs="?", default="results.json", help="Path to JSON results file")
    parser.add_argument("--total-files", type=int, default=None, help="Total analyzed files (optional)")
    parser.add_argument("--total-projects", type=int, default=None, help="Total analyzed projects (optional)")
    parser.add_argument("--out-rules", default="prevalence_by_rule.csv", help="Output CSV for per-rule prevalence")
    parser.add_argument("--out-projects", default="prevalence_by_project.csv", help="Output CSV for per-project prevalence")
    parser.add_argument("--out-summary", default="prevalence_summary.json", help="Output JSON summary")
    args = parser.parse_args()

    in_path = Path(args.input)
    data = load_json(in_path)
    if not isinstance(data, dict):
        raise SystemExit("Error: top-level JSON must be an object mapping file paths to rule dictionaries")

    rule_ids = [f"R{i}" for i in range(RULE_MIN, RULE_MAX + 1)]

    files_touched: Dict[str, Set[str]] = {rid: set() for rid in rule_ids}
    projects_touched: Dict[str, Set[str]] = {rid: set() for rid in rule_ids}
    occurrences: Dict[str, int] = {rid: 0 for rid in rule_ids}

    all_files_in_json: Set[str] = set()
    all_projects_in_json: Set[str] = set()

    project_any_occurrences: Dict[str, int] = {}
    project_files_touched: Dict[str, Set[str]] = {}
    project_rules_touched: Dict[str, Set[str]] = {}

    for file_path, rules_dict in data.items():
        if not isinstance(file_path, str):
            file_path = str(file_path)

        all_files_in_json.add(file_path)
        project_id = extract_project_id(file_path)
        if project_id:
            all_projects_in_json.add(project_id)

        if not isinstance(rules_dict, dict):
            continue

        for rid, inst in rules_dict.items():
            if rid not in occurrences:
                continue

            n = count_instances(inst)
            if n <= 0:
                continue

            files_touched[rid].add(file_path)
            occurrences[rid] += n

            if project_id:
                projects_touched[rid].add(project_id)
                project_any_occurrences[project_id] = project_any_occurrences.get(project_id, 0) + n
                project_files_touched.setdefault(project_id, set()).add(file_path)
                project_rules_touched.setdefault(project_id, set()).add(rid)

    total_files = args.total_files if args.total_files is not None else len(all_files_in_json)
    total_projects = args.total_projects if args.total_projects is not None else len(all_projects_in_json)

    any_files_touched_union: Set[str] = set()
    any_projects_touched_union: Set[str] = set()
    total_occurrences_all = 0

    for rid in rule_ids:
        any_files_touched_union |= files_touched[rid]
        any_projects_touched_union |= projects_touched[rid]
        total_occurrences_all += occurrences[rid]

    with open(args.out_rules, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "rule_id",
            "files_touched",
            "projects_touched",
            "occurrences",
            "file_prevalence_pct",
            "project_prevalence_pct",
            "avg_occurrences_per_touched_file",
        ])
        for rid in rule_ids:
            nf = len(files_touched[rid])
            np = len(projects_touched[rid])
            no = occurrences[rid]

            file_prev = (100.0 * nf / total_files) if total_files > 0 else 0.0
            proj_prev = (100.0 * np / total_projects) if total_projects > 0 else 0.0
            avg_per_file = (no / nf) if nf > 0 else 0.0

            w.writerow([rid, nf, np, no, f"{file_prev:.6f}", f"{proj_prev:.6f}", f"{avg_per_file:.6f}"])

    with open(args.out_projects, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "project_id",
            "files_touched",
            "rules_touched",
            "occurrences",
        ])
        for project_id in sorted(all_projects_in_json):
            nf = len(project_files_touched.get(project_id, set()))
            nr = len(project_rules_touched.get(project_id, set()))
            no = project_any_occurrences.get(project_id, 0)
            w.writerow([project_id, nf, nr, no])

    summary = {
        "input": str(in_path),
        "rules_range": {"min": RULE_MIN, "max": RULE_MAX},
        "totals_used_for_prevalence": {
            "total_files": total_files,
            "total_projects": total_projects,
            "note": "If you passed --total-files or --total-projects, those override totals inferred from the JSON paths",
        },
        "overall": {
            "files_touched_any_rule": len(any_files_touched_union),
            "projects_touched_any_rule": len(any_projects_touched_union),
            "occurrences_all_rules": total_occurrences_all,
            "file_prevalence_any_rule_pct": (100.0 * len(any_files_touched_union) / total_files) if total_files > 0 else 0.0,
            "project_prevalence_any_rule_pct": (100.0 * len(any_projects_touched_union) / total_projects) if total_projects > 0 else 0.0,
        },
        "per_rule_counts": {
            rid: {
                "files_touched": len(files_touched[rid]),
                "projects_touched": len(projects_touched[rid]),
                "occurrences": occurrences[rid],
            }
            for rid in rule_ids
        },
    }

    Path(args.out_summary).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Input: {in_path}")
    print(f"Total files used for prevalence: {total_files}")
    print(f"Total projects used for prevalence: {total_projects}")
    print(f"Files touched by any rule: {len(any_files_touched_union)}")
    print(f"Projects touched by any rule: {len(any_projects_touched_union)}")
    print(f"Occurrences across all rules: {total_occurrences_all}")
    print(f"Wrote: {args.out_rules}")
    print(f"Wrote: {args.out_projects}")
    print(f"Wrote: {args.out_summary}")


if __name__ == "__main__":
    main()
