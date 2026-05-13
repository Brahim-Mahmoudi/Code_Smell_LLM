from __future__ import annotations

import os
import sys
import ast
import json
import argparse
import traceback
import warnings
import re
from pathlib import Path
from collections import defaultdict
from typing import Callable, Iterable

import requests
import csv


SCRIPT_DIR = Path(__file__).resolve().parent


def find_rules_root() -> Path:
    candidates = [
        SCRIPT_DIR / "test_rules",
        SCRIPT_DIR.parents[1] / "test_rules",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


RULES_ROOT = find_rules_root()
GITHUB_API = "https://api.github.com"
API_VERSION = "2022-11-28"


class RuleHandle:
    def __init__(self, rule_id: str, module, func: Callable):
        self.rule_id = rule_id
        self.module = module
        self.func = func
        self.add_parent_info = getattr(module, "add_parent_info", None)
        self.saved_report = getattr(module, "report", None)


_RULE_CACHE: dict[str, RuleHandle] = {}


def discover_available_rules(rules_root: Path) -> list[str]:
    if not rules_root.exists():
        return []
    return [p.name for p in sorted(rules_root.iterdir()) if p.is_dir() and p.name.startswith("R")]


def import_rule_cached(rule_id: str) -> RuleHandle:
    if rule_id in _RULE_CACHE:
        return _RULE_CACHE[rule_id]

    mod_name = f"test_rules.{rule_id}.generated_rules_{rule_id}"
    module = __import__(mod_name, fromlist=[f"rule_{rule_id}"])

    func_name = f"rule_{rule_id}"
    if not hasattr(module, func_name):
        raise AttributeError(f"Module {mod_name} does not define {func_name}")

    func = getattr(module, func_name)
    if not callable(func):
        raise TypeError(f"{mod_name}.{func_name} is not callable")

    h = RuleHandle(rule_id, module, func)
    _RULE_CACHE[rule_id] = h
    return h


def analyze_source_text(virtual_path: str, source: str, selected_rules: list[str]) -> dict[str, list[str]]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source, filename=virtual_path)
    except Exception as e:
        return {"PARSE_ERROR": [f"{virtual_path}: {e}"]}

    results: dict[str, list[str]] = {}

    for rid in selected_rules:
        messages: list[str] = []
        try:
            handle = import_rule_cached(rid)
        except Exception:
            results[rid] = [f"Rule import error:\n{traceback.format_exc()}"]
            continue

        module = handle.module
        rule_func = handle.func

        def report(msg: str) -> None:
            messages.append(str(msg))

        saved_report = handle.saved_report
        module.report = report

        try:
            if callable(handle.add_parent_info):
                handle.add_parent_info(tree)
            rule_func(tree)
        except Exception:
            messages.append(f"Execution error:\n{traceback.format_exc()}")
        finally:
            if saved_report is not None:
                module.report = saved_report
            else:
                try:
                    delattr(module, "report")
                except Exception:
                    pass

        if messages:
            results[rid] = messages

    return results


