from setuptools import setup, find_packages

setup(
    name="iacgenius",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'click>=8.1.0',
        'streamlit>=1.28.0',
        'python-dotenv>=1.0.0',
        'toml>=0.10.2',
        'keyring>=25.6.0', # Added keyring dependency
        'cryptography>=42.0.5', # Added cryptography dependency
        # Dependencies for Streamlit app and core functionality
        # 'streamlit>=1.28.0', # Removed duplicate, using specific version below
        # 'requests>=2.31.0', # Removed duplicate, using specific version below
        'streamlit>=1.37.0', # Patched version for CVE
        'requests==2.31.0', # Specific version for requests
        'pygments>=2.15.1', # Patched version for ReDoS
        'openai>=1.12.0',
        'anthropic>=0.18.1',
        'typing-extensions>=4.9.0',
        'pydantic>=2.6.1',
        'boto3', # Added for AWS Bedrock support
        # Removed checkov as it's run via subprocess from a separate env now
        'yamllint>=1.33.0', # For YAML linting
        'python-hcl2>=4.3.0', # For HCL (Terraform) parsing
    ],
    entry_points={
        'console_scripts': [
            'iacgenius=iacgenius.cli:cli',
        ],
    },
)
