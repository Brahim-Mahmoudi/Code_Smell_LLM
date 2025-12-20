#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import pandas as pd


@dataclass(frozen=True)
class RepoInfo:
    full_name: str
    owner: str
    repo: str
    ref: Optional[str]
    original_ref: Optional[str]
    resolved_commit_sha: Optional[str]
    providers_repo: List[str]
    files: List[Dict[str, Any]]


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(
            f"JSON invalide dans {path}.\n"
            f"Erreur: {e}\n"
            f"Vérifie que le fichier n'est pas tronqué et se termine bien."
        )


def extract_repos(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[RepoInfo]]:
    meta = data.get("meta", {})
    repos_raw = data.get("repos", {})

    if not isinstance(repos_raw, dict):
        raise SystemExit("Champ 'repos' absent ou invalide, attendu un objet JSON.")

    repos: List[RepoInfo] = []
    for full_name, r in repos_raw.items():
        if not isinstance(r, dict):
            continue
        if r.get("error") is not None:
            continue

        files = r.get("files") or []
        if not files:
            continue

        owner = r.get("owner") or ""
        repo = r.get("repo") or ""
        if not owner or not repo:
            continue

        repos.append(
            RepoInfo(
                full_name=full_name,
                owner=owner,
                repo=repo,
                ref=r.get("ref"),
                original_ref=r.get("original_ref"),
                resolved_commit_sha=r.get("resolved_commit_sha"),
                providers_repo=list(r.get("providers") or []),
                files=list(files),
            )
        )

    return meta, repos


def greedy_whole_repo_assignment(repos: List[RepoInfo], k: int) -> Dict[int, Dict[str, Any]]:
    repos_sorted = sorted(repos, key=lambda x: len(x.files), reverse=True)
    assign: Dict[int, Dict[str, Any]] = {i: {"repos": [], "files": []} for i in range(1, k + 1)}

    for repo in repos_sorted:
        i_min = min(assign.keys(), key=lambda i: len(assign[i]["files"]))
        assign[i_min]["repos"].append(repo)
        for f in repo.files:
            assign[i_min]["files"].append((repo, f))

    return assign


def compute_desired_counts(total_files: int, k: int) -> Dict[int, int]:
    base = total_files // k
    rem = total_files % k
    return {i: base + (1 if i <= rem else 0) for i in range(1, k + 1)}


def rebalance_min_splits(assign: Dict[int, Dict[str, Any]], desired: Dict[int, int]) -> Tuple[Dict[int, Dict[str, Any]], set]:
    split_repos = set()

    def counts() -> Dict[int, int]:
        return {i: len(assign[i]["files"]) for i in assign}

    def move_repo(src: int, dst: int, repo: RepoInfo) -> None:
        assign[src]["repos"] = [r for r in assign[src]["repos"] if r.full_name != repo.full_name]

        kept = []
        moved = []
        for (r, f) in assign[src]["files"]:
            if r.full_name == repo.full_name:
                moved.append((r, f))
            else:
                kept.append((r, f))
        assign[src]["files"] = kept

        assign[dst]["repos"].append(repo)
        assign[dst]["files"].extend(moved)

    def move_one_file(src: int, dst: int) -> bool:
        if not assign[src]["files"]:
            return False

        repo_to_files: Dict[str, List[Tuple[RepoInfo, Dict[str, Any]]]] = {}
        for (r, f) in assign[src]["files"]:
            repo_to_files.setdefault(r.full_name, []).append((r, f))

        repo_name, file_list = max(repo_to_files.items(), key=lambda kv: len(kv[1]))
        r, f = file_list[-1]

        removed = False
        new_src = []
        for (rr, ff) in assign[src]["files"]:
            if (not removed) and rr.full_name == repo_name and ff == f:
                removed = True
            else:
                new_src.append((rr, ff))
        assign[src]["files"] = new_src

        if all(rr.full_name != repo_name for rr in assign[dst]["repos"]):
            assign[dst]["repos"].append(r)
        assign[dst]["files"].append((r, f))

        split_repos.add(repo_name)
        return True

    max_iters = 200000
    for _ in range(max_iters):
        c = counts()
        above = [i for i in c if c[i] > desired[i]]
        below = [i for i in c if c[i] < desired[i]]
        if not above or not below:
            break

        src = max(above, key=lambda i: c[i] - desired[i])
        dst = max(below, key=lambda i: desired[i] - c[i])

        best_repo = None
        best_score = None

        src_repos = sorted(assign[src]["repos"], key=lambda r: len(r.files))
        for repo in src_repos:
            n = len(repo.files)
            new_src = c[src] - n
            new_dst = c[dst] + n

            if new_src < desired[src] or new_dst > desired[dst]:
                continue

            score = abs(new_src - desired[src]) + abs(new_dst - desired[dst])
            if best_score is None or score < best_score:
                best_score = score
                best_repo = repo

        if best_repo is not None:
            move_repo(src, dst, best_repo)
            continue

        if not move_one_file(src, dst):
            break

    return assign, split_repos


