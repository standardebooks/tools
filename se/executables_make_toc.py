#!/usr/bin/env python3
"""
routine which tries to create a valid table of contents file for SE projects
"""
import argparse
import os
from typing import TextIO
from enum import Enum
import regex

from bs4 import BeautifulSoup, Tag


# global variable (not a constant)
verbose = False


class TocItem:
	"""
	small class to hold data on each table of contents item
	found in the project
	"""
	filelink = ''
	level = 0
	roman = ''
	title = ''
	subtitle = ''
	id = ''
	epubtype = ''

	def output(self) -> str:
		"""
		the output method just outputs the linking tag line
		eg <a href=... depending on the data found
		"""
		outstring = ''

		if title_is_entirely_roman(self.title):
			if self.subtitle == '':  # no subtitle
				outstring += tabs(1) + '<a href="text/' + self.filelink + '" epub:type="z3998:roman">' + self.roman + '</a>\n'
			else:
				outstring += tabs(1) + '<a href="text/' + self.filelink + '">' + self.title + ': ' + self.subtitle + '</a>\n'
		else:
			outstring += tabs(1) + '<a href="text/' + self.filelink + '">' + self.title + '</a>\n'

		return outstring


class Position(Enum):
	"""
	enum to indicate whether a landmark is frontmatter, bodymatter or backmatter
	"""
	NONE = 0
	FRONT = 1
	BODY = 2
	BACK = 3


class LandmarkItem:
	"""
	small class to hold data on landmark items found in the project
	"""
	title = ''
	filelink = ''
	epubtype = ''
	place: Position = Position.FRONT

	def output(self, worktype: str = 'fiction', worktitle: str = 'WORKTITLE'):
		"""
		returns the linking string to be included in landmarks section
		"""
		outstring = ''
		if self.place == Position.FRONT:
			outstring = tabs(4) + '<li>\n' + tabs(5) + '<a href="text/' + self.filelink \
						+ '" epub:type="frontmatter ' + self.epubtype + '">' + self.title + '</a>\n' + tabs(4) + '</li>\n'
		if self.place == Position.BODY:
			outstring = tabs(4) + '<li>\n' + tabs(5) + '<a href="text/' + self.filelink \
						+ '" epub:type="bodymatter z3998:' + worktype + '">' + worktitle + '</a>\n' + tabs(4) + '</li>\n'
		if self.place == Position.BACK:
			outstring = tabs(4) + '<li>\n' + tabs(5) + '<a href="text/' + self.filelink \
						+ '" epub:type="backmatter ' + self.epubtype + '">' + self.title + '</a>\n' + tabs(4) + '</li>\n'
		return outstring


def tabs(num_tabs: int) -> str:
	"""
	convenience function to return given number of tabs as a string.
	offset is optional
	"""
	if num_tabs > 0:
		return '\t' * num_tabs
	return ''


def indent(level: int, offset: int = 0) -> str:
	"""
	convenience function to return given number of tabs as a string.
	offset is optional
	"""
	num_tabs = (level * 2 + 2) + offset  # offset may be negative
	if num_tabs > 0:
		return '\t' * num_tabs
	return ''


def get_content_files(opf: BeautifulSoup) -> list:
	"""
	reads the spine from content.opf to obtain a list of content files, in the order wanted for the ToC
	"""
	itemrefs = opf.find_all('itemref')
	retlist = []
	for itemref in itemrefs:
		retlist.append(itemref['idref'])
	return retlist


def get_worktitle(opf: BeautifulSoup) -> str:
	"""
	pulls the title of the work out of the content.opf file
	"""
	dctitle = opf.find('dc:title')
	if dctitle is not None:
		return dctitle.string
	return 'WORKTITLE'


def gethtml(filename: str) -> str:
	"""
	reads an xhtml file and returns the text
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
	retrieve the epubtype of this file to see if it's a landmark item
	"""
	# try for a heading
	first_head = soup.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
	if first_head is not None:
		parent = first_head.find_parent(['section', 'article'])
	else:  # no heading so go hunting for some content
		para = soup.find(['p', 'header', 'img'])  # we find the first <p> or <header>
		parent = para.find_parent(['section', 'article'])
	try:
		return parent['epub:type']
	except KeyError:
		return ''


