#!/usr/bin/env python3
"""
This module contains the make-toc function which tries to create a
valid table of contents file for SE projects.

Strictly speaking, the generate_toc() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put in a separate file.
"""

from enum import Enum
from pathlib import Path
from typing import Tuple, List
import regex
from lxml import etree
import se
import se.formatting
import se.easy_xml
from se.easy_xml import EasyXmlTree, EasyXmlElement


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
	title_is_ordinal = False
	lang = ""
	id = ""
	epub_type = ""
	division = BookDivision.NONE
	place = Position.FRONT

	@property
	def toc_link(self) -> str:
		"""
		Generates the hyperlink for the ToC item.

		INPUTS:
		None

		OUTPUTS:
		the linking tag line eg <a href=... depending on the data found.
		"""

		out_string = ""
		if not self.title:
			raise se.InvalidInputException(f"Couldn't find title in: [path][link=file://{self.file_link}]{self.file_link}[/][/].")

		if self.subtitle and self.lang:
			# test for a foreign language subtitle, and adjust accordingly
			self.subtitle = f"<span xml:lang=\"{self.lang}\">{self.subtitle}</span>"

		# If the title is entirely Roman numeral, put epub:type within <a>.
		if regex.search(r"^<span epub:type=\"z3998:roman\">[IVXLC]+<\/span>$", self.title):
			# title is a pure roman number
			if self.subtitle == "":  # put the roman flag inside the <a> tag
				out_string += f"<a href=\"text/{self.file_link}\" epub:type=\"z3998:roman\">{self.roman}</a>\n"
			else:
				out_string += f"<a href=\"text/{self.file_link}\"><span epub:type=\"z3998:roman\">{self.roman}</span>: {self.subtitle}</a>\n"
		else:
			# title has text other than a roman numeral
			if self.subtitle != "" and (self.title_is_ordinal or (self.division in [BookDivision.PART, BookDivision.DIVISION, BookDivision.VOLUME])):
				# Use the subtitle only if we're a Part or Division or Volume or if title was an ordinal
				out_string += f"<a href=\"text/{self.file_link}\">{self.title}"

				# Don't append a colon if the ordinal already ends in punctuation, for example  `1.` or `(a)`
				if not regex.search(r"\p{Punctuation}$", self.title):
					out_string += ":"

				out_string += f" {self.subtitle}</a>\n"
			else:
				# test for a foreign language title, and adjust accordingly
				if self.lang:
					out_string += f"<a href=\"text/{self.file_link}\" xml:lang=\"{self.lang}\">{self.title}</a>\n"
				else:
					out_string += f"<a href=\"text/{self.file_link}\">{self.title}</a>\n"

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
			out_string = f"<li>\n<a href=\"text/{self.file_link}\" epub:type=\"frontmatter {self.epub_type}\">{self.title}</a>\n</li>\n"
		if self.place == Position.BODY:
			out_string = f"<li>\n<a href=\"text/{self.file_link}\" epub:type=\"bodymatter z3998:{work_type}\">{work_title}</a>\n</li>\n"
		if self.place == Position.BACK:
			out_string = f"<li>\n<a href=\"text/{self.file_link}\" epub:type=\"backmatter {self.epub_type}\">{self.title}</a>\n</li>\n"

		return out_string

def get_place(node: EasyXmlElement) -> Position:
	"""
	Returns place of file in ebook, eg frontmatter, backmatter, etc.

	INPUTS:
	node: EasyXmlElement representation of the file

	OUTPUTS:
	a Position enum value indicating the place in the book
	"""

	epub_type = node.get_attr("epub:type")
	if not epub_type:
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

