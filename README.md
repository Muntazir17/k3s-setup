# Project Setup Guide

## Prerequisites
Ensure your Ubuntu:22.04 system is up to date and has the necessary tools installed before starting.

## Step 1: Update System
Update your system packages:
```bash
apt update
```

## Step 2: Install Python and pip with Virtual Environment
Install Python and pip:
```bash
apt install python3 python3-pip -y
```
Install the virtual environment module:
```bash
apt install python3-venv -y
```

## Step 3: Install k3s on the System
Run the following command to install k3s:
```bash
curl -sfL https://get.k3s.io | sh -
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
```

## Step 7: Configure Docker Permissions
Add the current user to the Docker group:
```bash
usermod -aG docker $USER
```

## Step 8: Verify and Configure k3s
Check if the k3s configuration file exists:
```bash
ls /etc/rancher/k3s/k3s.yaml
```
Copy the k3s configuration file to your home directory:
```bash
cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
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
Use `curl` to test the application by replacing `<IP-Addr>` with your server's IP address:
```bash
curl -X POST http://<IP-Addr>:5000/build-and-deploy -F "dockerfile=@Dockerfile"
```
