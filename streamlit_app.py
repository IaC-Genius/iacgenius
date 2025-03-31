import streamlit as st
import os # Still needed for os.getenv
import json
# import toml # No longer needed directly here
# import requests # No longer needed
import base64
import io
import zipfile
# import tempfile # No longer needed
# import subprocess # No longer needed
# Ensure json is imported (it was already, but good practice) - Removed redundant import

# --- Removed direct checkov imports ---
# from checkov.common.runners.runner_registry import RunnerRegistry
# from checkov.runner_filter import RunnerFilter
# from checkov.common.output.report import Report

# Import from core package
from iacgenius.config_handler import ConfigError # read_config no longer needed here
# Import explain_iac_finding as well
from iacgenius.generator import generate_infrastructure # Removed unused explain_iac_finding
# Import the infrastructure module to access its functions
from iacgenius import infrastructure
# from iacgenius.infrastructure import get_infrastructure_types, get_language_for_code # Now accessed via infrastructure module
from iacgenius.llm_integration import get_available_providers, get_available_models, validate_api_key # Use central functions

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
    st.session_state.generated_code = {} # Store dict like {"type": "Terraform", "code": "..."}

if 'generation_history' not in st.session_state:
    st.session_state.generation_history = [] # Store list of dicts like generated_code + description, provider, model
if 'available_models' not in st.session_state:
    st.session_state.available_models = [] # Initialize dynamically fetched models
if 'env_api_key' not in st.session_state:
    st.session_state.env_api_key = None # Store API key found in environment
if 'api_key_validated' not in st.session_state:
    st.session_state.api_key_validated = False # Track if key/creds are validated
if 'api_key_info' not in st.session_state: # Initialize here as well
    st.session_state.api_key_info = ""

# --- Removed Duplicated Functions ---
# load_config() - Handled by backend or read_config if needed for UI defaults
# validate_api_key() - Imported from llm_integration
# call_llm_api() - Replaced by generate_infrastructure
# generate_iac() - Replaced by generate_infrastructure
# get_language_for_code() - Imported from infrastructure module
# ------------------------------------

# Helper function to create a download link (Keep)
def get_download_link(code, filename, label="Download Code"):
    """Generate a download link for the code"""
    b64 = base64.b64encode(code.encode()).decode()
    href = f'<a href="data:text/plain;base64,{b64}" download="{filename}" target="_blank">{label}</a>'
    return href

