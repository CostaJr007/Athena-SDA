#!/bin/bash

# Automated setup script for Fedora Linux
# Athena-SDA project

echo "=========================================================="
echo "      Configuring Athena-SDA project environment          "
echo "=========================================================="

# 1. Update and install system dependencies
echo "-> 1. Updating repositories and installing compilers..."
sudo dnf update -y
sudo dnf groupinstall "Development Tools" -y
sudo dnf install python3-devel python3-pip python3-virtualenv python3-tkinter -y

# 2. Create Python virtual environment
echo "-> 2. Creating Python virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Virtual environment created."
else
    echo "Virtual environment (.venv) already exists."
fi

# 3. Activate and install Python dependencies
echo "-> 3. Activating venv and installing ML libraries..."
source .venv/bin/activate

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "=========================================================="
echo "    Setup complete!                                      "
echo "    Activate the environment with:                       "
echo "    source .venv/bin/activate                             "
echo "=========================================================="
