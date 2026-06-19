"""
Provide the temporary-file cleanup functions used by the vendored converter.
"""

import atexit
import os
import shutil
from contextlib import suppress


def remove_dir(path: str) -> None:
	"""
	Remove a directory without raising cleanup errors.
	"""

	with suppress(Exception):
		shutil.rmtree(path, ignore_errors=True)

def unlink(path: str) -> None:
	"""
	Remove a file without raising cleanup errors.
	"""

	with suppress(Exception):
		if os.path.exists(path):
			os.remove(path)

def remove_folder_atexit(path: str) -> None:
	"""
	Register a directory for removal when the converter exits.
	"""

	atexit.register(remove_dir, os.path.abspath(path))

def remove_file_atexit(path: str) -> None:
	"""
	Register a file for removal when the converter exits.
	"""

	atexit.register(unlink, os.path.abspath(path))

def run_program_now(command_line: list[str]) -> None:
	"""
	Run a cleanup command when the converter exits.
	"""

	import subprocess
	atexit.register(subprocess.run, command_line, check=False)
