from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from adaptron.core.registry import register_plugin
from adaptron.deploy.base import BaseDeployer, DeploymentArtifact

logger = logging.getLogger(__name__)


@register_plugin("deployer", "gguf")
class GGUFDeployer(BaseDeployer):
    async def deploy(
        self,
        model_path: str,
        output_dir: str | None = None,
        quantization: str = "Q4_K_M",
        **kwargs,
    ) -> DeploymentArtifact:
        model_dir = Path(model_path)
        out_dir = Path(output_dir or model_path)
        out_dir.mkdir(parents=True, exist_ok=True)

        gguf_path = out_dir / f"model-{quantization}.gguf"

        logger.info("Converting model to GGUF format: %s", quantization)
        convert_cmd = [
            "python",
            "-m",
            "llama_cpp.convert",
            "--outfile",
            str(gguf_path),
            "--outtype",
            quantization.lower(),
            str(model_dir),
        ]

        try:
            subprocess.run(convert_cmd, check=True, capture_output=True, text=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                f"GGUF conversion failed. Ensure llama-cpp-python is installed. Error: {e}"
            )

        return DeploymentArtifact(
            target="gguf",
            path=str(gguf_path),
            metadata={"quantization": quantization},
        )
