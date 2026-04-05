from setuptools import setup, find_packages

setup(
    name="murmur",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "murmur=murmur.cli:main",
        ],
    },
    python_requires=">=3.9",
)
