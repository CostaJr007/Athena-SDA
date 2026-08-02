#!/bin/bash

# Script de setup automatizado para Fedora Linux
# Projeto Athena-SDA

echo "=========================================================="
echo "      Configurando Ambiente do Projeto Athena-SDA         "
echo "=========================================================="

# 1. Update and install system dependencies
echo "-> 1. Updating repositories and installing compilers..."
sudo dnf update -y
sudo dnf groupinstall "Development Tools" -y
sudo dnf install python3-devel python3-pip python3-virtualenv python3-tkinter -y

# 2. Criar ambiente virtual Python
echo "-> 2. Criando ambiente virtual Python (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Ambiente virtual criado."
else
    echo "Virtual environment (.venv) already exists."
fi

# 3. Activate and install Python dependencies
echo "-> 3. Ativando o ambiente virtual e instalando bibliotecas de ML..."
source .venv/bin/activate

pip install --upgrade pip setuptools wheel

# Install scientific, ML, TDA, visualization, and AI libraries
pip install numpy pandas scipy pandas-ta numba scikit-learn xgboost scikit-fuzzy ripser persim ibm-watsonx-ai

echo "=========================================================="
echo "    Setup complete!                                      "
echo "    Para ativar o ambiente virtual na pasta do projeto, rode: "
echo "    source .venv/bin/activate                             "
echo "=========================================================="