def build_df_for_annotator(assign: Dict[int, Dict[str, Any]], split_repos: set, annotator_idx: int) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for repo, f in assign[annotator_idx]["files"]:
        rows.append(
            {
                "annotator": f"annotateur_{annotator_idx}",
                "repo_full_name": repo.full_name,
                "owner": repo.owner,
                "repo": repo.repo,
                "original_ref": f.get("original_ref", repo.original_ref),
                "resolved_commit_sha": f.get("resolved_commit_sha", repo.resolved_commit_sha),
                "file_path": f.get("file_path"),
                "providers_file": ", ".join(f.get("providers") or []),
                "providers_repo": ", ".join(repo.providers_repo or []),
                "status": "",
                "done_date": "",
                "notes": "",
                "repo_is_split_across_annotators": "yes" if repo.full_name in split_repos else "no",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="stratified_sample_692_repos.json", help="Chemin vers le JSON complet")
    p.add_argument("--annotators", type=int, default=7, help="Nombre d'annotateurs")
    p.add_argument("--out-dir", default="annotator_assignments", help="Dossier de sortie")
    p.add_argument("--format", choices=["xlsx", "csv", "both"], default="xlsx", help="Format de sortie")
    args = p.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = load_json(in_path)
    meta, repos = extract_repos(data)

    if not repos:
        raise SystemExit("Aucun repo exploitable trouvé dans le JSON (ou tous en erreur, ou sans fichiers).")

    k = int(args.annotators)
    total_files = sum(len(r.files) for r in repos)
    desired = compute_desired_counts(total_files, k)

    assign = greedy_whole_repo_assignment(repos, k)
    assign, split_repos = rebalance_min_splits(assign, desired)

    summary_rows = []
    for i in range(1, k + 1):
        df_i = build_df_for_annotator(assign, split_repos, i)
        summary_rows.append(
            {
                "annotator": f"annotateur_{i}",
                "n_files": int(df_i.shape[0]),
                "n_unique_repos": int(df_i["repo_full_name"].nunique()) if not df_i.empty else 0,
                "n_files_in_split_repos": int((df_i["repo_is_split_across_annotators"] == "yes").sum()) if not df_i.empty else 0,
                "desired_n_files": desired[i],
                "delta": int(df_i.shape[0] - desired[i]),
            }
        )

        if args.format in ("xlsx", "both"):
            out_xlsx = out_dir / f"annotateur_{i}.xlsx"
            with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
                pd.DataFrame([meta] if isinstance(meta, dict) else [{"meta": str(meta)}]).to_excel(writer, sheet_name="Meta", index=False)
                df_i.to_excel(writer, sheet_name="Assignments", index=False)

        if args.format in ("csv", "both"):
            out_csv = out_dir / f"annotateur_{i}.csv"
            df_i.to_csv(out_csv, index=False)

    summary = pd.DataFrame(summary_rows)
    summary_xlsx = out_dir / "summary.xlsx"
    summary_csv = out_dir / "summary.csv"

    with pd.ExcelWriter(summary_xlsx, engine="openpyxl") as writer:
        pd.DataFrame([meta] if isinstance(meta, dict) else [{"meta": str(meta)}]).to_excel(writer, sheet_name="Meta", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)

    summary.to_csv(summary_csv, index=False)

    print("Terminé")
    print(f"Dossier sortie: {out_dir.resolve()}")
    print(f"Total repos: {len(repos)}")
    print(f"Total fichiers: {total_files}")
    print("Fichiers générés:")
    print(f"  {summary_xlsx.name}")
    print(f"  {summary_csv.name}")
    for i in range(1, k + 1):
        if args.format in ("xlsx", "both"):
            print(f"  annotateur_{i}.xlsx")
        if args.format in ("csv", "both"):
            print(f"  annotateur_{i}.csv")


if __name__ == "__main__":
    main()
