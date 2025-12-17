import json
import random
import os
import re
import requests

INPUT_FILE = "repo_summary.json"
OUTPUT_FILE = "stratified_sample.json"
TOTAL_POPULATION = 16005
TARGET_SAMPLE_SIZE = 384

GITHUB_API = "https://api.github.com"
SESSION = requests.Session()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

_SHA1_RE = re.compile(r"^[0-9a-fA-F]{40}$")

def is_full_sha(value: str) -> bool:
    return isinstance(value, str) and _SHA1_RE.match(value.strip()) is not None

def resolve_ref_to_sha(owner: str, repo: str, ref: str) -> str | None:
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

def generate_stratified_sample():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    sampled_data = {}
    total_selected = 0
    sha_cache = {}

    print("Starting stratified sampling")
    print(f"Population (N): {TOTAL_POPULATION}")
    print(f"Target (n): {TARGET_SAMPLE_SIZE}")

    for repo_name, repo_data in data.items():
        files_list = repo_data.get("files", [])
        N_i = len(files_list)
        if N_i == 0:
            continue

        ratio = N_i / TOTAL_POPULATION
        n_i = int(round(ratio * TARGET_SAMPLE_SIZE))
        if n_i > N_i:
            n_i = N_i
        if n_i <= 0:
            continue

        selected_files = random.sample(files_list, n_i)

        owner = repo_data.get("owner")
        repo = repo_data.get("repo")
        ref = repo_data.get("ref")

        resolved_sha = None
        if isinstance(owner, str) and isinstance(repo, str) and isinstance(ref, str):
            cache_key = f"{owner}/{repo}@{ref}"
            if cache_key in sha_cache:
                resolved_sha = sha_cache[cache_key]
            else:
                resolved_sha = resolve_ref_to_sha(owner, repo, ref)
                sha_cache[cache_key] = resolved_sha

        sampled_repo = repo_data.copy()
        sampled_repo["ref"] = ref
        sampled_repo["resolved_commit_sha"] = resolved_sha
        sampled_repo["files"] = selected_files
        sampled_repo["num_llm_files"] = len(selected_files)

        for fobj in selected_files:
            if isinstance(fobj, dict):
                fobj["ref"] = ref
                fobj["resolved_commit_sha"] = resolved_sha
                fobj["commit_sha"] = resolved_sha if resolved_sha else ref

        sampled_data[repo_name] = sampled_repo
        total_selected += len(selected_files)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        json.dump(sampled_data, out, indent=2, ensure_ascii=False)

    print(f"Generated file: {OUTPUT_FILE}")
    print(f"Total files selected: {total_selected} (Target: {TARGET_SAMPLE_SIZE})")

if __name__ == "__main__":
    generate_stratified_sample()
