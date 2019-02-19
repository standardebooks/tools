#!/usr/bin/env python3
"""
Defines several functions that are useful for interacting with epub files.
"""

import os
import zipfile
import itertools
import regex
from lxml import etree
import se
import se.easy_xml


def convert_toc_to_ncx(epub_root_absolute_path: str, toc_filename: str, xsl_filename: str) -> se.easy_xml.EasyXmlTree:
	"""
	Take an epub3 HTML5 ToC file and convert it to an epub2 NCX file. NCX output is written to the same directory as the ToC file, in a file named "toc.ncx".

	epub structure must be in the SE format.

	INPUTS
	epub_root_absolute_path: The root directory of an unzipped epub
	toc_filename: The filename of the ToC file
	xsl_filename: The filename for the XSL file used to perform the transformation

	OUTPUTS
	An se.easy_xml.EasyXmlTree representing the HTML5 ToC file
	"""

	# Use an XSLT transform to generate the NCX
	with open(os.path.join(epub_root_absolute_path, "epub", toc_filename), "r", encoding="utf-8") as file:
		toc_tree = se.easy_xml.EasyXmlTree(file.read())

	transform = etree.XSLT(etree.parse(xsl_filename))
	ncx_tree = transform(toc_tree.etree, cwd="'{}{}'".format(epub_root_absolute_path, os.path.sep))

	with open(os.path.join(epub_root_absolute_path, "epub", "toc.ncx"), "w", encoding="utf-8") as file:
		ncx_xhtml = etree.tostring(ncx_tree, encoding="unicode", pretty_print=True, with_tail=False)
		ncx_xhtml = regex.sub(r" xml:lang=\"\?\?\"", "", ncx_xhtml)

		# Make nicely incrementing navpoint IDs and playOrders
		ncx_xhtml = regex.sub(r"<navMap id=\".*\">", "<navMap id=\"navmap\">", ncx_xhtml)

		counter = itertools.count(1)
		ncx_xhtml = regex.sub(r"<navPoint id=\"id[a-z0-9]+?\"", lambda x: "<navPoint id=\"navpoint-{count}\" playOrder=\"{count}\"".format(count=next(counter)), ncx_xhtml)

		ncx_xhtml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + ncx_xhtml

		file.write(ncx_xhtml)

	return toc_tree

def write_epub(epub_root_absolute_path: str, output_absolute_path: str) -> None:
	"""
	Given a root directory, compress it into a final epub file.

	INPUTS
	epub_root_absolute_path: The root directory of an unzipped epub
	output_absolute_path: The filename of the output file

	OUTPUTS
	None
	"""

	# We can't enable global compression here because according to the spec, the `mimetype` file must be uncompressed.  The rest of the files, however, can be compressed.
	with zipfile.ZipFile(output_absolute_path, mode="w") as epub:
		epub.write(os.path.join(epub_root_absolute_path, "mimetype"), "mimetype")
		epub.write(os.path.join(epub_root_absolute_path, "META-INF", "container.xml"), "META-INF/container.xml", compress_type=zipfile.ZIP_DEFLATED)

		for root, _, files in os.walk(epub_root_absolute_path):
			for file in files:
				if file != "mimetype" and file != "container.xml":
					epub.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), epub_root_absolute_path), compress_type=zipfile.ZIP_DEFLATED)
