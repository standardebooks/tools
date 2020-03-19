"""
This module implements the `se version` command.
"""

import os
import sys

import pkg_resources

import se


def version() -> int:
	"""
	Entry point for `se version`
	"""

	# Is distribution an editable install?
	# Copied from a pip utility function which is not publicly accessible. See https://stackoverflow.com/questions/42582801/check-whether-a-python-package-has-been-installed-in-editable-egg-link-mode

	distributions = {v.key: v for v in iter(pkg_resources.working_set)}

	dist_is_editable = False
	for path_item in sys.path:
		egg_link = os.path.join(path_item, distributions['standardebooks'].project_name + '.egg-link')
		if os.path.isfile(egg_link):
			dist_is_editable = True

	print(f"{se.VERSION}{' (developer installation)' if dist_is_editable else ''}")
	return 0