def add_landmark(dom: EasyXmlTree, textf: str, landmarks: list):
	"""
	Adds an item to landmark list with appropriate details.

	INPUTS:
	dom: EasyXmlTree representation of the file we are indexing in ToC
	textf: path to the file
	landmarks: the list of landmark items we are building

	OUTPUTS:
	None
	"""

	epub_type = ""
	sections = dom.xpath("//body/*[name() = 'section' or name() = 'article']")
	if not sections:
		raise se.InvalidInputException("Couldn't locate first section")
	epub_type = sections[0].get_attr("epub:type")
	bodys = dom.xpath("//body")
	if not bodys:
		raise se.InvalidInputException("Couldn't locate body")

	if not epub_type:  # some productions don't have an epub:type in outermost section, so get it from body tag
		epub_type = bodys[0].get_attr("epub:type")

	if epub_type in ["frontmatter", "bodymatter", "backmatter"]:
		return  # if epub_type is ONLY frontmatter, bodymatter, backmatter, we don't want this as a landmark

	landmark = TocItem()
	if epub_type:
		landmark.epub_type = epub_type
		landmark.file_link = textf
		landmark.place = get_place(bodys[0])
		if epub_type == "halftitlepage":
			landmark.title = "Half Title"
		else:
			landmark.title = dom.xpath("//head/title/text()", True)  # Use the page title as the landmark entry title.
			if landmark.title is None:
				# This is a bit desperate, use this only if there's no proper <title> tag in file.
				landmark.title = landmark.epub_type.capitalize()
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

	# we don't want frontmatter items to be included once we've started the body items
	started_body = False
	for item in landmarks_list:
		if item.place == Position.BODY:
			started_body = True
		if started_body and item.place == Position.FRONT:
			item.place = Position.NONE

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
			out_string += this_item.toc_link
			out_string += "</li>\n"

		if next_item.level > this_item.level:  # PARENT, start a new ol list
			out_string += "<li>\n"
			out_string += this_item.toc_link
			out_string += "<ol>\n"
			unclosed_ol += 1

		if next_item.level < this_item.level:  # LAST CHILD, close off the list
			out_string += "<li>\n"
			out_string += this_item.toc_link
			out_string += "</li>\n"  # Close off this item.
			torepeat = this_item.level - next_item.level
			while torepeat and unclosed_ol:  # neither can go below zero
				# We need to repeat a few times as may be jumping back from eg h5 to h2
				out_string += "</ol>\n"  # End of embedded list.
				out_string += "</li>\n"  # End of parent item.
				unclosed_ol -= 1
				torepeat -= 1
	return out_string



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

	try:
		with open(toc_path) as file:
			toc_dom = se.easy_xml.EasyXhtmlTree(file.read())
	except Exception as ex:
		raise se.InvalidInputException(f"Existing ToC not found. Exception: {ex}")

	# There should be exactly two nav sections.
	navs = toc_dom.xpath("//nav")

	if len(navs) < 2:
		raise se.InvalidInputException("Existing ToC has too few nav sections.")

	# now remove and then re-add the ol sections to clear them
	for nav in navs:
		ols = nav.xpath("./ol")  # just want the immediate ol children
		for ol_item in ols:
			ol_item.remove()

	# this is ugly and stupid, but I can't figure out an easier way to do it
	item_ol = EasyXmlElement(etree.Element("ol"), toc_dom.namespaces)
	item_ol.lxml_element.text = "TOC_ITEMS"
	navs[0].append(item_ol)
	landmark_ol = EasyXmlElement(etree.Element("ol"), toc_dom.namespaces)
	landmark_ol.lxml_element.text = "LANDMARK_ITEMS"
	navs[1].append(landmark_ol)
	xhtml = toc_dom.to_string()
	xhtml = xhtml.replace("TOC_ITEMS", process_items(item_list))
	xhtml = xhtml.replace("LANDMARK_ITEMS", process_landmarks(landmark_list, work_type, work_title))

	return se.formatting.format_xhtml(xhtml)

def get_parent_id(hchild: EasyXmlElement) -> str:
	"""
	Climbs up the document tree looking for parent id in a <section> tag.

	INPUTS:
	hchild: a heading tag for which we want to find the parent id

	OUTPUTS:
	the id of the parent section
	"""

	# position() = 1 gets the nearest ancestor
	parents = hchild.xpath("./ancestor::*[name() = 'section' or name() = 'article'][@id][position() = 1]")

	if parents:
		return parents[0].get_attr("id")

	return ""

def extract_strings(node: EasyXmlElement) -> str:
	"""
	Returns string representation of a tag, ignoring linefeeds

	INPUTS:
	node: a tag as xpath node

	OUTPUTS:
	just the string contents of the tag
	"""

	out_string = node.inner_xml()
	out_string = strip_notes(out_string)
	return regex.sub(r"[\n\t]", "", out_string)

