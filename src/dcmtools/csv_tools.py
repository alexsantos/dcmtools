import csv
import re
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

UID_RE = re.compile(r"^[0-9]+(\.[0-9]+)*$")  # loose DICOM UID shape

def read_csv_rows(path: str) -> Tuple[Dict[str, str], Iterator[Dict[str, str]]]:
    f = open(path, newline="", encoding="utf-8")
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        f.close()
        raise ValueError("CSV has no header.")
    header_map = {h.lower(): h for h in reader.fieldnames}
    return header_map, iter(reader)

def validate_csv_file(path: str, require_issuer: bool, default_issuer: Optional[str]) -> Dict:
    problems: List[str] = []
    rows_checked = 0
    uids_seen: set[str] = set()
    tgt_uids_seen: set[str] = set()

    header_map, rows = read_csv_rows(path)
    required = {"source_study_uid", "target_patient_id"}
    missing = required - set(header_map.keys())
    if missing:
        problems.append(f"Missing required columns: {', '.join(sorted(missing))}")

    for idx, row in enumerate(rows, start=2):  # header is line 1
        rows_checked += 1
        src = row.get(header_map.get("source_study_uid", "source_study_uid")) or ""
        pid = row.get(header_map.get("target_patient_id", "target_patient_id")) or ""
        issuer = row.get(header_map.get("issuer_of_patient_id", "issuer_of_patient_id")) \
                 or default_issuer or ""
        tgt = row.get(header_map.get("target_study_uid", "target_study_uid")) or ""

        if not src:
            problems.append(f"Line {idx}: empty source_study_uid")
        if src and not UID_RE.match(src):
            problems.append(f"Line {idx}: source_study_uid looks invalid: {src}")
        if not pid:
            problems.append(f"Line {idx}: empty target_patient_id")

        if require_issuer and not issuer:
            problems.append(f"Line {idx}: issuer_of_patient_id missing and no --default-issuer provided")

        if src:
            if src in uids_seen:
                problems.append(f"Line {idx}: duplicate source_study_uid {src}")
            uids_seen.add(src)
        if tgt:
            if not UID_RE.match(tgt):
                problems.append(f"Line {idx}: target_study_uid looks invalid: {tgt}")
            if tgt in tgt_uids_seen:
                problems.append(f"Line {idx}: duplicate target_study_uid {tgt}")
            tgt_uids_seen.add(tgt)

    return {"ok": len(problems) == 0, "rows": rows_checked, "problems": problems}

def iter_rows(path: str, default_issuer: Optional[str] = None):
    header_map, rows = read_csv_rows(path)
    for i, row in enumerate(rows, start=1):
        src = row.get(header_map.get("source_study_uid")) or row.get("source_study_uid")
        pid = row.get(header_map.get("target_patient_id")) or row.get("target_patient_id")
        issuer = row.get(header_map.get("issuer_of_patient_id")) or row.get("issuer_of_patient_id") or default_issuer
        tgt = row.get(header_map.get("target_study_uid")) or row.get("target_study_uid")
        yield {"row": i, "src": src, "pid": pid, "issuer": issuer, "tgt": tgt}