def get_place(soup: BeautifulSoup) -> Position:
	"""
	returns place of file in ebook, eg frontmatter, backmatter, etc.
	"""
	bod = soup.body
	try:
		epubtype = bod['epub:type']
	except KeyError:
		return Position.NONE
	if 'backmatter' in epubtype:
		retval = Position.BACK
	elif 'frontmatter' in epubtype:
		retval = Position.FRONT
	elif 'bodymatter' in epubtype:
		retval = Position.BODY
	else:
		retval = Position.NONE
	return retval


def add_landmark(soup: BeautifulSoup, textf: str, landmarks: list):
	"""
	adds item to landmark list with appropriate details
	"""
	epubtype = get_epub_type(soup)
	title = soup.find('title').string
	landmark = LandmarkItem()
	landmark.title = title
	if epubtype != '':
		landmark.epubtype = epubtype
		landmark.filelink = textf
		landmark.place = get_place(soup)
		landmarks.append(landmark)


def process_landmarks(landmarks_list: list, tocfile: TextIO, worktype: str, worktitle: str):
	"""
	goes through all found landmark items and writes them to the toc file
	"""
	frontitems = [item for item in landmarks_list if item.place == Position.FRONT]
	bodyitems = [item for item in landmarks_list if item.place == Position.BODY]
	backitems = [item for item in landmarks_list if item.place == Position.BACK]

	for item in frontitems:
		tocfile.write(item.output())

	if bodyitems:
		tocfile.write(bodyitems[0].output(worktype, worktitle))  # just the first item

	for item in backitems:
		tocfile.write(item.output())


def process_items(item_list: list, tocfile: TextIO):
	"""
	goes through all found toc items and writes them to the toc file
	"""
	unclosed_ol = 0   # keep track of how many ordered lists we open

	# process all but last item so we can look ahead
	for index in range(0, len(item_list) - 1):  # ignore very last item, which is a dummy
		thisitem = item_list[index]
		nextitem = item_list[index + 1]

		toprint = ''

		# check to see if next item is at same, lower or higher level than us
		if nextitem.level == thisitem.level:  # SIMPLE
			toprint += indent(thisitem.level) + '<li>\n'
			toprint += indent(thisitem.level) + thisitem.output()
			toprint += indent(thisitem.level) + '</li>\n'

		if nextitem.level > thisitem.level:  # PARENT
			toprint += indent(thisitem.level) + '<li>\n'
			toprint += indent(thisitem.level) + thisitem.output()
			toprint += indent(thisitem.level) + tabs(1) + '<ol>\n'
			unclosed_ol += 1

		if nextitem.level < thisitem.level:  # LAST CHILD
			toprint += indent(thisitem.level) + '<li>\n'
			toprint += indent(thisitem.level) + thisitem.output()
			toprint += indent(thisitem.level) + '</li>\n'  # end of this item
			torepeat = thisitem.level - nextitem.level
			current_level = thisitem.level
			if torepeat > 0 and unclosed_ol > 0:
				for _ in range(0, torepeat):  # need to repeat a few times as may be jumping back from eg h5 to h2
					toprint += indent(current_level, -1) + '</ol>\n'  # end of embedded list
					unclosed_ol -= 1
					toprint += indent(current_level, -2) + '</li>\n'  # end of parent item
					current_level -= 1

		tocfile.write(toprint)

	while unclosed_ol > 0:
		# shouldn't ever get here, but just to be safe...
		tocfile.write(tabs(3) + '</ol>\n')
		unclosed_ol -= 1
		tocfile.write(tabs(2) + '</li>\n')


