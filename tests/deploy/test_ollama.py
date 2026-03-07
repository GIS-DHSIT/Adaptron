from adaptron.deploy.ollama import OllamaDeployer


def test_generates_modelfile():
    deployer = OllamaDeployer()
    modelfile = deployer.generate_modelfile(
        model_path="/models/adaptron.gguf",
        system_prompt="You are a helpful domain assistant.",
        temperature=0.7,
    )
    assert "FROM /models/adaptron.gguf" in modelfile
    assert "SYSTEM" in modelfile
    assert "0.7" in modelfile


def test_model_name_generation():
    deployer = OllamaDeployer()
    name = deployer.model_name("my-project")
    assert name == "adaptron-my-project"
