#!/usr/bin/env python3
"""
This module contains the make-toc function which tries to create a
valid table of contents file for SE projects.

Strictly speaking, the generate_toc() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put in a separate file.
"""

from pathlib import Path
from enum import Enum
import regex
from bs4 import BeautifulSoup, Tag
import se
from se.formatting import format_xhtml


class BookDivision(Enum):
	"""
	Enum to indicate the division of a particular ToC item.
	"""

	NONE = 0
	ARTICLE = 1
	SUBCHAPTER = 2
	CHAPTER = 3
	DIVISION = 4
	PART = 5
	VOLUME = 6

class Position(Enum):
	"""
	Enum to indicate whether a landmark is frontmatter, bodymatter or backmatter.
	"""

	NONE = 0
	FRONT = 1
	BODY = 2
	BACK = 3

class TocItem:
	"""
	Small class to hold data on each table of contents item
	found in the project.
	"""

	# pylint: disable=too-many-instance-attributes

	file_link = ""
	level = 0
	roman = ""
	title = ""
	subtitle = ""
	id = ""
	epub_type = ""
	division = BookDivision.NONE
	place: Position = Position.FRONT

	def toc_link(self) -> str:
		"""
		Generates the hyperlink for the ToC item.

		INPUTS:
		None

		OUTPUTS:
		the linking tag line eg <a href=... depending on the data found.
		"""

		out_string = ""
		if self.title is None:
			return ""

		# If the title is entirely Roman numeral, put epub:type within <a>.
		if regex.search(r"^<span epub:type=\"z3998:roman\">[IVXLC]{1,10}<\/span>$", self.title):
			if self.subtitle == "":
				out_string += "<a href=\"text/{}\" epub:type=\"z3998:roman\">{}</a>\n".format(self.file_link, self.roman)
			else:
				out_string += "<a href=\"text/{}\">{}: {}</a>\n".format(self.file_link, self.title, self.subtitle)
		else:  # Use the subtitle only if we're a Part or Division or Volume
			if self.subtitle != "" and (self.division in [BookDivision.PART, BookDivision.DIVISION, BookDivision.VOLUME]):
				out_string += "<a href=\"text/{}\">{}: {}</a>\n".format(self.file_link, self.title, self.subtitle)
			else:
				out_string += "<a href=\"text/{}\">{}</a>\n".format(self.file_link, self.title)

		return out_string

	def landmark_link(self, work_type: str = "fiction", work_title: str = "WORK_TITLE"):
		"""
		Generates the landmark item (including list item tags) for the ToC item

		INPUTS:
		work_type: ("fiction" or "non-fiction")
		work_title: the title of the book, eg "Don Quixote"

		OUTPUTS:
		the linking string to be included in landmarks section.
		"""

		out_string = ""
		if self.place == Position.FRONT:
			out_string = "<li>\n<a href=\"text/{}\" epub:type=\"frontmatter {}\">{}</a>\n</li>\n".format(self.file_link, self.epub_type, self.title)
		if self.place == Position.BODY:
			out_string = "<li>\n<a href=\"text/{}\" epub:type=\"bodymatter z3998:{}\">{}</a>\n</li>\n".format(self.file_link, work_type, work_title)
		if self.place == Position.BACK:
			out_string = "<li>\n<a href=\"text/{}\" epub:type=\"backmatter {}\">{}</a>\n</li>\n".format(self.file_link, self.epub_type, self.title)

		return out_string

def get_epub_type(soup: BeautifulSoup) -> str:
	"""
	Retrieve the epub_type of this file to see if it's a landmark item.

	INPUTS:
	soup: BeautifulSoup representation of the file

	OUTPUTS:
	the epub_type, eg: "dedication", "epigraph", etc.
	"""

	# Try for a heading.
	first_head = soup.find(["h1", "h2", "h3", "h4", "h5", "h6"])
	if first_head is not None:
		parent = first_head.find_parent(["section", "article"])
	else:  # No heading found so go hunting for some other content.
		paragraph = soup.find(["p", "header", "img"])  # We look for the first such item.
		if paragraph is not None:
			parent = paragraph.find_parent(["section", "article"])
		else:
			return ""

	if parent is None:
		parent = soup.find("body")

	try:
		return parent["epub:type"]
	except KeyError:
		# Immediate parent has no epub:type, try for higher up.
		body = soup.find("body")
		return body.get("epub:type") or ""


