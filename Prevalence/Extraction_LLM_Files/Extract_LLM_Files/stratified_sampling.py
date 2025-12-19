import json
import os
import re
import math
import requests
from typing import Optional, Dict, Any, List, Tuple
import random

INPUT_FILE = "/Users/bramss/Desktop/repo_summary.json"
OUTPUT_FILE = "stratified_sample_692_repos.json"

N = 38981
n = 381  # 95% IC

GITHUB_API = "https://api.github.com"
SESSION = requests.Session()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

_SHA1_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def is_full_sha(value: str) -> bool:
    return isinstance(value, str) and _SHA1_RE.match(value.strip()) is not None


def resolve_ref_to_sha(owner: str, repo: str, ref: str) -> Optional[str]:
    if not isinstance(ref, str) or not ref.strip():
        return None
    ref = ref.strip()
    if is_full_sha(ref):
        return ref

    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits/{ref}"
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        resp = SESSION.get(url, headers=headers, timeout=30)
    except Exception as exc:
        print(f"Warning: cannot resolve {owner}/{repo}@{ref} ({exc})")
        return None

    if resp.status_code >= 300:
        try:
            payload = resp.json()
            msg = payload.get("message")
        except Exception:
            msg = resp.text[:200]
        print(f"Warning: cannot resolve {owner}/{repo}@{ref} (http {resp.status_code}) {msg}")
        return None

    try:
        payload = resp.json()
    except Exception:
        print(f"Warning: cannot decode JSON for {owner}/{repo}@{ref}")
        return None

    sha = payload.get("sha")
    if isinstance(sha, str) and sha.strip():
        return sha.strip()
    return None


def weighted_sample_without_replacement(keys: List[str], weights: List[float], k: int, rng: random.Random) -> List[str]:
    if k <= 0:
        return []
    if k >= len(keys):
        return list(keys)

    scored: List[Tuple[float, str]] = []
    for key, w in zip(keys, weights):
        if w <= 0:
            continue
        u = rng.random()
        score = u ** (1.0 / w)
        scored.append((score, key))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [key for _, key in scored[:k]]


def allocate_exact_n_proportional(repo_sizes: Dict[str, int], target_n: int) -> Dict[str, int]:
    repos = [(r, int(n)) for r, n in repo_sizes.items() if int(n) > 0]
    if not repos:
        raise ValueError("No repos with positive size")

    total = sum(n for _, n in repos)
    if total < target_n:
        raise ValueError(f"Not enough total files in selected repos: total={total} < target_n={target_n}")

    floors: Dict[str, int] = {}
    frac: List[Tuple[float, str]] = []

    for r, N_i in repos:
        q = (target_n * N_i) / total
        f = int(math.floor(q))
        if f > N_i:
            f = N_i
        floors[r] = f
        frac.append((q - math.floor(q), r))

    alloc = dict(floors)
    used = sum(alloc.values())
    remaining = target_n - used

    frac.sort(reverse=True, key=lambda x: x[0])

    if remaining > 0:
        idx = 0
        guard = 0
        max_guard = 10_000_000
        while remaining > 0:
            if guard > max_guard:
                raise RuntimeError("Allocation loop guard triggered")
            guard += 1

            if idx >= len(frac):
                idx = 0

            _, r = frac[idx]
            idx += 1

            cap = repo_sizes[r]
            if alloc[r] < cap:
                alloc[r] += 1
                remaining -= 1

    if sum(alloc.values()) != target_n:
        raise RuntimeError("Exact allocation failed")

    for r, v in alloc.items():
        if v < 0 or v > repo_sizes[r]:
            raise RuntimeError("Allocation violates capacity constraints")

    return alloc


def canonical_owner_repo(repo_name: str, repo_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], str]:
    owner = repo_data.get("owner")
    repo = repo_data.get("repo")

    if isinstance(owner, str) and owner.strip() and isinstance(repo, str) and repo.strip():
        key = f"{owner.strip()}/{repo.strip()}"
        return owner.strip(), repo.strip(), key

    if isinstance(repo_name, str) and "/" in repo_name:
        o, r = repo_name.split("/", 1)
        o = o.strip()
        r = r.strip()
        if o and r:
            key = f"{o}/{r}"
            return o, r, key

    return None, None, str(repo_name)


def normalize_file_obj(fobj: Any) -> Dict[str, Any]:
    if isinstance(fobj, dict):
        return dict(fobj)
    if isinstance(fobj, str) and fobj.strip():
        return {"file_path": fobj.strip()}
    return {}


