---
invisible:
- toc        # Hide table of contents
---
# Installation

## Requirements
Passthrough works with Python 3.6 or newer, and depends on the lxml and NumPy packages.

## Setting up a virtual environment
If you want to follow along with the tutorial, we recommend creating a virtual 
environment for your project. We will be using `venv`, but you are of course free to use
[Poetry](https://python-poetry.org/) or similar if you want.

Navigate to a fresh directory and execute:
```commandline
python3 -m venv env 
source env/bin/activate
```

It is generally a good idea to ensure that `pip` is up to date:
```commandline
pip install --upgrade pip
```

## Installing Passthrough
The Passthrough library lives on [PyPI](https://pypi.org/) and can be installed with 
`pip`:
```commandline
pip install passthrough
```
This will install the required dependencies and allow you to 
```#!python from passthrough import Template```.

