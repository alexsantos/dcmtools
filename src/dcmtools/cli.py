import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import typer

from .api import get_study_attributes_call, move_study_call, decode_response_body
from .auth import TokenManager
from .csv_tools import validate_csv_file, iter_rows
from .uid import make_target_study_uid, DEFAULT_ORG_UID_ROOT

app = typer.Typer(help="Move dcm4chee studies between patients (single/batch), with validation & concurrency.")


# -------------------- show-study --------------------

@app.command("show-study")
def show_study(
    base_url: str = typer.Option(..., help="e.g., https://host:8443"),
    aet: str = typer.Option(..., help="Archive AE Title, e.g., CUFVNAQUAA"),
    study_uid: str = typer.Option(..., help="StudyInstanceUID to query"),
    timeout: int = typer.Option(60, help="HTTP timeout seconds"),
    insecure: bool = typer.Option(False, "--insecure", help="Allow insecure TLS"),
    # Auth
    token: Optional[str] = typer.Option(None, help="Static Bearer token"),
    token_endpoint: Optional[str] = typer.Option(None, help="OAuth2 token endpoint"),
    client_id: Optional[str] = typer.Option(None, help="OAuth2 client_id"),
    client_secret: Optional[str] = typer.Option(None, help="OAuth2 client_secret"),
    scope: Optional[str] = typer.Option(None, help="OAuth2 scope"),
):
    """Retrieve and print study attributes as JSON."""
    tm = build_token_manager(token, token_endpoint, client_id, client_secret, scope, insecure, timeout)
    bearer = tm.get()

    resp = get_study_attributes_call(base_url, aet, bearer, study_uid, insecure=insecure, timeout=timeout)
    if resp.status_code == 401 and not token:
        bearer = tm.get(force_refresh=True)
        resp = get_study_attributes_call(base_url, aet, bearer, study_uid, insecure=insecure, timeout=timeout)

    body = decode_response_body(resp)
    if resp.status_code == 200:
        typer.secho(f"OK HTTP {resp.status_code}", fg=typer.colors.GREEN)
        print(json.dumps(body, indent=2))
    else:
        typer.secho(f"ERROR HTTP {resp.status_code}", fg=typer.colors.RED)
        print(json.dumps({"status": "error", "http": resp.status_code, "response": body}, indent=2))
        raise typer.Exit(code=1)


# -------------------- validate-csv --------------------

@app.command("validate-csv")
def validate_csv(
    csv: str = typer.Option(..., "--csv", help="CSV to validate"),
    require_issuer: bool = typer.Option(True, help="Fail if IssuerOfPatientID is absent and no default provided"),
    default_issuer: Optional[str] = typer.Option(None, help="Issuer used when column is missing"),
):
    """Validate CSV headers, empties, duplicates, and loose UID shape."""
    result = validate_csv_file(csv, require_issuer, default_issuer)
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        raise typer.Exit(code=1)

# -------------------- helpers --------------------

def build_token_manager(
    token: Optional[str],
    token_endpoint: Optional[str],
    client_id: Optional[str],
    client_secret: Optional[str],
    scope: Optional[str],
    insecure: bool,
    timeout: int,
) -> TokenManager:
    if not token and not token_endpoint:
        typer.secho("Provide either --token OR OAuth2 options (--token-endpoint/--client-id/--client-secret).", fg=typer.colors.RED)
        raise typer.Exit(code=2)
    return TokenManager(
        static_token=token,
        token_endpoint=token_endpoint,
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        insecure=insecure,
        timeout=timeout,
    )

# -------------------- move-one --------------------

@app.command("move-one")
def move_one(
    base_url: str = typer.Option(..., help="e.g., https://host:8443"),
    aet: str = typer.Option(..., help="Archive AE Title, e.g., CUFVNAQUAA"),
    source_study_uid: str = typer.Option(..., help="StudyInstanceUID to move"),
    target_patient_id: str = typer.Option(..., help="Target PatientID"),
    issuer_of_patient_id: str = typer.Option(..., help="Issuer (0010,0021), e.g., JMS"),
    target_study_uid: Optional[str] = typer.Option(None, help="If omitted, generated using --org-uid-root"),
    org_uid_root: str = typer.Option(DEFAULT_ORG_UID_ROOT, help="UID root for target Study UID generation"),
    timeout: int = typer.Option(60, help="HTTP timeout seconds"),
    insecure: bool = typer.Option(False, "--insecure", help="Allow insecure TLS"),
    # Auth
    token: Optional[str] = typer.Option(None, help="Static Bearer token"),
    token_endpoint: Optional[str] = typer.Option(None, help="OAuth2 token endpoint"),
    client_id: Optional[str] = typer.Option(None, help="OAuth2 client_id"),
    client_secret: Optional[str] = typer.Option(None, help="OAuth2 client_secret"),
    scope: Optional[str] = typer.Option(None, help="OAuth2 scope"),
):
    """Move a single study between patients using dcm4chee's proprietary endpoint."""
    tm = build_token_manager(token, token_endpoint, client_id, client_secret, scope, insecure, timeout)
    tgt_uid = target_study_uid or make_target_study_uid(org_uid_root)
    typer.secho(f"Target StudyInstanceUID: {tgt_uid}", fg=typer.colors.BLUE)

    bearer = tm.get()
    resp = move_study_call(base_url, aet, bearer, source_study_uid, target_patient_id,
                           issuer_of_patient_id, tgt_uid, insecure=insecure, timeout=timeout)
    if resp.status_code == 401 and not token:
        bearer = tm.get(force_refresh=True)
        resp = move_study_call(base_url, aet, bearer, source_study_uid, target_patient_id,
                               issuer_of_patient_id, tgt_uid, insecure=insecure, timeout=timeout)

    body = decode_response_body(resp)
    if resp.status_code in (200, 202):
        typer.secho(f"OK HTTP {resp.status_code}", fg=typer.colors.GREEN)
        print(json.dumps({
            "status": "ok", "http": resp.status_code,
            "targetStudyInstanceUID": tgt_uid, "response": body
        }, indent=2))
    else:
        typer.secho(f"ERROR HTTP {resp.status_code}", fg=typer.colors.RED)
        print(json.dumps({
            "status": "error", "http": resp.status_code,
            "targetStudyInstanceUID": tgt_uid, "response": body
        }, indent=2))
        raise typer.Exit(code=1)

