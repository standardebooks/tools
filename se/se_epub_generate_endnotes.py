#!/usr/bin/env python3
"""
This module contains the generate_endnotes function which locates all endnotes
in order and renumbers them from 1.

Strictly speaking, the generate_endnotes() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put in a separate file.
"""

import os
from bs4 import BeautifulSoup, Tag
import se
from se.formatting import format_xhtml

class ListNote:
	"""
	Class to hold information on endnotes
	"""

	number = 0
	anchor = ""
	contents = []  # the strings and tags inside an <li> element
	back_link = ""
	source_file = ""
	matched = False

class ProcessInfo:
	"""
	Class to hold information such as current note number, etc.
	"""

	current_number = 1
	notes_changed = 0
	change_list = []

def gethtml(file_path: str) -> str:
	"""
	Reads an xhtml file and returns the text

	INPUTS:
	file_path: path to the xhtml file to process

	OUTPUTS:
	The text of the xhtml file
	"""

	try:
		fileobject = open(file_path, 'r', encoding='utf-8')
	except IOError:
		raise se.FileExistsException('Could not open ' + file_path)
	text = fileobject.read()
	fileobject.close()
	return text

def extract_anchor(href: str) -> str:
	"""
	Extracts just the anchor from a URL (ie, what follows a hash symbol)

	INPUTS:
	href: should be like: "../text/endnotes.xhtml#note-1"

	OUTPUTS:
	the anchor: just the part after the hash, eg "note-1" in the example above
	"""

	hash_position = href.find("#") + 1  # we want the characters AFTER the hash
	if hash_position > 0:
		return href[hash_position:]
	return ""

def process_file(text_path: str, file_name: str, endnotes: list, process_info: ProcessInfo):
	"""
	Reads a content file, locates and processes the endnote references,
	accumulating info on them in a global list, and returns the next note number.
	Note that it REWRITES the file if the endnote references have changed.

	INPUTS:
	text_path: path to the text files in the project
	file_name: the name of the file being processed eg chapter-1.xhtml
	endnotes: list of endnotes we are checking
	process_info: stores the current note number we are allocating, total changed, etc.

	OUTPUTS:
	endnotes: list of endnotes, these may include changes to source_file and number properties
	process_info: includes incremented endnote number, and adds changes made
	"""

	file_path = os.path.join(text_path, file_name)
	xhtml = gethtml(file_path)
	soup = BeautifulSoup(xhtml, "lxml")
	links = soup.find_all("a")
	needs_rewrite = False
	for link in links:
		epub_type = link.get("epub:type") or ""
		if epub_type == "noteref":
			old_anchor = ""
			href = link.get("href") or ""
			if href:
				old_anchor = extract_anchor(href)
			new_anchor = "note-{:d}".format(process_info.current_number)
			if new_anchor != old_anchor:
				process_info.change_list.append("Changed " + old_anchor + " to " + new_anchor + " in " + file_name)
				process_info.notes_changed += 1
				# update the link in the soup object
				link["href"] = 'endnotes.xhtml#' + new_anchor
				link["id"] = 'noteref-{:d}'.format(process_info.current_number)
				link.string = str(process_info.current_number)
				needs_rewrite = True
			# now try to find this in endnotes
			matches = list(filter(lambda x, old=old_anchor: x.anchor == old, endnotes))
			if not matches:
				raise se.InvalidInputException("Couldn't find endnote with anchor " + old_anchor)
			if len(matches) > 1:
				raise se.InvalidInputException("Duplicate anchors in endnotes file for anchor " + old_anchor)
			# found a single match, which is what we want
			listnote = matches[0]
			listnote.number = process_info.current_number
			listnote.matched = True
			# we don't change the anchor or the back ref just yet
			listnote.source_file = file_name
			process_info.current_number += 1

	# if we need to write back the body text file
	if needs_rewrite:
		new_file = open(file_path, "w")
		new_file.write(format_xhtml(str(soup)))
		new_file.close()

def get_notes(endnotes_soup: BeautifulSoup) -> list:
	"""
	Gets the list of notes in the current endnotes.xhtml file. These objects include the whole
	text of the note.

	INPUTS:
	endnotes_soup: the endnotes.xhtml file as a BS object.

	OUTPUTS:
	a list of endnote objects found in the endnotes.xhtml file.
	"""

	ret_list = []
	ol_tag: BeautifulSoup = endnotes_soup.find("ol")
	items = ol_tag.find_all("li")
	# do something
	for item in items:
		note = ListNote()
		note.contents = []
		for content in item.contents:
			note.contents.append(content)
			if isinstance(content, Tag):
				links = content.find_all("a")
				for link in links:
					epub_type = link.get("epub:type") or ""
					if epub_type == "se:referrer":
						href = link.get("href") or ""
						if href:
							note.back_link = href
		note.anchor = item.get("id") or ""

		ret_list.append(note)
	return ret_list


def recreate(textpath: str, notes_soup: BeautifulSoup, endnotes: list):
	"""
	Rebuilds endnotes.xhtml in the correct (possibly new) order.

	INPUTS:
	textpath: path to text folder in SE project
	notes_soup: BS object of the endnotes.xhtml file
	endnotes: list of endnote objects
	"""

	ol_tag = notes_soup.ol
	ol_tag.clear()
	for endnote in endnotes:
		if endnote.matched:
			li_tag = notes_soup.new_tag("li")
			li_tag["id"] = "note-" + str(endnote.number)
			li_tag["epub:type"] = "endnote"
			for content in endnote.contents:
				if isinstance(content, Tag):
					links = content.find_all("a")
					for link in links:
						epub_type = link.get("epub:type") or ""
						if epub_type == "se:referrer":
							href = link.get("href") or ""
							if href:
								link["href"] = endnote.source_file + "#noteref-" + str(endnote.number)
				li_tag.append(content)
			ol_tag.append(li_tag)
	new_file = open(os.path.join(textpath, "endnotes.xhtml"), "w")
	# new_file.write(format_xhtml(str(notes_soup)))
	new_file.write(str(notes_soup))
	new_file.close()


# don't process these files
EXCLUDE_LIST = ["titlepage.xhtml", "colophon.xhtml", "uncopyright.xhtml", "imprint.xhtml", "halftitle.xhtml", "endnotes.xhtml"]


def generate_endnotes(self) -> str:
	"""
	Entry point for `SeEpub.generate_toc()`.
	"""

	endnotes_filepath = str(self.path / "src" / "epub" / "text" / "endnotes.xhtml")
	text_path = str(self.path / "src" / "epub" / "text")
	xhtml = gethtml(endnotes_filepath)
	notes_soup = BeautifulSoup(xhtml, "html.parser")
	endnotes = get_notes(notes_soup)

	file_list = self.get_content_files()

	processed = 0
	report = ""
	process_info = ProcessInfo()

	for file_name in file_list:
		if file_name in EXCLUDE_LIST:
			continue
		processed += 1
		process_file(text_path, file_name, endnotes, process_info)
	if processed == 0:
		report += "No files processed. Did you update manifest and order the spine?" + "\n"
	else:
		report += "Found {:d} endnotes.".format(process_info.current_number - 1) + "\n"
		if process_info.notes_changed > 0:
			# now we need to recreate the endnotes file
			recreate(text_path, notes_soup, endnotes)
			report += "Changed {:d} endnotes".format(process_info.notes_changed) + "\n"
			report += "endnotes.xhtml recreated" + "\n"
		else:
			report += "No changes made"
	return report
