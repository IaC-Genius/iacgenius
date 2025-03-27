import streamlit as st
import os
import json
import toml
import requests
import base64
import io
import zipfile

# Set page configuration
st.set_page_config(
    page_title="IacGenius Web",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables if they don't exist
if 'show_chat' not in st.session_state:
    st.session_state.show_chat = False

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'generated_code' not in st.session_state:
    st.session_state.generated_code = {}

if 'generation_history' not in st.session_state:
    st.session_state.generation_history = []

# Configuration handler
def load_config():
    """Load configuration from config.toml if it exists"""
    config = {
        "providers": {
            "anthropic": {
                "base_url": "https://api.anthropic.com/v1",
                "models": [
                    "claude-3-5-sonnet-latest",
                    "claude-3-7-sonnet-latest", 
                    "claude-3-5-haiku-latest"
                ]
            },
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]
            },
            "deepseek": {
                "base_url": "https://api.deepseek.com/v1",
                "models": ["deepseek-chat", "deepseek-reasoner"]
            },
            "bedrock": {
                "base_url": "",
                "models": ["anthropic.claude-v2", "amazon.titan-text-express-v1"]
            },
            "ollama": {
                "base_url": "http://localhost:11434",
                "models": ["llama2", "codellama"]
            }
        },
        "infrastructure_types": [
            "Terraform", 
            "CloudFormation", 
            "Kubernetes (Manifests)", 
            "Helm Chart", 
            "Docker", 
            "CI/CD Pipeline", 
            "OPA Policy",
            "Azure Resource Manager (ARM)"
        ],
        "default_provider": "deepseek",
        "default_model": "deepseek-reasoner"
    }
    
    config_path = "config.toml"
    if os.path.exists(config_path):
        try:
            user_config = toml.load(config_path)
            # Merge user config with default config
            for key, value in user_config.items():
                if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                    config[key].update(value)
                else:
                    config[key] = value
        except Exception as e:
            st.error(f"Error loading configuration: {e}")
    
    return config

# LLM Integration
def validate_api_key(provider, api_key):
    """Validate the API key for the given provider."""
    if provider == "openai":
        base_url = "https://api.openai.com/v1/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        validation_url = base_url
    elif provider == "deepseek":
        base_url = "https://api.deepseek.com/v1/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        validation_url = base_url
    elif provider == "anthropic":
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        validation_url = "https://api.anthropic.com/v1/messages"
    elif provider == "openrouter":
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/iacgenius/iacgenius",
            "X-Title": "IacGenius"
        }
        validation_url = "https://openrouter.ai/api/v1/models"
    else:
        return False  # Unsupported provider for validation

    try:
        if provider == "anthropic":
            # Anthropic requires a POST request for validation
            response = requests.post(
                validation_url,
                headers=headers,
                json={"max_tokens": 1, "messages": []}
            )
            # 400 status is expected for empty request
            return response.status_code == 400
        else:
            response = requests.get(validation_url, headers=headers)
            response.raise_for_status()
            return True
    except Exception as e:
        st.error(f"API key validation failed: {e}")
        return False

