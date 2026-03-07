from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

import adaptron

app = typer.Typer(name="adaptron", help="End-to-end LLM Fine-tuning Framework")
console = Console()


@app.command()
def version():
    """Show Adaptron version."""
    console.print(f"Adaptron v{adaptron.__version__}")


@app.command()
def init(project_dir: Path = typer.Option(".", help="Project directory")):
    """Initialize a new Adaptron project with default config."""
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    config_path = project_dir / "adaptron.yaml"
    default_config = """# Adaptron Pipeline Configuration
wizard:
  primary_goal: qa_docs
  data_sources:
    - docs
  data_freshness: static
  hardware: mid
  timeline: medium
  accuracy: professional
  model_size: small

overrides:
  epochs: 3
  learning_rate: 0.0002
  batch_size: 4
  lora_rank: 64
  max_seq_length: 2048
  quantization: Q4_K_M

data:
  input_dir: ./data
  output_dir: ./output

deploy:
  targets:
    - gguf
    - ollama
"""
    config_path.write_text(default_config)
    console.print(f"[green]Initialized Adaptron project at {project_dir}[/green]")
    console.print(f"  Config: {config_path}")
    console.print("  Edit adaptron.yaml to configure your pipeline, then run: adaptron run")


@app.command()
def run(config: Path = typer.Option("adaptron.yaml", help="Path to config file")):
    """Run the full fine-tuning pipeline."""
    from adaptron.core.config import PipelineConfig

    if not config.exists():
        console.print(f"[red]Config file not found: {config}[/red]")
        console.print("Run 'adaptron init' to create a default config.")
        raise typer.Exit(code=1)
    pipeline_config = PipelineConfig.from_yaml(config)
    console.print(
        f"[blue]Pipeline config loaded:[/blue] {len(pipeline_config.training_modes)} training mode(s)"
    )
    console.print(f"  Base model: {pipeline_config.base_model}")
    console.print(f"  Modes: {', '.join(pipeline_config.training_modes)}")
    console.print("[yellow]Full pipeline execution coming soon.[/yellow]")


@app.command()
def wizard():
    """Launch the interactive Training Strategy Wizard."""
    console.print("[yellow]Interactive wizard coming soon. Use the web UI for now.[/yellow]")


if __name__ == "__main__":
    app()