def output_toc(item_list: list, landmark_list, outtocpath: str, worktype: str, worktitle: str):
	"""
	outputs the contructed ToC based on the lists of items  and landmarks found, to the specified output file
	"""
	if len(item_list) < 2:
		print('Too few ToC items found')
		return
	try:
		if os.path.exists(outtocpath):
			os.remove(outtocpath)  # get rid of file if it already exists
		tocfile = open(outtocpath, 'a', encoding='utf-8')
	except IOError:
		print('Unable to open output file! ' + outtocpath)
		return
	write_toc_start(tocfile)
	process_items(item_list, tocfile)
	write_toc_middle(tocfile)
	process_landmarks(landmark_list, tocfile, worktype, worktitle)
	write_toc_end(tocfile)

	tocfile.close()


def write_toc_start(tocfile):
	"""
	write opening part of ToC
	"""
	tocfile.write('<?xml version="1.0" encoding="utf-8"?>\n')
	tocfile.write('<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" ')
	tocfile.write('epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, ')
	tocfile.write('se: https://standardebooks.org/vocab/1.0" xml:lang="en-US">\n')
	tocfile.write(tabs(1) + '<head>\n')
	tocfile.write(tabs(2) + '<title>Table of Contents</title>\n')
	tocfile.write(tabs(1) + '</head>\n')
	tocfile.write(tabs(1) + '<body epub:type="frontmatter">\n')
	tocfile.write(tabs(2) + '<nav epub:type="toc">\n')
	tocfile.write(tabs(3) + '<h2 epub:type="title">Table of Contents</h2>\n')
	tocfile.write(tabs(3) + '<ol>\n')


def write_toc_middle(tocfile):
	"""
	write middle part of ToC and start of Landmarks
	"""
	tocfile.write(tabs(3) + '</ol>\n')
	tocfile.write(tabs(2) + '</nav>\n')
	tocfile.write(tabs(2) + '<nav epub:type="landmarks">\n')
	tocfile.write(tabs(3) + '<h2 epub:type="title">Landmarks</h2>\n')
	tocfile.write(tabs(3) + '<ol>\n')


def write_toc_end(tocfile):
	"""
	write closing part of ToC
	"""
	tocfile.write(tabs(3) + '</ol>\n')
	tocfile.write(tabs(2) + '</nav>\n')
	tocfile.write(tabs(1) + '</body>\n')
	tocfile.write('</html>')


def get_parent_id(hchild: Tag) -> str:
	"""
	climbs up the document tree looking for parent id in a <section> tag.
	"""
	parent = hchild.find_parent("section")
	if parent is None:
		return ''
	try:
		return parent['id']
	except KeyError:
		return ''


def extract_strings(atag: Tag) -> str:
	"""
	returns only the string content of a tag, ignoring noteref and its content
	"""
	retstring = ''
	for child in atag.contents:
		if child != '\n':
			if isinstance(child, Tag):
				try:
					epubtype = child['epub:type']
					if 'z3998:roman' in epubtype:
						retstring += str(child)  # want the whole span
					if 'noteref' in epubtype:
						continue
				except KeyError:  # tag has no epubtype, probably <abbr>
					retstring += child.string
			else:
				retstring += child  # must be NavigableString
	return retstring


