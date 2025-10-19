#!/usr/bin/env python3
"""
This module contains the make-toc function which tries to create a valid table of contents file for SE projects.

Strictly speaking, the generate_toc() function should be a class member of SeEpub. But the function is very big and it makes editing easier to put in a separate file.
"""

from enum import Enum
import regex
import roman
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
	Small class to hold data on each table of contents item found in the project.
	"""

	# pylint: disable=too-many-instance-attributes

	file_link = ""
	hidden = False # Did the `<h#>` element have the `hidden` attribute? If so, that means we *must* include it as a subtitle.
	level = 0
	roman = ""
	title = ""
	subtitle = ""
	title_is_ordinal = False
	lang = ""
	toc_id = ""
	epub_type = ""
	division = BookDivision.NONE
	place = Position.FRONT
	has_headers = True

	@property
	def toc_link(self) -> str:
		"""
		Generates the hyperlink for the ToC item.

		INPUTS:
		None.

		OUTPUTS:
		The linking tag line, e.g. `<a href=...` depending on the data found.
		"""

		out_string = ""
		if not self.title:
			raise se.InvalidInputException(f"Couldn’t find title in: [path][link=file://{self.file_link}]{self.file_link}[/][/].")

		if self.subtitle and self.lang:
			# Test for a foreign language subtitle, and adjust accordingly.
			self.subtitle = f"<span xml:lang=\"{self.lang}\">{self.subtitle}</span>"

		# If the title is entirely roman numeral, put epub:type within `<a>`.
		if regex.search(r"^<span epub:type=\"z3998:roman\">[^<]+<\/span>$", self.title):
			# Title is a pure roman numeral.
			if self.subtitle == "":  # Put the roman flag inside the `<a>` element.
				out_string += f"<a href=\"text/{self.file_link}\" epub:type=\"z3998:roman\">{self.roman}</a>\n"
			else:
				out_string += f"<a href=\"text/{self.file_link}\"><span epub:type=\"z3998:roman\">{self.roman}</span>: {self.subtitle}</a>\n"
		else:
			# Title has text other than a roman numeral.
			if self.subtitle != "" and (self.hidden or self.title_is_ordinal or (self.division in [BookDivision.PART, BookDivision.DIVISION, BookDivision.VOLUME])):
				# Use the subtitle only if we're a Part or Division or Volume or if title was an ordinal.
				out_string += f"<a href=\"text/{self.file_link}\">{self.title}"

				# Don't append a colon if the ordinal already ends in punctuation, for example `1.` or `(a)`.
				if not regex.search(r"\p{Punctuation}$", self.title):
					out_string += ":"

				out_string += f" {self.subtitle}</a>\n"
			else:
				# Test for a foreign language title, and adjust accordingly.
				if self.lang:
					out_string += f"<a href=\"text/{self.file_link}\" xml:lang=\"{self.lang}\">{self.title}</a>\n"
				else:
					out_string += f"<a href=\"text/{self.file_link}\">{self.title}</a>\n"

		# Replace `<br/>` with a single space.
		out_string = regex.sub(r"<br/>\s*", " ", out_string)

		return out_string

	def landmark_link(self, work_title: str = "WORK_TITLE") -> str:
		"""
		Generates the landmark item (including list item tags) for the ToC item.

		INPUTS:
		work_type: `fiction` or `non-fiction`.
		work_title: the title of the book, eg `Don Quixote`.

		OUTPUTS:
		the linking string to be included in landmarks section.
		"""

		out_string = ""
		if self.place == Position.FRONT:
			out_string = f"<li>\n<a href=\"text/{self.file_link}\" epub:type=\"frontmatter {self.epub_type}\">{self.title}</a>\n</li>\n"
		if self.place == Position.BODY:
			out_string = f"<li>\n<a href=\"text/{self.file_link}\" epub:type=\"bodymatter\">{work_title}</a>\n</li>\n"
		if self.place == Position.BACK:
			out_string = f"<li>\n<a href=\"text/{self.file_link}\" epub:type=\"backmatter {self.epub_type}\">{self.title}</a>\n</li>\n"

		return out_string

def get_place(node: EasyXmlElement) -> Position:
	"""
	Returns place of file in ebook, eg frontmatter, backmatter, etc.

	INPUTS:
	node: `EasyXmlElement` representation of the file.

	OUTPUTS:
	a `Position` enum value indicating the place in the book.
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

