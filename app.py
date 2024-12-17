from flask import Flask, request, jsonify
import tempfile
import os
import subprocess
from kubernetes import client, config

app = Flask(__name__)

# Load Kubernetes configuration
config.load_kube_config()
k8s_api = client.CoreV1Api()

def deploy_to_k3s(image_name, image_id):
    """Deploy a pod to k3s cluster with the specified Docker image."""
    if not image_name:
        raise ValueError("Image name must be provided.")

    # Sanitize and validate pod name
    sanitized_image_id = (image_id.replace(":", "-")[:12] if image_id else "default")
    pod_name = f"dockerfile-pod-{sanitized_image_id}".rstrip('-')

    # Define the pod spec
    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": pod_name},
        "spec": {
            "containers": [
                {
                    "name": "dockerfile-container",
                    "image": image_name,
                    "imagePullPolicy": "Never",
                }
            ]
        },
    }

    # Create the pod in the default namespace
    try:
        k8s_api.create_namespaced_pod(namespace="default", body=pod_manifest)
        return f"Pod '{pod_name}' successfully created with image '{image_name}'."
    except client.exceptions.ApiException as e:
        raise RuntimeError(f"Error creating pod: {e}")


@app.route("/build-and-deploy", methods=["POST"])
def build_and_deploy():
    if "dockerfile" not in request.files:
        return jsonify({"error": "Dockerfile not provided."}), 400

    dockerfile = request.files["dockerfile"]

    if dockerfile.filename == "":
        return jsonify({"error": "Empty Dockerfile provided."}), 400

    # Save the Dockerfile to a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        dockerfile.save(dockerfile_path)

        try:
            # Step 1: Build Docker image
            image_name = "dockerfile-app:latest"
            build_command = f"docker build -t {image_name} {temp_dir}"
            build_result = subprocess.run(build_command, shell=True, capture_output=True, text=True)

            if build_result.returncode != 0:
                return jsonify({"error": "Docker build failed.", "details": build_result.stderr}), 500

            # Extract image ID
            image_id = build_result.stdout.strip()  # Simplified for now

            # Step 2: Save Docker image as tarball
            tarball_name = "dockerfile-app.tar"
            tarball_path = os.path.join(temp_dir, tarball_name)
            save_command = f"docker save -o {tarball_path} {image_name}"
            save_result = subprocess.run(save_command, shell=True, capture_output=True, text=True)

            if save_result.returncode != 0:
                return jsonify({"error": "Docker save failed.", "details": save_result.stderr}), 500

            # Step 3: Import tarball into containerd
            import_command = f"ctr -n k8s.io images import {tarball_path}"
            import_result = subprocess.run(import_command, shell=True, capture_output=True, text=True)

            if import_result.returncode != 0:
                return jsonify({"error": "Containerd import failed.", "details": import_result.stderr}), 500

            # Step 4: Deploy the image to k3s
            deployment_message = deploy_to_k3s(image_name, image_id)

            # Success response
            return jsonify({
                "message": "Image built, saved, imported into containerd, and deployed successfully.",
                "deployment_message": deployment_message,
                "image_id": image_id
            })

        except Exception as e:
            return jsonify({"error": "An unexpected error occurred.", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
