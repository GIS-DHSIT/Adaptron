from __future__ import annotations

import logging

from adaptron.core.registry import register_plugin
from adaptron.deploy.base import BaseDeployer, DeploymentArtifact

logger = logging.getLogger(__name__)


@register_plugin("deployer", "huggingface")
class HuggingFaceDeployer(BaseDeployer):
    """Deploys trained models to HuggingFace Hub."""

    async def deploy(
        self,
        model_path: str,
        repo_id: str = "",
        private: bool = False,
        commit_message: str = "Upload model via Adaptron",
        **kwargs,
    ) -> DeploymentArtifact:
        if not repo_id:
            raise ValueError("repo_id is required for HuggingFace Hub deployment.")

        try:
            from huggingface_hub import HfApi
        except ImportError:
            raise RuntimeError(
                "huggingface_hub is not installed. "
                "Install it with: pip install huggingface_hub"
            )

        api = HfApi()

        logger.info("Uploading model to HuggingFace Hub: %s", repo_id)
        try:
            api.create_repo(repo_id=repo_id, private=private, exist_ok=True)
            api.upload_folder(
                folder_path=model_path,
                repo_id=repo_id,
                commit_message=commit_message,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to upload model to HuggingFace Hub. "
                f"Ensure you are authenticated (huggingface-cli login). "
                f"Error: {e}"
            ) from e

        url = f"https://huggingface.co/{repo_id}"
        return DeploymentArtifact(
            target="huggingface",
            url=url,
            model_id=repo_id,
            metadata={
                "private": private,
                "commit_message": commit_message,
            },
        )