def process_headings(soup: BeautifulSoup, textf: str, toclist: list, nest_under_halftitle: bool):
	"""
	find headings in current file and extract data
	into items added to toclist
	"""
	# find all the h1, h2 etc headings
	heads = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

	if not heads:  # may be a dedication or an epigraph, with no heading tag
		special_item = TocItem()
		sections = soup.find_all('section')  # count the sections within this file
		special_item.level = len(sections)
		title_tag = soup.find('title')  # use page title as the ToC entry title
		special_item.title = title_tag.string
		special_item.filelink = textf
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
	test to see if there's nothing else in a title than a roman number.
	if so, we can collapse the epub type into the surrounding ToC <a> tag
	"""
	pattern = r'^<span epub:type="z3998:roman">[IVXLC]{1,10}<\/span>$'
	compiled_regex = regex.compile(pattern)
	return compiled_regex.search(title)


def process_heading(heading, is_toplevel, textf) -> TocItem:
	"""
	generate and return a TocItem from this heading
	"""
	tocitem = TocItem()
	parent_sections = heading.find_parents(['section', 'article'])
	tocitem.level = len(parent_sections)
	# this stops the first heading in a file getting an anchor id, which is what we want
	if is_toplevel:
		tocitem.id = ''
		tocitem.filelink = textf
	else:
		tocitem.id = get_parent_id(heading)
		if tocitem.id == '':
			tocitem.filelink = textf
		else:
			tocitem.filelink = textf + '#' + tocitem.id
	# a heading may include z3998:roman directly,
	# eg <h5 epub:type="title z3998:roman">II</h5>
	try:
		attribs = heading['epub:type']
	except KeyError:
		if verbose:
			print(textf + ': warning: heading with no epub:type')
		attribs = ''
	if 'z3998:roman' in attribs:
		tocitem.roman = extract_strings(heading)
		tocitem.title = '<span epub:type="z3998:roman">' + tocitem.roman + '</span>'
		return tocitem

	process_heading_contents(heading, tocitem)

	return tocitem


def process_heading_contents(heading, tocitem):
	"""
	go through each item in the heading contents
	and try to pull out the toc item data
	"""
	accumulator = ''  # we'll use this to build up the title
	for child in heading.contents:  # was children
		if child != '\n':
			if isinstance(child, Tag):
				try:
					epubtype = child['epub:type']
				except KeyError:
					epubtype = 'blank'
					if child.name == 'abbr':
						accumulator += extract_strings(child)
						continue  # skip following and go to next child

				if 'z3998:roman' in epubtype:
					tocitem.roman = extract_strings(child)
					accumulator += str(child)
				elif 'subtitle' in epubtype:
					tocitem.subtitle = extract_strings(child)
				elif 'title' in epubtype:
					tocitem.title = extract_strings(child)
				elif 'noteref' in epubtype:
					pass  # do nowt
				else:
					tocitem.title = extract_strings(child)
			else:  # should be a simple NavigableString
				accumulator += str(child)
	if tocitem.title == '':
		tocitem.title = accumulator


def process_all_content(filelist, textpath) -> (list, list):
	"""
	analyze the whole content of the project, build  and return lists
	if tocitems and landmarks
	"""
	toclist = []
	landmarks = []
	nest_under_halftitle = False
	for textf in filelist:
		if verbose:
			print('Processing: ' + textf)
		html_text = gethtml(os.path.join(textpath, textf))
		soup = BeautifulSoup(html_text, 'html.parser')
		place = get_place(soup)
		if place == Position.BACK:
			nest_under_halftitle = False
		process_headings(soup, textf, toclist, nest_under_halftitle)
		if textf == 'halftitle.xhtml':
			nest_under_halftitle = True
		add_landmark(soup, textf, landmarks)
	# we add this dummy item because outputtoc always needs to look ahead to the next item
	lasttoc = TocItem()
	lasttoc.level = 1
	lasttoc.title = "dummy"
	toclist.append(lasttoc)
	return landmarks, toclist


def make_toc(args):
	"""
	Entry point for 'se make-toc'
	"""
	rootpath = args.directory
	tocpath = os.path.join(rootpath, 'src', 'epub', 'toc.xhtml')
	textpath = os.path.join(rootpath, 'src', 'epub', 'text')
	opfpath = os.path.join(rootpath, 'src', 'epub', 'content.opf')

	temptext = gethtml(opfpath)
	opf = BeautifulSoup(temptext, 'html.parser')
	filelist = get_content_files(opf)
	worktitle = get_worktitle(opf)

	if not os.path.exists(opfpath):
		print("Error: this does not seem to be a Standard Ebooks root directory")
		exit(-1)

	if args.nonfiction is not None:
		worktype = 'non-fiction'
	else:
		worktype = 'fiction'

	global verbose
	verbose = args.verbose

	landmarks, toclist = process_all_content(filelist, textpath)

	outpath = tocpath
	if args.output is not None:
		outpath = args.output

	output_toc(toclist, landmarks, outpath, worktype, worktitle)

	if verbose:
		print(" OK")

	return 0
