"""
This module implements the `se build-images` command.
"""

import argparse
from pathlib import Path

import se
import se.images
from se.se_epub import SeEpub

def build_images(plain_output: bool) -> int:
	"""
	Entry point for `se build-images`.
	"""

	parser = argparse.ArgumentParser(description="Generate ebook cover and titlepages for Standard Ebooks ebooks, and then build ebook covers and titlepages, placing the output in `DIRECTORY/src/epub/images/`.")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("-g", "--no-generate", action="store_true", help="don't generate new source cover/titlepage SVGs, only build existing ones")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	console = se.init_console()

	for directory in args.directories:
		directory = Path(directory).resolve()

		if args.verbose:
			console.print(se.prep_output(f"Processing [path][link=file://{directory}]{directory}[/][/] ...", plain_output))

		try:
			se_epub = SeEpub(directory)

			if args.verbose:
				console.print("\tCleaning metadata ...", end="")

			# Remove useless metadata from cover source files.
			for file_path in directory.glob("**/cover.*"):
				se.images.remove_image_metadata(file_path)

			# Only generate the cover if this is an SE ebook.
			if se_epub.is_se_ebook and not args.no_generate:
				if args.verbose:
					console.print(" OK")
					console.print(se.prep_output(f"\tGenerating [path][link=file://{directory / 'images/cover.svg'}]cover.svg[/][/] ...", plain_output), end="")

				se_epub.generate_cover_svg()

			if args.verbose:
				console.print(" OK")
				console.print(se.prep_output(f"\tBuilding [path][link=file://{directory / 'src/epub/images/cover.svg'}]cover.svg[/][/] ...", plain_output), end="")

			se_epub.build_cover_svg()

			# Only generate the titlepage if this is an SE ebook.
			if se_epub.is_se_ebook and not args.no_generate:
				if args.verbose:
					console.print(" OK")
					console.print(se.prep_output(f"\tGenerating [path][link=file://{directory / 'images/titlepage.svg'}]titlepage.svg[/][/] ...", plain_output), end="")

				se_epub.generate_titlepage_svg()

			if args.verbose:
				console.print(" OK")
				console.print(se.prep_output(f"\tBuilding [path][link=file://{directory / 'src/epub/images/titlepage.svg'}]titlepage.svg[/][/] ...", plain_output), end="")

			se_epub.build_titlepage_svg()

			if args.verbose:
				console.print(" OK")

			if args.verbose:
				console.print("\tOptimizing PNGs ...", end="")

			# Optimize PNGs that we're distributing.
			for file_path in directory.glob("src/epub/**/*.png"):
				se.images.optimize_png(file_path)

			if args.verbose:
				console.print(" OK")

		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

	return 0
