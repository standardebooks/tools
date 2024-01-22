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

import re
from pathlib import Path
from setuptools import find_packages, setup


# Get the long description from the README file
def _get_file_contents(file_path: Path) -> str:
	"""
	Helper function to get README contents
	"""

	with open(file_path, encoding="utf-8") as file:
		return file.read()

def _get_version() -> str:
	"""
	Helper function to get VERSION from source code
	"""

	source_path = Path("se/__init__.py")
	contents = _get_file_contents(source_path)
	match = re.search(r'^VERSION = "([^"]+)"$', contents, flags=re.MULTILINE)
	if not match:
		raise RuntimeError(f"VERSION not found in {source_path}")
	return match.group(1)

setup(
	version=_get_version(),
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
		"Programming Language :: Python :: 3"
	],
	keywords="ebooks epub",
	packages=find_packages(),
	include_package_data=True,
	entry_points={
		"console_scripts": [
			"se = se.main:main",
		],
	},
	project_urls={
		"Source": "https://standardebooks.org/tools",
	},

	############################################################
	# WARNING!!!!!!
	#
	# NOBODY MAY EDIT THESE DEPENDENCIES, IN ANY WAY, FOR ANY REASON.
	# THE ONLY PERSON WHO MAY EDIT THESE IS THE EDITOR-IN-CHIEF.
	#
	# Packaging and dependencies in Python are complex and fragile.
	# Well-meaning attempts at upgrading packages or messing with pinned dependencies
	# often end up breaking the entire install.
	# This toolset targets a specific version of Python, and libraries are pinned to specific
	# versions to prevent surprise breakage. Don't edit this!
	############################################################
	python_requires=">=3.8,<=3.12",
	install_requires=[
		"cairosvg==2.7.1",
		"chardet==5.2.0",
		"cssselect==1.2.0",
		"cssutils==2.9.0",
		"ftfy==6.0.3",
		"gitpython==3.1.41",
		"importlib_resources==1.0.2",
		"lxml==4.9.3",
		"natsort==8.4.0",
		"pillow==10.2.0",
		"psutil==5.9.6",
		"pyphen==0.14.0",
		"regex==2023.10.3",
		"requests==2.31.0",
		"rich==13.7.0",
		"roman==4.1",
		"selenium==4.9.0",
		"smartypants==2.0.1",
		"tinycss2==1.2.1",
		"titlecase==2.4",
		"unidecode==1.3.7"
	]
)
