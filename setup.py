#!/usr/bin/env python3
"""
The setup script used to package the se library and executables.

To build the project, enter the project's root directory and do:
python3 setup.py bdist_wheel

After the project has been built, you can install it locally:
pip3 install dist/standardebooks-*.whl

To upload the build to pypi, twine is required:
pip3 install twine
"""

from pathlib import Path
from setuptools import setup, find_packages

# Get the long description from the README file
def _get_file_contents(file_path: Path) -> str:
    """
    Helper function to get README contents
    """

    with open(file_path, encoding="utf-8") as file:
        return file.read()

setup(
    version="1.0.26",
    name="standardebooks",
    description="The toolset used to produce Standard Ebooks epub ebooks.",
    long_description=_get_file_contents(Path(__file__).resolve().parent / "README.md"),
    long_description_content_type="text/markdown",
    url="https://standardebooks.org",
    author="Standard Ebooks",
    author_email="admin@standardebooks.org",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5"
    ],
    keywords="ebooks epub",
    packages=find_packages(),
    python_requires=">=3.5", # The latest version installed by default on Ubuntu 16.04 is 3.5.2
    install_requires=[
        "beautifulsoup4==4.8.0",
        "cssselect==1.0.3",
        "ftfy==5.5.1",
        "gitpython==2.1.5",
        "lxml==4.4.0",
        "psutil==5.5.0",
        "pyhyphen==3.0.1",
        # "pyopenssl>=19.0.0",  # Required to allows the `requests` package to use https on Mac OSX, but segfaults when installed on Ubuntu
        "python-magic==0.4.13",
        "regex==2017.7.26",
        "requests>=2.20.0",
        "roman==3.2.0",
        "smartypants==2.0.1",
        "titlecase==0.11.0",
        "termcolor==1.1.0",
        "terminaltables==3.1.0"
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "se = se.executables:main",
        ],
    },
    project_urls={
        "Source": "https://github.com/standardebooks/tools/",
    }
)
