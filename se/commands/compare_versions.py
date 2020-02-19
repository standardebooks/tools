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
from PIL import Image, ImageChops
import psutil

import se


def _resize_canvas(image: Image, new_width: int, new_height: int) -> Image:
	"""
	Expand an image's canvas with black, to the new height and width.
	"""
	temp_image = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 255))
	temp_image.paste(image, (0, new_height))

	return temp_image

def compare_versions() -> int:
	"""
	Entry point for `se compare-versions`

	WARNING: Firefox hangs when taking a screenshot on FF 69+, so this command is effectively broken until FF fixes the bug.
	See https://bugzilla.mozilla.org/show_bug.cgi?id=1589978
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
			se.print_error("Repo is clean. This command must be run on a dirty repo.", args.verbose)
			continue

		# Put Git's changes into the stash
		git_command.stash()

		with tempfile.TemporaryDirectory() as temp_directory_name:
			# Generate screenshots of the pre-change repo
			for filename in target_filenames:
				filename = Path(filename)

				# Path arguments must be cast to string for Windows compatibility.
				subprocess.run([str(firefox_path), "--screenshot", f"{temp_directory_name}/{filename.name}-original.png", str(filename)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

			# Pop the stash
			git_command.stash("pop")

			# Generate screenshots of the post-change repo, and compare them to the old screenshots
			for filename in target_filenames:
				file_path = Path(filename)
				file_new_screenshot_path = Path(temp_directory_name) / (file_path.name + "-new.png")
				file_original_screenshot_path = Path(temp_directory_name) / (file_path.name + "-original.png")
				file_diff_screenshot_path = Path(temp_directory_name) / (file_path.name + "-diff.png")

				# Path arguments must be cast to string for Windows compatibility.
				subprocess.run([str(firefox_path), "--screenshot", str(file_new_screenshot_path), str(filename)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

				has_difference = False
				original_image = Image.open(file_original_screenshot_path)
				new_image = Image.open(file_new_screenshot_path)

				# Make sure the original and new images are the same size.
				# If they're not, add pixels in either direction until they match.
				original_height, original_width = original_image.size
				new_height, new_width = new_image.size

				if original_height > new_height:
					new_image = _resize_canvas(new_image, new_width, original_height)

				if original_width > new_width:
					new_image = _resize_canvas(new_image, original_width, new_height)

				if new_height > original_height:
					original_image = _resize_canvas(original_image, original_width, new_height)

				if new_width > original_width:
					original_image = _resize_canvas(original_image, new_width, original_height)

				# Now get the diff
				diff = ImageChops.difference(original_image, new_image)

				# Process every pixel to see if there's a difference, and then convert that difference to red
				width, height = diff.size
				for image_x in range(0, width - 1):
					for image_y in range(0, height - 1):
						if diff.getpixel((image_x, image_y)) != (0, 0, 0, 0):
							has_difference = True
							diff.putpixel((image_x, image_y), (255, 0, 0, 255)) # Change the mask color to red

				if has_difference:
					print("{}Difference in {}\n".format("\t" if args.verbose else "", filename), end="", flush=True)

					if args.copy_images:
						try:
							output_directory = Path("./" + target.name + "_diff-output/")
							output_directory.mkdir(parents=True, exist_ok=True)

							shutil.copy(file_new_screenshot_path, output_directory)
							shutil.copy(file_original_screenshot_path, output_directory)

							original_image.paste(diff.convert("RGB"), mask=diff)
							original_image.save(file_diff_screenshot_path / (file_path.name + "-diff.png"))

						except Exception:
							pass

	return 0
