#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extract ~N recent GitHub repositories that likely use LLMs or multimodal LLMs
(RLM, VLM, LVLM, reasoning models, vision language models), and export to CSV:

index,owner,repo,commit_sha,source

Auth
  export GITHUB_TOKEN="..."
  python extract_llm_repos.py --target 500 --out out.csv

Notes
  GitHub Search API returns up to 1000 results per search and has separate rate limits.
  Search endpoints: up to 30 requests per minute
  Code search: 10 requests per minute
  https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28
"""

from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import requests


GITHUB_API = "https://api.github.com"
API_VERSION = "2022-11-28"


def utc_today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


def iso_date(d: dt.date) -> str:
    return d.isoformat()


def daterange_windows(end_date: dt.date, start_date: dt.date, window_days: int) -> List[Tuple[dt.date, dt.date]]:
    if start_date > end_date:
        return []
    windows: List[Tuple[dt.date, dt.date]] = []
    cur_end = end_date
    while cur_end >= start_date:
        cur_start = cur_end - dt.timedelta(days=window_days - 1)
        if cur_start < start_date:
            cur_start = start_date
        windows.append((cur_start, cur_end))
        cur_end = cur_start - dt.timedelta(days=1)
    return windows


def clamp_text(s: str, max_len: int) -> str:
    s = s or ""
    if len(s) <= max_len:
        return s
    return s[:max_len]


@dataclass(frozen=True)
class RepoRow:
    owner: str
    repo: str
    commit_sha: str
    source: str


class GitHubClient:
    def __init__(self, token: Optional[str], user_agent: str = "llm-repo-extractor/1.0"):
        self.s = requests.Session()
        self.token = token
        self.user_agent = user_agent

    def _headers(self, accept: str = "application/vnd.github+json") -> Dict[str, str]:
        h = {
            "Accept": accept,
            "User-Agent": self.user_agent,
            "X-GitHub-Api-Version": API_VERSION,
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def request_json(self, method: str, url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
        backoff = 2.0
        for attempt in range(1, 9):
            resp = self.s.request(method, url, headers=self._headers(), params=params, timeout=timeout)
            if resp.status_code in (200, 201):
                return resp.json()

            retry_after = resp.headers.get("Retry-After")
            remaining = resp.headers.get("X-RateLimit-Remaining")
            reset = resp.headers.get("X-RateLimit-Reset")

            body_text = ""
            try:
                body_text = resp.text or ""
            except Exception:
                body_text = ""

            is_rate = resp.status_code in (403, 429) and (
                "rate limit" in body_text.lower()
                or "secondary rate" in body_text.lower()
                or "abuse" in body_text.lower()
            )

            if is_rate:
                wait_s = None
                if retry_after and retry_after.isdigit():
                    wait_s = float(retry_after) + 1.0
                elif remaining == "0" and reset and reset.isdigit():
                    reset_ts = int(reset)
                    now_ts = int(time.time())
                    wait_s = max(5.0, float(reset_ts - now_ts) + 2.0)
                else:
                    wait_s = min(90.0, backoff) + random.random()

                time.sleep(wait_s)
                backoff = min(120.0, backoff * 2.0)
                continue

            if resp.status_code in (500, 502, 503, 504):
                time.sleep(min(30.0, backoff) + random.random())
                backoff = min(60.0, backoff * 2.0)
                continue

            try:
                j = resp.json()
                raise RuntimeError(f"GitHub API error {resp.status_code} for {url}: {j}")
            except Exception:
                raise RuntimeError(f"GitHub API error {resp.status_code} for {url}: {clamp_text(body_text, 400)}")

        raise RuntimeError(f"GitHub API failed after retries for {url}")

    def get_text(self, url: str, timeout: int = 30) -> str:
        resp = self.s.get(url, headers={"User-Agent": self.user_agent}, timeout=timeout)
        resp.raise_for_status()
        return resp.text

    def search_repositories(self, q: str, sort: str = "updated", order: str = "desc", per_page: int = 100, page: int = 1) -> Dict[str, Any]:
        url = f"{GITHUB_API}/search/repositories"
        params = {"q": q, "sort": sort, "order": order, "per_page": per_page, "page": page}
        return self.request_json("GET", url, params=params)

    def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        url = f"{GITHUB_API}/repos/{owner}/{repo}"
        return self.request_json("GET", url)

    def get_commit_sha_for_ref(self, owner: str, repo: str, ref: str) -> str:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/commits/{ref}"
        j = self.request_json("GET", url)
        sha = (j or {}).get("sha") or ""
        return sha

    def get_readme_text(self, owner: str, repo: str, ref: Optional[str]) -> str:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
        params = {"ref": ref} if ref else None
        j = self.request_json("GET", url, params=params)
        if not isinstance(j, dict):
            return ""
        if "content" in j and j.get("encoding") == "base64":
            try:
                raw = base64.b64decode(j["content"])
                return raw.decode("utf-8", errors="replace")
            except Exception:
                return ""
        dl = j.get("download_url")
        if dl:
            try:
                return self.get_text(dl)
            except Exception:
                return ""
        return ""

    def get_content_text(self, owner: str, repo: str, path: str, ref: Optional[str]) -> str:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref} if ref else None
        j = self.request_json("GET", url, params=params)
        if not isinstance(j, dict):
            return ""
        if j.get("type") != "file":
            return ""
        if "content" in j and j.get("encoding") == "base64":
            try:
                raw = base64.b64decode(j["content"])
                return raw.decode("utf-8", errors="replace")
            except Exception:
                return ""
        dl = j.get("download_url")
        if dl:
            try:
                return self.get_text(dl)
            except Exception:
                return ""
        return ""


STRONG_PATTERNS = [
    r"\bopenai\b",
    r"\banthropic\b",
    r"\bclaude\b",
    r"\bgemini\b",
    r"\bgoogle[-_ ]generativeai\b",
    r"\bollama\b",
    r"\bvllm\b",
    r"\blangchain\b",
    r"\bllama[-_ ]index\b",
    r"\blitellm\b",
    r"\bopenrouter\b",
    r"\bazure[-_ ]ai[-_ ]openai\b",
    r"\bbedrock\b",
    r"\bmistral\b",
    r"\bgroq\b",
    r"\btogether\b",
    r"\bfireworks\b",
    r"\bllava\b",
    r"\bqwen[-_ ]vl\b",
    r"\binstructblip\b",
    r"\bblip[-_ ]2\b",
    r"\bvision[-_ ]language\b",
    r"\bvision language\b",
    r"\bvlm\b",
    r"\blvlm\b",
    r"\bmultimodal\b",
    r"\bgpt[-_ ]4o\b",
    r"\breasoning model\b",
    r"\breasoning language\b",
    r"\bdeepseek[-_ ]r1\b",
]

WEAK_PATTERNS = [
    r"\bllm\b",
    r"\bllms\b",
    r"\bvision\b",
    r"\bmultimodal\b",
    r"\btool[-_ ]calling\b",
    r"\bfunction[-_ ]calling\b",
    r"\bchat[-_ ]completion\b",
]

STRONG_RE = re.compile("|".join(f"(?:{p})" for p in STRONG_PATTERNS), flags=re.IGNORECASE)
WEAK_RE = re.compile("|".join(f"(?:{p})" for p in WEAK_PATTERNS), flags=re.IGNORECASE)


def llm_likelihood_score(texts: Iterable[str]) -> int:
    strong = 0
    weak = 0
    for t in texts:
        if not t:
            continue
        if STRONG_RE.search(t):
            strong += 1
        if WEAK_RE.search(t):
            weak += 1
    if strong >= 1:
        return 3 + min(3, strong)
    return min(2, weak)


def is_candidate_repo(owner: str, repo: str, default_branch: str, gh: GitHubClient) -> bool:
    ref = default_branch or None

    readme = gh.get_readme_text(owner, repo, ref)
    time.sleep(0.2)

    files_to_probe = [
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
        "setup.py",
        "environment.yml",
        "package.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "Gemfile",
    ]

    contents: List[str] = [readme]
    for fp in files_to_probe:
        txt = gh.get_content_text(owner, repo, fp, ref)
        if txt:
            contents.append(txt)
        time.sleep(0.12)

        score = llm_likelihood_score(contents)
        if score >= 3:
            return True

    return llm_likelihood_score(contents) >= 3


def build_queries(min_stars: int) -> List[str]:
    base_filters = f"fork:false archived:false stars:>={min_stars}"
    queries = [
        f'topic:llm {base_filters}',
        f'topic:multimodal {base_filters}',
        f'topic:vision-language-model {base_filters}',
        f'"vision-language" in:readme {base_filters}',
        f'"vision language" in:readme {base_filters}',
        f'vlm in:readme {base_filters}',
        f'lvlm in:readme {base_filters}',
        f'multimodal in:readme {base_filters}',
        f'llava in:readme {base_filters}',
        f'qwen-vl in:readme {base_filters}',
        f'"reasoning model" in:readme {base_filters}',
        f'"reasoning language" in:readme {base_filters}',
        f'deepseek-r1 in:readme {base_filters}',
        f'gpt-4o in:readme {base_filters}',
        f'openai in:readme {base_filters}',
        f'anthropic in:readme {base_filters}',
        f'gemini in:readme {base_filters}',
        f'ollama in:readme {base_filters}',
        f'vllm in:readme {base_filters}',
    ]
    return queries


def collect_repos(
    gh: GitHubClient,
    target: int,
    since_days: int,
    window_days: int,
    min_stars: int,
    source_label: str,
    sleep_search_s: float,
) -> List[RepoRow]:
    end_date = utc_today()
    start_date = end_date - dt.timedelta(days=since_days)
    windows = daterange_windows(end_date=end_date, start_date=start_date, window_days=window_days)
    queries = build_queries(min_stars=min_stars)

    seen: Set[str] = set()
    out: List[RepoRow] = []

    for (w_start, w_end) in windows:
        pushed_range = f"pushed:{iso_date(w_start)}..{iso_date(w_end)}"

        random.shuffle(queries)

        for q_base in queries:
            if len(out) >= target:
                return out

            q = f"{q_base} {pushed_range}"

            page = 1
            while page <= 10 and len(out) < target:
                time.sleep(sleep_search_s)

                try:
                    res = gh.search_repositories(q=q, sort="updated", order="desc", per_page=100, page=page)
                except RuntimeError:
                    break

                items = res.get("items") or []
                if not items:
                    break

                for it in items:
                    if len(out) >= target:
                        return out

                    full_name = it.get("full_name") or ""
                    if not full_name or "/" not in full_name:
                        continue
                    if full_name in seen:
                        continue

                    owner = (it.get("owner") or {}).get("login") or ""
                    repo = it.get("name") or ""
                    default_branch = it.get("default_branch") or ""
                    if not owner or not repo:
                        continue

                    seen.add(full_name)

                    try:
                        if not default_branch:
                            meta = gh.get_repo(owner, repo)
                            default_branch = meta.get("default_branch") or ""
                            time.sleep(0.1)

                        if not default_branch:
                            continue

                        if not is_candidate_repo(owner, repo, default_branch, gh):
                            continue

                        sha = gh.get_commit_sha_for_ref(owner, repo, default_branch)
                        time.sleep(0.15)

                        if not sha:
                            continue

                        out.append(RepoRow(owner=owner, repo=repo, commit_sha=sha, source=source_label))
                        print(f"{len(out)}/{target} repos validés", flush=True)


                    except Exception:
                        continue

                page += 1

    return out


def write_csv(rows: List[RepoRow], out_path: str) -> None:
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["index", "owner", "repo", "commit_sha", "source"])
        for i, r in enumerate(rows):
            w.writerow([i, r.owner, r.repo, r.commit_sha, r.source])


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--target", type=int, default=500)
    p.add_argument("--since-days", type=int, default=365)
    p.add_argument("--window-days", type=int, default=14)
    p.add_argument("--min-stars", type=int, default=3)
    p.add_argument("--out", type=str, default="llm_repos_500.csv")
    p.add_argument("--source", type=str, default="Own_Extracted_Dataset.xlsx")
    p.add_argument("--sleep-search-s", type=float, default=2.1)
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        print("Missing GITHUB_TOKEN in environment", file=sys.stderr)
        print('Example: export GITHUB_TOKEN="ghp_..."\n', file=sys.stderr)
        return 2

    gh = GitHubClient(token=token)

    rows = collect_repos(
        gh=gh,
        target=args.target,
        since_days=args.since_days,
        window_days=args.window_days,
        min_stars=args.min_stars,
        source_label=args.source,
        sleep_search_s=args.sleep_search_s,
    )

    if len(rows) < args.target:
        print(f"Collected {len(rows)} repos, below target {args.target}", file=sys.stderr)
        print("Try increasing --since-days or lowering --min-stars or increasing --window-days", file=sys.stderr)

    rows = rows[: args.target]
    write_csv(rows, args.out)
    print(f"Wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
