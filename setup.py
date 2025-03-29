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
    ],
    entry_points={
        'console_scripts': [
            'iacgenius=iacgenius.cli:cli',
        ],
    },
)