# -------------------- move-batch --------------------

@app.command("move-batch")
def move_batch(
    csv: str = typer.Option(..., "--csv", help="CSV: source_study_uid,target_patient_id[,issuer_of_patient_id][,target_study_uid]"),
    base_url: str = typer.Option(..., help="e.g., https://host:8443"),
    aet: str = typer.Option(..., help="Archive AE Title"),
    out: Optional[str] = typer.Option(None, "--out", help="Write results CSV here"),
    default_issuer: Optional[str] = typer.Option(None, help="Fallback IssuerOfPatientID if column missing"),
    org_uid_root: str = typer.Option(DEFAULT_ORG_UID_ROOT, help="UID root for generating target Study UIDs"),
    timeout: int = typer.Option(60, help="HTTP timeout seconds"),
    insecure: bool = typer.Option(False, "--insecure", help="Allow insecure TLS"),
    dry_run: bool = typer.Option(False, help="Do not call API; print what would happen"),
    concurrency: int = typer.Option(4, help="Number of parallel moves"),
    # Auth
    token: Optional[str] = typer.Option(None, help="Static Bearer token"),
    token_endpoint: Optional[str] = typer.Option(None, help="OAuth2 token endpoint"),
    client_id: Optional[str] = typer.Option(None, help="OAuth2 client_id"),
    client_secret: Optional[str] = typer.Option(None, help="OAuth2 client_secret"),
    scope: Optional[str] = typer.Option(None, help="OAuth2 scope"),
):
    """Batch move studies from a CSV. Auto-refresh token (client credentials). Uses a thread pool."""
    tm = build_token_manager(token, token_endpoint, client_id, client_secret, scope, insecure, timeout)

    # Dry-run path prints the intended actions
    if dry_run:
        for r in iter_rows(csv, default_issuer):
            tgt = r["tgt"] or make_target_study_uid(org_uid_root)
            typer.echo(f"[dry-run] row={r['row']} src={r['src']} -> tgtStudy={tgt} pid={r['pid']} issuer={r['issuer']}")
        return

    # Worker with 401 retry
    def worker(task: Dict) -> Dict:
        i, src, pid, issuer, tgt = task["row"], task["src"], task["pid"], task["issuer"], task["tgt"]
        result = {"row": i, "source_study_uid": src, "target_study_uid": tgt,
                  "target_patient_id": pid, "issuer_of_patient_id": issuer,
                  "status": "pending", "http": None, "error": None}
        try:
            if not issuer:
                raise ValueError("IssuerOfPatientID is required (provide column or --default-issuer).")
            bearer = tm.get()
            resp = move_study_call(base_url, aet, bearer, src, pid, issuer, tgt, insecure=insecure, timeout=timeout)
            if resp.status_code == 401 and not token:
                bearer = tm.get(force_refresh=True)
                resp = move_study_call(base_url, aet, bearer, src, pid, issuer, tgt, insecure=insecure, timeout=timeout)
            result["http"] = resp.status_code
            body = decode_response_body(resp)
            if resp.status_code in (200, 202):
                result["status"] = "ok"
            else:
                result["status"] = "error"
                result["error"] = body.get("errorMessage") if isinstance(body, dict) else body
        except Exception as ex:
            result["status"] = "error"
            result["error"] = str(ex)
        return result

    # Build tasks (ensuring target UID exists)
    tasks: List[Dict] = []
    for r in iter_rows(csv, default_issuer):
        tgt = r["tgt"] or make_target_study_uid(org_uid_root)
        tasks.append({**r, "tgt": tgt})

    results: List[Dict] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        fut_map = {ex.submit(worker, t): t for t in tasks}
        for fut in as_completed(fut_map):
            r = fut.result()
            results.append(r)
            typer.echo(
                f"[{r['status']}] row={r['row']} src={r['source_study_uid']} -> tgtStudy={r['target_study_uid']} "
                f"pid={r['target_patient_id']} issuer={r['issuer_of_patient_id']}"
                + (f" http={r['http']}" if r.get("http") else "")
                + (f" err={r['error']}" if r.get("error") else "")
            )

    # Optional results CSV
    if out:
        import csv as _csv
        fields = ["row", "source_study_uid", "target_study_uid", "target_patient_id",
                  "issuer_of_patient_id", "status", "http", "error"]
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = _csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in sorted(results, key=lambda x: x["row"]):
                w.writerow(r)
        typer.secho(f"Wrote results to {out}", fg=typer.colors.BLUE)

    summary = {
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "error": sum(1 for r in results if r["status"] == "error"),
        "total": len(results),
    }
    print(json.dumps({"summary": summary}, indent=2))
