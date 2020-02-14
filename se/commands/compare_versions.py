"""
This module implements the `se compare-versions` command.
"""

import argparse
import fnmatch
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import git
import psutil

import se


def compare_versions() -> int:
	"""
	Entry point for `se compare-versions`
	"""

	parser = argparse.ArgumentParser(description="Use Firefox to render and compare XHTML files in an ebook repository. Run on a dirty repository to visually compare the repository’s dirty state with its clean state. If a file renders differently, copy screenshots of the new, original, and diff (if available) renderings into the current working directory. Diff renderings may not be available if the two renderings differ in dimensions. WARNING: DO NOT START FIREFOX WHILE THIS PROGRAM IS RUNNING!")
	parser.add_argument("-i", "--include-common", dest="include_common_files", action="store_true", help="include commonly-excluded SE files like imprint, titlepage, and colophon")
	parser.add_argument("-n", "--no-images", dest="copy_images", action="store_false", help="don’t copy diff images to the current working directory in case of difference")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="a directory containing XHTML files")
	args = parser.parse_args()

	# Check for some required tools.
	try:
		firefox_path = se.get_firefox_path()
	except Exception:
		se.print_error("Couldn’t locate firefox. Is it installed?")
		return se.MissingDependencyException.code

	which_compare = shutil.which("compare")
	if which_compare:
		compare_path = Path(which_compare)
	else:
		se.print_error("Couldn’t locate compare. Is imagemagick installed?")
		return se.MissingDependencyException.code

	# Firefox won't start in headless mode if there is another Firefox process running; check that here.
	if "firefox" in (p.name() for p in psutil.process_iter()):
		se.print_error("Firefox is required, but it’s currently running. Stop all instances of Firefox and try again.")
		return se.FirefoxRunningException.code

	for target in args.targets:
		target = Path(target).resolve()

		target_filenames = set()
		if target.is_dir():
			for root, _, filenames in os.walk(target):
				for filename in fnmatch.filter(filenames, "*.xhtml"):
					if args.include_common_files or filename not in se.IGNORED_FILENAMES:
						target_filenames.add(Path(root) / filename)
		else:
			se.print_error(f"Target must be a directory: {target}")
			continue

		if args.verbose:
			print(f"Processing {target} ...\n", end="", flush=True)

		git_command = git.cmd.Git(target)

		if "nothing to commit" in git_command.status():
			se.print_error("Repo is clean. This script must be run on a dirty repo.", args.verbose)
			continue

		# Put Git's changes into the stash
		git_command.stash()

		with tempfile.TemporaryDirectory() as temp_directory_name:
			# Generate screenshots of the pre-change repo
			for filename in target_filenames:
				filename = Path(filename)

				# Path arguments must be cast to string for Windows compatibility.
				subprocess.run([str(firefox_path), "-screenshot", f"{temp_directory_name}/{filename.name}-original.png", str(filename)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

			# Pop the stash
			git_command.stash("pop")

			# Generate screenshots of the post-change repo, and compare them to the old screenshots
			for filename in target_filenames:
				file_path = Path(filename)
				file_new_screenshot_path = Path(temp_directory_name) / (file_path.name + "-new.png")
				file_original_screenshot_path = Path(temp_directory_name) / (file_path.name + "-original.png")
				file_diff_screenshot_path = Path(temp_directory_name) / (file_path.name + "-diff.png")

				# Path arguments must be cast to string for Windows compatibility.
				subprocess.run([str(firefox_path), "-screenshot", str(file_new_screenshot_path), str(filename)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

				# Path arguments must be cast to string for Windows compatibility.
				output = subprocess.run([str(compare_path), "-metric", "ae", str(file_original_screenshot_path), str(file_new_screenshot_path), str(file_diff_screenshot_path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout.decode().strip()

				if output != "0":
					print("{}Difference in {}\n".format("\t" if args.verbose else "", filename), end="", flush=True)

					if args.copy_images:
						try:
							output_directory = Path("./" + target.name + "_diff-output/")
							output_directory.mkdir(parents=True, exist_ok=True)

							shutil.copy(file_new_screenshot_path, output_directory)
							shutil.copy(file_original_screenshot_path, output_directory)
							shutil.copy(file_diff_screenshot_path, output_directory)
						except Exception:
							pass
	return 0
