#!/usr/bin/env python3
"""
This module contains the make-toc function which tries to create a
valid table of contents file for SE projects.

Strictly speaking, the make_toc() function should be a class member of SeEpub. But
the function is very big and it makes editing easier to put in a separate file.

"""
import os
from enum import Enum
import regex
from bs4 import BeautifulSoup, Tag
from se.formatting import format_xhtml


class TocItem:
	"""
	Small class to hold data on each table of contents item
	found in the project.
	"""
	file_link = ''
	level = 0
	roman = ''
	title = ''
	subtitle = ''
	id = ''
	epub_type = ''

	def output(self) -> str:
		"""
		The output method just outputs the linking tag line
		eg <a href=... depending on the data found.
		"""
		outstring = ''

		if title_is_entirely_roman(self.title):
			if self.subtitle == '':
				outstring += '<a href="text/' + self.file_link + '" epub:type="z3998:roman">' + self.roman + '</a>' + '\n'
			else:
				outstring += '<a href="text/' + self.file_link + '">' + self.title + ': ' + self.subtitle + '</a>' + '\n'
		else:
			outstring += '<a href="text/' + self.file_link + '">' + self.title + '</a>' + '\n'

		return outstring


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
	title = ''
	file_link = ''
	epub_type = ''
	place: Position = Position.FRONT

	def output(self, work_type: str = 'fiction', work_title: str = 'WORKTITLE'):
		"""
		Returns the linking string to be included in landmarks section.
		"""
		outstring = ''
		if self.place == Position.FRONT:
			outstring = '<li>' + '\n' + '<a href="text/' + self.file_link \
						+ '" epub:type="frontmatter ' + self.epub_type + '">' + self.title + '</a>' + '\n' + '</li>' + '\n'
		if self.place == Position.BODY:
			outstring = '<li>' + '\n' + '<a href="text/' + self.file_link \
						+ '" epub:type="bodymatter z3998:' + work_type + '">' + work_title + '</a>' + '\n' + '</li>' + '\n'
		if self.place == Position.BACK:
			outstring = '<li>' + '\n' + '<a href="text/' + self.file_link \
						+ '" epub:type="backmatter ' + self.epub_type + '">' + self.title + '</a>' + '\n' + '</li>' + '\n'
		return outstring


def get_content_files(opf: BeautifulSoup) -> list:
	"""
	Reads the spine from content.opf to obtain a list of content files, in the order wanted for the ToC.
	"""
	itemrefs = opf.find_all('itemref')
	retlist = []
	for itemref in itemrefs:
		retlist.append(itemref['idref'])
	return retlist


def get_work_title_and_type(opf: BeautifulSoup) -> (str, str):
	"""
	From content.opf, which we assume has been correctly completed,
	pulls out the title and determines if the type is fiction or nonfiction.
	Returns this information as a tuple.
	"""
	# First, set up the defaults if we can't find the info.
	work_type = 'fiction'
	work_title = 'WORKTITLE'
	dctitle = opf.find('dc:title')
	if dctitle is not None:
		work_title = dctitle.string
	subjects = opf.find_all('se:subject')
	for subject in subjects:
		if 'Nonfiction' in subject:
			work_type = 'non-fiction'
			break
	return work_title, work_type


def get_html(filename: str) -> str:
	"""
	Reads an xhtml file and returns the text.
	"""
	try:
		fileobject = open(filename, 'r', encoding='utf-8')
	except IOError:
		print('Could not open ' + filename)
		return ''
	text = fileobject.read()
	fileobject.close()
	return text


def get_epub_type(soup: BeautifulSoup) -> str:
	"""
	Retrieve the epub_type of this file to see if it's a landmark item.
	"""
	# Try for a heading.
	first_head = soup.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
	if first_head is not None:
		parent = first_head.find_parent(['section', 'article'])
	else:  # No heading found so go hunting for some other content.
		para = soup.find(['p', 'header', 'img'])  # We look for the first such item.
		parent = para.find_parent(['section', 'article'])
	try:
		return parent['epub:type']
	except KeyError:
		return ''


def get_place(soup: BeautifulSoup) -> Position:
	"""
	Returns place of file in ebook, eg frontmatter, backmatter, etc.
	"""
	bod = soup.body
	try:
		epub_type = bod['epub:type']
	except KeyError:
		return Position.NONE
	if 'backmatter' in epub_type:
		retval = Position.BACK
	elif 'frontmatter' in epub_type:
		retval = Position.FRONT
	elif 'bodymatter' in epub_type:
		retval = Position.BODY
	else:
		retval = Position.NONE
	return retval


def add_landmark(soup: BeautifulSoup, textf: str, landmarks: list):
	"""
	Adds an item to landmark list with appropriate details.
	"""
	epub_type = get_epub_type(soup)
	title = soup.find('title').string
	landmark = LandmarkItem()
	landmark.title = title
	if epub_type != '':
		landmark.epub_type = epub_type
		landmark.file_link = textf
		landmark.place = get_place(soup)
		landmarks.append(landmark)


