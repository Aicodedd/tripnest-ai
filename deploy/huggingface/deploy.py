"""Upload TripNest AI to a Hugging Face Space (Docker SDK).

    HF_TOKEN=<write token> python deploy/huggingface/deploy.py <hf-username> [space-name]

The token is read from the environment only and is never written to disk or to the repository.
huggingface_hub stores the binary model file correctly, which a plain git push cannot.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def stage(dst: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.db", "tests", "legacy", ".pytest_cache")
    shutil.copytree(ROOT / "backend", dst / "backend", ignore=ignore)
    shutil.copytree(ROOT / "frontend", dst / "frontend", ignore=ignore)
    shutil.copy(ROOT / "requirements.txt", dst / "requirements.txt")
    shutil.copy(HERE / "Dockerfile", dst / "Dockerfile")
    shutil.copy(HERE / "SPACE_README.md", dst / "README.md")


def main() -> None:
    if len(sys.argv) < 2 or not os.environ.get("HF_TOKEN"):
        sys.exit("usage: HF_TOKEN=<write token> python deploy/huggingface/deploy.py <hf-username> [space-name]")
    user, space = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "tripnest-ai")
    repo = f"{user}/{space}"
    api = HfApi(token=os.environ["HF_TOKEN"])
    with tempfile.TemporaryDirectory() as tmp:
        stage(Path(tmp))
        # The Space was created as Static; make sure the Docker SDK is what gets built.
        api.create_repo(repo, repo_type="space", space_sdk="docker", exist_ok=True)
        api.upload_folder(folder_path=tmp, repo_id=repo, repo_type="space", commit_message="Deploy TripNest AI",
                          delete_patterns=["*"])
    print(f"Uploaded. Build logs: https://huggingface.co/spaces/{repo}")
    print(f"Live URL once built: https://{user}-{space}.hf.space")


if __name__ == "__main__":
    main()
