import json
import urllib.parse
from typing import Optional

import requests

MOVE_CODE = "113037^DCM"  # vendor-specific path segment

def move_study_call(
    base_url: str,
    aet: str,
    bearer_token: str,
    source_study_uid: str,
    target_patient_id: str,
    issuer_of_patient_id: str,
    target_study_uid: str,
    insecure: bool = False,
    timeout: int = 60,
) -> requests.Response:
    """
    POST {base}/dcm4chee-arc/aets/{AET}/rs/studies/{TargetStudyUID}/move/113037^DCM
         ?PatientID={PID2}&IssuerOfPatientID={Issuer}
    Body: {"StudyInstanceUID":"{SourceStudyUID}"}
    """
    move_path = (
        f"/dcm4chee-arc/aets/{urllib.parse.quote(aet, safe='')}/rs/"
        f"studies/{urllib.parse.quote(target_study_uid, safe='')}/move/{urllib.parse.quote(MOVE_CODE, safe='')}"
    )
    url = base_url.rstrip("/") + move_path
    params = {"PatientID": target_patient_id, "IssuerOfPatientID": issuer_of_patient_id}
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {"StudyInstanceUID": source_study_uid}
    return requests.post(url, params=params, headers=headers, json=payload, timeout=timeout, verify=not insecure)

def decode_response_body(resp: requests.Response):
    try:
        return resp.json()
    except Exception:
        return resp.text
