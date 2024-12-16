#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

echo "############################################################################"
echo "#                                                                          #"
echo "#                   Docker Installer for Ubuntu                            #"
echo "#                                                                          #"
echo "############################################################################"
echo ""

# Step 1: Update the package list
echo "Updating package list..."
sudo apt-get update -y

# Step 2: Install prerequisite packages
echo "Installing prerequisite packages..."
sudo apt-get install -y ca-certificates curl

# Step 3: Add Docker's official GPG key
echo "Adding Docker's official GPG key..."
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Step 4: Add the Docker repository
echo "Adding Docker repository to sources list..."
echo \
	  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
	    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
	      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Step 5: Update the package list again
echo "Updating package list for Docker..."
sudo apt-get update -y

# Step 6: Install Docker packages
echo "Installing Docker packages..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Step 7: Start and enable Docker service
echo "Starting and enabling Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

# Step 8: Verify Docker installation
echo "Verifying Docker installation..."
if docker --version; then
	  echo "Docker installed and running successfully!"
  else
	    echo "Docker installation failed!"
	      exit 1
fi

echo "############################################################################"
echo "#                                                                          #"
echo "#                 Docker Installation Completed                            #"
echo "#                                                                          #"
echo "############################################################################"