def process_landmarks(landmarks_list: list, work_type: str, work_title: str):
	"""
	Runs through all found landmark items and writes them to the toc file.
	"""
	frontitems = [item for item in landmarks_list if item.place == Position.FRONT]
	bodyitems = [item for item in landmarks_list if item.place == Position.BODY]
	backitems = [item for item in landmarks_list if item.place == Position.BACK]

	outstring = ''
	for item in frontitems:
		outstring += item.output()
	if bodyitems:
		outstring += bodyitems[0].output(work_type, work_title)  # Just the first bodymatter item.
	for item in backitems:
		outstring += item.output()
	return outstring


def process_items(item_list: list) -> str:
	"""
	Runs through all found toc items and returns them as a string.
	"""
	unclosed_ol = 0  # Keep track of how many ordered lists we open.
	outstring = ''

	# Process all but last item so we can look ahead.
	for index in range(0, len(item_list) - 1):  # Ignore very last item, which is a dummy.
		thisitem = item_list[index]
		nextitem = item_list[index + 1]

		# Check to see if next item is at same, lower or higher level than us.
		if nextitem.level == thisitem.level:  # SIMPLE
			outstring += '<li>' + '\n'
			outstring += thisitem.output()
			outstring += '</li>' + '\n'

		if nextitem.level > thisitem.level:  # PARENT
			outstring += '<li>' + '\n'
			outstring += thisitem.output()
			outstring += '<ol>' + '\n'
			unclosed_ol += 1

		if nextitem.level < thisitem.level:  # LAST CHILD
			outstring += '<li>' + '\n'
			outstring += thisitem.output()
			outstring += '</li>' + '\n'  # Close off this item.
			torepeat = thisitem.level - nextitem.level
			if torepeat > 0 and unclosed_ol > 0:
				for _ in range(0, torepeat):  # We need to repeat a few times as may be jumping back from eg h5 to h2
					outstring += '</ol>' + '\n'  # End of embedded list.
					unclosed_ol -= 1
					outstring += '</li>' + '\n'  # End of parent item.
	return outstring


def get_opf(opfpath) -> BeautifulSoup:
	"""
	Returns a BeautifulSoup object representing the content.opf file.
	"""
	opftext = get_html(opfpath)
	return BeautifulSoup(opftext, 'html.parser')


def get_existing_toc(tocpath: str) -> BeautifulSoup:
	"""
	Returns a BeautifulSoup object representing the existing ToC file.
	"""
	toctext = get_html(tocpath)
	return BeautifulSoup(toctext, 'html.parser')


def output_toc(item_list: list, landmark_list, tocpath: str, overwrite: bool, work_type: str, work_title: str):
	"""
	Outputs the contructed ToC based on the lists of items and landmarks found,
	either to stdout or overwriting the existing ToC file
	"""
	if len(item_list) < 2:
		print('Too few ToC items found')
		return

	existing_toc: BeautifulSoup = get_existing_toc(tocpath)
	if existing_toc is None:
		print("Existing ToC not found")
		return

	# There should be exactly two nav sections.
	navs = existing_toc.find_all('nav')

	if len(navs) < 2:
		print("Existing ToC has too few nav sections")
		return

	item_ol = navs[0].find('ol')
	item_ol.clear()
	landmark_ol = navs[1].find('ol')
	landmark_ol.clear()
	item_html = process_items(item_list)
	new_items = BeautifulSoup(item_html, 'html.parser')
	item_ol.append(new_items)
	landmarks_html = process_landmarks(landmark_list, work_type, work_title)
	new_landmarks = BeautifulSoup(landmarks_html, 'html.parser')
	landmark_ol.append(new_landmarks)
	writestring = format_xhtml(str(existing_toc))

	if overwrite:
		try:
			if os.path.exists(tocpath):
				os.remove(tocpath)  # Get rid of existing file.
			tocfile = open(tocpath, 'w', encoding='utf-8')
		except IOError:
			print('Unable to overwrite ToC file!')
			return
		tocfile.write(writestring)
		tocfile.close()
	else:  # Output to stdout.
		print(writestring)


def get_parent_id(hchild: Tag) -> str:
	"""
	Climbs up the document tree looking for parent id in a <section> tag.
	"""
	parent = hchild.find_parent(['section', 'article'])
	if parent is None:
		return ''
	try:
		return parent['id']
	except KeyError:
		return ''


def extract_strings(atag: Tag) -> str:
	"""
	Returns only the string content of a tag, ignoring noteref and its content.
	"""
	retstring = ''
	for child in atag.contents:
		if child != '' + '\n':
			if isinstance(child, Tag):
				try:
					epub_type = child['epub:type']
					if 'z3998:roman' in epub_type:
						retstring += str(child)  # We want the whole span.
					if 'noteref' in epub_type:
						continue
				except KeyError:  # The tag has no epub_type, probably <abbr>.
					retstring += child.string
			else:
				retstring += child  # Must be NavigableString.
	return retstring


