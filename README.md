# Project Setup Guide

## Prerequisites
Ensure your system is up to date and has the necessary tools installed before starting.

## Step 1: Install k3s
Run the following command to install k3s:
```bash
curl -sfL https://get.k3s.io | sh -
```

## Step 2: Update System
Update your system packages:
```bash
sudo apt update && sudo apt upgrade -y
```

## Step 3: Install Python and pip with Virtual Environment
Install Python and pip:
```bash
sudo apt install python3 python3-pip -y
```
Install the virtual environment module:
```bash
sudo apt install python3-venv -y
```

## Step 4: Install Docker
Run the Docker installation script:
```bash
sh docker-install.sh
```

## Step 5: Start the Python Virtual Environment
Create and activate the virtual environment:
```bash
python3 -m venv myenv
source myenv/bin/activate
```

## Step 6: Install Python Requirements
Install the required Python packages:
```bash
pip install -r requirements.txt
pip install --upgrade docker
```

## Step 7: Configure Docker Permissions
Add the current user to the Docker group:
```bash
sudo usermod -aG docker $USER
```

## Step 8: Configure k3s
Copy the k3s configuration file to your home directory:
```bash
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
```
Set the KUBECONFIG environment variable:
```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

## Step 9: Create and Start the Flask App
Run the Flask server:
```bash
python server.py
```

## Step 10: Test the Flask App
Use `curl` to test the application:
```bash
curl -X POST http://localhost:5000/build-and-deploy \
    -F "dockerfile=@/new-dir/Dockerfile"
