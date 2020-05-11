"""
This module implements the `se interactive-sr` command.
"""

import argparse
import shutil
import subprocess

import se


def interactive_sr() -> int:
	"""
	Entry point for `se interactive-sr`
	"""

	parser = argparse.ArgumentParser(description="Use Vim to perform an interactive search and replace on a list of files. Use y/n/a to confirm (y) or reject (n) a replacement, or to replace (a)ll.")
	parser.add_argument("regex", metavar="REGEX", help="a Vim-flavored regex in the form of `/FIND/REPLACE/`; do not include flags; if using () backreferences, parentheses must be escaped")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="a file on which to perform the search and replace")
	args = parser.parse_args()

	# Check for required utilities
	vim_path = shutil.which("vim")

	if vim_path is None:
		se.print_error("Couldn’t locate [bash]vim[/]. Is it installed?")
		return se.MissingDependencyException.code

	# 'set title' shows the filename in the terminal title
	# 'set eventignore-=Syntax' enables syntax highlighting in all files
	# 'wqa writes and quits all buffers
	# Full command: vim "+silent set title" "+silent bufdo set eventignore-=Syntax | %s${regex}gce | silent update" "+silent qa" "$@"
	subprocess.call([vim_path, "+silent set title", f"+silent bufdo set eventignore-=Syntax | %s{args.regex}gce | silent update", "+silent qa"] + args.targets)

	return 0