def get_place(soup: BeautifulSoup) -> Position:
	"""
	Returns place of file in ebook, eg frontmatter, backmatter, etc.

	INPUTS:
	soup: BeautifulSoup representation of the file

	OUTPUTS:
	a Position enum value indicating the place in the book
	"""

	epub_type = soup.body.get("epub:type") or ""
	if epub_type == "":
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

	INPUTS:
	soup: BeautifulSoup representation of the file we are indexing in ToC
	textf: path to the file
	landmarks: the list of landmark items we are building

	OUTPUTS:
	None
	"""

	epub_type = get_epub_type(soup)
	landmark = TocItem()
	if epub_type != "":
		landmark.epub_type = epub_type
		landmark.file_link = textf
		landmark.place = get_place(soup)
		title_tag = soup.find("title")
		if title_tag is not None:
			landmark.title = title_tag.string
			if landmark.title is None:
				# This is a bit desperate, use this only if there's no proper <title> tag in file.
				landmark.title = landmark.epub_type.capitalize
		else:
			landmark.title = landmark.epub_type.capitalize
		landmarks.append(landmark)

def process_landmarks(landmarks_list: list, work_type: str, work_title: str):
	"""
	Runs through all found landmark items and writes them to the toc file.

	INPUTS:
	landmarks_list: the completed list of landmark items
	work_type: "fiction" or "non-fiction"
	work_title: the title of the book

	OUTPUTS:
	None
	"""

	front_items = [item for item in landmarks_list if item.place == Position.FRONT]
	body_items = [item for item in landmarks_list if item.place == Position.BODY]
	back_items = [item for item in landmarks_list if item.place == Position.BACK]

	out_string = ""
	for item in front_items:
		out_string += item.landmark_link()
	if body_items:
		out_string += body_items[0].landmark_link(work_type, work_title)  # Just the first bodymatter item.
	for item in back_items:
		out_string += item.landmark_link()
	return out_string

def process_items(item_list: list) -> str:
	"""
	Runs through all found toc items and returns them as a string.

	INPUTS:
	item_list: list of ToC items

	OUTPUTS:
	A string representing (possibly nested) html lists of the structure of the ToC
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
			out_string += this_item.toc_link()
			out_string += "</li>\n"

		if next_item.level > this_item.level:  # PARENT
			out_string += "<li>\n"
			out_string += this_item.toc_link()
			out_string += "<ol>\n"
			unclosed_ol += 1

		if next_item.level < this_item.level:  # LAST CHILD
			out_string += "<li>\n"
			out_string += this_item.toc_link()
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

	INPUTS:
	toc_path: the path to the existing ToC file

	OUTPUTS:
	A BeautifulSoup object representing the current ToC file
	"""

	with open(toc_path, "r", encoding="utf-8") as file:
		return BeautifulSoup(file.read(), "html.parser")

def output_toc(item_list: list, landmark_list, toc_path: str, work_type: str, work_title: str) -> str:
	"""
	Outputs the contructed ToC based on the lists of items and landmarks found,
	either to stdout or overwriting the existing ToC file

	INPUTS:
	item_list: list of ToC items (the first part of the ToC)
	landmark_list: list of landmark items (the second part of the ToC)
	work_type: "fiction" or "non-fiction"
	work_title: the title of the book

	OUTPUTS:
	a html string representing the new ToC
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

	INPUTS:
	hchild: a heading tag for which we want to find the parent id

	OUTPUTS:
	the id of the parent section
	"""

	parent = hchild.find_parent(["section", "article"])
	if parent is None:
		return ""
	return parent.get("id") or ""

def extract_strings(tag: Tag) -> str:
	"""
	Returns string representation of a tag, ignoring linefeeds

	INPUTS:
	tag: a BeautifulSoup tag

	OUTPUTS:
	just the string contents of the tag
	"""

	out_string = ""
	for child in tag.contents:
		out_string += str(child)
	#  Now strip out any linefeeds or tabs we may have encountered.
	return regex.sub(r"(\n|\t)", "", out_string)

def process_headings(soup: BeautifulSoup, textf: str, toc_list: list, nest_under_halftitle: bool, single_file: bool):
	"""
	Find headings in current file and extract title data
	into items added to toc_list.

	INPUTS:
	soup: a BeautifulSoup representation of the current file
	textf: the path to the file
	toc_list: the list of ToC items we are building
	nest_under_halftitle: does this item need to be nested?
	single_file: is there only a single content item in the production?

	OUTPUTS:
	None
	"""

	# Find all the h1, h2 etc headings.
	heads = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])

	if not heads:  # May be a dedication or an epigraph, with no heading tag.
		if single_file and nest_under_halftitle:
			# There's a halftitle, but only this one content file with no subsections,
			# so leave out of ToC.
			return
		special_item = TocItem()
		# Need to determine level depth.
		# We don't have a heading, so get first content item
		content_item = soup.find(["p", "header", "img"])
		if content_item is not None:
			parents = content_item.find_parents(["section", "article"])
			special_item.level = len(parents)
			if special_item.level == 0:
				special_item.level = 1
		if nest_under_halftitle:
			special_item.level += 1
		title_tag = soup.find("title")  # Use the page title as the ToC entry title.
		if title_tag is not None:
			special_item.title = title_tag.string
			if special_item.title is None:
				special_item.title = "NO TITLE"
		else:  # no <title> tag or content
			special_item.title = "NO TITLE"
		special_item.file_link = textf
		toc_list.append(special_item)
		return

	place = get_place(soup)
	is_toplevel = True
	for heading in heads:
		if place == Position.BODY and single_file:
			toc_item = process_heading(heading, textf, is_toplevel, True)
		else:
			toc_item = process_heading(heading, textf, is_toplevel, False)
		# Tricky check to see if we want to include the item because there's a halftitle
		# but only a single content file with no subsidiary sections.
		if is_toplevel and single_file and nest_under_halftitle and len(heads) == 1:
			continue
		if nest_under_halftitle:
			toc_item.level += 1
		is_toplevel = False
		toc_list.append(toc_item)

def process_heading(heading: BeautifulSoup, textf: str, is_toplevel: bool, single_file: bool) -> TocItem:
	"""
	Generate and return a TocItem from this heading.

	INPUTS:
	heading: a BeautifuSoup tag representing a heading tag
	text: the path to the file
	is_toplevel: is this heading at the top-most level in the file?
	single_file: is there only one content file in the production (like some Poetry volumes)?

	OUTPUTS:
	a qualified ToCItem object
	"""

	toc_item = TocItem()
	parent_sections = heading.find_parents(["section", "article"])
	if parent_sections:
		toc_item.level = len(parent_sections)
	else:
		toc_item.level = 1
	toc_item.division = get_book_division(heading)

	# This stops the first heading in a file getting an anchor id, we don't generally want that.
	# The exceptions are things like poems within a single-file volume.
	toc_item.id = get_parent_id(heading) # pylint: disable=invalid-name
	if toc_item.id == "":
		toc_item.file_link = textf
	else:
		if not is_toplevel:
			toc_item.file_link = textf + "#" + toc_item.id
		elif single_file:  # It IS the first heading in the file, but there's only a single content file?
			toc_item.file_link = textf + "#" + toc_item.id
		else:
			toc_item.file_link = textf

	# A heading may include z3998:roman directly,
	# eg <h5 epub:type="title z3998:roman">II</h5>.
	attribs = heading.get("epub:type") or ""

	if "z3998:roman" in attribs:
		toc_item.roman = extract_strings(heading)
		toc_item.title = "<span epub:type=\"z3998:roman\">" + toc_item.roman + "</span>"
		return toc_item

	process_heading_contents(heading, toc_item)

	return toc_item

def get_book_division(tag: BeautifulSoup) -> BookDivision:
	"""
	Determine the kind of book division. At present only Part and Division
	are important; but others stored for possible future logic.

	INPUTS:
	tag: a BeautifulSoup tag object

	OUTPUTS:
	a BookDivision enum value representing the kind of division
	"""

	parent_section = tag.find_parents(["section", "article"])

	if not parent_section:
		parent_section = tag.find_parents("body")

	section_epub_type = parent_section[0].get("epub:type") or ""

	retval = BookDivision.NONE

	if "part" in section_epub_type:
		retval = BookDivision.PART
	if "division" in section_epub_type:
		retval = BookDivision.DIVISION
	if ("volume" in section_epub_type) and ("se:short-story" not in section_epub_type):
		retval = BookDivision.VOLUME
	if "subchapter" in section_epub_type:
		retval = BookDivision.SUBCHAPTER
	if "chapter" in section_epub_type:
		retval = BookDivision.CHAPTER
	if "article" in parent_section[0].name:
		retval = BookDivision.ARTICLE

	return retval

def strip_notes(text: str) -> str:
	"""
	Returns html text stripped of noterefs.

	INPUTS:
	text: html which may include noterefs

	OUTPUTS:
	cleaned html string
	"""

	return regex.sub(r'<a .*?epub:type="noteref".*?>.*?<\/a>', "", text)

def process_heading_contents(heading: BeautifulSoup, toc_item: TocItem):
	"""
	Run through each item in the heading contents
	and try to pull out the toc item data.

	INPUTS:
	heading: a BeautifulSoup object representing a heading tag and its contents
	toc_item: a ToC item object to be qualified

	OUTPUTS:
	None
	"""

	accumulator = ""  # We'll use this to build up the title.
	for child in heading.contents:
		if isinstance(child, Tag):
			epub_type = child.get("epub:type") or ""
			if epub_type == "":
				if child.name == "span":  # If it's an otherwise empty <span>, just take contents.
					accumulator += extract_strings(child)
				else:  # If it's a tag without epub:type, such as <abbr>, take whole thing, tags and all.
					accumulator += str(child)
				continue  # Skip following and go to next child.

			if "z3998:roman" in epub_type:
				toc_item.roman = extract_strings(child)
				accumulator += str(child)
			elif "subtitle" in epub_type:
				toc_item.subtitle = extract_strings(child)
			elif "title" in epub_type:
				toc_item.title = extract_strings(child)
			elif "se:" in epub_type:  # Likely to be a semantically tagged italic.
				accumulator += str(child)  # Include the whole thing, tags and all.
			else:
				accumulator += extract_strings(child)
		else:  # This should be a simple NavigableString.
			accumulator += str(child)
	if toc_item.title == "":
		#  Now strip out any linefeeds or tabs we may have encountered.
		toc_item.title = regex.sub(r"(\n|\t)", "", accumulator)

def process_all_content(file_list: list, text_path: str) -> (list, list):
	"""
	Analyze the whole content of the project, build and return lists
	if toc_items and landmarks.

	INPUTS:
	file_list: a list of all content files
	text_path: the path to the contents folder (src/epub/text)

	OUTPUTS:
	a tuple containing the list of Toc items and the list of landmark items
	"""

	toc_list = []
	landmarks = []

	# We make two passes through the work, because we need to know
	# how many bodymatter items there are. So we do landmarks first.
	for textf in file_list:
		with open(Path(text_path) / textf, "r", encoding="utf-8") as file:
			html_text = file.read()
		soup = BeautifulSoup(html_text, "html.parser")
		add_landmark(soup, textf, landmarks)

	# Now we test to see if there is only one body item
	body_items = [item for item in landmarks if item.place == Position.BODY]
	single_file = (len(body_items) == 1)

	nest_under_halftitle = False
	for textf in file_list:
		with open(Path(text_path) / textf, "r", encoding="utf-8") as file:
			html_text = file.read()
		soup = BeautifulSoup(strip_notes(html_text), "html.parser")
		place = get_place(soup)
		if place == Position.BACK:
			nest_under_halftitle = False
		process_headings(soup, textf, toc_list, nest_under_halftitle, single_file)
		if textf == "halftitle.xhtml":
			nest_under_halftitle = True

	# We add this dummy item because outputtoc always needs to look ahead to the next item.
	last_toc = TocItem()
	last_toc.level = 1
	last_toc.title = "dummy"
	toc_list.append(last_toc)

	return landmarks, toc_list

def generate_toc(self) -> str:
	"""
	Entry point for `SeEpub.generate_toc()`.
	"""

	file_list = self.get_content_files()
	work_title = self.get_work_title()
	work_type = self.get_work_type()

	landmarks, toc_list = process_all_content(file_list, self.path / "src" / "epub" / "text")

	return output_toc(toc_list, landmarks, self.path / "src" / "epub" / "toc.xhtml", work_type, work_title)