def generate_sample(
    seed: int = 42,
    target_repos: int = 200,
    repo_sampling: str = "pps",
    N: int = N,
    n: int = n,
) -> None:
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"{INPUT_FILE} not found")

    rng = random.Random(seed)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    eligible_repo_keys: List[str] = []
    repo_sizes: Dict[str, int] = {}

    for repo_name, repo_data in data.items():
        if not isinstance(repo_data, dict):
            continue
        files_list = repo_data.get("files", [])
        N_i = len(files_list) if isinstance(files_list, list) else 0
        if N_i <= 0:
            continue
        eligible_repo_keys.append(repo_name)
        repo_sizes[repo_name] = N_i

    if not eligible_repo_keys:
        raise ValueError("No eligible repos in input")

    if target_repos <= 0 or target_repos >= len(eligible_repo_keys):
        selected_repos = list(eligible_repo_keys)
    else:
        if repo_sampling not in {"pps", "uniform"}:
            raise ValueError("repo_sampling must be pps or uniform")

        if repo_sampling == "uniform":
            selected_repos = rng.sample(eligible_repo_keys, target_repos)
        else:
            keys = eligible_repo_keys
            weights = [float(repo_sizes[k]) for k in keys]
            selected_repos = weighted_sample_without_replacement(keys, weights, target_repos, rng)

    selected_repo_sizes = {k: repo_sizes[k] for k in selected_repos}
    allocation = allocate_exact_n_proportional(selected_repo_sizes, n)

    sampled_repos: Dict[str, Any] = {}
    sha_cache: Dict[str, Optional[str]] = {}

    total_selected = 0
    skipped_missing_owner_repo = 0
    skipped_empty_files = 0

    for repo_name in selected_repos:
        repo_data = data.get(repo_name)
        if not isinstance(repo_data, dict):
            continue

        files_list = repo_data.get("files", [])
        if not isinstance(files_list, list) or not files_list:
            skipped_empty_files += 1
            continue

        owner, repo, key = canonical_owner_repo(repo_name, repo_data)
        if owner is None or repo is None:
            skipped_missing_owner_repo += 1
            continue

        n_i = allocation.get(repo_name, 0)
        if n_i <= 0:
            continue
        if n_i > len(files_list):
            n_i = len(files_list)

        picked_raw = rng.sample(files_list, n_i)
        selected_files: List[Dict[str, Any]] = []
        for x in picked_raw:
            fo = normalize_file_obj(x)
            if fo.get("file_path"):
                selected_files.append(fo)

        if not selected_files:
            continue

        original_ref = repo_data.get("ref")
        resolved_sha = None

        if isinstance(original_ref, str) and original_ref.strip():
            cache_key = f"{owner}/{repo}@{original_ref.strip()}"
            if cache_key in sha_cache:
                resolved_sha = sha_cache[cache_key]
            else:
                resolved_sha = resolve_ref_to_sha(owner, repo, original_ref.strip())
                sha_cache[cache_key] = resolved_sha

        final_ref = resolved_sha if resolved_sha else (original_ref if isinstance(original_ref, str) else "")

        sampled_repo = dict(repo_data)
        sampled_repo["owner"] = owner
        sampled_repo["repo"] = repo
        sampled_repo["original_ref"] = original_ref
        sampled_repo["ref"] = final_ref
        sampled_repo["resolved_commit_sha"] = resolved_sha
        sampled_repo["files"] = selected_files
        sampled_repo["num_llm_files"] = len(selected_files)
        sampled_repo["N_i"] = len(files_list)
        sampled_repo["n_i"] = len(selected_files)

        for fobj in selected_files:
            fobj["original_ref"] = original_ref
            fobj["ref"] = final_ref
            fobj["resolved_commit_sha"] = resolved_sha
            fobj["commit_sha"] = resolved_sha if resolved_sha else final_ref

        sampled_repos[key] = sampled_repo
        total_selected += len(selected_files)

    output_payload = {
        "meta": {
            "seed": seed,
            "repo_sampling": repo_sampling,
            "target_repos": target_repos if target_repos > 0 else "all",
            "population_N": N,
            "target_n": n,
            "eligible_repos": len(eligible_repo_keys),
            "selected_repos": len(sampled_repos),
            "total_selected_files": total_selected,
            "skipped_missing_owner_repo": skipped_missing_owner_repo,
            "skipped_empty_files": skipped_empty_files,
        },
        "repos": sampled_repos,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        json.dump(output_payload, out, indent=2, ensure_ascii=False)

    print(f"Generated file: {OUTPUT_FILE}")
    print(f"Repos selected: {output_payload['meta']['selected_repos']}")
    print(f"Total files selected: {total_selected} (Target: {n})")
    print(f"Skipped repos with missing owner/repo: {skipped_missing_owner_repo}")
    print(f"Skipped repos with empty files: {skipped_empty_files}")


if __name__ == "__main__":
    generate_sample(
        seed=30,
        target_repos=692,
        repo_sampling="pps",
        N=N,
        n=n,
    )
