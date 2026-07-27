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

# 1. Base Científica e Processamento de Dados
pip install numpy pandas scipy pandas-ta jinja2

# 2. Compilação JIT (Acelera os cálculos de Hurst e Entropia)
pip install numba

# 3. Machine Learning e Inteligência Fuzzy
pip install scikit-learn xgboost scikit-fuzzy

# 4. Análise de Dados Topológicos (TDA - Homologia Persistente)
pip install ripser persim

# 5. Interface Gráfica e Visualizações 3D
pip install streamlit plotly watchdog

# 6. Integração com IBM watsonx / LLM Granite
pip install ibm-watsonx-ai
```

---

## 4. O que faremos na Próxima Sessão (Roteiro)

Quando você abrir a nova sessão no Linux, o agente IA poderá guiar você nas seguintes etapas de codificação:

```
ETAPA 1: Criar a pasta de código local `athena/`
ETAPA 2: Codificar o extrator de features (`athena/engine.py`)
         - Shannon Entropy
         - Kolmogorov Proxy (compressão zlib)
         - Hurst Exponent (R/S)
ETAPA 3: Criar gerador de TLE de testes e ingestão (`athena/utils.py`)
ETAPA 4: Criar o pipeline de ML (`athena/models.py`)
         - Isolation Forest para anomalias
         - XGBoost para classificação (🟢🟡🟠🔴)
ETAPA 5: Criar o motor lógico de incertezas (`athena/fuzzy.py`)
ETAPA 6: Ligar o copiloto inteligente Bob (`athena/bob.py`)
ETAPA 7: Montar a tela Streamlit 3D (`app.py`)
```

---

## 5. Como rodar a aplicação para testar
Após a criação dos arquivos de código, você poderá testar a aplicação executando:
```bash
streamlit run app.py
```
Isso abrirá o navegador no painel interativo do **Athena-SDA**.
