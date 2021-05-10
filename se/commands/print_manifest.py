"""
This module implements the `se print-manifest` command.
"""

import argparse

import lxml.etree as etree
import se
import se.easy_xml
import se.formatting
from se.se_epub import SeEpub


def print_manifest() -> int:
	"""
	Entry point for `se print-manifest`
	"""

	parser = argparse.ArgumentParser(description="Print the <manifest> element for the given Standard Ebooks source directory to standard output, for use in that directory’s metadata file.")
	parser.add_argument("-i", "--in-place", action="store_true", help="overwrite the <manifest> element in the metadata file instead of printing to stdout")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	if not args.in_place and len(args.directories) > 1:
		se.print_error("Multiple directories are only allowed with the [bash]--in-place[/] option.")
		return se.InvalidArgumentsException.code

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)
		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

		if args.in_place:
			for node in se_epub.metadata_dom.xpath("/package/manifest"):
				node.replace_with(se.easy_xml.EasyXmlElement(etree.fromstring(str.encode(se_epub.generate_manifest()))))

			with open(se_epub.metadata_file_path, "w", encoding="utf-8") as file:
				file.write(se.formatting.format_xml(se_epub.metadata_dom.to_string()))
		else:
			print(se_epub.generate_manifest())

	return 0
