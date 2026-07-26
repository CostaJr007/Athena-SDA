# Guia de Configuração e Inicialização no Linux (Fedora)

Este documento contém o passo a passo completo para configurar o ambiente de desenvolvimento, instalar as ferramentas de Machine Learning e estruturar os próximos passos do **Projeto Athena-SDA** no Fedora Linux.

---

## 1. Instalação de Pacotes do Sistema (dnf)

Abra o terminal do Fedora e execute os seguintes comandos para instalar os compiladores, bibliotecas de desenvolvimento do Python e utilitários de contêineres:

```bash
# Atualizar a lista de pacotes
sudo dnf update -y

# Instalar ferramentas de compilação (gcc, g++, make)
sudo dnf groupinstall "Development Tools" -y

# Instalar bibliotecas de desenvolvimento Python e tkinter (necessário para Streamlit/Plotly local)
sudo dnf install python3-devel python3-pip python3-tkinter python3-virtualenv -y
```

### Opcional: Aceleração por GPU
* **Se você usa placa NVIDIA:** Habilite o repositório **RPM Fusion** e instale os drivers CUDA oficiais:
  ```bash
  sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/fedora39/x86_64/cuda-fedora39.repo
  sudo dnf clean all
  sudo dnf install cuda-drivers cuda -y
  ```
* **Se você usa placa AMD:** Instale o suporte ROCm nativo no Fedora:
  ```bash
  sudo dnf install rocm-hip rocm-opencl -y
  ```

---

## 2. Configurando o Ambiente Python (Virtualenv)

No diretório compartilhado do seu drive `D:` (onde o projeto está salvo), execute:

```bash
# Navegar até a pasta do projeto (ajuste o ponto de montagem do drive D no Linux, ex: /run/media/usuario/...)
cd /run/media/seu-usuario/D/Athena-SDA/

# Criar o ambiente virtual Python
python3 -m venv .venv

# Ativar o ambiente virtual
source .venv/bin/activate

# Atualizar gerenciadores de pacotes internos
pip install --upgrade pip setuptools wheel
```

---

## 3. Instalando a Stack de ML e IA (Pip)

Com o ambiente virtual ativo (`(.venv)` no prompt), instale as bibliotecas necessárias para as 14 teorias e visualizações:

```bash
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
