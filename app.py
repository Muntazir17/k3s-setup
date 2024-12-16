from flask import Flask, request, jsonify
import docker
import tempfile
import os
import subprocess
from kubernetes import client, config

app = Flask(__name__)

# Initialize Docker client
docker_client = docker.from_env()

# Load Kubernetes configuration
config.load_kube_config()
k8s_api = client.CoreV1Api()

def import_to_containerd(image_tar_path):
    """Imports a Docker image tarball into containerd."""
    if not os.path.exists(image_tar_path):
        raise ValueError("The provided image tarball path does not exist.")
    try:
        # Use ctr CLI to import the image into containerd
        subprocess.run(["ctr", "-n", "k8s.io", "images", "import", image_tar_path], check=True)
        return "Image successfully imported into containerd."
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to import image to containerd: {e}")
def deploy_to_k3s(image_name, image_id):
    """Deploy a pod to k3s cluster with the specified Docker image."""
    if not image_name:
        raise ValueError("Image name must be provided.")

    # Use the image ID in the pod name for easy differentiation
    pod_name = f"dockerfile-pod-{image_id[:12]}"  # Use the first 12 characters of the image ID to create a unique pod name

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
            # Build the Docker image
            image_name = "dockerfile-app:latest"
            image, _ = docker_client.images.build(path=temp_dir, tag=image_name)

            # Store the image ID for future use
            image_id = image.id

            # Save the image as a tarball
            image_tar_path = os.path.join(temp_dir, "image.tar")
            with open(image_tar_path, "wb") as tar_file:
                for chunk in image.save():
                    tar_file.write(chunk)

            # Import the tarball into containerd
            import_message = import_to_containerd(image_tar_path)

            # Deploy the image to k3s
            deployment_message = deploy_to_k3s(image_name, image_id)
            return jsonify({"import_message": import_message, "deployment_message": deployment_message, "image_id": image_id})

        except docker.errors.BuildError as build_error:
            return jsonify({"error": f"Docker build failed: {build_error}"}), 500
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
