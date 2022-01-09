"""
This module implements the `se build-manifest` command.
"""

import argparse

from lxml import etree

import se
import se.easy_xml
import se.formatting
from se.se_epub import SeEpub


def build_manifest(plain_output: bool) -> int:
	"""
	Entry point for `se build-manifest`
	"""

	parser = argparse.ArgumentParser(description="Generate the <manifest> element for the given Standard Ebooks source directory and write it to the ebook’s metadata file.")
	parser.add_argument("-s", "--stdout", action="store_true", help="print to stdout instead of writing to the metadata file")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	if args.stdout and len(args.directories) > 1:
		se.print_error("Multiple directories are only allowed without the [bash]--stdout[/] option.", plain_output=plain_output)
		return se.InvalidArgumentsException.code

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)

			if args.stdout:
				print(se_epub.generate_manifest().to_string())
			else:
				nodes = se_epub.metadata_dom.xpath("/package/manifest")
				if nodes:
					for node in nodes:
						node.replace_with(se_epub.generate_manifest())
				else:
					for node in se_epub.metadata_dom.xpath("/package"):
						node.append(se_epub.generate_manifest())

				# If we have images in the manifest, add or remove some accessibility metadata while we're here
				access_mode_nodes = se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessMode' and text() = 'visual']")
				access_mode_sufficient_nodes = se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessibilityFeature' and text() = 'alternativeText']")

				if se_epub.metadata_dom.xpath("/package/manifest/item[starts-with(@media-type, 'image/') and not(re:test(@href, 'images/(cover\\.svg||logo\\.svg|titlepage\\.svg)$'))]"):
					# Add access modes if we have images
					if not access_mode_nodes:
						se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessMode' and text() = 'textual']")[0].lxml_element.addnext(etree.XML("<meta property=\"schema:accessMode\">visual</meta>"))

					if not access_mode_sufficient_nodes:
						se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessModeSufficient']")[0].lxml_element.addnext(etree.XML("<meta property=\"schema:accessibilityFeature\">alternativeText</meta>"))
				else:
					# If we don't have images, then remove any access modes that might be there erroneously
					for node in access_mode_nodes:
						node.remove()

					for node in access_mode_sufficient_nodes:
						node.remove()

				with open(se_epub.metadata_file_path, "w", encoding="utf-8") as file:
					file.write(se.formatting.format_xml(se_epub.metadata_dom.to_string()))

		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

	return 0
