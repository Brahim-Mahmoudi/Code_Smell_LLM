import argparse
import csv
import datetime as dt
import json
import re
from pathlib import PurePosixPath, Path

RULE_TO_COL = {
    "R25": "TNES",
    "R26": "NMVP",
    "R27": "NSM",
    "R28": "UMM",
    "R29": "NSO",
    "R30": "RENES",
    "R31": "RVP",
    "R32": "OSP",
    "R33": "AIC",
}

CSV_COLS = [
    "Timestamp",
    "RepoName",
    "FilePath",
    "NSO",
    "UMM",
    "TNES",
    "NMVP",
    "NSM",
    "RENES",
    "RVP",
    "OSP",
    "AIC",
]

LINE_RE = re.compile(r"\bline\s+(\d+)\b", re.IGNORECASE)

def format_timestamp(t: dt.datetime | None = None) -> str:
    t = t or dt.datetime.now()
    return f"{t.month}/{t.day}/{t.year} {t.hour:02d}:{t.minute:02d}:{t.second:02d}"

def canonical_file_id(abs_path: str, owner: str, repo: str, sha: str) -> str:
    sha7 = sha[:7]
    marker = f"{owner}-{repo}-{sha7}"
    p = abs_path.replace("\\", "/")
    idx = p.find(marker)
    if idx != -1:
        return p[idx:]
    m = re.search(r"/extract/([^/]+/.+)$", p)
    if m:
        return m.group(1)
    return f"{owner}-{repo}-{sha7}/{PurePosixPath(p).name}"

def extract_line_list(messages: list[str]) -> str:
    nums: list[int] = []
    for msg in messages:
        if not isinstance(msg, str):
            continue
        for g in LINE_RE.findall(msg):
            try:
                nums.append(int(g))
            except ValueError:
                pass
    if nums:
        uniq = sorted(set(nums))
        return "; ".join(str(x) for x in uniq)
    cleaned = [str(m).strip() for m in messages if str(m).strip()]
    if not cleaned:
        return ""
    s = " | ".join(cleaned[:3])
    return s[:200]

def json_to_rows(payload: dict, stamp: str) -> list[dict]:
    rows: list[dict] = []
    for repo_full, repo_obj in payload.items():
        if not isinstance(repo_obj, dict):
            continue
        owner = repo_obj.get("owner")
        repo = repo_obj.get("repo")
        by_sha = repo_obj.get("by_sha")
        if not owner or not repo or not isinstance(by_sha, dict):
            continue

        for sha, sha_obj in by_sha.items():
            if not isinstance(sha_obj, dict):
                continue
            alerts = sha_obj.get("alerts")
            if not isinstance(alerts, dict):
                continue

            for abs_path, per_file in alerts.items():
                row = {c: "" for c in CSV_COLS}
                row["Timestamp"] = stamp
                row["RepoName"] = f"{owner}/{repo}"
                row["FilePath"] = canonical_file_id(abs_path, owner, repo, sha)

                if isinstance(per_file, dict):
                    if "MISSING_FILE" in per_file or "PARSE_ERROR" in per_file:
                        rows.append(row)
                        continue

                    for rule_id, messages in per_file.items():
                        col = RULE_TO_COL.get(rule_id)
                        if not col:
                            continue
                        if isinstance(messages, list):
                            row[col] = extract_line_list(messages)
                        else:
                            row[col] = str(messages)

                rows.append(row)
    return rows

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json", type=Path, required=True)
    ap.add_argument("--output-csv", type=Path, required=True)
    args = ap.parse_args()

    payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    stamp = format_timestamp()
    rows = json_to_rows(payload, stamp)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote {len(rows)} rows to {args.output_csv}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