def add_landmark(dom: EasyXmlTree, textf: str, landmarks: list) -> None:
	"""
	Adds an item to landmark list with appropriate details.

	INPUTS:
	dom: `EasyXmlTree` representation of the file we are indexing in ToC.
	textf: path to the file.
	landmarks: the list of landmark items we are building.

	OUTPUTS:
	None
	"""

	# According to the IDPF a11y best practices page: <http://idpf.org/epub/a11y/techniques/#sem-003>:
	#
	# > it is recommended to include a link to the start of the body matter as well as to any major reference sections (e.g., table of contents, endnotes, bibliography, glossary, index).
	#
	# So, we only want the start of the text, and (endnotes,glossary,bibliography,loi) in the landmarks.

	epub_type = ""
	sections = dom.xpath("//body/*[name() = 'section' or name() = 'article' or name() = 'nav']")
	if not sections:
		raise se.InvalidInputException("Couldn’t locate first [xhtml]<section>[/], [xhtml]<article>[/], or [xhtml]<nav>[/].")
	epub_type = sections[0].get_attr("epub:type")
	bodys = dom.xpath("//body")
	if not bodys:
		raise se.InvalidInputException("Couldn’t locate [xhtml]<body>[/].")

	if not epub_type:  # Some productions don't have an epub:type in outermost section, so get it from `<body>` element.
		epub_type = bodys[0].get_attr("epub:type")
		if not epub_type:
			epub_type = ""

	if epub_type in ["frontmatter", "bodymatter", "backmatter"]:
		return  # If `epub_type` is *only* `frontmatter`, `bodymatter`, `backmatter`, we don't want this as a landmark.

	if dom.xpath("//*[contains(@epub:type, 'frontmatter')]"):
		return # We don't want frontmatter in the landmarks.

	if dom.xpath("//*[contains(@epub:type, 'backmatter')]") and not regex.search(r"\b(loi|endnotes|bibliography|glossary|index)\b", epub_type):
		return # We only want certain backmatter in the landmarks.

	# We may wind up with a `(front|body|back)matter` semantic in `epub_type`, remove it here since we add it to the landmark later.
	epub_type = regex.sub(r"(front|body|back)matter\s*", "", epub_type)

	landmark = TocItem()
	if epub_type:
		landmark.epub_type = epub_type
		landmark.file_link = textf
		landmark.place = get_place(bodys[0])
		landmark.has_headers = len(dom.xpath("//hgroup | //h1 | //h2 | //h3 | //h4 | //h5 | //h6")) > 0
		if epub_type == "halftitlepage":
			landmark.title = "Half Title"
		elif epub_type == "titlepage":
			# Exception: The titlepage always is always titled `titlepage` in the ToC.
			landmark.title = "Titlepage"
			landmark.lang = "" # Reset the language in case the ebook is title is not English.
		else:
			landmark.title = dom.xpath("//head/title/text()", True)  # Use the page title as the landmark entry title.
			if landmark.title is None:
				# This is a bit desperate, use this only if there's no proper `<title>` element in file.
				landmark.title = landmark.epub_type.capitalize()

		landmarks.append(landmark)

