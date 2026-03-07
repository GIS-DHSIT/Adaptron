from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from adaptron.core.registry import register_plugin
from adaptron.deploy.base import BaseDeployer, DeploymentArtifact

logger = logging.getLogger(__name__)


@register_plugin("deployer", "ollama")
class OllamaDeployer(BaseDeployer):
    def model_name(self, project_name: str) -> str:
        return f"adaptron-{project_name}"

    def generate_modelfile(
        self,
        model_path: str,
        system_prompt: str = "You are a helpful AI assistant fine-tuned for domain-specific tasks.",
        temperature: float = 0.7,
        context_length: int = 4096,
    ) -> str:
        return (
            f"FROM {model_path}\n"
            f"\n"
            f'SYSTEM """{system_prompt}"""\n'
            f"\n"
            f"PARAMETER temperature {temperature}\n"
            f"PARAMETER num_ctx {context_length}\n"
            f'PARAMETER stop "### Instruction:"\n'
            f'PARAMETER stop "### Response:"\n'
        )

    async def deploy(
        self,
        model_path: str,
        project_name: str = "default",
        system_prompt: str = "You are a helpful AI assistant fine-tuned for domain-specific tasks.",
        auto_serve: bool = False,
        **kwargs,
    ) -> DeploymentArtifact:
        name = self.model_name(project_name)
        modelfile_content = self.generate_modelfile(
            model_path=model_path, system_prompt=system_prompt
        )
        modelfile_path = Path(model_path).parent / "Modelfile"
        modelfile_path.write_text(modelfile_content)

        logger.info("Creating Ollama model: %s", name)
        try:
            subprocess.run(
                ["ollama", "create", name, "-f", str(modelfile_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                f"Failed to register model with Ollama. Ensure Ollama is installed. Error: {e}"
            )

        if auto_serve:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        return DeploymentArtifact(
            target="ollama",
            model_id=name,
            path=str(modelfile_path),
            metadata={"modelfile": modelfile_content},
        )
