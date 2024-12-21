import os
import re
import time
import tempfile
import subprocess
import logging
from flask import Flask, request, jsonify
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Kubernetes configuration
config.load_kube_config()
apps_v1_api = client.AppsV1Api()

# Configuration constants
K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "default")
DEPLOY_WAIT_TIME = int(os.getenv("DEPLOY_WAIT_TIME", "30"))
IMAGE_PULL_POLICY = os.getenv("IMAGE_PULL_POLICY", "Never")

def deploy_to_k3s(image_name, deployment_name):
    """Deploy a container to k3s with the specified Docker image."""
    if not image_name:
        raise ValueError("Image name must be provided.")
    if not deployment_name:
        raise ValueError("Deployment name must be provided.")
    if not re.match(r"^[a-zA-Z0-9_\-]+$", deployment_name):
        raise ValueError("Deployment name contains invalid characters.")

    deployment_manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": deployment_name},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": deployment_name}},
            "template": {
                "metadata": {"labels": {"app": deployment_name}},
                "spec": {
                    "containers": [
                        {
                            "name": "dockerfile-container",
                            "image": image_name,
                            "imagePullPolicy": IMAGE_PULL_POLICY,
                        }
                    ]
                },
            },
        },
    }

    try:
        apps_v1_api.create_namespaced_deployment(namespace=K8S_NAMESPACE, body=deployment_manifest)
        return f"Deployment '{deployment_name}' successfully created with image '{image_name}'."
    except ApiException as e:
        if e.status == 409:
            return f"Deployment '{deployment_name}' already exists."
        raise RuntimeError(f"Kubernetes API error: {e.reason}")

def delete_deployment(deployment_name):
    """Delete a deployment in k3s."""
    if not deployment_name:
        raise ValueError("Deployment name must be provided.")

    try:
        apps_v1_api.read_namespaced_deployment(name=deployment_name, namespace=K8S_NAMESPACE)
        apps_v1_api.delete_namespaced_deployment(name=deployment_name, namespace=K8S_NAMESPACE)
        return f"Deployment '{deployment_name}' successfully deleted."
    except ApiException as e:
        if e.status == 404:
            return f"Deployment '{deployment_name}' does not exist."
        raise RuntimeError(f"Kubernetes API error: {e.reason}")

def cleanup_function(image_name):
    """Remove Docker image and containerd image."""
    cleanup_messages = []

    # Remove Docker image
    try:
        remove_docker_command = f"docker rmi -f {image_name}"
        remove_docker_result = subprocess.run(remove_docker_command, shell=True, capture_output=True, text=True)

        if remove_docker_result.returncode == 0:
            cleanup_messages.append(f"Docker image '{image_name}' successfully removed.")
        else:
            cleanup_messages.append(f"Failed to remove Docker image '{image_name}': {remove_docker_result.stderr}")
    except Exception as e:
        cleanup_messages.append(f"Error removing Docker image: {str(e)}")

    # Remove image from containerd
    try:
        remove_ctr_command = f"ctr -n k8s.io images remove {image_name}"
        remove_ctr_result = subprocess.run(remove_ctr_command, shell=True, capture_output=True, text=True)

        if remove_ctr_result.returncode == 0:
            cleanup_messages.append(f"Containerd image '{image_name}' successfully removed.")
        else:
            cleanup_messages.append(f"Failed to remove containerd image '{image_name}': {remove_ctr_result.stderr}")
    except Exception as e:
        cleanup_messages.append(f"Error removing containerd image: {str(e)}")

    return "; ".join(cleanup_messages)

@app.route("/build-and-deploy", methods=["POST"])
def build_and_deploy():
    """Build and deploy a Dockerfile to k3s."""
    if "dockerfile" not in request.files:
        return jsonify({"error": "Dockerfile not provided."}), 400

    dockerfile = request.files["dockerfile"]

    if dockerfile.filename == "":
        return jsonify({"error": "Empty Dockerfile provided."}), 400

    with tempfile.TemporaryDirectory() as temp_dir:
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        dockerfile.save(dockerfile_path)

        try:
            image_time_stamp = time.strftime("%Y%m%d%H%M%S")
            image_name = f"dockerfile-app-{image_time_stamp}"

            # Step 1: Build Docker image
            build_command = f"docker build -t {image_name} {temp_dir}"
            build_result = subprocess.run(build_command, shell=True, capture_output=True, text=True)

            if build_result.returncode != 0:
                logger.error(f"Docker build failed: {build_result.stderr}")
                return jsonify({"error": "Docker build failed.", "details": build_result.stderr}), 500

            docker_build_message = "Image built successfully."

            # Step 2: Save Docker image as tarball
            tarball_name = "dockerfile-app.tar"
            tarball_path = os.path.join(temp_dir, tarball_name)
            save_command = f"docker save -o {tarball_path} {image_name}"
            save_result = subprocess.run(save_command, shell=True, capture_output=True, text=True)

            if save_result.returncode != 0:
                logger.error(f"Docker save failed: {save_result.stderr}")
                return jsonify({"error": "Docker save failed.", "details": save_result.stderr}), 500

            tarball_save_message = "Image saved as tarball successfully."

            # Step 3: Import tarball into containerd
            import_command = f"ctr -n k8s.io images import {tarball_path}"
            import_result = subprocess.run(import_command, shell=True, capture_output=True, text=True)

            if import_result.returncode != 0:
                logger.error(f"Containerd import failed: {import_result.stderr}")
                return jsonify({"error": "Containerd import failed.", "details": import_result.stderr}), 500

            ctr_import_message = "Image loaded into containerd successfully."

            # Step 4: Deploy the image to k3s
            deployment_name = f"test-deploy-{image_time_stamp}"
            deployment_message = deploy_to_k3s(image_name, deployment_name)

            # Wait before deleting the deployment
            time.sleep(DEPLOY_WAIT_TIME)

            # Step 5: Delete the deployment
            deletion_message = delete_deployment(deployment_name)

            # Step 6: Cleanup Docker and containerd images
            cleanup_message = cleanup_function(image_name)

            return jsonify({
                "message": "Image built, saved, imported into containerd, deployed, and cleaned up successfully.",
                "details": {
                    "docker_build": docker_build_message,
                    "tarball_save": tarball_save_message,
                    "ctr_import": ctr_import_message,
                    "deployment_message": deployment_message,
                    "deletion_message": deletion_message,
                    "cleanup_message": cleanup_message,
                },
            })

        except Exception as e:
            logger.exception("An unexpected error occurred.")
            return jsonify({"error": "An unexpected error occurred.", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
