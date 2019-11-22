"""
Common helper functions for tests.
"""

import subprocess
import shlex
import pytest

def run(cmd: str) -> subprocess.CompletedProcess:
	"""Run the provided shell string as a command in a subprocess. Returns a
	status object when the command completes.
	"""
	args = shlex.split(cmd)
	return subprocess.run(args, stderr=subprocess.PIPE, check=False)

def must_run(cmd: str) -> None:
	"""Run the provided shell string as a command in a subprocess. Forces a
	test failure if the command fails.
	"""
	result = run(cmd)
	if result.returncode == 0:
		if not result.stderr:
			return
		pytest.fail("stderr was not empty after command '{}'\n{}".format(cmd, result.stderr.decode()))
	else:
		fail_msg = "error code {} from command '{}'".format(result.returncode, cmd)
		if result.stderr:
			fail_msg += "\n" + result.stderr.decode()
		pytest.fail(fail_msg)
