#!/usr/bin/env python3

import os
import zipfile
import itertools
import regex
import se.easy_xml
from lxml import etree


UNICODE_BOM = "\ufeff"


def strip_bom(unicode_string):
	if unicode_string.startswith(UNICODE_BOM):
		unicode_string = unicode_string[1:]

	return unicode_string

def quiet_remove(filename):
	try:
		os.remove(filename)
	except Exception:
		pass

def convert_toc_to_ncx(epub_root_directory, toc_filename, xsl_filename):
	# Use an XSLT transform to generate the NCX
	with open(os.path.join(epub_root_directory, "epub", toc_filename), "r", encoding="utf-8") as file:
		toc_tree = se.easy_xml.EasyXmlTree(file.read())

	transform = etree.XSLT(etree.parse(xsl_filename))
	ncx_tree = transform(toc_tree.etree, cwd="'{}{}'".format(epub_root_directory, os.path.sep))

	with open(os.path.join(epub_root_directory, "epub", "toc.ncx"), "w", encoding="utf-8") as file:
		ncx_xhtml = etree.tostring(ncx_tree, encoding="unicode", pretty_print=True, with_tail=False)
		ncx_xhtml = regex.sub(r" xml:lang=\"\?\?\"", "", ncx_xhtml)

		# Make nicely incrementing navpoint IDs and playOrders
		ncx_xhtml = regex.sub(r"<navMap id=\".*\">", "<navMap id=\"navmap\">", ncx_xhtml)

		counter = itertools.count(1)
		ncx_xhtml = regex.sub(r"<navPoint id=\"id[a-z0-9]+?\"", lambda x: "<navPoint id=\"navpoint-{count}\" playOrder=\"{count}\"".format(count=next(counter)), ncx_xhtml)

		ncx_xhtml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + ncx_xhtml

		file.write(ncx_xhtml)

	return toc_tree

def write_epub(file_path, directory):
	# We can't enable global compression here because according to the spec, the `mimetype` file must be uncompressed.  The rest of the files, however, can be compressed.
	with zipfile.ZipFile(file_path, mode="w") as epub:
		epub.write(os.path.join(directory, "mimetype"), "mimetype")
		epub.write(os.path.join(directory, "META-INF", "container.xml"), "META-INF/container.xml", compress_type=zipfile.ZIP_DEFLATED)

		for root, _, files in os.walk(directory):
			for file in files:
				if file != "mimetype" and file != "container.xml":
					epub.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), directory), compress_type=zipfile.ZIP_DEFLATED)
