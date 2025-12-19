from __future__ import annotations

import os
import sys
import ast
import json
import argparse
import traceback
import warnings
from pathlib import Path
from collections import defaultdict
from typing import Callable

import requests


SCRIPT_DIR = Path(__file__).resolve().parent
RULES_ROOT = SCRIPT_DIR / "test_rules"
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


def analyze_selected_files_remote(
    session: requests.Session,
    owner: str,
    repo: str,
    sha: str,
    file_paths: list[str],
    selected_rules: list[str],
    token: str | None,
) -> tuple[dict[str, dict[str, list[str]]], int]:
    """
    file_paths are values from stratified_sample.json, e.g.
    "1Panel-dev-MaxKB-d33dd45/apps/common/handle/impl/text/pdf_split_handle.py"
    We strip the first component and use the rest as repo-relative path.
    """
    out: dict[str, dict[str, list[str]]] = {}
    analyzed = 0

    for raw in file_paths:
        p = Path(raw)
        if len(p.parts) <= 1:
            rel = str(p)
        else:
            rel = str(Path(*p.parts[1:]))

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


def load_sample(sample_json: Path) -> tuple[dict, dict]:
    payload = json.loads(sample_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object at top level")

    if "repos" in payload and isinstance(payload["repos"], dict):
        meta = payload.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
        return meta, payload["repos"]

    return {}, payload



def group_files_by_sha(entry: dict) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)

    repo_sha = entry.get("resolved_commit_sha")
    if isinstance(repo_sha, str):
        repo_sha = repo_sha.strip()
    else:
        repo_sha = ""

    for f in entry.get("files", []) or []:
        if not isinstance(f, dict):
            continue
        fp = f.get("file_path")
        if not isinstance(fp, str) or not fp.strip():
            continue

        sha = f.get("resolved_commit_sha") or f.get("commit_sha") or repo_sha
        if not isinstance(sha, str) or not sha.strip():
            continue

        grouped[sha.strip()].append(fp.strip())

    return dict(grouped)


def main() -> int:
    sys.path.insert(0, str(SCRIPT_DIR))

    ap = argparse.ArgumentParser(
        description="Analyze only listed files from stratified_sample.json by fetching file contents via GitHub Contents API."
    )
    ap.add_argument("--sample-json", type=Path, required=True)
    ap.add_argument("--output-file", type=Path, default=Path("specDetect_results_by_repo.json"))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--rules", nargs="+")
    ap.add_argument("--exclude", nargs="+")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--max-repos", type=int, default=0, help="0 means no limit")
    args = ap.parse_args()

    available = discover_available_rules(RULES_ROOT)
    if args.all:
        excluded = set(args.exclude or [])
        selected = [r for r in available if r not in excluded]
    elif args.rules:
        selected = args.rules
    else:
        print("Error: provide --all or --rules")
        return 1

    invalid = [r for r in selected if r not in available]
    if invalid:
        print(f"Error: unknown rule IDs: {invalid}")
        return 1

    sample_meta, repos_dict = load_sample(args.sample_json)
    token = os.getenv("GITHUB_TOKEN")

    session = requests.Session()

    results_by_repo: dict[str, dict] = {}
    processed = 0

    for full_name, entry in repos_dict.items():
        if args.max_repos and processed >= args.max_repos:
            break
        if not isinstance(entry, dict):
            continue

        owner = entry.get("owner")
        repo = entry.get("repo")
        if not owner or not repo:
            if isinstance(full_name, str) and "/" in full_name:
                owner, repo = full_name.split("/", 1)
            else:
                results_by_repo[str(full_name)] = {"error": "missing owner/repo"}
                processed += 1
                continue

        if entry.get("error"):
            results_by_repo[f"{owner}/{repo}"] = {"error": str(entry.get("error"))}
            processed += 1
            continue

        sha_to_files = group_files_by_sha(entry)
        if not sha_to_files:
            results_by_repo[f"{owner}/{repo}"] = {"error": "no files or missing resolved_commit_sha"}
            processed += 1
            continue

        repo_payload: dict = {"owner": owner, "repo": repo, "by_sha": {}}

        for sha, file_paths in sha_to_files.items():
            print(f"\nFetching listed files {owner}/{repo} at {sha}")
            try:
                print(f"Analyzing {owner}/{repo} at {sha} for {len(file_paths)} listed files")
                alerts, analyzed_count = analyze_selected_files_remote(
                    session=session,
                    owner=owner,
                    repo=repo,
                    sha=sha,
                    file_paths=file_paths,
                    selected_rules=selected,
                    token=token,
                )

                repo_payload["by_sha"][sha] = {
                    "num_listed_files": len(file_paths),
                    "num_analyzed_files": analyzed_count,
                    "alerts": alerts,
                }
            except Exception as e:
                repo_payload["by_sha"][sha] = {"error": str(e), "trace": traceback.format_exc()}

        results_by_repo[f"{owner}/{repo}"] = repo_payload
        processed += 1

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    output_payload = {
        "meta": {
            **sample_meta,
            "analysis": {
                "rules": selected,
                "max_repos": args.max_repos,
            },
        },
        "repos": results_by_repo,
    }

    args.output_file.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote results to {args.output_file}")

    if args.summary:
        rule_counts = defaultdict(int)

        total_listed_files = 0
        total_analyzed_files = 0
        total_files_in_alerts_dict = 0

        missing_files = 0
        parse_errors = 0
        http_errors = 0
        files_with_real_alerts = 0

        for _, payload in results_by_repo.items():
            by_sha = payload.get("by_sha", {})
            if not isinstance(by_sha, dict):
                continue

            for _, sha_payload in by_sha.items():
                total_listed_files += int(sha_payload.get("num_listed_files", 0))
                total_analyzed_files += int(sha_payload.get("num_analyzed_files", 0))

                alerts = sha_payload.get("alerts")
                if not isinstance(alerts, dict):
                    continue

                total_files_in_alerts_dict += len(alerts)

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
        print(f"Repos processed: {processed}")
        print(f"Listed files total: {total_listed_files}")
        print(f"Listed files analyzed: {total_analyzed_files}")
        print(f"Files present in alerts dict: {total_files_in_alerts_dict}")
        print(f"Files with real alerts: {files_with_real_alerts}")
        print(f"Missing files: {missing_files}")
        print(f"HTTP errors: {http_errors}")
        print(f"Parse errors: {parse_errors}")
        for rid, cnt in sorted(rule_counts.items()):
            print(f"{rid}: {cnt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
