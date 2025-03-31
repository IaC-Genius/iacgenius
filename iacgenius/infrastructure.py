import os
import toml
from typing import List, Optional # Ensure Dict and Any are removed

# Default infrastructure types if not defined in config
DEFAULT_INFRASTRUCTURE_TYPES = [
    "Terraform", 
    "CloudFormation", 
    "Kubernetes (Manifests)", 
    "Helm Chart", 
    "Docker", 
    "CI/CD Pipeline", 
    "OPA Policy",
    "Azure Resource Manager (ARM)"
]

# Mapping of infrastructure types to file extensions
INFRASTRUCTURE_FILE_EXTENSIONS = {
    "Terraform": ".tf",
    "CloudFormation": ".yaml",
    "Kubernetes (Manifests)": ".yaml",
    "Helm Chart": ".yaml",
    "Docker": "Dockerfile",
    "CI/CD Pipeline": ".yaml",
    "OPA Policy": ".rego",
    "Azure Resource Manager (ARM)": ".json"
}

# Mapping of infrastructure types to syntax highlighting languages
INFRASTRUCTURE_LANGUAGES = {
    "Terraform": "terraform",
    "CloudFormation": "yaml",
    "Kubernetes (Manifests)": "yaml",
    "Helm Chart": "yaml",
    "Docker": "dockerfile",
    "CI/CD Pipeline": "yaml",
    "OPA Policy": "rego",
    "Azure Resource Manager (ARM)": "json"
}

def get_infrastructure_types() -> List[str]:
    """Get the list of supported infrastructure types"""
    config_path = "config.toml"
    if os.path.exists(config_path):
        try:
            config = toml.load(config_path)
            if "infrastructure_types" in config:
                return config["infrastructure_types"]
        except Exception:
            pass
    return DEFAULT_INFRASTRUCTURE_TYPES

def get_file_extension(infra_type: str) -> str:
    """Get the appropriate file extension for the infrastructure type"""
    return INFRASTRUCTURE_FILE_EXTENSIONS.get(infra_type, ".txt")

def get_language_for_code(infra_type: str) -> str:
    """Get the appropriate language for syntax highlighting based on infrastructure type"""
    return INFRASTRUCTURE_LANGUAGES.get(infra_type, "text")

def create_prompt_template(infra_type: str, description: str, cloud_provider: str,
                          region: Optional[str] = None, tags: Optional[str] = None,
                          target_versions: Optional[str] = None) -> str: # Added target_versions
    """Create a prompt template for infrastructure generation"""
    # Build cloud environment context
    cloud_context = f"Cloud Environment Context:\n- Provider: {cloud_provider}\n"
    
    if region:
        cloud_context += f"- Region: {region}\n"
    
    if tags:
        tag_lines = "\n".join([f"- {tag.strip()}" for tag in tags.split('\n') if tag.strip()])
        if tag_lines:
            cloud_context += f"- Resource Tags:\n{tag_lines}\n"
    
    # Build the full prompt
    prompt = f"""
{cloud_context}

You are a specialized Infrastructure as Code expert focusing on {infra_type}. Your task is to generate secure and production-ready code following these guidelines:

1. Analyze Requirements:
- Infrastructure Description: {description}
- Consider scalability, high availability, and disaster recovery requirements
- Identify potential security implications and compliance needs

2. Code Generation Guidelines:
- Follow security best practices and compliance standards
- Include comprehensive comments explaining each resource and its purpose
- Document security considerations and potential risks
- Provide parameter descriptions and valid value ranges
- Implement proper resource naming conventions and tagging
- Add error handling and input validation where applicable
- **IMPORTANT: Include standard version constraints for the IaC tool and any providers used (e.g., `required_version` and `required_providers` block in Terraform).**

3. Resource Configuration:
- List all relevant configuration options for each resource
- Highlight required vs optional parameters
- Include recommended values and usage examples
- Document dependencies between resources
"""

    # Define version_instructions *before* using it in the final prompt f-string
    version_instructions = ""
    if target_versions:
        version_instructions = f"\n**Target Version Constraints:**\nPlease ensure the generated code is compatible with and explicitly specifies the following versions if applicable:\n{target_versions}\n"

    # Append final instructions
    prompt += f"\nProvide the infrastructure code with detailed comments and proper formatting.{version_instructions}\nInclude a brief summary of security considerations and available configuration options."

    return prompt