# Helper function to create a zip file with multiple files (Keep)
def get_zip_download_link(files, zip_filename="iac_files.zip", label="Download All Files"):
    """Generate a download link for multiple files as a zip"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for filename, content in files.items():
            zip_file.writestr(filename, content)

    b64 = base64.b64encode(zip_buffer.getvalue()).decode()
    href = f'<a href="data:application/zip;base64,{b64}" download="{zip_filename}" target="_blank">{label}</a>'
    return href

# --- New Helper Function ---
# Map provider names to expected environment variables
PROVIDER_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "bedrock": "AWS_REGION", # Bedrock uses AWS credentials chain, check region as proxy
    "ollama": None # Ollama doesn't use env vars for keys
}

def check_env_api_key():
    """Checks for API key in environment based on selected provider."""
    provider = st.session_state.provider_selectbox # Get current provider
    env_var = PROVIDER_ENV_VARS.get(provider)
    api_key_input_widget = st.session_state.get("api_key_input", "") # Get current input value

    if env_var:
        env_key = os.getenv(env_var)
        if env_key:
            st.session_state.env_api_key = env_key # Store the actual key
            # Don't overwrite manual input if user started typing
            if not api_key_input_widget:
                 st.session_state.api_key_info = f"API Key/Credentials found in environment variable ({env_var})."
                 # Set input to placeholder only if empty
                 # Streamlit doesn't easily allow changing input value directly after render,
                 # so we rely on the info message and internal state `env_api_key`.
                 # Consider adding a visual cue or placeholder text if possible in future Streamlit versions.
            else:
                 # User typed something, keep their input but still store env key internally
                 st.session_state.api_key_info = f"Manual input detected. Using it instead of environment variable ({env_var})."

            # Reset validation status on provider change if env key found
            st.session_state.api_key_validated = False
            st.session_state.available_models = []
            return # Found env key

    # If no env var for provider OR env var not set
    st.session_state.env_api_key = None
    if provider not in ["bedrock", "ollama"]: # These don't strictly need a key in the input field
         st.session_state.api_key_info = "Please enter your API key or set the corresponding environment variable."
    else:
         st.session_state.api_key_info = f"{provider.capitalize()} uses credentials/local setup. Validation checks connectivity."
    # Reset validation status and models on provider change (Corrected Indentation)
    st.session_state.api_key_validated = False
    st.session_state.available_models = []


# --- End New Helper Function ---

# Main application
def main():
    # Example usage of zip download link if needed later:
    # zip_href = get_zip_download_link({"file1.txt": "content1", "file2.py": "print('hello')"})
    # st.markdown(zip_href, unsafe_allow_html=True)

    st.title("🏗️ IacGenius Web")
    st.subheader("AI-powered Infrastructure-as-Code Generator")

    # Get available providers from the backend
    available_providers = get_available_providers()
    # Determine default provider
    default_provider = available_providers[0] if available_providers else None

    # Sidebar for provider configuration
    with st.sidebar:
        st.header("Provider Configuration")

        # Provider selection triggers environment check
        selected_provider = st.selectbox(
            "LLM Provider",
            options=available_providers,
            index=available_providers.index(default_provider) if default_provider in available_providers else 0,
            key="provider_selectbox",
            on_change=check_env_api_key # Call helper on change
        )

        # Trigger initial check if state is empty (first run)
        if not st.session_state.api_key_info:
             check_env_api_key()

        # API Key input - Allow manual override
        # Display info message based on env check
        st.info(st.session_state.api_key_info)
        api_key_input = st.text_input(
             "API Key (Overrides ENV VAR if entered)",
             type="password",
             key="api_key_input",
             # placeholder="Detected in ENV" if st.session_state.env_api_key else "Enter API Key" # Placeholder tricky
        )

        # Determine the key to use for validation/generation
        # Priority: Manual Input > Environment Variable > None
        key_to_use = api_key_input if api_key_input else st.session_state.env_api_key

        # --- Updated Validation and Model Fetching ---
        if st.button("Validate & Fetch Models"):
            st.session_state.available_models = [] # Clear previous models
            st.session_state.api_key_validated = False # Reset validation status

            # For Bedrock/Ollama, validation checks connectivity/setup, not a specific key input
            if selected_provider in ["ollama", "bedrock"]:
                st.info(f"Validating {selected_provider} connectivity/credentials...")
                try:
                    is_valid = validate_api_key(selected_provider, None) # Pass None, validation uses internal checks
                    if is_valid:
                        st.success(f"{selected_provider.capitalize()} connection/credentials appear valid.")
                        # Fetch models immediately after successful validation
                        with st.spinner("Fetching available models..."):
                             models = get_available_models(selected_provider, None) # Pass None for key
                             # st.write(f"Debug: get_available_models returned: {models}") # Removed DEBUGGING
                             if models:
                                  st.session_state.available_models = models
                                  st.session_state.api_key_validated = True # Set validated flag ONLY if models are fetched
                                  st.success(f"Fetched {len(models)} models for {selected_provider}.")
                             else:
                                  # More specific warning if fetching returned empty list after validation
                                  st.error(f"Validation succeeded, but failed to fetch models for {selected_provider}. Check terminal logs for details.")
                                  st.session_state.available_models = [] # Ensure it's empty
                                  # Optionally fallback to static list here if desired
                    else:
                        # Should be caught by exception below, but handle just in case
                        st.error(f"{selected_provider.capitalize()} validation failed.")
                except ConfigError as e:
                    st.error(f"Validation Error: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred during validation: {e}")

            # For providers requiring a key
            elif not key_to_use:
                st.warning(f"Please enter an API key or set the {PROVIDER_ENV_VARS.get(selected_provider, 'appropriate')} environment variable.")
            else:
                st.info(f"Validating API Key for {selected_provider}...")
                try:
                    is_valid = validate_api_key(selected_provider, key_to_use)
                    if is_valid:
                        st.success(f"API Key for {selected_provider} appears valid.")
                        # Fetch models immediately after successful validation
                        with st.spinner("Fetching available models..."):
                             models = get_available_models(selected_provider, key_to_use)
                             # st.write(f"Debug: get_available_models returned: {models}") # Removed DEBUGGING
                             if models:
                                  st.session_state.available_models = models
                                  st.session_state.api_key_validated = True # Set validated flag ONLY if models are fetched
                                  st.success(f"Fetched {len(models)} models for {selected_provider}.")
                             else:
                                  # More specific warning if fetching returned empty list after validation
                                  st.error(f"Validation succeeded, but failed to fetch models for {selected_provider}. Check terminal logs for details.")
                                  st.session_state.available_models = [] # Ensure it's empty
                                  # Optionally fallback to static list here if desired
                    else:
                        # Should be caught by exception below
                        st.error(f"API Key validation failed for {selected_provider}.")
                except ConfigError as e:
                    st.error(f"Validation Error: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred during validation: {e}")
            st.rerun() # Re-add rerun to update the UI after state changes

        # Model selection - Use dynamically fetched list from session state
        # Disable if key not validated or no models fetched
        model_options = st.session_state.available_models
        model_select_disabled = not st.session_state.api_key_validated or not model_options

        selected_model = st.selectbox(
            "Model",
            options=model_options,
            index=0 if model_options else 0, # Default to first if available
            key="model_selectbox",
            disabled=model_select_disabled,
            help="Validate API Key / Credentials first to fetch and enable models." if model_select_disabled else "Select the model to use."
        )

        st.divider()

        st.header("Generation Parameters")
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.1, # Defaulted to 0.2 like backend
                              help="Higher values make output more random, lower values more deterministic")
        max_tokens = st.slider("Max Tokens", min_value=500, max_value=4096, value=2048, step=128, # Increased max slightly
                             help="Maximum length of generated response")
        target_versions_input = st.text_input(
            "Target IaC Version(s) (Optional)",
            placeholder="e.g., Terraform AWS Provider ~> 5.0",
            help="Specify desired versions for IaC tools or providers."
        )

    # Main content area with tabs
    tab_generate, tab_load, tab_chat = st.tabs(["Generate New Code", "Load Existing Code", "Chat"])

    # --- Load Existing Code Tab ---
    with tab_load:
        st.header("Load Your Existing Infrastructure Code")
        st.info("Paste your existing IaC code below, select its type, and click 'Load Code' to start modifying or analyzing it.")

        # Use backend function to get types
        available_infra_types_load = infrastructure.get_infrastructure_types()
        selected_infra_type_load = st.selectbox(
            "Select Infrastructure Type",
            options=available_infra_types_load,
            key="load_infra_type"
        )

        existing_code_input = st.text_area(
            "Paste your code here",
            height=400,
            key="load_code_area"
        )

        if st.button("Load Code & Validate", key="load_code_button"):
            if not existing_code_input:
                st.warning("Please paste your code into the text area.")
            elif not selected_infra_type_load:
                 st.warning("Please select the type of infrastructure code.")
            else:
                # Basic validation passed (not empty)
                st.session_state.generated_code = {
                    "type": selected_infra_type_load,
                    "code": existing_code_input,
                    "params": { # Add placeholder params for consistency
                        "description": "Loaded existing code",
                        "iac_type": selected_infra_type_load,
                        "cloud_provider": "Unknown", # Cannot know from pasted code
                        "llm_provider": selected_provider, # Use current sidebar selection
                        "model": selected_model,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "region": None,
                        "tags": None
                    }
                }
                # Add to history
                st.session_state.generation_history.append({
                    "infra_type": selected_infra_type_load,
                    "description": "Loaded existing code",
                    "code": existing_code_input,
                    "provider": "User", # Indicate it came from user input
                    "model": "N/A"
                })
                st.success(f"{selected_infra_type_load} code loaded successfully! You can now view and modify it in the 'Generate New Code' tab.")
                # Consider switching tabs automatically? Streamlit doesn't directly support this easily.
                # User needs to manually switch back to the Generate tab.

    # --- Generate New Code Tab (Previously tab1) ---
    with tab_generate:
        st.header("Generate Infrastructure Code")

        col1, col2 = st.columns([2, 1])

        with col1:
            # Cloud configuration presets (Keep UI, but data is passed to backend)
            with st.expander("🌩️ Cloud Configuration Presets", expanded=True):
                col_preset1, col_preset2 = st.columns(2)
                with col_preset1:
                    cloud_providers_presets = ["AWS", "Azure", "Google Cloud", "Oracle Cloud", "DigitalOcean", "OpenStack", "Generic"]
                    selected_cloud_provider_ui = st.selectbox(
                        "Cloud Provider", options=cloud_providers_presets + ["Other..."], index=0, key="cloud_provider_select"
                    )
                    custom_cloud_provider = ""
                    if selected_cloud_provider_ui == "Other...":
                        custom_cloud_provider = st.text_input("Enter Custom Cloud Provider", key="custom_cloud_provider_input")
                    # Determine final cloud provider to pass to backend
                    final_cloud_provider = custom_cloud_provider if selected_cloud_provider_ui == "Other..." and custom_cloud_provider else selected_cloud_provider_ui

                    region = st.text_input("Default Region", value="us-east-1", help="e.g., us-east-1, eastus")
                with col_preset2:
                    tags = st.text_area("Resource Tags (key=value)", height=68, help="One tag per line", placeholder="env=prod\nowner=team-infra")

            # Infrastructure type and description
            # Use backend function to get types
            available_infra_types = infrastructure.get_infrastructure_types() # Use module access
            infra_type = st.selectbox("Infrastructure Type", options=available_infra_types)

            description = st.text_area("Describe your infrastructure needs", height=200, placeholder="Example: Create an AWS VPC with two public subnets...")

            col_gen, col_mod = st.columns([1, 1])
            with col_gen:
                # Disable button if model selection is disabled (i.e., key not validated or no models)
                generate_button = st.button("Generate Code", disabled=model_select_disabled)
            with col_mod:
                # Modification logic needs rework to use generate_infrastructure
                modify_input = st.text_area("Modification Request", key="mod_input", placeholder="Enter modification request...", label_visibility="collapsed")
                # Disable button if model selection is disabled OR no code generated yet
                modify_button = st.button("Modify Code", disabled=model_select_disabled or not st.session_state.generated_code)

            # --- Refactored Generation Logic ---
            if generate_button and description:
                # Check for model selection *before* trying to generate (Corrected logic placement)
                if not selected_model or model_select_disabled:
                     st.warning("Please validate credentials/API key and select a model first.")
                else:
                    with st.spinner("Generating code..."):
                        try:
                            # Call the central generator function
                            result_json_str = generate_infrastructure(
                                description=description,
                                iac_type=infra_type,
                                cloud_provider=final_cloud_provider,
                                llm_provider=selected_provider, # From sidebar
                                model=selected_model,           # From sidebar (now dynamic)
                                api_key=key_to_use,             # Use determined key (input or env)
                                temperature=temperature,        # From sidebar
                                max_tokens=max_tokens,          # From sidebar
                                region=region if region else None, # From main area
                                tags=tags if tags else None,        # From main area
                                target_versions=target_versions_input if target_versions_input else None # Pass target versions
                            )
                            result_data = json.loads(result_json_str)
                            generated_code_text = result_data.get("code", "")

                            if generated_code_text:
                                st.session_state.generated_code = {
                                    "type": infra_type,
                                    "code": generated_code_text,
                                    # Store params used for potential modification later
                                    "params": {
                                        "description": description, # Original description
                                        "iac_type": infra_type,
                                        "cloud_provider": final_cloud_provider,
                                        "llm_provider": selected_provider,
                                        "model": selected_model,
                                        "temperature": temperature,
                                        "max_tokens": max_tokens,
                                        "region": region,
                                        "tags": tags
                                    }
                                }
                                st.success("Code generated successfully!")
                                # Add to history
                                st.session_state.generation_history.append({
                                    "infra_type": infra_type,
                                    "description": description,
                                    "code": generated_code_text,
                                    "provider": selected_provider,
                                    "model": selected_model
                                })
                            else:
                                st.error("Generation succeeded but no code was returned.")

                        except ConfigError as e:
                             st.error(f"Configuration Error: {e}")
                        except Exception as e:
                             st.error(f"Generation failed: {e}")

            # --- Refactored Modification Logic ---
            if modify_button and modify_input and st.session_state.generated_code:
                 # Check for model selection *before* trying to modify (Corrected logic placement)
                 if not selected_model or model_select_disabled:
                      st.warning("Please validate credentials/API key and select a model first.")
                 else:
                    with st.spinner("Modifying code..."):
                        try:
                            original_code = st.session_state.generated_code["code"]
                            original_params = st.session_state.generated_code.get("params", {}) # Get params used previously

                            # Construct a new description/prompt including the modification request
                            modification_prompt = f"""
