from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from adaptron.core.registry import global_registry
from adaptron.deploy.huggingface import HuggingFaceDeployer


def test_registered_as_deployer_huggingface():
    cls = global_registry.get("deployer", "huggingface")
    assert cls is HuggingFaceDeployer


@pytest.mark.asyncio
async def test_deploy_uploads_to_hub():
    deployer = HuggingFaceDeployer()

    mock_api_instance = MagicMock()
    mock_hf_module = MagicMock()
    mock_hf_module.HfApi.return_value = mock_api_instance

    with patch.dict("sys.modules", {"huggingface_hub": mock_hf_module}):
        artifact = await deployer.deploy(
            model_path="/tmp/my-model",
            repo_id="user/my-model",
            private=True,
            commit_message="Test upload",
        )

    assert artifact.target == "huggingface"
    assert artifact.url == "https://huggingface.co/user/my-model"
    assert artifact.model_id == "user/my-model"
    assert artifact.metadata["private"] is True
    assert artifact.metadata["commit_message"] == "Test upload"

    mock_api_instance.create_repo.assert_called_once_with(
        repo_id="user/my-model", private=True, exist_ok=True,
    )
    mock_api_instance.upload_folder.assert_called_once_with(
        folder_path="/tmp/my-model",
        repo_id="user/my-model",
        commit_message="Test upload",
    )


@pytest.mark.asyncio
async def test_deploy_missing_repo_id():
    deployer = HuggingFaceDeployer()
    with pytest.raises(ValueError, match="repo_id is required"):
        await deployer.deploy(model_path="/tmp/my-model")


@pytest.mark.asyncio
async def test_deploy_upload_failure():
    deployer = HuggingFaceDeployer()

    mock_api_instance = MagicMock()
    mock_api_instance.create_repo.side_effect = Exception("Invalid token")

    with patch.dict("sys.modules", {"huggingface_hub": MagicMock(HfApi=MagicMock(return_value=mock_api_instance))}):
        with pytest.raises(RuntimeError, match="Failed to upload model to HuggingFace Hub"):
            await deployer.deploy(
                model_path="/tmp/my-model",
                repo_id="user/my-model",
            )


@pytest.mark.asyncio
async def test_deploy_missing_huggingface_hub():
    deployer = HuggingFaceDeployer()

    with patch.dict("sys.modules", {"huggingface_hub": None}):
        with pytest.raises(RuntimeError, match="huggingface_hub is not installed"):
            await deployer.deploy(
                model_path="/tmp/my-model",
                repo_id="user/my-model",
            )
