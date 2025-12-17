from __future__ import annotations

import os
import sys
import ast
import json
import argparse
import traceback
import tempfile
import tarfile
import warnings
from pathlib import Path
from collections import defaultdict
from typing import Callable

import requests


SCRIPT_DIR = Path(__file__).resolve().parent
RULES_ROOT = SCRIPT_DIR / "test_rules"

DEFAULT_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "node_modules",
    "dist",
    "build",
}


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


def analyze_file(filepath: Path, selected_rules: list[str]) -> dict[str, list[str]]:
    if not filepath.exists():
        return {"MISSING_FILE": [f"Missing file: {filepath}"]}

    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source, filename=str(filepath))
    except Exception as e:
        return {"PARSE_ERROR": [f"{filepath}: {e}"]}

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


def analyze_selected_files(repo_root: Path, file_paths: list[str], selected_rules: list[str]) -> tuple[dict[str, dict[str, list[str]]], int]:
    """
    file_paths are values from stratified_sample.json, e.g.
    "1Panel-dev-MaxKB-d33dd45/apps/common/handle/impl/text/pdf_split_handle.py"
    We strip the first component and resolve against repo_root.
    """
    out: dict[str, dict[str, list[str]]] = {}
    analyzed = 0

    for raw in file_paths:
        p = Path(raw)
        if len(p.parts) <= 1:
            rel = p
        else:
            rel = Path(*p.parts[1:])

        fp = repo_root / rel
        analyzed += 1
        res = analyze_file(fp, selected_rules)
        out[str(fp)] = res  
        

    return out, analyzed


def github_tarball_url(owner: str, repo: str, sha: str) -> str:
    return f"https://api.github.com/repos/{owner}/{repo}/tarball/{sha}"


def _is_within_directory(directory: Path, target: Path) -> bool:
    directory = directory.resolve()
    target = target.resolve()
    return str(target).startswith(str(directory) + os.sep) or target == directory


def safe_extract_tar(tar: tarfile.TarFile, path: Path) -> None:
    for member in tar.getmembers():
        member_path = path / member.name
        if not _is_within_directory(path, member_path):
            raise RuntimeError("Unsafe tar content detected (path traversal).")

    try:
        tar.extractall(path=path, filter="data")
    except TypeError:
        tar.extractall(path=path)


def download_tarball_to(owner: str, repo: str, sha: str, dest_file: Path, token: str | None) -> None:
    url = github_tarball_url(owner, repo, sha)
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with requests.get(url, headers=headers, stream=True, timeout=120) as r:
        r.raise_for_status()
        with dest_file.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def extract_tarball(tar_path: Path, extract_dir: Path) -> Path:
    with tarfile.open(tar_path, mode="r:gz") as tar:
        safe_extract_tar(tar, extract_dir)

    subdirs = [p for p in extract_dir.iterdir() if p.is_dir()]
    if len(subdirs) == 1:
        return subdirs[0]

    candidates = sorted(subdirs, key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0]

    raise RuntimeError("Extraction produced no directory.")


def load_sample(sample_json: Path) -> dict:
    payload = json.loads(sample_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Expected stratified_sample.json to be a dict keyed by owner/repo.")
    return payload


def group_files_by_sha(entry: dict) -> dict[str, list[str]]:
    """
    Returns sha -> [file_path, ...]
    Uses file.resolved_commit_sha primarily, falls back to entry.resolved_commit_sha.
    """
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
        description="Analyze only listed files from stratified_sample.json using GitHub tarballs at resolved_commit_sha."
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

    sample = load_sample(args.sample_json)
    token = os.getenv("GITHUB_TOKEN")

    results_by_repo: dict[str, dict] = {}
    processed = 0

    for full_name, entry in sample.items():
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

        repo_payload: dict = {
            "owner": owner,
            "repo": repo,
            "by_sha": {},
        }

        for sha, file_paths in sha_to_files.items():
            print(f"\nFetching tarball {owner}/{repo} at {sha}")
            try:
                with tempfile.TemporaryDirectory(prefix="specdetect_repo_") as tmp:
                    tmp_dir = Path(tmp)
                    tar_path = tmp_dir / "repo.tar.gz"
                    extract_dir = tmp_dir / "extract"
                    extract_dir.mkdir(parents=True, exist_ok=True)

                    download_tarball_to(owner, repo, sha, tar_path, token)
                    repo_root = extract_tarball(tar_path, extract_dir)

                    print(f"Analyzing {owner}/{repo} at {sha} for {len(file_paths)} listed files")
                    alerts, analyzed_count = analyze_selected_files(repo_root, file_paths, selected)

                    repo_payload["by_sha"][sha] = {
                        "num_listed_files": len(file_paths),
                        "num_analyzed_files": analyzed_count,
                        "alerts": alerts,
                    }

            except requests.HTTPError as e:
                repo_payload["by_sha"][sha] = {"error": f"http error: {e}"}
            except Exception as e:
                repo_payload["by_sha"][sha] = {"error": str(e), "trace": traceback.format_exc()}

        results_by_repo[f"{owner}/{repo}"] = repo_payload
        processed += 1

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(results_by_repo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote results to {args.output_file}")

    if args.summary:
        rule_counts = defaultdict(int)

        total_listed_files = 0
        total_analyzed_files = 0
        total_files_in_alerts_dict = 0

        missing_files = 0
        parse_errors = 0
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
        print(f"Parse errors: {parse_errors}")
        for rid, cnt in sorted(rule_counts.items()):
            print(f"{rid}: {cnt}")

    return 0



if __name__ == "__main__":
    raise SystemExit(main())
