#!/usr/bin/env python3
"""
Defines several functions that are useful for interacting with epub files.
"""

import os
from collections.abc import Callable
from datetime import datetime
from hashlib import file_digest
from pathlib import Path
import struct
import sys
import zipfile
from repro_zipfile import ReproducibleZipFile, date_time, file_mode
from lxml import etree
from se.formatting import generate_epoch_timestamp
import se
import se.easy_xml


ZIP_COMPRESSION_CACHE_MAX_SIZE = 128 * 1024 * 1024
type EpubCompressionCache = dict[tuple[bytes, int, int | None], tuple[int, bytes]]


class _CachedEpubZipFile(ReproducibleZipFile):
	"""Reuse compressed file contents while preserving reproducible ZIP metadata."""

	# Inherited state omitted from the standard library's type stubs.
	_writing: bool
	_strict_timestamps: bool
	_writecheck: Callable[[zipfile.ZipInfo], None]

	def __init__(self, output_path: Path, compression_cache: EpubCompressionCache) -> None:
		"""
		Open an EPUB archive with a cache shared by one ebook's build variants.
		"""

		super().__init__(output_path, mode="w", compression=zipfile.ZIP_DEFLATED)
		self._compression_cache = compression_cache

	def write(self, filename: str | os.PathLike[str], arcname: str | os.PathLike[str] | None = None, compress_type: int | None = None, compresslevel: int | None = None) -> None:
		"""
		Write a member using its original compressed bytes when its contents match.
		"""

		path = Path(filename)
		if compress_type is None:
			compress_type = self.compression
		if compresslevel is None:
			compresslevel = self.compresslevel

		# Keep directory entries, stored members, ZIP64 members, and error handling with the original writer.
		if not self.fp or self._writing or compress_type != zipfile.ZIP_DEFLATED or path.is_dir() or path.stat().st_size * 1.05 > zipfile.ZIP64_LIMIT:
			super().write(filename, arcname, compress_type, compresslevel)
			return

		with path.open("rb") as file:
			key = (file_digest(file, "sha256").digest(), compress_type, compresslevel)
		cached = self._compression_cache.get(key)

		if cached is not None:
			# Rebuild metadata for this member's current name, timestamp, and permissions.
			info = zipfile.ZipInfo.from_file(filename, arcname, strict_timestamps=self._strict_timestamps)
			info.date_time = date_time()
			info.external_attr = file_mode() << 16
			info.compress_type = compress_type
			info.compress_level = compresslevel
			info.CRC, compressed = cached
			info.compress_size = len(compressed)
			self.fp.seek(self.start_dir)
			info.header_offset = self.fp.tell()
			self._writecheck(info)
			self._didModify = True
			self.fp.write(info.FileHeader(False))
			self.fp.write(compressed)
			self.start_dir = self.fp.tell()
			self.filelist.append(info)
			self.NameToInfo[info.filename] = info
		else:
			super().write(filename, arcname, compress_type, compresslevel)
			info = self.filelist[-1]
			# Retain only a bounded amount of compressed data, and leave subsequent writes at the archive end.
			if info.compress_size <= ZIP_COMPRESSION_CACHE_MAX_SIZE - sum(len(entry[1]) for entry in self._compression_cache.values()):
				self.fp.seek(info.header_offset)
				# The fixed 30-byte local header gives the lengths of the filename and extra fields preceding the payload.
				_, name_length, extra_length = struct.unpack("<4s22xHH", self.fp.read(30))
				self.fp.seek(info.header_offset + 30 + name_length + extra_length)
				self._compression_cache[key] = (info.CRC, self.fp.read(info.compress_size))
				self.fp.seek(self.start_dir)


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
	with open(epub_root_absolute_path / "epub" / toc_filename, "rb") as file:
		xhtml = se.read_utf8(file)

	toc_tree = se.easy_xml.EasyXmlTree(xhtml)
	with open(xsl_filename, "rb") as file:
		se.read_utf8(file)
		file.seek(0)
		transform = etree.XSLT(etree.parse(file))
	ncx_dom = se.easy_xml.EasyXmlTree(transform(etree.fromstring(xhtml), cwd=f"'{epub_root_absolute_path.as_posix()}/'"))

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

def write_epub(epub_root_absolute_path: Path, output_absolute_path: Path, last_update_datetime: datetime | None, compression_cache: EpubCompressionCache | None = None) -> None:
	"""
	Given a root directory, compress it into a final epub file.

	INPUTS
	epub_root_absolute_path: The root directory of an unzipped epub
	output_absolute_path: The filename of the output file
	last_update_datetime: The datetime when the epub source was last updated
	compression_cache: Compressed member contents shared by one ebook's build variants, or `None` to disable reuse.

	OUTPUTS
	None
	"""

	# Windows text writes use CRLF line endings by default, so normalize every UTF-8 file immediately before creating any build type.
	if sys.platform == "win32":
		se.convert_directory_line_endings(epub_root_absolute_path, False)

	# Set the timestamp used by ReproducibleZipFile to the timestamp of the last git commit, if available.
	if last_update_datetime is not None:
		os.environ["SOURCE_DATE_EPOCH"] = generate_epoch_timestamp(last_update_datetime)

	epub_file: ReproducibleZipFile
	if compression_cache is None:
		epub_file = ReproducibleZipFile(output_absolute_path, mode="w", compression=zipfile.ZIP_DEFLATED)
	else:
		epub_file = _CachedEpubZipFile(output_absolute_path, compression_cache)

	with epub_file as epub:
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
