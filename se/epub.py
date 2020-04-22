#!/usr/bin/env python3
"""
Defines several functions that are useful for interacting with epub files.
"""

import os
from pathlib import Path
import zipfile
import itertools
import regex
from lxml import etree
import se
import se.easy_xml


def convert_toc_to_ncx(epub_root_absolute_path: Path, toc_filename: str, xsl_filename: Path) -> se.easy_xml.EasyXhtmlTree:
	"""
	Take an epub3 HTML5 ToC file and convert it to an epub2 NCX file. NCX output is written to the same directory as the ToC file, in a file named "toc.ncx".

	epub structure must be in the SE format.

	INPUTS
	epub_root_absolute_path: The root directory of an unzipped epub
	toc_filename: The filename of the ToC file
	xsl_filename: The filename for the XSL file used to perform the transformation

	OUTPUTS
	An se.easy_xml.EasyXhtmlTree representing the HTML5 ToC file
	"""

	# Use an XSLT transform to generate the NCX
	with open(epub_root_absolute_path / "epub" / toc_filename, "r", encoding="utf-8") as file:
		xhtml = file.read()

	toc_tree = se.easy_xml.EasyXhtmlTree(xhtml)
	transform = etree.XSLT(etree.parse(str(xsl_filename)))
	ncx_tree = transform(etree.fromstring(str.encode(xhtml)), cwd=f"'{epub_root_absolute_path}{os.path.sep}'")

	with open(epub_root_absolute_path / "epub" / "toc.ncx", "w", encoding="utf-8") as file:
		ncx_xhtml = etree.tostring(ncx_tree, encoding="unicode", pretty_print=True, with_tail=False)
		ncx_xhtml = regex.sub(r" xml:lang=\"\?\?\"", "", ncx_xhtml)

		# Make nicely incrementing navpoint IDs and playOrders
		ncx_xhtml = regex.sub(r"<navMap id=\".*\">", "<navMap id=\"navmap\">", ncx_xhtml)

		counter = itertools.count(1)
		ncx_xhtml = regex.sub(r"<navPoint id=\"id[\p{Letter}0-9]+?\"", lambda x: "<navPoint id=\"navpoint-{count}\" playOrder=\"{count}\"".format(count=next(counter)), ncx_xhtml)

		ncx_xhtml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n{ncx_xhtml}"

		file.write(ncx_xhtml)

	return toc_tree

def write_epub(epub_root_absolute_path: Path, output_absolute_path: Path) -> None:
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
		epub.write(epub_root_absolute_path / "mimetype", "mimetype")
		epub.write(epub_root_absolute_path / "META-INF" / "container.xml", "META-INF/container.xml", compress_type=zipfile.ZIP_DEFLATED)

		for root, _, files in os.walk(epub_root_absolute_path):
			for file in files:
				if file not in ("mimetype", "container.xml"):
					epub.write(Path(root) / file, (Path(root) / file).relative_to(epub_root_absolute_path), compress_type=zipfile.ZIP_DEFLATED)
