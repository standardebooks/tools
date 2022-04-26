"""
This module implements the `se convert-sectioning` command.
"""

import argparse

import se
import se.easy_xml
import se.formatting
from se.se_epub import SeEpub


def convert_sectioning(plain_output: bool) -> int: # pylint: disable=unused-argument
	"""
	Entry point for `se convert-sectioning`
	"""

	parser = argparse.ArgumentParser(description="Generate the <spine> element for the given Standard Ebooks source directory and write it to the ebook’s metadata file.")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)

			print(directory)

			for file_path in se_epub.spine_file_paths:
				with open(file_path, "r+", encoding="utf-8") as file:
					dom = se.easy_xml.EasyXmlTree(file.read())

					nodes = dom.xpath("//*[ (name() = 'section' or name() = 'article') and parent::*[name() = 'section' or name() = 'article'] and count(preceding-sibling::*) = 0 and count(following-sibling::*) = 0]")

					if nodes:
						deepest_section = nodes[len(nodes) - 1]

						deepest_section.set_attr("data-parent", deepest_section.parent.get_attr("id"))

						for node in deepest_section.xpath("./ancestor::*[ (name() = 'section' or name() = 'article') ]"):
							node.unwrap()

						file.seek(0)
						file.write(se.formatting.format_xhtml(dom.to_string()))
						file.truncate()

		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

	return 0
