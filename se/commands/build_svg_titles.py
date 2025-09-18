"""
This module implements the `se build-svg-titles` command.
"""

import argparse

import se
import se.easy_xml
from se.se_epub import SeEpub


def build_svg_titles(plain_output: bool) -> int:
	"""
	Entry point for `se build-svg-titles`.
	"""

	parser = argparse.ArgumentParser(description="Update or add SVG <title> elements based on the alt attributes from the <img> elements.")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	console = se.init_console()

	for directory in args.directories:
		try:
			if args.verbose:
				console.print(se.prep_output(f"Processing [path][link=file://{directory}]{directory}[/][/] ...", plain_output))

			se_epub = SeEpub(directory)

			# Load the `alt` attributes for all illustrations.
			for filename in se_epub.spine_file_paths:
				dom = se_epub.get_dom(filename)

				for img in dom.xpath(r"/html/body//img[re:test(@src,'\.svg$')]"):
					img_src = img.get_attr("src")
					img_alt = img.get_attr("alt")

					if not img_alt:
						continue

					# Update or add the title to the SVG.
					svg_path = se.abspath_relative_to(img_src, filename)
					try:
						svg_dom = se_epub.get_dom(svg_path)
						svg_element = svg_dom.xpath("/svg")[0]

						# Check for existing `<title>` elements in the SVG.
						title_elements = svg_dom.xpath("/svg/title")
						if len(title_elements) == 0:
							# Add a properly indented `<title>` element at the start of the `<svg>`.
							title_element = se.easy_xml.EasyXmlElement("<title/>")
							svg_element.prepend(title_element)
							svg_element.text = "\n\t"
						else:
							# Remove any additional `<title>` elements.
							for title_element in title_elements[1:]:
								title_element.remove()

							# Select the first element for updating.
							title_element = title_elements[0]

						# Update the text in the `<title>` element.
						title_element.text = img_alt

						with open(svg_path, "w", encoding="utf-8") as file:
							file.write(svg_dom.to_string())

					except FileNotFoundError:
						se.print_error(f"Couldn’t open file: [path][link=file://{svg_path}]{svg_path}[/][/].", plain_output=plain_output)

		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

	return 0
