"""
This module implements the `se build-manifest` command.
"""

import argparse

from lxml import etree

import se
import se.formatting
from se.se_epub import SeEpub


def build_manifest(plain_output: bool) -> int:
	"""
	Entry point for `se build-manifest`.
	"""

	parser = argparse.ArgumentParser(description="Generate the <manifest> element for the given Standard Ebooks source directory and write it to the ebook’s metadata file.")
	parser.add_argument("-s", "--stdout", action="store_true", help="print to stdout instead of writing to the metadata file")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	if args.stdout and len(args.directories) > 1:
		se.print_error("Multiple directories are not allowed with the [bash]--stdout[/] option.", plain_output=plain_output)
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

				# If we have images in the manifest, add or remove some accessibility metadata while we're here.
				access_mode_visual_nodes = se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessMode' and text() = 'visual']")
				access_mode_sufficient_nodes = se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessModeSufficient']")
				accessibility_feature_alt_text_nodes = se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessibilityFeature' and text() = 'alternativeText']")

				if se_epub.metadata_dom.xpath("/package/manifest/item[starts-with(@media-type, 'image/')]"):
					# There are images in this epub!

					# See <https://github.com/w3c/publ-a11y/issues/145#issuecomment-1421339961>.

					is_missing_alt_attributes = False
					has_significant_images = False
					for filename in se.get_target_filenames([directory], ".xhtml"):
						dom = se_epub.get_dom(filename)

						# Do we have any images that are missing `@alt` attributes?
						if dom.xpath("/html/body//img[not(@alt)]"):
							is_missing_alt_attributes = True

						# Do we have any images that are not decorative? See <https://kb.daisy.org/publishing/docs/metadata/schema.org/accessMode/visual.html>.
						if dom.xpath("/html/body//img[not(re:test(@epub:type, '\\b(z3998:publisher-logo|titlepage|cover)\\b')) and not(ancestor::*[re:test(@epub:type, '\\b(titlepage|cover)\\b')])]"):
							has_significant_images = True

					# Add access modes if we have images.
					if is_missing_alt_attributes or has_significant_images:
						if not access_mode_visual_nodes:
							se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessMode' and text() = 'textual']")[0].lxml_element.addnext(etree.XML("<meta property=\"schema:accessMode\">visual</meta>"))

						if is_missing_alt_attributes:
							for node in accessibility_feature_alt_text_nodes:
								node.remove()

							for node in access_mode_sufficient_nodes:
								node.text = "visual"

						else:
							for node in access_mode_sufficient_nodes:
								node.text = "textual"

					else:
						for node in access_mode_visual_nodes:
							node.remove()

						if not accessibility_feature_alt_text_nodes:
							se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessModeSufficient']")[0].lxml_element.addnext(etree.XML("<meta property=\"schema:accessibilityFeature\">alternativeText</meta>"))
				else:
					# If we don't have images, then remove any access modes that might be there erroneously.
					for node in access_mode_visual_nodes:
						node.remove()

					for node in accessibility_feature_alt_text_nodes:
						node.remove()

				# If we have MathML in the manifest, add some accessibility metadata while we're here.
				mathml_accesibility_nodes = se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessibilityFeature' and text() = 'MathML']")
				mathml_described_accesibility_nodes = se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessibilityFeature' and text() = 'describedMath']")

				if se_epub.metadata_dom.xpath("/package/manifest/item[contains(@properties, 'mathml')]"):
					start_nodes = se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessibilityFeature' and text() = 'alternativeText']")
					if not start_nodes:
						start_nodes = se_epub.metadata_dom.xpath("/package/metadata/meta[@property='schema:accessModeSufficient']")

					start_node = start_nodes[0]

					# Add access modes if we have MathML.
					if not mathml_accesibility_nodes:
						start_node.lxml_element.addnext(etree.XML("<meta property=\"schema:accessibilityFeature\">MathML</meta>"))

					if not mathml_described_accesibility_nodes:
						start_node.lxml_element.addnext(etree.XML("<meta property=\"schema:accessibilityFeature\">describedMath</meta>"))

				else:
					# If we don't have MathML, then remove any access modes that might be there erroneously.
					for node in mathml_accesibility_nodes:
						node.remove()

					for node in mathml_described_accesibility_nodes:
						node.remove()

				with open(se_epub.metadata_file_path, "w", encoding="utf-8") as file:
					file.write(se.formatting.format_xml(se_epub.metadata_dom.to_string()))

		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

	return 0