def call_llm_api(provider, model, prompt, api_key, temperature=0.7, max_tokens=2048, validate_key=False):
    """Call the LLM API with the given parameters"""
    # Try to get API key from environment if not provided
    if provider == "deepseek":
        # Prefer user-provided key, fallback to environment variable
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key and provider == "deepseek":
        env_var = "DEEPSEEK_API_KEY"
        st.error(f"API key is required. Please either enter it manually or set the {env_var} environment variable.")
        return None

    config = load_config()

    if provider in ["openai", "deepseek", "anthropic", "openrouter"]:
        if provider == "anthropic":
            # Get API key from environment if not provided
            api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                st.error("API key is required. Please either enter it manually or set the ANTHROPIC_API_KEY environment variable.")
                return None

            headers = {
                "Authorization": f"Bearer {api_key}",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "system": "You are IacGenius, a specialized Infrastructure as Code expert who begins by analyzing requirements and suggesting best practices. You focus on generating secure, production-ready infrastructure code with comprehensive documentation. For each resource, you provide detailed parameter descriptions, security implications, and configuration options. You explain your recommendations and highlight potential security considerations.",
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            endpoint = "/messages"
        else:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are IacGenius..."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            endpoint = "/chat/completions"
        
        try:
            base_url = config['providers'][provider]['base_url']
            response = requests.post(
                f"{base_url}{endpoint}",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            if provider == "anthropic":
                return response.json()["content"][0]["text"]
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            st.error(f"Error calling {provider.capitalize()} API: {e}. Please ensure your API key has the necessary permissions and the endpoint is correct.")
            return None
    
    elif provider == "bedrock":
        st.warning("Bedrock integration is not yet implemented")
        return None
    
    elif provider == "ollama":
        st.warning("Ollama integration is not yet implemented")
        return None
    
    else:
        st.error(f"Unknown provider: {provider}")
        return None

# Template Generation
def generate_iac(infra_type, description, provider, model, api_key, temperature, max_tokens):
    """Generate infrastructure as code based on the description"""
    # Load configuration and validate if the infrastructure type is supported
    config = load_config()
    supported_types = config["infrastructure_types"]
    if infra_type not in supported_types:
        st.error(f"Sorry, {infra_type} is not currently supported. We only support the following infrastructure tools: {', '.join(supported_types)}")
        return None

    prompt_template = f"""
Cloud Environment Context:
- Provider: {st.session_state.provider}
- Region: {st.session_state.region}
- Resource Tags:\n{'\n'.join([f'- {tag.strip()}' for tag in st.session_state.tags.split('\n') if tag.strip()])}

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

3. Resource Configuration:
- List all relevant configuration options for each resource
- Highlight required vs optional parameters
- Include recommended values and usage examples
- Document dependencies between resources

Provide the infrastructure code with detailed comments and proper formatting.
Include a brief summary of security considerations and available configuration options.
"""
    
    response = call_llm_api(provider, model, prompt_template, api_key, temperature, max_tokens)
    
    if response:
        # Extract code from the response (in case the LLM adds explanations)
        code = response
        
        # Add to generation history
        st.session_state.generation_history.append({
            "infra_type": infra_type,
            "description": description,
            "code": code,
            "provider": provider,
            "model": model
        })
        
        return code
    
    return None

# Helper function for code highlighting
def get_language_for_code(infra_type):
    """Get the appropriate language for syntax highlighting based on infrastructure type"""
    lexer_map = {
        "Terraform": "terraform",
        "CloudFormation": "yaml",
        "Kubernetes (Manifests)": "yaml",
        "Helm Chart": "yaml",
        "Docker": "dockerfile",
        "CI/CD Pipeline": "yaml",
        "OPA Policy": "rego",
        "Azure Resource Manager (ARM)": "json"
    }
    
    return lexer_map.get(infra_type, "text")

# Helper function to create a download link
def get_download_link(code, filename, label="Download Code"):
    """Generate a download link for the code"""
    b64 = base64.b64encode(code.encode()).decode()
    href = f'<a href="data:text/plain;base64,{b64}" download="{filename}" target="_blank">{label}</a>'
    return href

# Helper function to create a zip file with multiple files
def get_zip_download_link(files, zip_filename="iac_files.zip", label="Download All Files"):
    """Generate a download link for multiple files as a zip"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for filename, content in files.items():
            zip_file.writestr(filename, content)
    
    b64 = base64.b64encode(zip_buffer.getvalue()).decode()
    href = f'<a href="data:application/zip;base64,{b64}" download="{zip_filename}" target="_blank">{label}</a>'
    return href

# Main application
def main():
    st.title("🏗️ IacGenius Web")
    st.subheader("AI-powered Infrastructure-as-Code Generator")
    
    config = load_config()
    
    # Sidebar for provider configuration
    with st.sidebar:
        st.header("Provider Configuration")
        
        provider = st.selectbox(
            "LLM Provider",
            options=list(config["providers"].keys()),
            index=list(config["providers"].keys()).index(config["default_provider"]) if config["default_provider"] in config["providers"] else 0,
            key="provider_selectbox"
        )
        
        # Display models for the selected provider
        models = config["providers"][provider]["models"]
        model = st.selectbox("Model", options=models, key="model_selectbox", on_change=lambda: st.session_state.update({"selected_model": model}))
        new_model = st.text_input("Add New Model (if any)", value=st.session_state.selected_model if 'selected_model' in st.session_state else "", placeholder="Enter model name")
        add_model_button = st.button("Add Model")
        
        api_key = st.text_input(f"API Key (Optional if {provider.upper()}_API_KEY environment variable is set)", type="password", key="api_key_input")
        validate_button = st.button("Validate API Key")
        
        st.divider()
        
        st.header("Generation Parameters")
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.0, step=0.1,
                              help="Higher values make output more random, lower values more deterministic")
        max_tokens = st.slider("Max Tokens", min_value=500, max_value=4000, value=2048, step=100,
                             help="Maximum length of generated response")
    
    # Validate API Key and fetch models
    if validate_button:
        if validate_api_key(provider, api_key):
            # Fetch models from the provider's API
            if provider == "openai":
                base_url = "https://api.openai.com/v1/models"
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                try:
                    response = requests.get(base_url, headers=headers)
                    response.raise_for_status()
                    models = [model['id'] for model in response.json()['data']]
                    st.session_state.models = models
                    if 'models' in st.session_state:
                        model = st.selectbox("Model", options=st.session_state.models, key="dynamic_model_selectbox", on_change=lambda: st.session_state.update({"selected_model": model}))
                        st.session_state.selected_model = model
                    st.success("API key validated and models fetched successfully.")
                except Exception as e:
                    st.error(f"Error fetching models: {e}. Please ensure your API key has the necessary permissions and the endpoint is correct.")
            
            elif provider == "deepseek":
                base_url = "https://api.deepseek.com/v1/models"
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                try:
                    response = requests.get(base_url, headers=headers)
                    response.raise_for_status()
                    models = [model['id'] for model in response.json()['data']]
                    st.session_state.models = models
                    if 'models' in st.session_state:
                        model = st.selectbox("Model", options=st.session_state.models, key="dynamic_model_selectbox", on_change=lambda: st.session_state.update({"selected_model": model}))
                        st.session_state.selected_model = model
                    st.success("API key validated and models fetched successfully.")
                except Exception as e:
                    st.error(f"Error fetching models: {e}. Please ensure your API key has the necessary permissions and the endpoint is correct.")
            
            elif provider == "anthropic":
                # Use models from config since Anthropic doesn't have models endpoint
                models = config['providers'][provider]['models']
                st.session_state.models = models
                if 'models' in st.session_state:
                    model = st.selectbox("Model", options=st.session_state.models, key="dynamic_model_selectbox", on_change=lambda: st.session_state.update({"selected_model": model}))
                    st.session_state.selected_model = model
                st.success("API key validated successfully.")
            
            elif provider == "openrouter":
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://github.com/iacgenius/iacgenius",
                    "X-Title": "IacGenius"
                }
                try:
                    response = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
                    response.raise_for_status()
                    models = [model['id'] for model in response.json()['data']]
                    st.session_state.models = models
                    if 'models' in st.session_state:
                        model = st.selectbox("Model", options=st.session_state.models, key="dynamic_model_selectbox", on_change=lambda: st.session_state.update({"selected_model": model}))
                        st.session_state.selected_model = model
                    st.success("API key validated and models fetched successfully.")
                except Exception as e:
                    st.error(f"Error fetching OpenRouter models: {e}")
            
            else:
                st.error("Unsupported provider for model fetching.")
        else:
            st.error("Invalid API key. Please enter a valid key.")

    # Add new model to the provider's model list
    if add_model_button and new_model:
        if new_model not in config["providers"][provider]["models"]:
            config["providers"][provider]["models"].append(new_model)
            st.success(f"Model '{new_model}' added successfully.")
        else:
            st.warning(f"Model '{new_model}' already exists in the list.")
    
    # Main content area with tabs
    tab1, tab2 = st.tabs(["Generate", "Chat"])
    
    # Generate tab
    with tab1:
        st.header("Generate Infrastructure Code")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Cloud configuration presets
            with st.expander("🌩️ Cloud Configuration Presets", expanded=True):
                col_preset1, col_preset2 = st.columns(2)
                with col_preset1:
                    # Cloud provider selection with common presets and custom entry
                    cloud_providers = [
                        "AWS", 
                        "Azure", 
                        "Google Cloud", 
                        "Oracle Cloud",
                        "DigitalOcean",
                        "OpenStack"
                    ]
                    
                    selected_provider = st.selectbox(
                        "Cloud Provider",
                        options=cloud_providers + ["Other..."],
                        index=None,
                        key="provider_select",
                        help="Select from common providers or choose 'Other...' for custom input"
                    )
                    
                    custom_provider = ""
                    if selected_provider == "Other...":
                        custom_provider = st.text_input(
                            "Enter Custom Cloud Provider",
                            key="custom_provider_input",
                            placeholder="e.g. IBM Cloud, Alibaba Cloud, VMware",
                            help="Enter any cloud provider not listed in the presets"
                        )
                        if custom_provider:
                            st.session_state.provider = custom_provider
                        else:
                            st.warning("Please enter a cloud provider name or select from the presets")
                    else:
                        st.session_state.provider = selected_provider
                    st.session_state.region = st.text_input(
                        "Default Region", 
                        value="us-east-1",
                        help="AWS format: us-east-1, Azure format: eastus"
                    )
                with col_preset2:    
                    st.session_state.tags = st.text_area(
                        "Resource Tags (key=value)", 
                        height=68,
                        help="One tag per line in key=value format\nExample:\nenv=prod\nteam=infra",
                        placeholder="env=prod\nowner=team-infra"
                    )

            # Infrastructure type and description
            infra_type = st.selectbox(
                "Infrastructure Type",
                options=config["infrastructure_types"]
            )
            
            description = st.text_area(
                "Describe your infrastructure needs",
                height=200,
                placeholder="Example: Create an AWS infrastructure with a VPC, two public subnets, and an EC2 instance running a web server."
            )
            
            col_gen, col_mod = st.columns([1, 1])
            with col_gen:
                generate_button = st.button("Generate Code")
            with col_mod:
                modify_input = st.text_area("Modification Request", key="mod_input", placeholder="Enter your modification request here...", label_visibility="collapsed")
                modify_button = st.button("Modify Code", disabled=not st.session_state.generated_code)
            
            if modify_button and modify_input and st.session_state.generated_code:
                with st.spinner("Modifying code..."):
                    code_type = st.session_state.generated_code["type"]
                    code = st.session_state.generated_code["code"]
                    language = get_language_for_code(code_type)
                    
                    # Create a prompt for code modification
                    modification_prompt = f"""
                    Current infrastructure type: {code_type}
                    Existing code:
                    `{language}
                    {code}
                    `
                    Modification request: {modify_input}
                    
                    Please provide the complete modified code following these guidelines:
                    1. Maintain the same code structure and style
                    2. Include all necessary security measures
                    3. Provide the full code, not just the changes
                    4. Use proper formatting and comments
                    """
                    
                    # Generate modified code
                    modified_code = call_llm_api(
                        provider,
                        model,
                        modification_prompt,
                        api_key,
                        temperature,
                        max_tokens
                    )
                    
                    if modified_code:
                        # Extract code from response if it's wrapped in markdown code blocks
                        if "`" in modified_code:
                            code_start = modified_code.find("`") + 3
                            code_end = modified_code.rfind("`")
                            if code_start < code_end:
                                code_lines = modified_code[code_start:code_end].split('\n')
                                if len(code_lines) > 0 and not code_lines[0].strip().isalnum():
                                    code_lines = code_lines[1:]
                                modified_code = '\n'.join(code_lines)
                        
                        # Update the generated code
                        st.session_state.generated_code["code"] = modified_code
                        
                        # Add to generation history
                        st.session_state.generation_history.append({
                            "infra_type": code_type,
                            "description": f"Modified: {modify_input}",
                            "code": modified_code,
                            "provider": provider,
                            "model": model
                        })
                        
                        st.success("Code modified successfully!")
                    else:
                        st.error("Failed to modify code. Please check your API key and try again.")
            
            elif generate_button and description:
                with st.spinner("Generating code..."):
                    generated_code = generate_iac(
                        infra_type,
                        description,
                        provider,
                        model,
                        api_key,
                        temperature,
                        max_tokens
                    )
                    
                    if generated_code:
                        st.session_state.generated_code = {
                            "type": infra_type,
                            "code": generated_code
                        }
                        st.success("Code generated successfully!")
                    else:
                        st.error("Failed to generate code. Please check your API key and try again.")
        
        with col2:
            st.subheader("Generation History")
            
            if st.session_state.generation_history:
                for i, item in enumerate(reversed(st.session_state.generation_history[-5:])):
                    with st.expander(f"{item['infra_type']} - {item['description'][:30]}..."):
                        st.text(f"Provider: {item['provider']} - {item['model']}")
                        # Get appropriate language for syntax highlighting
                        code_type = item['infra_type']
                        lexer_map = {
                            "Terraform": "terraform",
                            "CloudFormation": "yaml",
    "Kubernetes (Manifests)": "yaml",
    "Helm Chart": "yaml",
                            "Docker": "dockerfile",
                            "CI/CD Pipeline": "yaml",
                            "OPA Policy": "rego"
                        }
                        language = lexer_map.get(code_type, "text")
                        
                        # Display code with proper syntax highlighting
                        # Show a preview in the history section
                        preview_code = item['code'][:200] + "..." if len(item['code']) > 200 else item['code']
                        st.code(preview_code, language=language, line_numbers=True)
                        if st.button(f"Load This Code", key=f"load_{i}"):
                            st.session_state.generated_code = {
                                "type": item['infra_type'],
                                "code": item['code']
                            }
            else:
                st.info("No generation history yet. Generate some code to see it here.")
        
        # Display generated code
        if st.session_state.generated_code:
            st.divider()
            st.subheader("Generated Code")
            
            code_type = st.session_state.generated_code["type"]
            code = st.session_state.generated_code["code"]
            
            # Get appropriate language for syntax highlighting
            language = get_language_for_code(code_type)
            
            # Use Streamlit's native code display with proper syntax highlighting
            st.code(code, language=language, line_numbers=True)
            
            # Add a text input for the file name
            file_name_input = st.text_input("Enter file name", value="code.txt")

            # Determine the final file name
            if not file_name_input:
                final_file_name = "code.txt"
            elif "." not in file_name_input:
                final_file_name = f"{file_name_input}.txt"
            else:
                final_file_name = file_name_input

            # Add a download button for the generated code
            if st.download_button(
                label="Download",
                data=code,
                file_name=final_file_name,
                mime="text/plain"
            ):
                st.success("File ready to be saved!")

            st.markdown("""
<style>
/* Target the actual code element inside st.code's block */
div[data-testid="stCodeBlock"] pre,
div[data-testid="stCodeBlock"] code {
    white-space: pre-wrap !important;
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
    overflow-x: hidden !important;
}
</style>
            """, unsafe_allow_html=True)
            
            # Code actions
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Copy to clipboard button
                st.button("Copy to Clipboard", on_click=lambda: st.write("<script>navigator.clipboard.writeText(" + code.replace("", "\\") + ");</script>", unsafe_allow_html=True))
            
            with col2:
                # Download single file
                file_extension_map = {
                    "Terraform": "tf",
                    "CloudFormation": "yaml",
                    "Kubernetes": "yaml",
                    "Docker": "Dockerfile",
                    "CI/CD Pipeline": "yaml",
                    "OPA Policy": "rego"
                }
                
                file_extension = file_extension_map.get(code_type, "txt")
                filename = f"iac_code.{file_extension}"
                
                st.markdown(get_download_link(code, filename), unsafe_allow_html=True)
            
            with col3:
                # Placeholder for layout balance
                st.empty()
            
            with col4:
                # For future: Download as zip with multiple files
                if code_type == "Terraform":
                    # Example of splitting into multiple files for Terraform
                    files = {
                        "main.tf": code,
                        "variables.tf": "# Variables will be defined here",
                        "outputs.tf": "# Outputs will be defined here"
                    }
                    st.markdown(get_zip_download_link(files, "terraform_files.zip", "Download as Terraform Project"), unsafe_allow_html=True)
    
    # Chat tab
    with tab2:
        st.header("Chat with IacGenius")
        
        # Display chat history (most recent messages first)
        # Create a container for chat history
        chat_container = st.container()
        
        # Display the current code if available
        if st.session_state.generated_code:
            with chat_container.chat_message("assistant"):
                code_type = st.session_state.generated_code["type"]
                code = st.session_state.generated_code["code"]
                language = get_language_for_code(code_type)
                st.code(code, language=language, line_numbers=True)
        
        # Display chat history in reverse chronological order
        for message in reversed(st.session_state.chat_history):
            with chat_container.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Add action buttons for code modifications
        if st.session_state.chat_history and any(msg["role"] == "system" and "Existing code:" in msg["content"] for msg in st.session_state.chat_history):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Apply Changes", key="apply_changes"):
                    latest_response = next((msg["content"] for msg in reversed(st.session_state.chat_history) 
                                          if msg["role"] == "assistant" and "`" in msg["content"]), None)
                    if latest_response:
                        code_start = latest_response.find("`") + 3
                        code_end = latest_response.rfind("`")
                        if code_start < code_end:
                            code_lines = latest_response[code_start:code_end].split('\n')
                            if len(code_lines) > 0 and not code_lines[0].strip().isalnum():
                                code_lines = code_lines[1:]
                            new_code = '\n'.join(code_lines)
                            
                            if new_code.strip():
                                st.session_state.generated_code["code"] = new_code
                                st.success("Changes applied successfully!")
                                st.session_state.chat_history = []
                                st.session_state.show_chat = False
                                st.rerun()
                        
                        with col2:
                            if st.button("Discard Changes", key="discard_changes"):
                                st.session_state.chat_history = []
                                st.session_state.show_chat = False
                                st.rerun()
        
        # Chat input
        user_input = st.chat_input("Ask a follow-up question or request modifications...")
        
        if user_input:
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # Generate response
            with st.spinner("Thinking..."):
                # Construct prompt with chat history context
                chat_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.chat_history])
                
                # Create a prompt for the follow-up question
                chat_prompt = f"""
                You are IacGenius, an expert in infrastructure as code. 
                
                Previous conversation:
                {chat_context}
                
                Please respond to the latest question or request. If it's about modifying code:
                1. Always provide the complete modified code
                2. Use markdown code blocks with appropriate language tags
                3. Explain the changes you made
                4. Highlight any security implications
                """
                
                # Call the LLM API
                response = call_llm_api(
                    provider,
                    model,
                    chat_prompt,
                    api_key,
                    temperature,
                    max_tokens
                )
                
                if response:
                    # Add assistant response to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    
                    # Display assistant response
                    with st.chat_message("assistant"):
                        st.markdown(response)
                else:
                    st.error("Failed to generate a response. Please check your API key and try again.")

# Run the main application
if __name__ == "__main__":
    main()
