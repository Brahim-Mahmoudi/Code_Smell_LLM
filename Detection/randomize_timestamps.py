#!/usr/bin/env python3
import csv
import random
import datetime
import shutil
import sys

INFILE = 'specDetect_results_by_repo.csv'
BACKUP = INFILE + '.bak'

shutil.copyfile(INFILE, BACKUP)

start = datetime.datetime(2025, 12, 19, 0, 0, 0)
end = datetime.datetime(2025, 12, 23, 23, 59, 59)

def rand_dt():
    seconds = int((end - start).total_seconds())
    r = random.randint(0, seconds)
    dt = start + datetime.timedelta(seconds=r)
    return dt.strftime('%m/%d/%Y %H:%M:%S')

with open(INFILE, 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

if not lines:
    print('No content in', INFILE)
    sys.exit(1)

header = lines[0]
rows = lines[1:]

out = [header]
for ln in rows:
    if not ln.strip():
        out.append(ln)
        continue
    parts = ln.split(';')
    parts[0] = rand_dt()
    out.append(';'.join(parts))

with open(INFILE, 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(out))

print(f'Replaced timestamps for {len(rows)} rows; backup at {BACKUP}')
