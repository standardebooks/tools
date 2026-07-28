#!/usr/bin/env python3
"""
Defines several functions that are useful for interacting with epub files.
"""

import os
from datetime import datetime
from pathlib import Path
import sys
import zipfile
from repro_zipfile import ReproducibleZipFile
from lxml import etree
from se.formatting import generate_epoch_timestamp
import se
import se.easy_xml


def _write_epub_file(epub: ReproducibleZipFile, input_path: Path, output_path: str | Path, compress_type: int | None = None) -> None:
	"""
	Write a file to an EPUB with platform-independent ZIP metadata.
	"""
	epub.write(input_path, output_path, compress_type=compress_type)

	# This sets the zip file's `created on platform` value to `unix`.
	epub.filelist[-1].create_system = 3

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

	# Use an XSLT transform to generate the NCX.
	with open(epub_root_absolute_path / "epub" / toc_filename, "r", encoding="utf-8") as file:
		xhtml = file.read()

	toc_tree = se.easy_xml.EasyXmlTree(xhtml)
	transform = etree.XSLT(etree.parse(str(xsl_filename)))
	ncx_dom = se.easy_xml.EasyXmlTree(transform(etree.fromstring(str.encode(xhtml)), cwd=f"'{epub_root_absolute_path.as_posix()}/'"))

	# Remove empty `xml:lang` attributes.
	for node in ncx_dom.xpath("//*[@xml:lang and re:test(@xml:lang, '^\\s*$')]"):
		node.remove_attr("xml:lang")

	for node in ncx_dom.xpath("//navMap"):
		node.set_attr("id", "navmap")

	# Make nicely incrementing `navpoint` IDs and `playOrder`s.
	count = 1
	for node in ncx_dom.xpath("//navPoint"):
		node.set_attr("id", f"navpoint-{count}")
		node.set_attr("playOrder", f"{count}")
		count = count + 1

	with open(epub_root_absolute_path / "epub" / "toc.ncx", "w", encoding="utf-8") as file:
		file.write(ncx_dom.to_string())

	return toc_tree

def write_epub(epub_root_absolute_path: Path, output_absolute_path: Path, last_update_datetime: datetime | None) -> None:
	"""
	Given a root directory, compress it into a final epub file.

	INPUTS
	epub_root_absolute_path: The root directory of an unzipped epub
	output_absolute_path: The filename of the output file
	last_update_datetime: The datetime when the epub source was last updated

	OUTPUTS
	None
	"""

	# Windows text writes use CRLF line endings by default, so normalize every UTF-8 file immediately before creating any build type.
	if sys.platform == "win32":
		for file_path in epub_root_absolute_path.glob("**/*"):
			if file_path.is_file():
				try:
					file_bytes = file_path.read_bytes()
					file_contents = file_bytes.decode("utf-8")
					normalized_file_bytes = file_contents.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
					if normalized_file_bytes != file_bytes:
						file_path.write_bytes(normalized_file_bytes)
				except UnicodeDecodeError:
					pass

	# Set the timestamp used by ReproducibleZipFile to the timestamp of the last git commit, if available.
	if last_update_datetime is not None:
		os.environ["SOURCE_DATE_EPOCH"] = generate_epoch_timestamp(last_update_datetime)

	with ReproducibleZipFile(output_absolute_path, mode="w", compression=zipfile.ZIP_DEFLATED) as epub:
		# According to the spec, the `mimetype` file must be uncompressed. The rest of the files, however, can be compressed.
		_write_epub_file(epub, epub_root_absolute_path / "mimetype", "mimetype", zipfile.ZIP_STORED)
		_write_epub_file(epub, epub_root_absolute_path / "META-INF" / "container.xml", "META-INF/container.xml")

		# Sort paths `as_posix()` because Windows orders files differently depending on case, and we want to preserve the same order so we can make byte-identical zip files.
		for file_path in sorted(epub_root_absolute_path.glob("**/*"), key=lambda path: path.relative_to(epub_root_absolute_path).as_posix()):
			if file_path.name not in ("mimetype", "container.xml"):
				_write_epub_file(epub, file_path, file_path.relative_to(epub_root_absolute_path))

	# Unset the timestamp environment variable that was set for ReproducibleZipFile.
	if last_update_datetime is not None:
		del os.environ["SOURCE_DATE_EPOCH"]
