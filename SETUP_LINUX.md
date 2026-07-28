# Linux Setup & Installation Guide (Fedora)

This document provides step-by-step instructions for configuring the development environment, installing Machine Learning tools, and running **Athena-SDA** on Linux systems.

---

## 1. System Package Installation (dnf)

Execute the following commands to install build tools, Python development headers, and system dependencies:

```bash
# Update package repositories
sudo dnf update -y

# Install build essentials (gcc, g++, make)
sudo dnf groupinstall "Development Tools" -y

# Install Python development packages and tkinter
sudo dnf install python3-devel python3-pip python3-tkinter python3-virtualenv -y
```

### Optional: GPU Acceleration
* **NVIDIA GPU:** Install CUDA drivers from the official NVIDIA RPM repository.
* **AMD GPU:** Install native ROCm HIP support:
  ```bash
  sudo dnf install rocm-hip rocm-opencl -y
  ```

---

## 2. Python Virtual Environment Setup

Navigate to your project folder and initialize the environment:

```bash
cd Athena-SDA/

# Create Python virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip and build tools
pip install --upgrade pip setuptools wheel
```

---

## 3. Installing Dependencies

With the virtual environment active (`(.venv)`), install the required dependencies:

```bash
pip install -r requirements.txt
```

---

## 4. Operational Ingest & Verification

```bash
# Ingest TLE history and space weather data
python scripts/run_anomaly_monitor.py seed-history --hf --start-year 2014
python scripts/run_anomaly_monitor.py seed-space-weather --force --start-year 2014

# Verify system status
python scripts/run_anomaly_monitor.py status
```

# 1. Scientific base and data processing
pip install numpy pandas scipy pandas-ta jinja2

# 2. JIT compilation (speeds up Hurst and entropy)
pip install numba

# 3. Machine learning and fuzzy intelligence
pip install scikit-learn xgboost scikit-fuzzy

# 4. Topological data analysis (TDA — persistent homology)
pip install ripser persim

# 5. GUI and 3D visualizations
pip install streamlit plotly watchdog

# 6. IBM watsonx / Granite LLM integration
pip install ibm-watsonx-ai
```

---

## 4. Next session roadmap

When you open a new Linux session, the AI agent can guide you through these coding steps:

```
STEP 1: Create the local code folder `athena/`
ETAPA 2: Codificar o extrator de features (`athena/engine.py`)
         - Shannon Entropy
         - Kolmogorov Proxy (zlib compression)
         - Hurst Exponent (R/S)
STEP 3: Create test TLE generator and ingest (`athena/utils.py`)
STEP 4: Create the ML pipeline (`athena/models.py`)
         - Isolation Forest para anomalias
         - XGBoost for classification (🟢🟡🟠🔴)
STEP 5: Create the uncertainty logic engine (`athena/fuzzy.py`)
ETAPA 6: Ligar o copiloto inteligente Bob (`athena/bob.py`)
ETAPA 7: Montar a tela Streamlit 3D (`app.py`)
```

---

## 5. How to run the app for testing
After creating the code files, you can test the application by running:
```bash
streamlit run app.py
```
This will open the browser on the interactive **Athena-SDA** panel.
