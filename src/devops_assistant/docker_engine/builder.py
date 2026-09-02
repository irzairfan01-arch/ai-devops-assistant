"""
Docker Build Validation Engine.
"""

import os
import time
import subprocess
from devops_assistant.config import DockerBuildResult


def validate_docker_build(target_path: str) -> DockerBuildResult:
    """Detects Dockerfile and validates image build containerization."""
    dockerfile_path = os.path.join(target_path, "Dockerfile")
    compose_path = os.path.join(target_path, "docker-compose.yml")

    has_docker = os.path.exists(dockerfile_path) or os.path.exists(compose_path)
    if not has_docker:
        return DockerBuildResult(
            dockerfile_found=False,
            success=True,
            image_tag="N/A",
            logs="No Dockerfile or docker-compose.yml found in repository."
        )

    start_time = time.time()
    tag = f"devops-assistant-test:{int(time.time())}"
    cmd = ["docker", "build", "-t", tag, target_path]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
        duration = round(time.time() - start_time, 2)
        success = res.returncode == 0

        logs = res.stdout + ("\n" + res.stderr if res.stderr else "")
        failure_reason = None if success else f"Docker build returned exit code {res.returncode}"

        return DockerBuildResult(
            dockerfile_found=True,
            success=success,
            image_tag=tag if success else "N/A",
            duration_seconds=duration,
            logs=logs,
            failure_reason=failure_reason
        )
    except FileNotFoundError:
        return DockerBuildResult(
            dockerfile_found=True,
            success=False,
            image_tag="N/A",
            logs="Docker CLI binary not found on local system.",
            failure_reason="Docker CLI missing"
        )
    except subprocess.TimeoutExpired:
        return DockerBuildResult(
            dockerfile_found=True,
            success=False,
            image_tag="N/A",
            logs="Docker build timed out after 180 seconds.",
            failure_reason="TimeoutExpired"
        )
    except Exception as e:
        return DockerBuildResult(
            dockerfile_found=True,
            success=False,
            image_tag="N/A",
            logs=f"Docker build failed with exception: {e}",
            failure_reason=str(e)
        )
