#!/bin/bash

# Script de setup automatizado para Fedora Linux
# Projeto Athena-SDA

echo "=========================================================="
echo "      Configurando Ambiente do Projeto Athena-SDA         "
echo "=========================================================="

# 1. Atualizar e instalar dependências de sistema
echo "-> 1. Atualizando repositórios e instalando compiladores..."
sudo dnf update -y
sudo dnf groupinstall "Development Tools" -y
sudo dnf install python3-devel python3-pip python3-virtualenv python3-tkinter -y

# 2. Criar ambiente virtual Python
echo "-> 2. Criando ambiente virtual Python (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Ambiente virtual criado."
else
    echo "Ambiente virtual (.venv) já existe."
fi

# 3. Ativar e Instalar Dependências do Python
echo "-> 3. Ativando o ambiente virtual e instalando bibliotecas de ML..."
source .venv/bin/activate

pip install --upgrade pip setuptools wheel

# Instalação das bibliotecas científicas, ML, TDA, visualizações e IA
pip install numpy pandas scipy pandas-ta numba scikit-learn xgboost scikit-fuzzy ripser persim streamlit plotly watchdog ibm-watsonx-ai

echo "=========================================================="
echo "    Setup Concluído!                                      "
echo "    Para ativar o ambiente virtual na pasta do projeto, rode: "
echo "    source .venv/bin/activate                             "
echo "=========================================================="
