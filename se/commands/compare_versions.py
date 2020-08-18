"""
This module implements the `se compare-versions` command.
"""

import argparse
from distutils.dir_util import copy_tree
import fnmatch
import os
import shutil
import tempfile
from pathlib import Path

import importlib_resources
import git
from natsort import natsorted
from PIL import Image, ImageChops
from rich.console import Console

import se
import se.browser


def _resize_canvas(image: Image, new_width: int, new_height: int) -> Image:
	"""
	Expand an image's canvas with black, to the new height and width.
	"""
	temp_image = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 255))
	temp_image.paste(image, (0, 0))

	return temp_image

def compare_versions() -> int:
	"""
	Entry point for `se compare-versions`
	"""

	parser = argparse.ArgumentParser(description="Use Firefox to render and compare XHTML files in an ebook repository. Run on a dirty repository to visually compare the repository’s dirty state with its clean state. If a file renders differently, place screenshots of the new, original, and diff (if available) renderings in the current working directory. A file called diff.html is created to allow for side-by-side comparisons of original and new files.")
	parser.add_argument("-i", "--include-common", dest="include_common_files", action="store_true", help="include commonly-excluded SE files like imprint, titlepage, and colophon")
	parser.add_argument("-n", "--no-images", dest="copy_images", action="store_false", help="don’t create images of diffs")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="a directory containing XHTML files")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=se.is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel

	# We wrap this whole thing in a try block, because we need to call
	# driver.quit() if execution is interrupted (like by ctrl + c, or by an unhandled exception). If we don't call driver.quit(),
	# Firefox will stay around as a zombie process even if the Python script is dead.
	try:
		try:
			driver = se.browser.initialize_selenium_firefox_webdriver()
		except se.MissingDependencyException as ex:
			se.print_error(ex)
			return ex.code

		# Ready to go!
		for target in args.targets:
			target = Path(target).resolve()

			if not target.is_dir():
				se.print_error(f"Target must be a directory: [path][link=file://{target}]{target}[/][/].")
				continue

			if args.verbose:
				console.print(f"Processing [path][link=file://{target}]{target}[/][/] ...")

			with tempfile.TemporaryDirectory() as work_directory_name:
				# Copy the Git repo to a temp folder, so we can stash and pop with impunity.
				# If we work directly on the real repo, ctrl + c may leave it in a stashed state unexpectedly.
				# We have to use this function instead of shutil.copytree because shutil.copytree
				# raises an error if the directory exists, in Python 3.6. Python 3.8+ has an option to ignore that.
				copy_tree(target, work_directory_name)

				target_filenames = set()

				for root, _, filenames in os.walk(work_directory_name):
					for xhtml_filename in fnmatch.filter(filenames, "*.xhtml"):
						if args.include_common_files or xhtml_filename not in se.IGNORED_FILENAMES:
							target_filenames.add(Path(root) / xhtml_filename)

				git_command = git.cmd.Git(work_directory_name)

				if "nothing to commit" in git_command.status():
					se.print_error("Repo is clean. This command must be run on a dirty repo.", args.verbose)
					continue

				output_directory = Path(f"./{target.name}_diff-output/")

				# Put Git's changes into the stash
				git_command.stash()

				with tempfile.TemporaryDirectory() as temp_directory_name:
					# Generate screenshots of the pre-change repo
					for filename in target_filenames:
						filename = Path(filename).resolve()

						if args.verbose:
							console.print(f"\tProcessing original [path][link=file://{filename}]{filename.name}[/][/] ...")

						driver.get(f"file://{filename}")
						# We have to take a screenshot of the html element, because otherwise we screenshot the viewport, which would result in a truncated image
						driver.find_element_by_tag_name("html").screenshot(f"{temp_directory_name}/{filename.name}-original.png")

					# Pop the stash
					git_command.stash("pop")

					files_with_differences = set()

					# Generate screenshots of the post-change repo, and compare them to the old screenshots
					for filename in target_filenames:
						filename = Path(filename).resolve()
						file_new_screenshot_path = Path(temp_directory_name) / (filename.name + "-new.png")
						file_original_screenshot_path = Path(temp_directory_name) / (filename.name + "-original.png")

						if args.verbose:
							console.print(f"\tProcessing new [path][link=file://{filename}]{filename.name}[/][/] ...")

						driver.get(f"file://{filename}")
						# We have to take a screenshot of the html element, because otherwise we screenshot the viewport, which would result in a truncated image
						driver.find_element_by_tag_name("html").screenshot(str(file_new_screenshot_path))

						has_difference = False
						original_image = Image.open(file_original_screenshot_path)
						new_image = Image.open(file_new_screenshot_path)

						# Make sure the original and new images are the same size.
						# If they're not, add pixels in either direction until they match.
						original_width, original_height = original_image.size
						new_width, new_height = new_image.size

						if original_height > new_height:
							new_image = _resize_canvas(new_image, new_width, original_height)
							new_image.save(file_new_screenshot_path)

						if original_width > new_width:
							new_image = _resize_canvas(new_image, original_width, new_height)
							new_image.save(file_new_screenshot_path)

						if new_height > original_height:
							original_image = _resize_canvas(original_image, original_width, new_height)
							original_image.save(file_original_screenshot_path)

						if new_width > original_width:
							original_image = _resize_canvas(original_image, new_width, original_height)
							original_image.save(file_original_screenshot_path)

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
							files_with_differences.add(filename)

							if args.copy_images:
								try:
									output_directory.mkdir(parents=True, exist_ok=True)

									shutil.copy(file_new_screenshot_path, output_directory)
									shutil.copy(file_original_screenshot_path, output_directory)

									original_image.paste(diff.convert("RGB"), mask=diff)
									original_image.save(output_directory / (filename.name + "-diff.png"))

								except Exception:
									pass

					for filename in natsorted(list(files_with_differences)):
						console.print("{}Difference in {}".format("\t" if args.verbose else "", f"[path][link=file://{filename}]{filename.name}[/][/]"))

					if files_with_differences and args.copy_images:
						# Generate an HTML file with diffs side by side
						html = ""

						for filename in natsorted(list(files_with_differences)):
							html += f"\t\t<section>\n\t\t\t<h1>{filename.name}</h1>\n\t\t\t<img src=\"{filename.name}-original.png\">\n\t\t\t<img src=\"{filename.name}-new.png\">\n\t\t</section>\n"

						with importlib_resources.open_text("se.data.templates", "diff-template.html", encoding="utf-8") as file:
							html = file.read().replace("<!--se:sections-->", html.strip())

						with open(output_directory / "diff.html", "w") as file:
							file.write(html)
							file.truncate()
	except KeyboardInterrupt as ex:
		# Bubble the exception up, but proceed to `finally` so we quit the driver
		raise ex
	finally:
		try:
			driver.quit()
		except Exception:
			# We might get here if we ctrl + c before selenium has finished initializing the driver
			pass

	return 0