def process_headings(soup: BeautifulSoup, textf: str, toclist: list, nest_under_halftitle: bool):
	"""
	Find headings in current file and extract title data
	into items added to toclist.
	"""
	# find all the h1, h2 etc headings
	heads = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

	if not heads:  # May be a dedication or an epigraph, with no heading tag.
		special_item = TocItem()
		sections = soup.find_all('section')  # Count the sections within this file.
		special_item.level = len(sections)
		title_tag = soup.find('title')  # Use the page title as the ToC entry title.
		special_item.title = title_tag.string
		special_item.file_link = textf
		toclist.append(special_item)
		return

	is_toplevel = True
	for heading in heads:
		tocitem = process_heading(heading, is_toplevel, textf)
		if nest_under_halftitle:
			tocitem.level += 1
		is_toplevel = False
		toclist.append(tocitem)


def title_is_entirely_roman(title: str) -> bool:
	"""
	This tests to see if there's nothing else in a title than a roman number.
	if so, we can collapse the epub type into the surrounding ToC <a> tag.
	"""
	pattern = r'^<span epub:type="z3998:roman">[IVXLC]{1,10}<\/span>$'
	compiled_regex = regex.compile(pattern)
	return compiled_regex.search(title)


def process_heading(heading, is_toplevel, textf) -> TocItem:
	"""
	Generate and return a TocItem from this heading.
	"""
	tocitem = TocItem()
	parent_sections = heading.find_parents(['section', 'article'])
	tocitem.level = len(parent_sections)
	# This stops the first heading in a file getting an anchor id, we don't want that.
	if is_toplevel:
		tocitem.id = ''
		tocitem.file_link = textf
	else:
		tocitem.id = get_parent_id(heading)
		if tocitem.id == '':
			tocitem.file_link = textf
		else:
			tocitem.file_link = textf + '#' + tocitem.id
	# A heading may include z3998:roman directly,
	# eg <h5 epub:type="title z3998:roman">II</h5>.
	try:
		attribs = heading['epub:type']
	except KeyError:
		attribs = ''
	if 'z3998:roman' in attribs:
		tocitem.roman = extract_strings(heading)
		tocitem.title = '<span epub:type="z3998:roman">' + tocitem.roman + '</span>'
		return tocitem

	process_heading_contents(heading, tocitem)
	return tocitem


def process_heading_contents(heading, tocitem):
	"""
	Run through each item in the heading contents
	and try to pull out the toc item data.
	"""
	accumulator = ''  # We'll use this to build up the title.
	for child in heading.contents:
		if child != '' + '\n':
			if isinstance(child, Tag):
				try:
					epub_type = child['epub:type']
				except KeyError:
					epub_type = 'blank'
					if child.name == 'abbr':
						accumulator += extract_strings(child)
						continue  # Skip following and go to next child.

				if 'z3998:roman' in epub_type:
					tocitem.roman = extract_strings(child)
					accumulator += str(child)
				elif 'subtitle' in epub_type:
					tocitem.subtitle = extract_strings(child)
				elif 'title' in epub_type:
					tocitem.title = extract_strings(child)
				elif 'noteref' in epub_type:
					pass  # Don't process it.
				else:
					tocitem.title = extract_strings(child)
			else:  # This should be a simple NavigableString.
				accumulator += str(child)
	if tocitem.title == '':
		tocitem.title = accumulator


def process_all_content(filelist, textpath) -> (list, list):
	"""
	Analyze the whole content of the project, build and return lists
	if tocitems and landmarks.
	"""
	toclist = []
	landmarks = []
	nest_under_halftitle = False
	for textf in filelist:
		html_text = get_html(os.path.join(textpath, textf))
		soup = BeautifulSoup(html_text, 'html.parser')
		place = get_place(soup)
		if place == Position.BACK:
			nest_under_halftitle = False
		process_headings(soup, textf, toclist, nest_under_halftitle)
		if textf == 'halftitle.xhtml':
			nest_under_halftitle = True
		add_landmark(soup, textf, landmarks)
	# We add this dummy item because outputtoc always needs to look ahead to the next item.
	lasttoc = TocItem()
	lasttoc.level = 1
	lasttoc.title = "dummy"
	toclist.append(lasttoc)
	return landmarks, toclist


def make_toc(self, in_place: bool, verbose: bool):
	"""
	Entry point for 'se make-toc'.
	"""
	rootpath = self.directory
	tocpath = os.path.join(rootpath, 'src', 'epub', 'toc.xhtml')
	textpath = os.path.join(rootpath, 'src', 'epub', 'text')
	opfpath = os.path.join(rootpath, 'src', 'epub', 'content.opf')

	opf = get_opf(opfpath)
	filelist = get_content_files(opf)
	work_title, work_type = get_work_title_and_type(opf)

	if not os.path.exists(opfpath):
		print("Error: this does not seem to be a Standard Ebooks root directory")
		exit(-1)

	landmarks, toclist = process_all_content(filelist, textpath)

	overwrite_existing = in_place

	output_toc(toclist, landmarks, tocpath, overwrite_existing, work_type, work_title)

	if verbose:
		print("Built Table of Contents with " + str(len(toclist)) + " entries.")

	return 0
