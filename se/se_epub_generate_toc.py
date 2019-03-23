#!/usr/bin/env python3
"""
This module contains the make-toc function which tries to create a
valid table of contents file for SE projects.

Strictly speaking, the generate_toc() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put in a separate file.
"""

import os
from enum import Enum
import regex
from bs4 import BeautifulSoup, Tag
import se
from se.formatting import format_xhtml


class Toc_item:
	"""
	Small class to hold data on each table of contents item
	found in the project.
	"""

	file_link = ""
	level = 0
	roman = ""
	title = ""
	subtitle = ""
	id = ""
	epub_type = ""

	def output(self) -> str:
		"""
		The output method just outputs the linking tag line
		eg <a href=... depending on the data found.
		"""

		out_string = ""

		# If the title is entirely Roman
		if regex.search(r"^<span epub:type=\"z3998:roman\">[IVXLC]{1,10}<\/span>$", self.title):
			if self.subtitle == "":
				out_string += "<a href=\"text/{}\" epub:type=\"z3998:roman\">{}</a>\n".format(self.file_link, self.roman)
			else:
				out_string += "<a href=\"text/{}\">{}: {}</a>\n".format(self.file_link, self.title, self.subtitle)
		else:
			out_string += "<a href=\"text/{}\">{}</a>\n".format(self.file_link, self.title)

		return out_string

class Position(Enum):
	"""
	Enum to indicate whether a landmark is frontmatter, bodymatter or backmatter.
	"""

	NONE = 0
	FRONT = 1
	BODY = 2
	BACK = 3

class LandmarkItem:
	"""
	Small class to hold data on landmark items found in the project.
	"""

	title = ""
	file_link = ""
	epub_type = ""
	place: Position = Position.FRONT

	def output(self, work_type: str = "fiction", work_title: str = "WORK_TITLE"):
		"""
		Returns the linking string to be included in landmarks section.
		"""

		out_string = ""
		if self.place == Position.FRONT:
			out_string = "<li>\n<a href=\"text/{}\" epub:type=\"frontmatter {}\">{}</a>\n</li>\n".format(self.file_link, self.epub_type, self.title)
		if self.place == Position.BODY:
			out_string = "<li>\n<a href=\"text/{}\" epub:type=\"bodymatter z3998:{}\">{}</a>\n</li>\n".format(self.file_link, work_type, work_title)
		if self.place == Position.BACK:
			out_string = "<li>\n<a href=\"text/{}\" epub:type=\"backmatter {}\">{}</a>\n</li>\n".format(self.file_link, self.epub_type, self.title)

		return out_string

def get_content_files(opf: BeautifulSoup) -> list:
	"""
	Reads the spine from content.opf to obtain a list of content files, in the order wanted for the ToC.
	"""

	itemrefs = opf.find_all("itemref")
	ret_list = []
	for itemref in itemrefs:
		ret_list.append(itemref["idref"])

	return ret_list

def get_work_title_and_type(opf: BeautifulSoup) -> (str, str):
	"""
	From content.opf, which we assume has been correctly completed,
	pulls out the title and determines if the type is fiction or nonfiction.
	Returns this information as a tuple.
	"""

	# First, set up the defaults if we can"t find the info.
	work_type = "fiction"
	work_title = "WORK_TITLE"
	dc_title = opf.find("dc:title")
	if dc_title is not None:
		work_title = dc_title.string
	subjects = opf.find_all("se:subject")
	for subject in subjects:
		if "Nonfiction" in subject:
			work_type = "non-fiction"
			break

	return work_title, work_type

def get_epub_type(soup: BeautifulSoup) -> str:
	"""
	Retrieve the epub_type of this file to see if it"s a landmark item.
	"""

	# Try for a heading.
	first_head = soup.find(["h1", "h2", "h3", "h4", "h5", "h6"])
	if first_head is not None:
		parent = first_head.find_parent(["section", "article"])
	else:  # No heading found so go hunting for some other content.
		paragraph = soup.find(["p", "header", "img"])  # We look for the first such item.
		parent = paragraph.find_parent(["section", "article"])
	try:
		return parent["epub:type"]
	except KeyError:
		return ""

def get_place(soup: BeautifulSoup) -> Position:
	"""
	Returns place of file in ebook, eg frontmatter, backmatter, etc.
	"""

	try:
		epub_type = soup.body["epub:type"]
	except KeyError:
		return Position.NONE

	if "backmatter" in epub_type:
		retval = Position.BACK
	elif "frontmatter" in epub_type:
		retval = Position.FRONT
	elif "bodymatter" in epub_type:
		retval = Position.BODY
	else:
		retval = Position.NONE

	return retval

