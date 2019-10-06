#!/usr/bin/env python3
"""
This module contains the renumber-endnotes function which tries to create a
valid table of contents file for SE projects.

Strictly speaking, the renumber_endnotes() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put in a separate file.
"""

import os
from bs4 import BeautifulSoup, Tag
import se
from se.formatting import format_xhtml
from se.se_epub_generate_toc import get_content_files

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
	reads an xhtml file and returns the text
	:param file_path: path to the xhtml file to process
	:return: text of xhtml file
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
	Extracts the anchor from a URL
	:param href: should be like: "../text/endnotes.xhtml#note-1"
	:return: just the part after the hash, eg "note-1"
	"""
	hash_position = href.find("#") + 1  # we want the characters AFTER the hash
	if hash_position > 0:
		return href[hash_position:]
	else:
		return ""

def process_file(text_path: str, file_name: str, endnotes: list, process_info: ProcessInfo):
	"""
	Reads a content file, locates and processes the endnotes,
	accumulating info on them in a global list, and returns the next note number
	:param text_path: path to the text files in the project
	:param file_name: the name of the file being processed eg chapter-1.xhtml
	:param endnotes: list of notes we are building
	:param process_info: stores the current note number we are allocating, total changed, etc.
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
			matches = list(filter(lambda x: x.anchor == old_anchor, endnotes))
			if len(matches) == 0:
				raise se.InvalidInputException("Couldn't find endnote with anchor " + old_anchor)
			elif len(matches) > 1:
				raise se.InvalidInputException("Duplicate anchors in endnotes file for anchor " + old_anchor)
			else:  # found a single match, which is what we want
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
	gets the list of notes in the current endnotes.xhtml file
	:param endnotes_soup: the endnotes.xhtml file as a BS object
	:return: list of note objects
	"""
	ret_list = []
	ol: BeautifulSoup = endnotes_soup.find("ol")
	items = ol.find_all("li")
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
	rebuilds endnotes.xhtml in the correct (possibly new) order
	:param textpath: path to text folder in SE project
	:param notes_soup:
	:param endnotes:
	:return:
	"""
	ol = notes_soup.ol
	ol.clear()
	for endnote in endnotes:
		if endnote.matched:
			li = notes_soup.new_tag("li")
			li["id"] = "note-" + str(endnote.number)
			li["epub:type"] = "endnote"
			for content in endnote.contents:
				if isinstance(content, Tag):
					links = content.find_all("a")
					for link in links:
						epub_type = link.get("epub:type") or ""
						if epub_type == "se:referrer":
							href = link.get("href") or ""
							if href:
								link["href"] = endnote.source_file + "#noteref-" + str(endnote.number)
				li.append(content)
			ol.append(li)
	new_file = open(os.path.join(textpath, "endnotes.xhtml"), "w")
	# new_file.write(format_xhtml(str(notes_soup)))
	new_file.write(str(notes_soup))
	new_file.close()


# don't process these files
exclude_list = ["titlepage.xhtml", "colophon.xhtml", "uncopyright.xhtml", "imprint.xhtml", "halftitle.xhtml", "endnotes.xhtml"]


def generate_endnotes(self) -> str:
	"""
	Entry point for `SeEpub.generate_toc()`.
	"""
	verbose = False  # TODO: pass this in as an argument
	endnotes_filepath = str(self.path / "src" / "epub" / "text" / "endnotes.xhtml")
	text_path = str(self.path / "src" / "epub" / "text")
	xhtml = gethtml(endnotes_filepath)
	notes_soup = BeautifulSoup(xhtml, "html.parser")
	endnotes = get_notes(notes_soup)

	xhtml = gethtml(self.path / "src" / "epub" / "content.opf")
	soup = BeautifulSoup(xhtml, "lxml")
	file_list = get_content_files(soup)

	processed = 0
	report = ""
	process_info = ProcessInfo()

	for file_name in file_list:
		if file_name in exclude_list:
			continue
		processed += 1
		process_file(text_path, file_name, endnotes, process_info)
	if processed == 0:
		report += "No files processed. Did you update manifest and order the spine?" + "\n"
	else:
		report += "Found {:d} endnotes.".format(process_info.current_number - 1) + "\n"
		if process_info.notes_changed > 0:
			if verbose:
				for line in process_info.change_list:
					report += line + "\n"
			# now we need to recreate the endnotes file
			recreate(text_path, notes_soup, endnotes)
			report += "Changed {:d} endnotes".format(process_info.notes_changed) + "\n"
			report += "endnotes.xhtml recreated" + "\n"
		else:
			report += "No changes made"
	return report
