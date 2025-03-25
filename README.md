# IACGenius - AI-Powered Infrastructure as Code Generator

IACGenius is an intelligent Infrastructure as Code (IaC) generator that leverages AI to create and manage cloud infrastructure templates. It supports multiple cloud providers and IaC formats through an intuitive CLI and web interface.

## Features

- 🖥️ **Dual Interface**: Choose between CLI and Web UI based on your preference
- 🤖 **Multi-LLM Support**: Compatible with DeepSeek, OpenAI, and Anthropic
- 🛠️ **Multiple IaC Formats**: Generate templates for:
  - Terraform
  - AWS CloudFormation
  - Kubernetes Manifests
  - Helm Charts
  - Docker Configurations
  - CI/CD Pipelines
  - OPA Policies
  - Azure ARM Templates
- 🔧 **Smart Configuration**: Easy setup and management of API keys and preferences
- 📊 **Interactive Web UI**: Built with Streamlit for a seamless user experience

## Quick Start

### Prerequisites

- Python 3.12 or higher
- pip package manager
- API key from one of the supported LLM providers

### Installation

```bash
# Clone the repository
git clone https://github.com/IaC-Genius/iacgenius.git
cd iacgenius

# Install the package
pip install -r requirements.txt
```

### Configuration

```bash
# Set your LLM provider API key
iacgenius config set --api-key YOUR_API_KEY

# Set default provider (deepseek/openai/anthropic)
iacgenius config set --provider deepseek

# Verify configuration
iacgenius config get
```

## Usage

### Command Line Interface

```bash
# Generate Terraform configuration for AWS EC2 instance
iacgenius generate --type terraform --provider aws --description "Create an EC2 instance with t2.micro type"

# Create Kubernetes deployment manifest
iacgenius generate --type kubernetes --description "Create a deployment with 3 replicas of nginx"

# Generate CloudFormation template for S3 bucket
iacgenius generate --type cloudformation --description "Create an S3 bucket with versioning enabled"
```

### Web Interface

1. Start the web server:

```bash
iacgenius run
```

2. Open http://localhost:8501 in your browser
3. Select your desired infrastructure type and provider
4. Describe your requirements in natural language
5. Review and download generated templates

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=iacgenius --cov-report=term-missing
```

### Code Style

This project follows PEP 8 guidelines and uses:

- flake8 for linting
- black for code formatting
- mypy for type checking

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system design.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security

Please do not expose your API keys in the code or commit them to the repository. Use environment variables or secure secret management solutions.

Report security vulnerabilities to [raj@iacgenius.com](mailto:raj@iacgenius.com).
