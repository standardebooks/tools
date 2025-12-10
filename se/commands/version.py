"""
This module implements the `se version` command.
"""

import se

def version() -> int:
	"""
	Entry point for `se version`.
	"""

	# Is distribution an editable install?
	# Copied from a pip utility function which is not publicly accessible. See <https://stackoverflow.com/questions/42582801/check-whether-a-python-package-has-been-installed-in-editable-egg-link-mode>.

	print(f"{se.VERSION}")
	return 0