def process_headings(dom: EasyXmlTree, textf: str, toc_list: list, nest_under_halftitle: bool, single_file: bool):
	"""
	Find headings in current file and extract title data
	into items added to toc_list.

	INPUTS:
	dom: an EasyXmlTree representation of the current file
	textf: the path to the file
	toc_list: the list of ToC items we are building
	nest_under_halftitle: does this item need to be nested?
	single_file: is there only a single content item in the production?

	OUTPUTS:
	None
	"""

	body = dom.xpath("//body")
	place = Position.NONE
	if body:
		place = get_place(body[0])
	else:
		raise se.InvalidInputException("Couldn't locate body node")

	is_toplevel = True

	# Find all the hgroups and h1, h2 etc headings.
	heads = dom.xpath("//hgroup | //h1 | //h2 | //h3 | //h4 | //h5 | //h6")

	# special treatment where we can't find any header or hgroups
	if not heads:  # May be a dedication or an epigraph, with no heading tag.
		if single_file and nest_under_halftitle:
			# There's a halftitle, but only this one content file with no subsections,
			# so leave out of ToC because the Toc will link to the halftitle.
			return
		special_item = TocItem()
		# Need to determine level depth.
		# We don't have a heading, so get first content item
		content_item = dom.xpath("//p | //header | //img")
		if content_item is not None:
			parents = content_item[0].xpath("./ancestor::*[name() = 'section' or name() = 'article']")
			special_item.level = len(parents)
			if special_item.level == 0:
				special_item.level = 1
		if nest_under_halftitle:
			special_item.level += 1
		special_item.title = dom.xpath("//head/title/text()", True)  # Use the page title as the ToC entry title.
		if special_item.title is None:
			special_item.title = "NO TITLE"
		special_item.file_link = textf
		toc_list.append(special_item)
		return

	for heading in heads:
		# don't process a heading separately if it's within a hgroup
		if heading.parent.tag == "hgroup":
			continue  # skip it

		if place == Position.BODY:
			toc_item = process_a_heading(heading, textf, is_toplevel, single_file)
		else:
			# if it's not a bodymatter item we don't care about whether it's single_file
			toc_item = process_a_heading(heading, textf, is_toplevel, False)

		# Tricky check to see if we want to include the item because there's a halftitle
		# but only a single content file with no subsidiary sections.
		if is_toplevel and single_file and nest_under_halftitle and len(heads) == 1:
			continue
		if nest_under_halftitle:
			toc_item.level += 1
		is_toplevel = False
		toc_list.append(toc_item)

def process_a_heading(node: EasyXmlElement, textf: str, is_toplevel: bool, single_file: bool) -> TocItem:
	"""
	Generate and return a single TocItem from this heading.

	INPUTS:
	node: an EasyXml node representing a heading
	text: the path to the file
	is_toplevel: is this heading at the top-most level in the file?
	single_file: is there only one content file in the production (like some Poetry volumes)?

	OUTPUTS:
	a qualified ToCItem object
	"""

	toc_item = TocItem()
	parent_sections = node.xpath("./ancestor::*[name() = 'section' or name() = 'article']")
	if parent_sections:
		toc_item.level = len(parent_sections)
	else:
		toc_item.level = 1

	toc_item.division = get_book_division(node)

	# is_top_level stops the first heading in a file getting an anchor id, we don't generally want that.
	# The exceptions are things like poems within a single-file volume.
	toc_item.id = get_parent_id(node)  # pylint: disable=invalid-name
	if toc_item.id == "":
		toc_item.file_link = textf
	else:
		if not is_toplevel:
			toc_item.file_link = f"{textf}#{toc_item.id}"
		elif single_file:  # It IS the first heading in the file, but there's only a single content file?
			toc_item.file_link = f"{textf}#{toc_item.id}"
		else:
			toc_item.file_link = textf

	toc_item.lang = node.get_attr("xml:lang")

	epub_type = node.get_attr("epub:type")

	# it may be an empty header tag eg <h3>, so we pass its parent rather than itself to evaluate the parent's descendants
	if not epub_type and node.tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
		parent = node.parent
		if parent:
			evaluate_descendants(parent, toc_item)
		else:  # shouldn't ever happen, but... just in case, raise an error
			raise se.InvalidInputException(f"Header without parent in file: [path][link=file://{textf}]{textf}[/][/].")
		return toc_item
	if epub_type:
		# A heading may include z3998:roman directly,
		# eg <h5 epub:type="title z3998:roman">II</h5>.
		if "z3998:roman" in epub_type:
			toc_item.roman = extract_strings(node)
			toc_item.title = f"<span epub:type=\"z3998:roman\">{toc_item.roman}</span>"
			return toc_item
		if "ordinal" in epub_type:  # but not a roman numeral (eg in Nietzche's Beyond Good and Evil)
			toc_item.title = extract_strings(node)
			toc_item.title_is_ordinal = True
			return toc_item
		# may be the halftitle page with a subtitle, so we need to burrow down
		if ("fulltitle" in epub_type) and (node.tag == "hgroup"):
			evaluate_descendants(node, toc_item)
			return toc_item
		# or it may be a straightforward one-level title eg: <h2 epub:type="title">Imprint</h2>
		if "title" in epub_type:
			toc_item.title = extract_strings(node)
			return toc_item

	# otherwise, burrow down into its structure to get the info
	evaluate_descendants(node, toc_item)

	return toc_item


def get_child_strings(node: EasyXmlElement) -> str:
	"""
	Get child strings
	"""

	children = node.xpath("*")
	child_strs = ""
	for child in children:
		child_strs += child.to_string() + "\n"
	return child_strs


