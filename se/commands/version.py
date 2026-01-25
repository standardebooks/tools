"""
This module implements the `se version` command.
"""
from importlib.metadata import Distribution
import json

import se

def version() -> int:
	"""
	Entry point for `se version`.
	"""

	# This API is discussed in https://github.com/pypa/setuptools/issues/4186. At some point (python 3.12 or 13?), an origin method was added to Distribution, which allows this to be done without needing json, e.g.
	# 	pkg_is_editable = Distribution.from_name("standardebooks").origin.dir_info.editable
	direct_url = Distribution.from_name("standardebooks").read_text("direct_url.json")
	if direct_url is None:
		pkg_is_editable = False
	else:
		pkg_is_editable = json.loads(direct_url).get("dir_info", {}).get("editable", False)

	se_version = f"{se.VERSION}"
	if pkg_is_editable:
		se_version += ", editable"

	print(se_version)
	return 0
