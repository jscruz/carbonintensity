"""Setup configuration."""
from setuptools import setup, find_packages

dependencies = ["aiohttp"]
test_dependencies = ["pytest", "pytest-asyncio", "pytest-runner"] + dependencies


with open("README.md", "r") as fh:
    README = fh.read()
setup(
    name="carbonintensity",
    version="0.0.0",
    author="Jorge Cruz Lambert",
    author_email="jscl@pm.me",
    description="Home Assistant Client library for Carbon Intensity API",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/jscruz/carbonintensity",
    packages=find_packages(),
    install_requires=dependencies,
    tests_require=test_dependencies,
    extras_require={"test": test_dependencies},
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
