from setuptools import setup, find_packages

setup(
    name="iacgenius",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'click==8.1.7',
        'streamlit>=1.24.0',
        'python-dotenv>=1.0.0',
        'toml>=0.10.2',
        'requests==2.31.0',
        'pygments>=2.15.0',
        'cryptography==42.0.5',
        'keyring==25.6.0',
        'openai>=1.12.0',
        'anthropic>=0.18.1',
        'typing-extensions>=4.9.0',
        'pydantic>=2.6.1',
    ],
    entry_points={
        'console_scripts': [
            'iacgenius=iacgenius.cli:cli',
        ],
    },
)