def add_landmark(soup: BeautifulSoup, textf: str, landmarks: list):
	"""
	Adds an item to landmark list with appropriate details.
	"""

	epub_type = get_epub_type(soup)
	landmark = LandmarkItem()
	landmark.title = soup.find("title").string
	if epub_type != "":
		landmark.epub_type = epub_type
		landmark.file_link = textf
		landmark.place = get_place(soup)
		landmarks.append(landmark)

def process_landmarks(landmarks_list: list, work_type: str, work_title: str):
	"""
	Runs through all found landmark items and writes them to the toc file.
	"""

	front_items = [item for item in landmarks_list if item.place == Position.FRONT]
	body_items = [item for item in landmarks_list if item.place == Position.BODY]
	back_items = [item for item in landmarks_list if item.place == Position.BACK]

	out_string = ""
	for item in front_items:
		out_string += item.output()
	if body_items:
		out_string += body_items[0].output(work_type, work_title)  # Just the first bodymatter item.
	for item in back_items:
		out_string += item.output()
	return out_string

def process_items(item_list: list) -> str:
	"""
	Runs through all found toc items and returns them as a string.
	"""

	unclosed_ol = 0  # Keep track of how many ordered lists we open.
	out_string = ""

	# Process all but last item so we can look ahead.
	for index in range(0, len(item_list) - 1):  # Ignore very last item, which is a dummy.
		this_item = item_list[index]
		next_item = item_list[index + 1]

		# Check to see if next item is at same, lower or higher level than us.
		if next_item.level == this_item.level:  # SIMPLE
			out_string += "<li>\n"
			out_string += this_item.output()
			out_string += "</li>\n"

		if next_item.level > this_item.level:  # PARENT
			out_string += "<li>\n"
			out_string += this_item.output()
			out_string += "<ol>\n"
			unclosed_ol += 1

		if next_item.level < this_item.level:  # LAST CHILD
			out_string += "<li>\n"
			out_string += this_item.output()
			out_string += "</li>\n"  # Close off this item.
			torepeat = this_item.level - next_item.level
			if torepeat > 0 and unclosed_ol > 0:
				for _ in range(0, torepeat):  # We need to repeat a few times as may be jumping back from eg h5 to h2
					out_string += "</ol>\n"  # End of embedded list.
					unclosed_ol -= 1
					out_string += "</li>\n"  # End of parent item.
	return out_string

def get_existing_toc(toc_path: str) -> BeautifulSoup:
	"""
	Returns a BeautifulSoup object representing the existing ToC file.
	"""

	with open(toc_path, "r", encoding="utf-8") as file:
		return BeautifulSoup(file.read(), "html.parser")

def output_toc(item_list: list, landmark_list, toc_path: str, work_type: str, work_title: str) -> str:
	"""
	Outputs the contructed ToC based on the lists of items and landmarks found,
	either to stdout or overwriting the existing ToC file
	"""

	if len(item_list) < 2:
		raise se.InvalidInputException("Too few ToC items found.")

	existing_toc: BeautifulSoup = get_existing_toc(toc_path)
	if existing_toc is None:
		raise se.InvalidInputException("Existing ToC not found.")

	# There should be exactly two nav sections.
	navs = existing_toc.find_all("nav")

	if len(navs) < 2:
		raise se.InvalidInputException("Existing ToC has too few nav sections.")

	item_ol = navs[0].find("ol")
	item_ol.clear()
	landmark_ol = navs[1].find("ol")
	landmark_ol.clear()
	new_items = BeautifulSoup(process_items(item_list), "html.parser")
	item_ol.append(new_items)
	new_landmarks = BeautifulSoup(process_landmarks(landmark_list, work_type, work_title), "html.parser")
	landmark_ol.append(new_landmarks)
	return format_xhtml(str(existing_toc))

def get_parent_id(hchild: Tag) -> str:
	"""
	Climbs up the document tree looking for parent id in a <section> tag.
	"""

	parent = hchild.find_parent(["section", "article"])
	if parent is None:
		return ""
	try:
		return parent["id"]
	except KeyError:
		return ""

def extract_strings(tag: Tag) -> str:
	"""
	Returns only the string content of a tag, ignoring noteref and its content.
	"""

	out_string = ""
	for child in tag.contents:
		if child != "\n":
			if isinstance(child, Tag):
				try:
					epub_type = child["epub:type"]
					if child.name == "i":
						# Likely a semantically tagged item, we just want the content.
						out_string += child.string
					if "z3998:roman" in epub_type:
						out_string += str(child)  # We want the whole span and content.
					if "noteref" in epub_type:
						continue  # Ignore the whole tag and its content.
				except KeyError:  # The tag has no epub_type, probably <abbr> or similar.
					out_string += child.string
			else:
				out_string += child  # Must be NavigableString.
	return out_string

