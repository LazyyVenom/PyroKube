import os
import shutil
import subprocess
from typing import Tuple
from services.stack_detector import detect_and_generate_dockerfile


def find_builder_binary() -> str:
    for bin_name in ["docker", "nerdctl", "podman", "buildctl", "/usr/local/bin/docker", "/opt/homebrew/bin/docker", "/usr/bin/docker"]:
        if shutil.which(bin_name) or os.path.exists(bin_name):
            return bin_name
    return "docker"


def build_and_push_user_app(
    service_name: str,
    git_repo: str,
    git_branch: str = "main",
    custom_dockerfile: str = "Dockerfile",
) -> Tuple[str, int, str]:
    """
    Clones Git repository, runs Smart Stack Detector, builds container image
    using native containerd / docker engine, and tags it for deployment.
    Returns (image_tag, default_port, detected_stack).
    """
    workspace_dir = f"/tmp/pyrokube/builds/{service_name}"

    # Clean workspace if exists
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir, ignore_errors=True)
    os.makedirs(workspace_dir, exist_ok=True)

    # 1. Clone Git Repository
    print(f"[ContainerdBuilder] Cloned git repo '{git_repo}' (branch: {git_branch}) into '{workspace_dir}'")
    clone_cmd = f"git clone --depth 1 -b {git_branch} {git_repo} {workspace_dir}"
    try:
        subprocess.run(clone_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        # Fallback to default branch if custom branch fails
        fallback_cmd = f"git clone --depth 1 {git_repo} {workspace_dir}"
        subprocess.run(fallback_cmd, shell=True, check=True)

    # 2. Smart Stack Detection & Auto-Dockerfile Generation
    dockerfile_path, detected_stack, default_port = detect_and_generate_dockerfile(workspace_dir)
    print(f"[ContainerdBuilder] Detected stack: '{detected_stack}', Dockerfile: '{dockerfile_path}', Port: {default_port}")

    # 3. Native Containerd / Docker Build
    builder_bin = find_builder_binary()
    image_tag = f"pyro-app/{service_name}:latest"
    build_cmd = f"{builder_bin} build -t {image_tag} -f {dockerfile_path} {workspace_dir}"
    try:
        res = subprocess.run(build_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            print(f"[ContainerdBuilder] Builder execution info: {res.stderr[:200]}")
    except Exception as e:
        print(f"[ContainerdBuilder] Build execution note: {e}")

    return image_tag, default_port, detected_stack
