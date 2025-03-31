# IACGenius Architecture Overview

## System Components

```mermaid
flowchart TD
    subgraph User Interface
        CLI[CLI Tool] -->|Commands| API[Core API]
        WebUI[Streamlit Web UI] -->|HTTP| API
    end

    subgraph Core Engine
        API --> Config[Configuration Manager]
        API --> Generator[Template Generator]
        API --> LLM[LLM Integration]

        Generator --> Templates[Template Registry]
        LLM --> Providers[(LLM Providers)]
    end

    subgraph Outputs
        Templates --> Terraform[Terraform Templates]
        Templates --> CloudFormation[CloudFormation Templates]
        Templates --> Kubernetes[Kubernetes Manifests]
    end

    Config --> Storage[(Config Storage)]
```

## Flow Sequence

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Core
    participant LLM
    participant Output

    User->>CLI: iacgenius generate --provider aws
    CLI->>Core: parse_command()
    Core->>LLM: get_llm_response(spec)
    LLM-->>Core: generated_config
    Core->>Output: render_template(config)
    Output-->>User: infrastructure.tf
```

## Key Modules

### 1. CLI Interface (`cli.py`)

- Command parsing with Click
- Configuration management commands
- Web UI launch capability

### 2. Core Engine (`iacgenius/`)

- `config_handler.py`: Manage user preferences and secrets
- `generator.py`: Template rendering engine
- `llm_integration.py`: AI provider abstractions

### 3. Web Interface (`streamlit_app.py`)

- Visual template builder
- Real-time preview
- Configuration dashboard
