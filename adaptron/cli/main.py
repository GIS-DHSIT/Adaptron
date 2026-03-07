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


@app.command()
def playground(
    model: str = typer.Option("", help="Model name to chat with"),
    rag: bool = typer.Option(False, help="Enable RAG context augmentation"),
    temperature: float = typer.Option(0.7, help="Sampling temperature"),
    max_tokens: int = typer.Option(2048, help="Maximum response tokens"),
):
    """Interactive chat with a finetuned model via Ollama."""
    import asyncio
    from adaptron.playground.engine import PlaygroundEngine, ChatMessage

    engine = PlaygroundEngine()

    # List models if none specified
    if not model:
        try:
            models = asyncio.run(engine.list_models())
            if not models:
                console.print("[red]No models found in Ollama.[/red]")
                raise typer.Exit(code=1)
            console.print("[blue]Available models:[/blue]")
            for i, m in enumerate(models):
                name = m.get("name", "unknown")
                prefix = "[green]*[/green] " if name.startswith("adaptron-") else "  "
                console.print(f"  {prefix}{i + 1}. {name}")

            choice = input("\nSelect model number (or type name): ").strip()
            try:
                idx = int(choice) - 1
                model = models[idx].get("name", "")
            except (ValueError, IndexError):
                model = choice
        except Exception as e:
            console.print(f"[red]Cannot connect to Ollama: {e}[/red]")
            console.print("Make sure Ollama is running: ollama serve")
            raise typer.Exit(code=1)

    console.print(f"\n[green]Chatting with:[/green] {model}")
    console.print(f"[dim]Temperature: {temperature} | Max tokens: {max_tokens} | RAG: {'ON' if rag else 'OFF'}[/dim]")
    console.print("[dim]Type 'quit' or 'exit' to stop. Type 'clear' to reset history.[/dim]\n")

    history: list[ChatMessage] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            console.print("[dim]Goodbye![/dim]")
            break
        if user_input.lower() == "clear":
            history.clear()
            console.print("[dim]Chat history cleared.[/dim]")
            continue

        history.append(ChatMessage(role="user", content=user_input))

        console.print(f"\n[green]{model}:[/green] ", end="")

        try:
            async def _stream():
                full = ""
                if rag:
                    stream_iter = await engine.chat_with_rag(
                        model=model, messages=history,
                        temperature=temperature, max_tokens=max_tokens, stream=True,
                    )
                else:
                    stream_iter = engine.chat_stream(
                        model=model, messages=history,
                        temperature=temperature, max_tokens=max_tokens,
                    )
                async for token in stream_iter:
                    print(token, end="", flush=True)
                    full += token
                print()
                return full

            response = asyncio.run(_stream())
            history.append(ChatMessage(role="assistant", content=response))
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            history.pop()  # Remove the failed user message

        print()


@app.command()
def connect_list():
    """List saved connection profiles."""
    from adaptron.connectors.manager import ConnectionManager
    manager = ConnectionManager()
    profiles = manager.list_profiles()
    if not profiles:
        console.print("[yellow]No saved connection profiles.[/yellow]")
        return
    for name in profiles:
        console.print(f"  • {name}")


@app.command()
def connect_test(profile: str = typer.Argument(..., help="Profile name to test")):
    """Test a saved connection profile."""
    import asyncio
    from adaptron.connectors.manager import ConnectionManager
    manager = ConnectionManager()
    try:
        connector = asyncio.run(manager.connect(profile))
        console.print(f"[green]Connection to '{profile}' successful![/green]")
        asyncio.run(connector.disconnect())
    except Exception as e:
        console.print(f"[red]Connection failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def connect_schema(profile: str = typer.Argument(..., help="Profile name")):
    """Show discovered schema for a connection profile."""
    import asyncio
    from adaptron.connectors.manager import ConnectionManager
    manager = ConnectionManager()
    try:
        connector = asyncio.run(manager.connect(profile))
        schema = asyncio.run(connector.discover_schema())
        for coll in schema.collections:
            console.print(f"\n[bold]{coll.name}[/bold] ({coll.source_type})")
            for field in coll.fields:
                pk = " [PK]" if field.is_primary_key else ""
                console.print(f"  {field.name}: {field.data_type}{pk}")
        asyncio.run(connector.disconnect())
    except Exception as e:
        console.print(f"[red]Schema discovery failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def connect_remove(profile: str = typer.Argument(..., help="Profile name to remove")):
    """Remove a saved connection profile."""
    from adaptron.connectors.manager import ConnectionManager
    manager = ConnectionManager()
    manager.remove_profile(profile)
    console.print(f"[green]Profile '{profile}' removed.[/green]")


if __name__ == "__main__":
    app()