def process_headings(soup: BeautifulSoup, textf: str, toc_list: list, nest_under_halftitle: bool):
	"""
	Find headings in current file and extract title data
	into items added to toc_list.
	"""

	# Find all the h1, h2 etc headings.
	heads = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])

	if not heads:  # May be a dedication or an epigraph, with no heading tag.
		special_item = Toc_item()
		sections = soup.find_all("section")  # Count the sections within this file.
		special_item.level = len(sections)
		title_tag = soup.find("title")  # Use the page title as the ToC entry title.
		special_item.title = title_tag.string
		special_item.file_link = textf
		toc_list.append(special_item)
		return

	is_toplevel = True
	for heading in heads:
		toc_item = process_heading(heading, is_toplevel, textf)
		if nest_under_halftitle:
			toc_item.level += 1
		is_toplevel = False
		toc_list.append(toc_item)

def process_heading(heading, is_toplevel, textf) -> Toc_item:
	"""
	Generate and return a Toc_item from this heading.
	"""

	toc_item = Toc_item()
	parent_sections = heading.find_parents(["section", "article"])
	toc_item.level = len(parent_sections)
	# This stops the first heading in a file getting an anchor id, we don't want that.
	if is_toplevel:
		toc_item.id = ""
		toc_item.file_link = textf
	else:
		toc_item.id = get_parent_id(heading)
		if toc_item.id == "":
			toc_item.file_link = textf
		else:
			toc_item.file_link = textf + "#" + toc_item.id
	# A heading may include z3998:roman directly,
	# eg <h5 epub:type="title z3998:roman">II</h5>.
	try:
		attribs = heading["epub:type"]
	except KeyError:
		attribs = ""
	if "z3998:roman" in attribs:
		toc_item.roman = extract_strings(heading)
		toc_item.title = "<span epub:type=\"z3998:roman\">" + toc_item.roman + "</span>"
		return toc_item

	process_heading_contents(heading, toc_item)
	return toc_item

def process_heading_contents(heading, toc_item):
	"""
	Run through each item in the heading contents
	and try to pull out the toc item data.
	"""

	accumulator = ""  # We'll use this to build up the title.
	for child in heading.contents:
		if child != "\n":
			if isinstance(child, Tag):
				try:
					epub_type = child["epub:type"]
				except KeyError:
					accumulator += extract_strings(child)
					continue  # Skip following and go to next child.

				if "z3998:roman" in epub_type:
					toc_item.roman = extract_strings(child)
					accumulator += str(child)
				elif "subtitle" in epub_type:
					toc_item.subtitle = extract_strings(child)
				elif "title" in epub_type:
					toc_item.title = extract_strings(child)
				elif "noteref" in epub_type:
					pass  # Don't process it.
				else:
					toc_item.title = extract_strings(child)
			else:  # This should be a simple NavigableString.
				accumulator += str(child)
	if toc_item.title == "":
		toc_item.title = accumulator

def process_all_content(file_list, text_path) -> (list, list):
	"""
	Analyze the whole content of the project, build and return lists
	if toc_items and landmarks.
	"""

	toc_list = []
	landmarks = []
	nest_under_halftitle = False
	for textf in file_list:
		with open(os.path.join(text_path, textf), "r", encoding="utf-8") as file:
			html_text = file.read()

		soup = BeautifulSoup(html_text, "html.parser")
		place = get_place(soup)
		if place == Position.BACK:
			nest_under_halftitle = False
		process_headings(soup, textf, toc_list, nest_under_halftitle)
		if textf == "halftitle.xhtml":
			nest_under_halftitle = True
		add_landmark(soup, textf, landmarks)

	# We add this dummy item because outputtoc always needs to look ahead to the next item.
	last_toc = Toc_item()
	last_toc.level = 1
	last_toc.title = "dummy"
	toc_list.append(last_toc)
	return landmarks, toc_list

def generate_toc(self) -> str:
	"""
	Entry point for `SeEpub.generate_toc()`.
	"""

	soup = BeautifulSoup(self.metadata_xhtml, "html.parser")
	file_list = get_content_files(soup)
	work_title, work_type = get_work_title_and_type(soup)

	landmarks, toc_list = process_all_content(file_list, os.path.join(self.directory, "src", "epub", "text"))

	return output_toc(toc_list, landmarks, os.path.join(self.directory, "src", "epub", "toc.xhtml"), work_type, work_title)