def process_landmarks(landmarks_list: list, work_title: str) -> str:
	"""
	Runs through all found landmark items and writes them to the toc file.

	INPUTS:
	landmarks_list: the completed list of landmark items.
	work_type: `fiction` or `non-fiction`.
	work_title: the title of the book.
	"""

	# We don't want frontmatter items to be included once we've started the body items.
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
		out_string += body_items[0].landmark_link(work_title)  # Just the first bodymatter item.
	for item in back_items:
		out_string += item.landmark_link()
	return out_string

def process_items(item_list: list) -> str:
	"""
	Runs through all found toc items and returns them as a string.

	INPUTS:
	item_list: list of ToC items.

	OUTPUTS:
	A string representing (possibly nested) HTML lists of the structure of the ToC.
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

		if next_item.level > this_item.level:  # Parent, start a new `<ol>` list.
			out_string += "<li>\n"
			out_string += this_item.toc_link
			out_string += "<ol>\n"
			unclosed_ol += 1

		if next_item.level < this_item.level:  # Last child, close off the list.
			out_string += "<li>\n"
			out_string += this_item.toc_link
			out_string += "</li>\n"  # Close off this item.
			torepeat = this_item.level - next_item.level
			while torepeat and unclosed_ol:  # Neither can go below zero.
				# We need to repeat a few times as may be jumping back from e.g. `<h5>` to `<h2>`.
				out_string += "</ol>\n"  # End of embedded list.
				out_string += "</li>\n"  # End of parent item.
				unclosed_ol -= 1
				torepeat -= 1
	return out_string

def output_toc(item_list: list, landmark_list, toc_path: str, work_title: str) -> str:
	"""
	Outputs the contructed ToC based on the lists of items and landmarks found, either to stdout or overwriting the existing ToC file.

	INPUTS:
	item_list: list of ToC items (the first part of the ToC).
	landmark_list: list of landmark items (the second part of the ToC).
	work_type: `fiction` or `non-fiction`.
	work_title: the title of the book.

	OUTPUTS:
	A HTML string representing the new ToC.
	"""

	if len(item_list) < 2:
		raise se.InvalidInputException("Too few ToC items found.")

	try:
		with open(toc_path, "r", encoding="utf-8") as file:
			toc_dom = se.easy_xml.EasyXmlTree(file.read())
	except Exception as ex:
		raise se.InvalidInputException(f"Existing ToC not found. Exception: {ex}")

	# There should be exactly two nav sections.
	navs = toc_dom.xpath("//nav")

	if len(navs) < 2:
		raise se.InvalidInputException("Existing ToC has too few nav sections.")

	# Now remove and then re-add the `<ol>` sections to clear them.
	for nav in navs:
		ols = nav.xpath("./ol")  # Just want the immediate `<ol>` children.
		for ol_item in ols:
			ol_item.remove()

	# This is ugly and stupid, but I can't figure out an easier way to do it.
	item_ol = EasyXmlElement(etree.Element("ol"), toc_dom.namespaces)
	item_ol.lxml_element.text = "TOC_ITEMS"
	navs[0].append(item_ol)
	landmark_ol = EasyXmlElement(etree.Element("ol"), toc_dom.namespaces)
	landmark_ol.lxml_element.text = "LANDMARK_ITEMS"
	navs[1].append(landmark_ol)
	xhtml = toc_dom.to_string()
	xhtml = xhtml.replace("TOC_ITEMS", process_items(item_list))
	xhtml = xhtml.replace("LANDMARK_ITEMS", process_landmarks(landmark_list, work_title))

	return se.formatting.format_xhtml(xhtml)

def get_parent_id(hchild: EasyXmlElement) -> str:
	"""
	Climbs up the document tree looking for parent ID in a `<section>` element.

	INPUTS:
	hchild: a heading element for which we want to find the parent ID.

	OUTPUTS:
	The ID of the parent section.
	"""

	# `position() = 1` gets the nearest ancestor.
	parents = hchild.xpath("./ancestor::*[name() = 'section' or name() = 'article'][@id][position() = 1]")

	if parents:
		return parents[0].get_attr("id")

	return ""

def extract_strings(node: EasyXmlElement) -> str:
	"""
	Returns string representation of an element, ignoring linefeeds.

	INPUTS:
	node: An xpath node.

	OUTPUTS:
	Just the string contents of the element.
	"""

	out_string = node.inner_xml()
	out_string = strip_notes(out_string)
	out_string = out_string.strip().replace("\n", " ") # Replace newlines with a space because we may have two elements in a row in a title, like `<abbr>S.S.</abbr> <i>Lusitania</i>`. When in `<h2>`, these elemetns will be on their own line, but in `<a>` they will be on the same line and require a space between them.
	return regex.sub(r"[\n\t]", "", out_string)

def process_headings(dom: EasyXmlTree, textf: str, toc_list: list, single_file: bool, single_file_without_headers: bool) -> None:
	"""
	Find headings in current file and extract title data into items added to `toc_list`.

	INPUTS:
	dom: An `EasyXmlTree` representation of the current file.
	textf: The path to the file.
	toc_list: The list of ToC items we are building.
	single_file: Is there only a single content item in the production?

	OUTPUTS:
	None.
	"""

	body = dom.xpath("//body")
	place = Position.NONE
	if body:
		place = get_place(body[0])
	else:
		raise se.InvalidInputException("Couldn’t locate [xhtml]<body>[/].")

	is_toplevel = True

	# Find all the `<hgroup>`s and `<h#>` headings.
	heads = dom.xpath("//hgroup | //h1 | //h2 | //h3 | //h4 | //h5 | //h6")

	# Special treatment where we can't find any heading or `<hgroup>`s.
	if not heads:  # May be a dedication or an epigraph, with no heading element.
		special_item = TocItem()
		# Need to determine level depth.
		# We don't have a heading, so get first content item.
		content_item = dom.xpath("//p | //header | //img")
		if content_item: # Check to see if it has a `data-parent` attribute, if so, we'll use that to determine depth.
			data_parent = content_item[0].xpath("//*[@data-parent]")
			if data_parent:
				special_item.level = get_level(content_item[0], toc_list)
			else: # Special items without `data-parents` get a default dept of 1.
				special_item.level = 1
		else:
			raise se.InvalidInputException(f"Unable to find heading or content item (p, header or img) in file: [path][link=file://{textf}]{textf}[/][/].")
		special_item.title = dom.xpath("//head/title/text()", True)  # Use the page title as the ToC entry title.
		if special_item.title is None:
			special_item.title = "NO TITLE"
		special_item.file_link = textf
		special_item.toc_id = get_toc_id_for_special_item(content_item[0])
		if not special_item.toc_id: # No luck so use quick and dirty method.
			special_item.toc_id = textf.replace('.xhtml','')
		special_item.place = place
		toc_list.append(special_item)
		return

	for heading in heads:
		# Don't process a heading separately if it's within a `<hgroup>`.
		if heading.parent.tag == "hgroup":
			continue  # Skip it.

		if place == Position.BODY:
			toc_item = process_a_heading(heading, textf, is_toplevel, single_file)
		else:
			# If it's not a bodymatter item we don't care about whether it's `single_file`.
			toc_item = process_a_heading(heading, textf, is_toplevel, False)

		toc_item.level = get_level(heading, toc_list)
		toc_item.place = place

		# Exception: The titlepage always is titled `titlepage` in the ToC.
		if dom.xpath("//section[re:test(@epub:type, '\\btitlepage\\b')]"):
			toc_item.title = "Titlepage"
			toc_item.lang = "" # Reset in case the title is not English.

		# Exception: If there is only a single body item *without headers* (like _Father Goriot_ or _The Path to Rome_), the half title page is listed as `Half-Titlepage` instead of the work title, so that we don't duplicate the work title in the ToC. We always include a link to the work body in the ToC because readers on the web version need to have access to the text starting point, since there are no back/forward nav buttons in XHTML files served on the web.
		if single_file_without_headers and dom.xpath("//section[re:test(@epub:type, '\\bhalftitlepage\\b')]"):
			toc_item.title = "Half-Titlepage"

		is_toplevel = False
		toc_list.append(toc_item)

def get_toc_id_for_special_item(node: EasyXmlElement) -> str:
	"""
	Get the id for a 'special item' node.
	"""
	parent_sections = node.xpath("./ancestor::*[name() = 'section' or name() = 'article']")
	for parent in parent_sections:
		toc_id = parent.get_attr("id")
		if toc_id:
			return toc_id
	return ""

def get_level(node: EasyXmlElement, toc_list: list) -> int:
	"""
	Get level of a node.
	"""

	# First need to check how deep this heading is within the current file.
	parent_sections = node.xpath("./ancestor::*[name() = 'section' or name() = 'article']")
	if parent_sections:
		depth = len(parent_sections)
	else:
		depth = 1

	if not node.parent:
		return depth  # Must be at the top level.

	data_parents = node.xpath("//*[@data-parent]")
	if not data_parents:
		return depth

	data_parent = data_parents[0].get_attr("data-parent")

	if data_parent:
		# See if we can find it in already processed (as we should if spine is correctly ordered).
		parent_file = [t for t in toc_list if t.toc_id == data_parent]
		if parent_file:
			this_level = parent_file[0].level + 1
			return this_level + depth - 1  # Subtract from depth because all headings should have depth >= 1.

	return depth

def process_a_heading(node: EasyXmlElement, textf: str, is_toplevel: bool, single_file: bool) -> TocItem:
	"""
	Generate and return a single TocItem from this heading.

	INPUTS:
	node: An `EasyXml` node representing a heading.
	text: The path to the file.
	is_toplevel: Is this heading at the top-most level in the file?
	single_file: Is there only one content file in the production (like some Poetry volumes)?

	OUTPUTS:
	A qualified `TocItem` object.
	"""

	toc_item = TocItem()

	toc_item.division = get_book_division(node)

	# `is_top_level` stops the first heading in a file getting an anchor id, we don't generally want that.
	# The exceptions are things like poems within a single-file volume.
	toc_item.toc_id = get_parent_id(node)  # pylint: disable=invalid-name
	if toc_item.toc_id == "":
		toc_item.file_link = textf
	else:
		if not is_toplevel:
			toc_item.file_link = f"{textf}#{toc_item.toc_id}"
		elif single_file:  # It *is* the first heading in the file, but there's only a single content file?
			toc_item.file_link = f"{textf}#{toc_item.toc_id}"
		else:
			toc_item.file_link = textf

	toc_item.lang = node.get_attr("xml:lang")

	if node.get_attr("hidden"):
		toc_item.hidden = True

	epub_type = node.get_attr("epub:type")

	# It may be an empty header element eg `<h3>`, so we pass its parent rather than itself to evaluate the parent's descendants.
	if not epub_type and node.tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
		parent = node.parent
		if parent:
			evaluate_descendants(parent, toc_item, textf)
		else:  # Shouldn't ever happen, but... just in case, raise an error.
			raise se.InvalidInputException(f"Heading without parent in file: [path][link=file://{textf}]{textf}[/][/].")
		return toc_item
	if epub_type:
		# A heading may include `z3998:roman` directly, e.g. `<h5 epub:type="title z3998:roman">II</h5>`.
		if "z3998:roman" in epub_type:
			toc_item.roman = extract_strings(node)
			try:
				roman.fromRoman(toc_item.roman)
			except roman.InvalidRomanNumeralError as err:
				raise se.InvalidInputException(f"Heading tagged as roman numeral is invalid: {toc_item.roman} in [path][link=file://{textf}]{textf}[/][/].") from err
			toc_item.title = f"<span epub:type=\"z3998:roman\">{toc_item.roman}</span>"
			return toc_item
		if "ordinal" in epub_type:  # But not a roman numeral (e.g. in Nietzche's _Beyond Good and Evil_).
			toc_item.title = extract_strings(node)
			toc_item.title_is_ordinal = True
			return toc_item
		# May be the halftitle page with a subtitle, so we need to burrow down.
		if ("fulltitle" in epub_type) and (node.tag == "hgroup"):
			evaluate_descendants(node, toc_item, textf)
			return toc_item
		# Or it may be a straightforward one-level title eg: `<h2 epub:type="title">Imprint</h2>`.
		if "title" in epub_type:
			toc_item.title = extract_strings(node)
			return toc_item

	# Otherwise, burrow down into its structure to get the info.
	evaluate_descendants(node, toc_item, textf)

	return toc_item

def get_child_strings(node: EasyXmlElement) -> str:
	"""
	Get child strings.
	"""

	children = node.xpath("./*")
	child_strs = ""
	for child in children:
		child_strs += child.to_string() + "\n"
	return child_strs

def evaluate_descendants(node: EasyXmlElement, toc_item: TocItem, textf: str) -> TocItem:
	"""
	Burrow down into a hgroup structure to qualify the ToC item.

	INPUTS:
	node: `EasyXmlElement` object representing a `<hgroup>`.

	OUTPUTS:
	toc_item: Qualified ToC item.
	"""
	children = node.xpath("./p | ./h1 | ./h2 | ./h3 | ./h4 | ./h5 | ./h6")
	for child in children:  # We expect these to be an `<h#>`.
		epub_type = child.get_attr("epub:type")

		if child.get_attr("hidden"):
			toc_item.hidden = True

		if not epub_type:
			# Should be a label/ordinal grouping.
			child_strings = get_child_strings(child)
			if "label" in child_strings and "ordinal" in child_strings:
				toc_item.title_is_ordinal = True
				# Strip label.
				child_strings = regex.sub(r"<span epub:type=\"label\">(.*?)</span>", " \\1 ", child_strings)
				# Remove ordinal if it's by itself in a `<span>`.
				child_strings = regex.sub(r"<span epub:type=\"ordinal\">(.*?)</span>", " \\1 ", child_strings)
				# Remove ordinal if it's joined with a roman numeral (which we want to keep).
				child_strings = regex.sub(r"\bordinal\b", "", child_strings)
				# Remove extra spaces.
				child_strings = regex.sub(r"[ ]{2,}", " ", child_strings)
				# Remove any carriage returns.
				child_strings = regex.sub(r"\n", "", child_strings)
				# Get rid of any endnotes.
				child_strings = strip_notes(child_strings)
				toc_item.title = child_strings.strip()
			continue  # Skip the following.
		if "z3998:roman" in epub_type:
			toc_item.roman = extract_strings(child)
			try:
				roman.fromRoman(toc_item.roman)
			except roman.InvalidRomanNumeralError as err:
				raise se.InvalidInputException(f"Heading tagged as roman numeral is invalid: {toc_item.roman} in [path][link=file://{textf}]{textf}[/][/].") from err
			if not toc_item.title:
				toc_item.title = f"<span epub:type=\"z3998:roman\">{toc_item.roman}</span>"
		elif "ordinal" in epub_type:  # But not a roman numeral or a labeled item, cases caught caught above.
			if not toc_item.title:
				toc_item.title = extract_strings(child)
				toc_item.title_is_ordinal = True
		if "subtitle" in epub_type:
			toc_item.subtitle = extract_strings(child)
		else:
			if "title" in epub_type:  # This allows for `fulltitle` to work here, too.
				if toc_item.title or toc_item.roman or toc_item.title_is_ordinal:  # If the title is already filled, must be a subtitle.
					toc_item.subtitle = extract_strings(child)
					if toc_item.roman or toc_item.title_is_ordinal:  # In these cases, we want to check language on subtitle.
						toc_item.lang = child.get_attr("xml:lang")
				else:
					toc_item.title = extract_strings(child)
					if not toc_item.lang:
						toc_item.lang = child.get_attr("xml:lang")

		if toc_item.title and toc_item.subtitle:  # Then we're done, get out of loop by returning.
			return toc_item
	return toc_item

def get_book_division(node: EasyXmlElement) -> BookDivision:
	"""
	Determine the kind of book division. At present only Part and Division are important; but others stored for possible future logic.

	INPUTS:
	tag: An `EasyXml` node representing a nelement.

	OUTPUTS:
	A `BookDivision` enum value representing the kind of division.
	"""

	parent_sections = node.xpath("./ancestor::*[name() = 'section' or name() = 'article']")

	if not parent_sections:
		parent_sections = node.xpath("./ancestor::body")

	if not parent_sections:  # Couldn't find a parent, so throw an error.
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
	text: HTMl which may include noterefs.

	OUTPUTS:
	Cleaned HTMl string.
	"""

	return regex.sub(r"""<a[^>]*?epub:type="noteref"[^>]*?>.*?<\/a>""", "", text)

