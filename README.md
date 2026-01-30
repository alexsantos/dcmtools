# dcmtools 🩺

A modern Python CLI for **moving DICOM studies between patients** on a **dcm4chee-arc** archive using its proprietary REST API.  
Built with [Typer](https://typer.tiangolo.com) for a fast, friendly command-line experience — just like `gcloud`.

---

## ✨ Features

- **Move studies** from one patient to another using dcm4chee’s REST `/move/113037^DCM` endpoint  
- **Inspect study attributes** to verify details like `InstitutionName`
- **Batch mode** with CSV input and concurrent transfers (`--concurrency`)  
- **Automatic OAuth2 token refresh** (Keycloak-compatible)  
- **CSV validator** to detect duplicates or missing fields before running  
- **Dry-run mode** to preview actions  
- Clean Typer-based CLI with color output and JSON summaries

---

## 🧱 Requirements

- Python **3.11+**
- `poetry` (for development)
- Works on macOS, Linux, and Windows

---

## 📦 Installation

### From source (recommended for internal use)

```bash
git clone https://github.com/your-org/dcmtools.git
cd dcmtools
poetry install
```

Run directly:
```bash
poetry run dcmtools --help
```

### From PyPI (if published)
```bash
pip install dcmtools
```

After installation, you’ll have the global command:

```bash
dcmtools --help
```

---

## ⚙️ Configuration overview

`dcmtools` communicates with your dcm4chee archive via REST:

- **Show Study**: `GET /dcm4chee-arc/aets/{AET}/rs/studies/{StudyUID}`
- **Move Study**: `POST /dcm4chee-arc/aets/{AET}/rs/studies/{TargetStudyUID}/move/113037^DCM`

The tool builds these calls automatically.

---

## 📋 CSV Format

The batch command expects a CSV file with **headers** (case-insensitive):

```csv
source_study_uid,target_patient_id,issuer_of_patient_id,target_study_uid
1.2.3.4.5,PID1001,JMS,
1.2.3.4.6,PID2002,JMS,1.3.6.1.4.1.62860.999.1
```

Columns:
- `source_study_uid` — StudyInstanceUID to move (from old patient)
- `target_patient_id` — PatientID for the new patient
- `issuer_of_patient_id` — (0010,0021) Issuer (required unless `--default-issuer` provided)
- `target_study_uid` — optional; if omitted, generated automatically with your org UID root

---

## 🧠 Commands

### 1️⃣ Validate your CSV

Before running any move, validate headers and field consistency.

```bash
dcmtools validate-csv --csv studies.csv --default-issuer JMS
```

Output:
```json
{
  "ok": true,
  "rows": 20,
  "problems": []
}
```

### 2️⃣ Show study attributes

Retrieve and print study attributes as JSON. This is useful for inspecting a study's details, such as the `InstitutionName`.

```bash
dcmtools show-study \
  --base-url "https://service.vna.example:8443" \
  --aet "CUFVNAQUAA" \
  --study-uid "1.2.3.4.5.6" \
  --token "your-bearer-token"
```

This will output a JSON object with the study's DICOM attributes.

### 3️⃣ Move a single study

Move one StudyInstanceUID from one patient to another.

```bash
dcmtools move-one \
  --base-url "https://service.vna.example:8443" \
  --aet "CUFVNAQUAA" \
  --source-study-uid "1.2.3.4.5.6" \
  --target-patient-id "PID123" \
  --issuer-of-patient-id "JMS" \
  --token-endpoint "https://keycloak.example/realms/cuf/protocol/openid-connect/token" \
  --client-id "rpa-client" \
  --client-secret "<secret>" \
  --insecure
```

### 4️⃣ Batch move from CSV

Move multiple studies in parallel.

```bash
dcmtools move-batch \
  --csv studies.csv \
  --base-url "https://service.vna.example:8443" \
  --aet "CUFVNAQUAA" \
  --default-issuer "JMS" \
  --out results.csv \
  --concurrency 8 \
  --token-endpoint "https://keycloak.example/realms/cuf/protocol/openid-connect/token" \
  --client-id "rpa-client" \
  --client-secret "<secret>" \
  --insecure
```

**Features:**
- Uses a thread pool (`--concurrency`) for faster throughput
- Automatically refreshes OAuth2 token
- Retries once on HTTP 401
- Writes results (status, HTTP code, error) to `results.csv`

Dry run:
```bash
dcmtools move-batch --csv studies.csv --default-issuer JMS --dry-run
```

---

## 🔐 Authentication

Two modes:

### Static token
```bash
--token "<bearer-token>"
```

### OAuth2 (recommended)
```bash
--token-endpoint "https://keycloak/.../token" \
--client-id "rpa-client" \
--client-secret "<secret>" \
[--scope "openid"]
```

The CLI automatically refreshes tokens before expiry. Safe under concurrency.

---

## ⚠️ Common errors

| Error | Meaning | Fix |
|--------|----------|-----|
| 401 Unauthorized | Invalid or expired token | Refresh token, check credentials |
| 409 Conflict | Study or UID conflict | Ensure target StudyInstanceUID is unique |
| 400 Bad Request | Missing parameters | Check CSV headers or CLI flags |
| Certificate verify failed | Untrusted TLS | Use `--insecure` (testing only) |

---

## 🧩 Development workflow

```bash
# install dependencies
poetry install

# run CLI
poetry run dcmtools --help

# run tests
pytest -v
```

Build distributable packages:
```bash
poetry build
```

Publish (PyPI or private index):
```bash
poetry publish -u __token__ -p <pypi-token>
```

---

## 🪪 License

MIT © 2025  
Created for internal CUF / JMS Lab tooling.

---

## 🧭 Summary

| Command | Description |
|----------|--------------|
| `dcmtools validate-csv` | Validate CSV file structure and data |
| `dcmtools show-study` | Retrieve and print study attributes |
| `dcmtools move-one` | Move a single study |
| `dcmtools move-batch` | Move multiple studies concurrently |
| `--dry-run` | Simulate without API calls |
| `--concurrency` | Control parallelism |
| `--out` | Save results CSV |

---

💡 **Tip:** Run `dcmtools --help` or `dcmtools <command> --help` to see live docs.