def github_get_raw_file(
    session: requests.Session,
    owner: str,
    repo: str,
    sha: str,
    rel_path: str,
    token: str | None,
    timeout_s: int = 60,
) -> tuple[str | None, str | None]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{rel_path}"
    headers = {
        "Accept": "application/vnd.github.raw",
        "User-Agent": "specdetect-contents-runner/1.0",
        "X-GitHub-Api-Version": API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        r = session.get(url, headers=headers, params={"ref": sha}, timeout=timeout_s)
        if r.status_code == 404:
            return None, "not found"
        r.raise_for_status()
        raw = r.content
        text = raw.decode("utf-8", errors="replace")
        return text, None
    except requests.HTTPError as e:
        return None, f"http error: {e}"
    except Exception as e:
        return None, f"error: {e}"


def strip_first_component(path_str: str) -> str:
    p = Path(path_str)
    if len(p.parts) <= 1:
        return str(p)
    return str(Path(*p.parts[1:]))


_SHA_RE = re.compile(r"(?i)(?:^|[^0-9a-f])([0-9a-f]{7,40})$")


def guess_sha_from_first_component(file_path: str) -> str | None:
    first = Path(file_path).parts[0] if file_path else ""
    if not first:
        return None
    m = _SHA_RE.search(first)
    if not m:
        return None
    return m.group(1)


def parse_owner_repo(repo_name: str) -> tuple[str | None, str | None]:
    if not repo_name:
        return None, None
    if "/" not in repo_name:
        return None, None
    owner, repo = repo_name.split("/", 1)
    owner = owner.strip()
    repo = repo.strip()
    if not owner or not repo:
        return None, None
    return owner, repo


def iter_csv_rows(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {k: (v or "").strip() for k, v in row.items()}


def analyze_selected_files_remote(
    session: requests.Session,
    owner: str,
    repo: str,
    sha: str,
    file_paths: list[str],
    selected_rules: list[str],
    token: str | None,
) -> tuple[dict[str, dict[str, list[str]]], int]:
    out: dict[str, dict[str, list[str]]] = {}
    analyzed = 0

    for raw_fp in file_paths:
        rel = strip_first_component(raw_fp)

        analyzed += 1
        virtual_path = f"{owner}/{repo}@{sha}/{rel}"

        source, err = github_get_raw_file(session, owner, repo, sha, rel, token)
        if source is None:
            if err == "not found":
                out[virtual_path] = {"MISSING_FILE": [f"Missing file: {virtual_path}"]}
            else:
                out[virtual_path] = {"HTTP_ERROR": [f"{virtual_path}: {err}"]}
            continue

        res = analyze_source_text(virtual_path, source, selected_rules)
        out[virtual_path] = res

    return out, analyzed


def main() -> int:
    sys.path.insert(0, str(SCRIPT_DIR))
    sys.path.insert(0, str(RULES_ROOT.parent))

    ap = argparse.ArgumentParser(
        description="Analyze only listed files from a CSV (RepoName, FilePath) by fetching file contents via GitHub Contents API."
    )
    ap.add_argument("--input-csv", type=Path, required=True)
    ap.add_argument("--output-file", type=Path, default=Path("specDetect_results_from_csv.json"))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--rules", nargs="+")
    ap.add_argument("--exclude", nargs="+")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--max-rows", type=int, default=0, help="0 means no limit")
    ap.add_argument("--commit-col", type=str, default="CommitSHA", help="Optional column containing a commit sha")
    args = ap.parse_args()

    available = discover_available_rules(RULES_ROOT)
    if not available:
        print(f"Error: no rules found under {RULES_ROOT}")
        return 1

    if args.all:
        excluded = set(args.exclude or [])
        selected = [r for r in available if r not in excluded]
    elif args.rules:
        selected = args.rules
    else:
        print("Error: provide --all or --rules")
        return 1

    if not selected:
        print(f"Error: no rules selected from {RULES_ROOT}")
        return 1

    invalid = [r for r in selected if r not in available]
    if invalid:
        print(f"Error: unknown rule IDs: {invalid}")
        return 1

    token = os.getenv("GITHUB_TOKEN")
    session = requests.Session()

    grouped: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    errors: list[str] = []

    row_count = 0
    for row in iter_csv_rows(args.input_csv):
        if args.max_rows and row_count >= args.max_rows:
            break
        row_count += 1

        repo_name = row.get("RepoName", "")
        file_path = row.get("FilePath", "")
        if not repo_name or not file_path:
            errors.append(f"row {row_count}: missing RepoName or FilePath")
            continue

        owner, repo = parse_owner_repo(repo_name)
        if not owner or not repo:
            errors.append(f"row {row_count}: invalid RepoName {repo_name}")
            continue

        sha = row.get(args.commit_col, "").strip()
        if not sha:
            sha = guess_sha_from_first_component(file_path) or ""

        if not sha:
            errors.append(f"row {row_count}: cannot infer commit sha from FilePath and no {args.commit_col} provided")
            continue

        grouped[(owner, repo, sha)].append(file_path)

    results_by_repo: dict[str, dict] = {}
    processed_groups = 0
    total_files = 0

    for (owner, repo, sha), file_paths in grouped.items():
        key = f"{owner}/{repo}"
        if key not in results_by_repo:
            results_by_repo[key] = {"owner": owner, "repo": repo, "by_sha": {}}

        unique_paths = list(dict.fromkeys(file_paths))
        total_files += len(unique_paths)
        processed_groups += 1

        print(f"\nAnalyzing {owner}/{repo} at {sha} for {len(unique_paths)} listed files")
        try:
            alerts, analyzed_count = analyze_selected_files_remote(
                session=session,
                owner=owner,
                repo=repo,
                sha=sha,
                file_paths=unique_paths,
                selected_rules=selected,
                token=token,
            )
            results_by_repo[key]["by_sha"][sha] = {
                "num_listed_files": len(unique_paths),
                "num_analyzed_files": analyzed_count,
                "alerts": alerts,
            }
        except Exception as e:
            results_by_repo[key]["by_sha"][sha] = {"error": str(e), "trace": traceback.format_exc()}

    output_payload = {
        "meta": {
            "analysis": {
                "rules": selected,
                "input_csv": str(args.input_csv),
                "commit_col": args.commit_col,
                "rows_read": row_count,
                "groups": processed_groups,
                "total_files_listed": total_files,
            },
            "row_errors": errors[:2000],
            "row_errors_truncated": len(errors) > 2000,
        },
        "repos": results_by_repo,
    }

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote results to {args.output_file}")

    if args.summary:
        rule_counts = defaultdict(int)
        missing_files = 0
        parse_errors = 0
        http_errors = 0
        files_with_real_alerts = 0
        analyzed_files_total = 0
        listed_files_total = 0

        for _, payload in results_by_repo.items():
            by_sha = payload.get("by_sha", {})
            if not isinstance(by_sha, dict):
                continue
            for _, sha_payload in by_sha.items():
                listed_files_total += int(sha_payload.get("num_listed_files", 0))
                analyzed_files_total += int(sha_payload.get("num_analyzed_files", 0))

                alerts = sha_payload.get("alerts")
                if not isinstance(alerts, dict):
                    continue

                for _, per_file in alerts.items():
                    if not isinstance(per_file, dict):
                        continue
                    if "MISSING_FILE" in per_file:
                        missing_files += 1
                        continue
                    if "HTTP_ERROR" in per_file:
                        http_errors += 1
                        continue
                    if "PARSE_ERROR" in per_file:
                        parse_errors += 1
                        continue

                    if per_file:
                        files_with_real_alerts += 1

                    for rule_id, msgs in per_file.items():
                        rule_counts[rule_id] += len(msgs)

        print("\nSummary")
        print(f"Groups processed: {processed_groups}")
        print(f"Listed files total: {listed_files_total}")
        print(f"Listed files analyzed: {analyzed_files_total}")
        print(f"Files with real alerts: {files_with_real_alerts}")
        print(f"Missing files: {missing_files}")
        print(f"HTTP errors: {http_errors}")
        print(f"Parse errors: {parse_errors}")
        for rid in selected:
            print(f"{rid}: {rule_counts.get(rid, 0)}")

        if errors:
            print(f"\nRow errors: {len(errors)} (first up to 20 shown)")
            for e in errors[:20]:
                print(e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