def evaluate_descendants(node: EasyXmlElement, toc_item):
	"""
	Burrow down into a hgroup structure to qualify the ToC item

	INPUTS:
	node: EasyXmlElement object representing a hgroup

	OUTPUTS:
	toc_item: qualified ToC item
	"""
	children = node.xpath("./h1 | ./h2 | ./h3 | ./h4 | ./h5 | ./h6")
	for child in children:  # we expect these to be h1, h2, h3, h4 etc
		if not toc_item.lang:
			toc_item.lang = child.get_attr("xml:lang")
		epub_type = child.get_attr("epub:type")
		if not epub_type:
			# should be a label/ordinal grouping
			child_strings = get_child_strings(child)
			if "label" in child_strings and "ordinal" in child_strings:  # quick test
				toc_item.title_is_ordinal = True
				# strip label
				child_strings = regex.sub(r"<span epub:type=\"label\">(.*?)</span>", " \\1 ", child_strings)
				# remove ordinal if it's by itself in a span
				child_strings = regex.sub(r"<span epub:type=\"ordinal\">(.*?)</span>", " \\1 ", child_strings)
				# remove ordinal if it's joined with a roman (which we want to keep)
				child_strings = regex.sub(r"\bordinal\b", "", child_strings)
				# remove extra spaces
				child_strings = regex.sub(r"[ ]{2,}", " ", child_strings)
				toc_item.title = child_strings.strip()
			continue  # skip the following
		if "z3998:roman" in epub_type:
			toc_item.roman = extract_strings(child)
			if not toc_item.title:
				toc_item.title = f"<span epub:type=\"z3998:roman\">{toc_item.roman}</span>"
		elif "ordinal" in epub_type:  # but not a roman numeral or a labelled item, cases caught caught above
			if not toc_item.title:
				toc_item.title = extract_strings(child)
				toc_item.title_is_ordinal = True
		if "subtitle" in epub_type:
			toc_item.subtitle = extract_strings(child)
		else:
			if "title" in epub_type:  # this allows for 'fulltitle' to work here, too
				if toc_item.title or toc_item.roman or toc_item.title_is_ordinal:  # if title already filled, must be a subtitle
					toc_item.subtitle = extract_strings(child)
				else:
					toc_item.title = extract_strings(child)
		if toc_item.title and toc_item.subtitle:  # then we're done
			return toc_item
	return toc_item

def get_book_division(node: EasyXmlElement) -> BookDivision:
	"""
	Determine the kind of book division. At present only Part and Division
	are important; but others stored for possible future logic.

	INPUTS:
	tag: an EasyXml node representing a tag

	OUTPUTS:
	a BookDivision enum value representing the kind of division
	"""

	parent_sections = node.xpath("./ancestor::*[name() = 'section' or name() = 'article']")

	if not parent_sections:
		parent_sections = node.xpath("./ancestor::body")

	if not parent_sections:  # couldn't find a parent, so throw an error
		raise se.InvalidInputException

	section_epub_type = parent_sections[-1].get_attr("epub:type")
	retval = BookDivision.NONE
	if not section_epub_type:
		return retval

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
	if "article" in parent_sections[-1].tag:
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

	return regex.sub(r'<a[^>]*?epub:type="noteref"[^>]*?>.*?<\/a>', "", text)

def process_all_content(file_list: list, text_path: str) -> Tuple[list, list]:
	"""
	Analyze the whole content of the project, build and return lists
	if toc_items and landmarks.

	INPUTS:
	file_list: a list of all content files
	text_path: the path to the contents folder (src/epub/text)

	OUTPUTS:
	a tuple containing the list of Toc items and the list of landmark items
	"""

	toc_list: List[TocItem] = []
	landmarks: List[TocItem] = []

	# We make two passes through the work, because we need to know
	# how many bodymatter items there are. So we do landmarks first.
	for textf in file_list:
		file_path = Path(text_path) / textf
		try:
			with open(file_path) as file:
				dom = se.easy_xml.EasyXhtmlTree(file.read())
		except Exception as ex:
			raise se.InvalidFileException(f"Couldn’t open file: [path][link=file://{file_path}]{file_path}[/][/].") from ex

		add_landmark(dom, textf, landmarks)

	# Now we test to see if there is only one body item
	body_items = [item for item in landmarks if item.place == Position.BODY]
	single_file = (len(body_items) == 1)

	nest_under_halftitle = False
	place = Position.NONE
	for textf in file_list:
		with open(Path(text_path) / textf, "r", encoding="utf-8") as file:
			dom = se.easy_xml.EasyXhtmlTree(file.read())
		body = dom.xpath("//body")
		if body:
			place = get_place(body[0])
		else:
			raise se.InvalidInputException("Couldn't locate body node")
		if place == Position.BACK:
			nest_under_halftitle = False
		process_headings(dom, textf, toc_list, nest_under_halftitle, single_file)
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
