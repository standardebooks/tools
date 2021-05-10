#!/usr/bin/env python3
"""
Defines several functions that are useful for interacting with epub files.
"""

from pathlib import Path
import zipfile
from lxml import etree
import se
import se.easy_xml


def convert_toc_to_ncx(epub_root_absolute_path: Path, toc_filename: str, xsl_filename: Path) -> se.easy_xml.EasyXmlTree:
	"""
	Take an HTML5 ToC file and convert it to an NCX file for compatibility with older ereaders. NCX output is written to the same directory as the ToC file, in a file named "toc.ncx".

	epub structure must be in the SE format.

	INPUTS
	epub_root_absolute_path: The root directory of an unzipped epub
	toc_filename: The filename of the ToC file
	xsl_filename: The filename for the XSL file used to perform the transformation

	OUTPUTS
	An se.easy_xml.EasyXmlTree representing the HTML5 ToC file
	"""

	# Use an XSLT transform to generate the NCX
	with open(epub_root_absolute_path / "epub" / toc_filename, "r", encoding="utf-8") as file:
		xhtml = file.read()

	toc_tree = se.easy_xml.EasyXmlTree(xhtml)
	transform = etree.XSLT(etree.parse(str(xsl_filename)))
	ncx_dom = se.easy_xml.EasyXmlTree(transform(etree.fromstring(str.encode(xhtml)), cwd=f"'{epub_root_absolute_path.as_posix()}/'"))

	# Remove empty lang tags
	for node in ncx_dom.xpath("//*[@xml:lang and re:test(@xml:lang, '^\\s*$')]"):
		node.remove_attr("xml:lang")

	for node in ncx_dom.xpath("//navMap"):
		node.set_attr("id", "navmap")

	# Make nicely incrementing navpoint IDs and playOrders
	count = 1
	for node in ncx_dom.xpath("//navPoint"):
		node.set_attr("id", f"navpoint-{count}")
		node.set_attr("playOrder", f"{count}")
		count = count + 1

	with open(epub_root_absolute_path / "epub" / "toc.ncx", "w", encoding="utf-8") as file:
		file.write(ncx_dom.to_string())

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

		for file_path in epub_root_absolute_path.glob("**/*"):
			if file_path.name not in ("mimetype", "container.xml"):
				epub.write(file_path, file_path.relative_to(epub_root_absolute_path), compress_type=zipfile.ZIP_DEFLATED)
