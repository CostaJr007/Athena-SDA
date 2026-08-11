# Linux Setup & Installation Guide (Fedora)

Step-by-step for configuring the environment and running **Athena-SDA** on Linux.

> Honest note: TLE/space-weather seeding needs network access to CelesTrak /
> GFZ / HuggingFace. If you just want the UI + current artifacts, skip seeding —
> `data/history/epochs.parquet` is already committed.

---

## 1. System packages (dnf)

```bash
sudo dnf update -y
sudo dnf groupinstall "Development Tools" -y
sudo dnf install python3-devel python3-pip python3-virtualenv -y
```

Optional GPU acceleration: CUDA (NVIDIA) or ROCm (AMD) — not required; the ML
models are small and run fine on CPU.

---

## 2. Python virtual environment

```bash
cd Athena-SDA
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

---

## 3. Verify the quant core (fast gate)

```bash
python scripts/smoke_test.py
# → SMOKE OK
```

---

## 4. Seed data (one-time; needs network)

```bash
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014
python scripts/run_anomaly_monitor.py status
```

---

## 5. Train + score the daily pipeline

```bash
# Monitor Isolation Forest (past-only baseline; hot-swap snapshot saved)
python scripts/run_anomaly_monitor.py train-baseline

# Priority pipeline (IF + XGBoost + MMD reference)
python -c "from src.models import train_and_save_models; train_and_save_models()"

# Score today's watchlist + suspect×asset pairs → risk_report_latest.json
python scripts/run_anomaly_monitor.py score
python scripts/run_anomaly_monitor.py score-pairs

# Ship the latest artifacts to the UI
bash scripts/sync_frontend_data.sh
```

---

## 6. Walk-forward validation (Claims A+B)

```bash
python scripts/run_paper_validation.py --run-wf --threshold 0.50
```

---

## 7. Mission board UI

```bash
cd src/frontend
npm install
npm run dev
# http://127.0.0.1:3000
```

Build for static hosting:

```bash
npm run build   # dist/
```