Original Request: {original_params.get('description', 'N/A')}
Previously Generated Code ({original_params.get('iac_type', 'N/A')} for {original_params.get('cloud_provider', 'N/A')}):
```
{original_code}
```
Modification Request: {modify_input}

Please provide the complete, updated code incorporating the modification request, following the original format and best practices.
"""
                            # Call generator again with the new prompt and original parameters
                            result_json_str = generate_infrastructure(
                                description=modification_prompt, # Use the combined prompt
                                iac_type=original_params.get('iac_type', infra_type), # Use original type
                                cloud_provider=original_params.get('cloud_provider', final_cloud_provider),
                                llm_provider=original_params.get('llm_provider', selected_provider),
                                model=original_params.get('model', selected_model), # Use original model used
                                api_key=key_to_use, # Use current determined key (input or env)
                                temperature=original_params.get('temperature', temperature),
                                max_tokens=original_params.get('max_tokens', max_tokens),
                                region=original_params.get('region', region if region else None),
                                tags=original_params.get('tags', tags if tags else None),
                                target_versions=target_versions_input if target_versions_input else None # Pass target versions
                            )
                            result_data = json.loads(result_json_str)
                            modified_code_text = result_data.get("code", "")

                            if modified_code_text:
                                # Update the main code display
                                st.session_state.generated_code["code"] = modified_code_text
                                # Update the params description to reflect modification
                                st.session_state.generated_code["params"]["description"] = f"Original: {original_params.get('description', 'N/A')} | Modified: {modify_input}"
                                st.success("Code modified successfully!")
                                # Add modification to history
                                st.session_state.generation_history.append({
                                    "infra_type": original_params.get('iac_type', infra_type),
                                    "description": f"Modified: {modify_input}",
                                    "code": modified_code_text,
                                    "provider": original_params.get('llm_provider', selected_provider),
                                    "model": original_params.get('model', selected_model)
                                })
                            else:
                                st.error("Modification succeeded but no code was returned.")

                        except ConfigError as e:
                             st.error(f"Configuration Error during modification: {e}")
                        except Exception as e:
                             st.error(f"Modification failed: {e}")


        with col2:
            st.subheader("Generation History")
            # History display logic remains largely the same
            if st.session_state.generation_history:
                for i, item in enumerate(reversed(st.session_state.generation_history[-5:])): # Show last 5
                    with st.expander(f"{item['infra_type']} - {item['description'][:30]}..."):
                        st.text(f"Provider: {item.get('provider','N/A')} - {item.get('model','N/A')}")
                        # Use the imported infrastructure module to call get_language_for_code
                        language = infrastructure.get_language_for_code(item['infra_type']) # Use imported function via module
                        preview_code = item['code'][:200] + "..." if len(item['code']) > 200 else item['code']
                        st.code(preview_code, language=language) # Removed line numbers for preview
                        if st.button(f"Load This Code", key=f"load_{i}"):
                            # Find the full history item to load params too if available
                            full_history_item = next((h for h in st.session_state.generation_history if h['code'] == item['code'] and h['description'] == item['description']), None)
                            st.session_state.generated_code = {
                                "type": item['infra_type'],
                                "code": item['code'],
                                "params": full_history_item.get("params") if full_history_item else None # Load params if found
                            }
                            st.rerun() # Rerun to update main display
            else:
                st.info("No generation history yet.")

        # Display generated code (logic mostly unchanged, uses imported get_language_for_code)
        if st.session_state.generated_code:
            st.divider()
            st.subheader("Generated Code")

            code_type = st.session_state.generated_code["type"]
            code = st.session_state.generated_code["code"]
            # Use the imported infrastructure module to call get_language_for_code
            language = infrastructure.get_language_for_code(code_type) # Use imported function via module

            st.code(code, language=language, line_numbers=True)

            # File naming and download logic (moved get_file_extension call here)
            # Use the imported infrastructure module to call get_file_extension
            default_ext = infrastructure.get_file_extension(code_type) # Use backend function via module
            default_filename = f"iacgenius_{code_type.lower().replace(' ', '_').replace('(', '').replace(')', '')}.{default_ext}"

            file_name_input = st.text_input("Enter file name for download", value=default_filename)
            final_file_name = file_name_input if file_name_input else default_filename

            st.download_button(label="Download Code", data=code, file_name=final_file_name, mime="text/plain")

            # --- Removed Validation/Scanning Section ---

    # --- Chat Tab (Previously tab2) ---
    with tab_chat:
        st.header("Chat with IacGenius")
        st.warning("Chat functionality needs refactoring to use the updated backend.") # Placeholder

        # --- Refactoring Needed for Chat ---
        # 1. Display history (mostly ok)
        # 2. Get response: Construct prompt including history AND current code context
        # 3. Call generate_infrastructure with the chat prompt
        # 4. Display response
        # 5. Handle applying/discarding code changes suggested in chat
        # --- End Refactoring Needed ---

        # Placeholder display
        for message in reversed(st.session_state.chat_history):
             with st.chat_message(message["role"]):
                  st.markdown(message["content"])

        if st.chat_input("Ask a follow-up question or request modifications..."):
             st.info("Chat response generation is temporarily disabled during refactoring.")


# Run the main application
if __name__ == "__main__":
    main()