def process_all_content(self, file_list: list) -> tuple[list, list]:
	"""
	Analyze the whole content of the project, build and return lists of `toc_items` and landmarks.

	INPUTS:
	file_list: A list of all content files.
	text_path: The path to the contents folder (e.g. `src/epub/text`).

	OUTPUTS:
	A tuple containing the list of Toc items and the list of landmark items.
	"""

	toc_list: list[TocItem] = []
	landmarks: list[TocItem] = []

	# We make two passes through the work, because we need to know how many bodymatter items there are. So we do landmarks first.
	for textf in file_list:
		try:
			dom = self.get_dom(textf)
		except Exception as ex:
			raise se.InvalidFileException(f"Couldn’t open file: [path][link=file://{textf}]{textf}[/][/]. Exception: {ex}") from ex

		add_landmark(dom, textf.name, landmarks)

	# Now we test to see if there is only one body item.
	body_items = [item for item in landmarks if item.place == Position.BODY]
	single_file = len(body_items) == 1
	single_file_without_headers = False

	# If there's only one body item, does that item have a header?
	if single_file:
		single_file_without_headers = not body_items[0].has_headers

	nest_under_halftitle = False

	for textf in file_list:
		with open(textf, "r", encoding="utf-8") as file:
			dom = se.easy_xml.EasyXmlTree(file.read())
		process_headings(dom, textf.name, toc_list, single_file, single_file_without_headers)

		# Only consider half title pages that are front matter. Some books, like C.S. Lewis's _Poetry_, may have half titles that are bodymatter.
		if dom.xpath("/html/body//*[contains(@epub:type, 'halftitlepage') and ancestor-or-self::*[contains(@epub:type, 'frontmatter')]]"):
			nest_under_halftitle = True

	# Now go through adjusting for nesting under halftitle.
	if nest_under_halftitle:
		# Tricky because a few books have forewords, etc. *after* the halftitle, so have to know if we've passed it.
		passed_halftitle = False
		for toc_item in toc_list:
			if toc_item.place == Position.BODY:
				toc_item.level += 1
			if passed_halftitle and toc_item.place == Position.FRONT:
				toc_item.level += 1
			if "halftitle" in toc_item.file_link:
				passed_halftitle = True


	# We add this dummy item because `output_toc()` always needs to look ahead to the next item.
	last_toc = TocItem()
	last_toc.level = 1
	last_toc.title = "dummy"
	toc_list.append(last_toc)

	return landmarks, toc_list

def generate_toc(self) -> str:
	"""
	Entry point for `SeEpub.generate_toc()`.
	"""

	work_title = self.get_title()

	landmarks, toc_list = process_all_content(self, self.spine_file_paths)

	return output_toc(toc_list, landmarks, self.toc_path, work_title)
