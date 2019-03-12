#!/usr/bin/env python3
"""
This module contains the create_draft function and various helper functions.

It *could* be inlined in executables.py, but it's broken out into its own file for readability
and maintainability.
"""

import os
import shutil
from subprocess import call
import unicodedata
from typing import Union
import requests
import git
import regex
from pkg_resources import resource_filename
from ftfy import fix_text
from bs4 import BeautifulSoup
import se
import se.formatting


def _get_word_widths(string: str, target_height: int) -> list:
	"""
	Helper function.
	Given a string and a target letter height, return an array of words with their corresponding widths.

	INPUTS
	string: The string to inspect
	target_height: The target letter height, in pixels.

	OUTPUTS
	An array of objects. Each object represents a word and its corresponding width in pixels.
	"""

	words = []
	for word in reversed(string.split()):
		width = 0

		for char in word:
			# Convert accented characters to unaccented characters
			char = regex.sub(r"\p{M}", "", unicodedata.normalize("NFKD", char))
			width += (se.LEAGUE_SPARTAN_100_WIDTHS[char] * target_height / 100) + se.LEAGUE_SPARTAN_KERNING + se.LEAGUE_SPARTAN_AVERAGE_SPACING

		width = width - se.LEAGUE_SPARTAN_KERNING - se.LEAGUE_SPARTAN_AVERAGE_SPACING

		words.append({"word": word, "width": width})

	return words

def _calculate_image_lines(string: str, target_height: int, canvas_width: int) -> list:
	"""
	Helper function.
	Given a string, a target letter height, and the canvas width, return an array representing the string
	broken down into enough lines to fill the canvas without overflowing. Lines are ordered with the widest at the bottom.

	INPUTS
	string: The string to inspect
	target_height: The target letter height, in pixels
	canvas_width: The width of the canvas, in pixels

	OUTPUTS
	An array of strings. Each string represents one line of text in the final image. The lines are ordered with the widest at the bottom.
	"""

	words = _get_word_widths(string, target_height)
	lines = []
	current_line = ""
	current_width = 0

	for word in words:
		if current_width == 0:
			current_width = word["width"]
		else:
			current_width = current_width + (se.LEAGUE_SPARTAN_100_WIDTHS[" "] * target_height / 100) + word["width"]

		if current_width < canvas_width:
			current_line = word["word"] + " " + current_line
		else:
			if current_line.strip() != "":
				lines.append(current_line.strip())
			current_line = word["word"]
			current_width = word["width"]

	lines.append(current_line.strip())

	lines.reverse()

	return lines

def _generate_titlepage_svg(title: str, authors: Union[str, list], contributors: dict, title_string: str) -> str:
	"""
	Generate a draft of the titlepage SVG.
	The function tries to build the title with the widest line at the bottom, moving up.
	We approximate a few values, like the width of a space, which are variable in the font.

	INPUTS
	title: The title
	authors: an author, or an array of authors
	contributors: a dict in the form of: {"contributor descriptor": "contributor name(s)" ... }
	title_string: The SE titlestring (e.g. "The Rubáiyát of Omar Khayyám. Translated by Edward Fitzgerald. Illustrated by Edmund Dulac")

	OUTPUTS
	A string representing the complete SVG source code of the titlepage.
	"""

	svg = ""
	canvas_width = se.TITLEPAGE_WIDTH - (se.TITLEPAGE_HORIZONTAL_PADDING * 2)

	if not isinstance(authors, list):
		authors = [authors]

	# Read our template SVG to get some values before we begin
	with open(resource_filename("se", os.path.join("data", "templates", "titlepage.svg")), "r", encoding="utf-8") as file:
		svg = file.read()

	# Remove the template text elements from the SVG source, we'll write out to it later
	svg = regex.sub(r"\s*<text.+</svg>", "</svg>", svg, flags=regex.DOTALL).strip()

	# Calculate the title lines
	title_lines = _calculate_image_lines(title.upper().replace("'", "’"), se.TITLEPAGE_TITLE_HEIGHT, canvas_width)

	# Calculate the author lines
	authors_lines = []
	for author in authors:
		authors_lines.append(_calculate_image_lines(author.upper().replace("'", "’"), se.TITLEPAGE_AUTHOR_HEIGHT, canvas_width))

	# Calculate the contributor lines
	contributor_lines = []
	for descriptor, contributor in contributors.items():
		contributor_lines.append([descriptor, _calculate_image_lines(contributor.upper().replace("'", "’"), se.TITLEPAGE_CONTRIBUTOR_HEIGHT, canvas_width)])

	# Construct the output
	text_elements = ""
	element_y = se.TITLEPAGE_VERTICAL_PADDING

	# Add the title
	for line in title_lines:
		element_y += se.TITLEPAGE_TITLE_HEIGHT
		text_elements += "\t<text class=\"title\" x=\"700\" y=\"{:.0f}\">{}</text>\n".format(element_y, line)
		element_y += se.TITLEPAGE_TITLE_MARGIN

	element_y -= se.TITLEPAGE_TITLE_MARGIN

	# Add the author(s)
	element_y += se.TITLEPAGE_AUTHOR_SPACING

	for author_lines in authors_lines:
		for line in author_lines:
			element_y += se.TITLEPAGE_AUTHOR_HEIGHT
			text_elements += "\t<text class=\"author\" x=\"700\" y=\"{:.0f}\">{}</text>\n".format(element_y, line)
			element_y += se.TITLEPAGE_AUTHOR_MARGIN

	element_y -= se.TITLEPAGE_AUTHOR_MARGIN

	# Add the contributor(s)
	if contributor_lines:
		element_y += se.TITLEPAGE_CONTRIBUTORS_SPACING
		for contributor in contributor_lines:
			element_y += se.TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_HEIGHT
			text_elements += "\t<text class=\"contributor-descriptor\" x=\"700\" y=\"{:.0f}\">{}</text>\n".format(element_y, contributor[0])
			element_y += se.TITLEPAGE_CONTRIBUTOR_MARGIN

			for person in contributor[1]:
				element_y += se.TITLEPAGE_CONTRIBUTOR_HEIGHT
				text_elements += "\t<text class=\"contributor\" x=\"700\" y=\"{:.0f}\">{}</text>\n".format(element_y, person)
				element_y += se.TITLEPAGE_CONTRIBUTOR_MARGIN

			element_y -= se.TITLEPAGE_CONTRIBUTOR_MARGIN

			element_y += se.TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_MARGIN

		element_y -= se.TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_MARGIN
	else:
		# Remove unused CSS
		svg = regex.sub(r"\n\t\t\.contributor-descriptor{.+?}\n", "", svg, flags=regex.DOTALL)
		svg = regex.sub(r"\n\t\t\.contributor{.+?}\n", "", svg, flags=regex.DOTALL)

	element_y += se.TITLEPAGE_VERTICAL_PADDING

	svg = svg.replace("</svg>", "\n" + text_elements + "</svg>\n").replace("TITLESTRING", title_string)
	svg = regex.sub(r"viewBox=\".+?\"", "viewBox=\"0 0 1400 {:.0f}\"".format(element_y), svg)

	return svg

def _generate_cover_svg(title: str, authors: Union[str, list], title_string: str) -> str:
	"""
	Generate a draft of the cover SVG.
	The function tries to build the title box with the widest line at the bottom, moving up.
	We approximate a few values, like the width of a space, which are variable in the font.

	INPUTS
	title: The title
	authors: an author, or an array of authors
	title_string: The SE titlestring (e.g. "The Rubáiyát of Omar Khayyám. Translated by Edward Fitzgerald. Illustrated by Edmund Dulac")

	OUTPUTS
	A string representing the complete SVG source code of the cover page.
	"""

	svg = ""
	canvas_width = se.COVER_TITLE_BOX_WIDTH - (se.COVER_TITLE_BOX_PADDING * 2)

	title = title.replace("'", "’")
	authors = authors.replace("'", "’")
	title_string = title_string.replace("'", "’")

	if not isinstance(authors, list):
		authors = [authors]

	# Read our template SVG to get some values before we begin
	with open(resource_filename("se", os.path.join("data", "templates", "cover.svg")), "r", encoding="utf-8") as file:
		svg = file.read()

	# Remove the template text elements from the SVG source, we'll write out to it later
	svg = regex.sub(r"\s*<text.+</svg>", "</svg>", svg, flags=regex.DOTALL).strip()

	# Calculate the title lines
	title_height = se.COVER_TITLE_HEIGHT
	title_class = "title"
	title_lines = _calculate_image_lines(title.upper(), title_height, canvas_width)

	if len(title_lines) > 2:
		title_height = se.COVER_TITLE_SMALL_HEIGHT
		title_class = "title-small"
		title_lines = _calculate_image_lines(title.upper(), title_height, canvas_width)

	if len(title_lines) > 2:
		title_height = se.COVER_TITLE_XSMALL_HEIGHT
		title_class = "title-xsmall"
		title_lines = _calculate_image_lines(title.upper(), title_height, canvas_width)

	# Calculate the author lines
	authors_lines = []
	for author in authors:
		authors_lines.append(_calculate_image_lines(author.upper(), se.COVER_AUTHOR_HEIGHT, canvas_width))

	# Construct the output
	text_elements = ""
	element_y = se.COVER_TITLE_BOX_Y + \
		+ ((se.COVER_TITLE_BOX_HEIGHT \
			- ((len(title_lines) * title_height) \
				+ ((len(title_lines) - 1) * se.COVER_TITLE_MARGIN) \
				+ se.COVER_AUTHOR_SPACING \
				+ (len(authors_lines) * se.COVER_AUTHOR_HEIGHT) \
		)) / 2)

	# Add the title
	for line in title_lines:
		element_y += title_height
		text_elements += "\t<text class=\"{}\" x=\"700\" y=\"{:.0f}\">{}</text>\n".format(title_class, element_y, line)
		element_y += se.COVER_TITLE_MARGIN

	element_y -= se.COVER_TITLE_MARGIN

	# Add the author(s)
	element_y += se.COVER_AUTHOR_SPACING

	for author_lines in authors_lines:
		for line in author_lines:
			element_y += se.COVER_AUTHOR_HEIGHT
			text_elements += "\t<text class=\"author\" x=\"700\" y=\"{:.0f}\">{}</text>\n".format(element_y, line)
			element_y += se.COVER_AUTHOR_MARGIN

	element_y -= se.COVER_AUTHOR_MARGIN

	# Remove unused CSS
	if title_class != "title":
		svg = regex.sub(r"\n\n\t\t\.title\{.+?\}", "", svg, flags=regex.DOTALL)

	if title_class != "title-small":
		svg = regex.sub(r"\n\n\t\t\.title-small\{.+?\}", "", svg, flags=regex.DOTALL)

	if title_class != "title-xsmall":
		svg = regex.sub(r"\n\n\t\t\.title-xsmall\{.+?\}", "", svg, flags=regex.DOTALL)

	svg = svg.replace("</svg>", "\n" + text_elements + "</svg>\n").replace("TITLESTRING", title_string)

	return svg

def _get_wikipedia_url(string: str, get_nacoaf_url: bool) -> (str, str):
	"""
	Helper function.
	Given a string, try to see if there's a Wikipedia page entry for that string.

	INPUTS
	string: The string to find on Wikipedia
	get_nacoaf_url: Include NACOAF URL in resulting tuple, if found?

	OUTPUTS
	A tuple of two strings. The first string is the Wikipedia URL, the second is the NACOAF URL.
	"""

	# We try to get the Wikipedia URL by the subject by taking advantage of the fact that Wikipedia's special search will redirect you immediately
	# if there's an article match.  So if the search page tries to redirect us, we use that redirect link as the Wiki URL.  If the search page
	# returns HTTP 200, then we didn't find a direct match and return nothing.

	try:
		response = requests.get("https://en.wikipedia.org/wiki/Special:Search", params={"search": string, "go": "Go"}, allow_redirects=False)
	except Exception as ex:
		se.print_error("Couldn’t contact Wikipedia. Error: {}".format(ex))

	if response.status_code == 302:
		nacoaf_url = None
		wiki_url = response.headers["Location"]

		if get_nacoaf_url:
			try:
				response = requests.get(wiki_url)
			except Exception as ex:
				se.print_error("Couldn’t contact Wikipedia. Error: {}".format(ex))

			for match in regex.findall(r"http://id\.loc\.gov/authorities/names/n[0-9]+", response.text):
				nacoaf_url = match

		return wiki_url, nacoaf_url

	return None, None

def create_draft(args: list) -> int:
	"""
	Entry point for `se create-draft`
	"""

	if args.create_github_repo and not args.create_se_repo:
		se.print_error("--create-github-repo option specified, but --create-se-repo option not specified.")
		return se.InvalidInputException.code

	if args.pg_url and not regex.match("^https?://www.gutenberg.org/ebooks/[0-9]+$", args.pg_url):
		se.print_error("Project Gutenberg URL must look like: https://www.gutenberg.org/ebooks/<EBOOK-ID>")
		return se.InvalidInputException.code

	# Put together some variables for later use
	identifier = se.formatting.make_url_safe(args.author) + "/" + se.formatting.make_url_safe(args.title)
	title_string = args.title.replace("'", "’") + ", by " + args.author.replace("'", "’")
	sorted_title = regex.sub(r"^(A|An|The) (.+)$", "\\2, \\1", args.title)
	pg_producers = []

	if args.translator:
		identifier = identifier + "/" + se.formatting.make_url_safe(args.translator)
		title_string = title_string + ". Translated by " + args.translator

	if args.illustrator:
		identifier = identifier + "/" + se.formatting.make_url_safe(args.illustrator)
		title_string = title_string + ". Illustrated by " + args.illustrator

	repo_name = identifier.replace("/", "_")

	if os.path.isdir(repo_name):
		se.print_error("./{}/ already exists.".format(repo_name))
		return se.InvalidInputException.code

	# Download PG HTML and do some fixups
	if args.pg_url:
		args.pg_url = args.pg_url.replace("http://", "https://")

		# Get the ebook metadata
		try:
			response = requests.get(args.pg_url)
			pg_metadata_html = response.text
		except Exception as ex:
			se.print_error("Couldn’t download Project Gutenberg ebook metadata page. Error: {}".format(ex))
			return se.RemoteCommandErrorException.code

		soup = BeautifulSoup(pg_metadata_html, "lxml")

		# Get the ebook HTML URL from the metadata
		pg_ebook_url = None
		for element in soup.select("a[type^=\"text/html\"]"):
			pg_ebook_url = regex.sub("^//", "https://", element["href"])

		if not pg_ebook_url:
			se.print_error("Could download ebook metadata, but couldn’t find URL for the ebook HTML.")
			return se.RemoteCommandErrorException.code

		# Get the ebook LCSH categories
		pg_subjects = []
		for element in soup.select("td[property=\"dcterms:subject\"]"):
			if element["datatype"] == "dcterms:LCSH":
				for subject_link in element.find("a"):
					pg_subjects.append(subject_link.strip())

		# Get the PG publication date
		pg_publication_year = None
		for element in soup.select("td[itemprop=\"datePublished\"]"):
			pg_publication_year = regex.sub(r".+?([0-9]{4})", "\\1", element.text)

		# Get the actual ebook URL
		try:
			response = requests.get(pg_ebook_url)
			pg_ebook_html = response.text
		except Exception as ex:
			se.print_error("Couldn’t download Project Gutenberg ebook HTML. Error: {}".format(ex))
			return se.RemoteCommandErrorException.code

		try:
			fixed_pg_ebook_html = fix_text(pg_ebook_html, uncurl_quotes=False)
			pg_ebook_html = se.strip_bom(fixed_pg_ebook_html)
		except Exception as ex:
			se.print_error("Couldn’t determine text encoding of Project Gutenberg HTML file. Error: {}".format(ex))
			return se.InvalidEncodingException.code

		# Try to guess the ebook language
		pg_language = "en-US"
		if "colour" in pg_ebook_html or "favour" in pg_ebook_html or "honour" in pg_ebook_html:
			pg_language = "en-GB"

	# Create necessary directories
	os.makedirs(os.path.join(repo_name, "images"))
	os.makedirs(os.path.join(repo_name, "src", "epub", "css"))
	os.makedirs(os.path.join(repo_name, "src", "epub", "images"))
	os.makedirs(os.path.join(repo_name, "src", "epub", "text"))
	os.makedirs(os.path.join(repo_name, "src", "META-INF"))

	# Write PG data if we have it
	if args.pg_url and pg_ebook_html:
		soup = BeautifulSoup(pg_ebook_html, "html.parser")

		# Try to get the PG producers.  We only try this if there's a <pre> block with the header info (which is not always the case)
		for element in soup(text=regex.compile(r"\*\*\*\s*Produced by.+$", flags=regex.DOTALL)):
			if element.parent.name == "pre":
				pg_producers = regex.sub(r".+?Produced by (.+?)\s*$", "\\1", element, flags=regex.DOTALL)
				pg_producers = regex.sub(r"\(.+?\)", "", pg_producers, flags=regex.DOTALL)
				pg_producers = regex.sub(r"(at )?https?://www\.pgdp\.net", "", pg_producers, flags=regex.DOTALL)
				pg_producers = regex.sub(r"[\r\n]+", " ", pg_producers, flags=regex.DOTALL)
				pg_producers = regex.sub(r",? and ", ", and ", pg_producers)
				pg_producers = pg_producers.replace(" and the Online", " and The Online")
				pg_producers = pg_producers.replace(", and ", ", ").strip().split(", ")

		# Try to strip out the PG header
		for element in soup(text=regex.compile(r"\*\*\*\s*START OF THIS")):
			for sibling in element.parent.find_previous_siblings():
				sibling.decompose()

			element.parent.decompose()

		# Try to strip out the PG license footer
		for element in soup(text=regex.compile(r"End of (the )?Project Gutenberg")):
			for sibling in element.parent.find_next_siblings():
				sibling.decompose()

			element.parent.decompose()

		with open(os.path.join(repo_name, "src", "epub", "text", "body.xhtml"), "w", encoding="utf-8") as file:
			file.write(str(soup))

	# Copy over templates
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "gitignore")), os.path.normpath(repo_name + "/.gitignore"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "LICENSE.md")), os.path.normpath(repo_name + "/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "META-INF", "container.xml")), os.path.normpath(repo_name + "/src/META-INF/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "mimetype")), os.path.normpath(repo_name + "/src/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "content.opf")), os.path.normpath(repo_name + "/src/epub/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "onix.xml")), os.path.normpath(repo_name + "/src/epub/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "toc.xhtml")), os.path.normpath(repo_name + "/src/epub/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "core.css")), os.path.normpath(repo_name + "/src/epub/css/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "local.css")), os.path.normpath(repo_name + "/src/epub/css/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "logo.svg")), os.path.normpath(repo_name + "/src/epub/images/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "colophon.xhtml")), os.path.normpath(repo_name + "/src/epub/text/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "imprint.xhtml")), os.path.normpath(repo_name + "/src/epub/text/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "titlepage.xhtml")), os.path.normpath(repo_name + "/src/epub/text/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "uncopyright.xhtml")), os.path.normpath(repo_name + "/src/epub/text/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "titlepage.svg")), os.path.normpath(repo_name + "/images/"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "cover.jpg")), os.path.normpath(repo_name + "/images/cover.jpg"))
	shutil.copy(resource_filename("se", os.path.join("data", "templates", "cover.svg")), os.path.normpath(repo_name + "/images/cover.svg"))

	# Try to find Wikipedia links if possible
	author_wiki_url, author_nacoaf_url = _get_wikipedia_url(args.author, True)
	ebook_wiki_url, _ = _get_wikipedia_url(args.title, False)
	translator_wiki_url = None
	if args.translator:
		translator_wiki_url, translator_nacoaf_url = _get_wikipedia_url(args.translator, True)

	# Pre-fill a few templates
	se.replace_in_file(os.path.normpath(repo_name + "/src/epub/text/titlepage.xhtml"), "TITLESTRING", title_string)
	se.replace_in_file(os.path.normpath(repo_name + "/images/titlepage.svg"), "TITLESTRING", title_string)
	se.replace_in_file(os.path.normpath(repo_name + "/images/cover.svg"), "TITLESTRING", title_string)

	# Create the titlepage SVG
	contributors = {}
	if args.translator:
		contributors["translated by"] = args.translator

	if args.illustrator:
		contributors["illustrated by"] = args.illustrator

	with open(os.path.join(repo_name, "images", "titlepage.svg"), "w", encoding="utf-8") as file:
		file.write(_generate_titlepage_svg(args.title, args.author, contributors, title_string))

	# Create the cover SVG
	with open(os.path.join(repo_name, "images", "cover.svg"), "w", encoding="utf-8") as file:
		file.write(_generate_cover_svg(args.title, args.author, title_string))

	if args.pg_url:
		se.replace_in_file(os.path.normpath(repo_name + "/src/epub/text/imprint.xhtml"), "PG_URL", args.pg_url)

	with open(os.path.join(repo_name, "src", "epub", "text", "colophon.xhtml"), "r+", encoding="utf-8") as file:
		colophon_xhtml = file.read()

		colophon_xhtml = colophon_xhtml.replace("SE_IDENTIFIER", identifier)
		colophon_xhtml = colophon_xhtml.replace(">AUTHOR<", ">{}<".format(args.author))
		colophon_xhtml = colophon_xhtml.replace("TITLE", args.title)

		if author_wiki_url:
			colophon_xhtml = colophon_xhtml.replace("AUTHOR_WIKI_URL", author_wiki_url)

		if args.pg_url:
			colophon_xhtml = colophon_xhtml.replace("PG_URL", args.pg_url)

			if pg_publication_year:
				colophon_xhtml = colophon_xhtml.replace("PG_YEAR", pg_publication_year)

			if pg_producers:
				producers_xhtml = ""
				for i, producer  in enumerate(pg_producers):
					if "Distributed Proofreading" in producer:
						producers_xhtml = producers_xhtml + "<a href=\"https://www.pgdp.net\">The Online Distributed Proofreading Team</a>"
					else:
						producers_xhtml = producers_xhtml + "<b class=\"name\">{}</b>".format(producer)

					if i < len(pg_producers) - 1:
						producers_xhtml = producers_xhtml + ", "

					if i == len(pg_producers) - 2:
						producers_xhtml = producers_xhtml + "and "

				producers_xhtml = producers_xhtml + "<br/>"

				colophon_xhtml = colophon_xhtml.replace("<b class=\"name\">TRANSCRIBER_1</b>, <b class=\"name\">TRANSCRIBER_2</b>, and <a href=\"https://www.pgdp.net\">The Online Distributed Proofreading Team</a><br/>", producers_xhtml)

		file.seek(0)
		file.write(colophon_xhtml)
		file.truncate()

	with open(os.path.join(repo_name, "src", "epub", "content.opf"), "r+", encoding="utf-8") as file:
		metadata_xhtml = file.read()

		metadata_xhtml = metadata_xhtml.replace("SE_IDENTIFIER", identifier)
		metadata_xhtml = metadata_xhtml.replace(">AUTHOR<", ">{}<".format(args.author))
		metadata_xhtml = metadata_xhtml.replace(">TITLE_SORT<", ">{}<".format(sorted_title))
		metadata_xhtml = metadata_xhtml.replace(">TITLE<", ">{}<".format(args.title))
		metadata_xhtml = metadata_xhtml.replace("VCS_IDENTIFIER", repo_name)

		if pg_producers:
			producers_xhtml = ""
			i = 1
			for producer in pg_producers:
				producers_xhtml = producers_xhtml + "\t\t<dc:contributor id=\"transcriber-{}\">{}</dc:contributor>\n".format(i, producer)

				if "Distributed Proofreading" in producer:
					producers_xhtml = producers_xhtml + "\t\t<meta property=\"file-as\" refines=\"#transcriber-{}\">Online Distributed Proofreading Team, The</meta>\n\t\t<meta property=\"se:url.homepage\" refines=\"#transcriber-{}\">https://pgdp.net</meta>\n".format(i, i)
				else:
					producers_xhtml = producers_xhtml + "\t\t<meta property=\"file-as\" refines=\"#transcriber-{}\">TRANSCRIBER_SORT</meta>\n".format(i)

				producers_xhtml = producers_xhtml + "\t\t<meta property=\"role\" refines=\"#transcriber-{}\" scheme=\"marc:relators\">trc</meta>\n".format(i)

				i = i + 1

			metadata_xhtml = regex.sub(r"\t\t<dc:contributor id=\"transcriber-1\">TRANSCRIBER</dc:contributor>\s*<meta property=\"file-as\" refines=\"#transcriber-1\">TRANSCRIBER_SORT</meta>\s*<meta property=\"se:url.homepage\" refines=\"#transcriber-1\">TRANSCRIBER_URL</meta>\s*<meta property=\"role\" refines=\"#transcriber-1\" scheme=\"marc:relators\">trc</meta>", "\t\t" + producers_xhtml.strip(), metadata_xhtml, flags=regex.DOTALL)

		if author_wiki_url:
			metadata_xhtml = metadata_xhtml.replace(">AUTHOR_WIKI_URL<", ">{}<".format(author_wiki_url))

		if author_nacoaf_url:
			metadata_xhtml = metadata_xhtml.replace(">AUTHOR_NACOAF_URL<", ">{}<".format(author_nacoaf_url))

		if ebook_wiki_url:
			metadata_xhtml = metadata_xhtml.replace(">EBOOK_WIKI_URL<", ">{}<".format(ebook_wiki_url))

		if args.translator:
			metadata_xhtml = metadata_xhtml.replace(">TRANSLATOR<", ">{}<".format(args.translator))

			if translator_wiki_url:
				metadata_xhtml = metadata_xhtml.replace(">TRANSLATOR_WIKI_URL<", ">{}<".format(translator_wiki_url))

			if translator_nacoaf_url:
				metadata_xhtml = metadata_xhtml.replace(">TRANSLATOR_NACOAF_URL<", ">{}<".format(translator_nacoaf_url))
		else:
			metadata_xhtml = regex.sub(r"<dc:contributor id=\"translator\">.+?<dc:contributor id=\"artist\">", "<dc:contributor id=\"artist\">", metadata_xhtml, flags=regex.DOTALL)

		if args.pg_url:
			if pg_subjects:
				subject_xhtml = ""

				i = 1
				for subject in pg_subjects:
					subject_xhtml = subject_xhtml + "\t\t<dc:subject id=\"subject-{}\">{}</dc:subject>\n".format(i, subject)
					i = i + 1

				i = 1
				for subject in pg_subjects:
					subject_xhtml = subject_xhtml + "\t\t<meta property=\"meta-auth\" refines=\"#subject-{}\">{}</meta>\n".format(i, args.pg_url)
					i = i + 1

				metadata_xhtml = regex.sub(r"\t\t<dc:subject id=\"subject-1\">SUBJECT_1</dc:subject>\s*<dc:subject id=\"subject-2\">SUBJECT_2</dc:subject>\s*<meta property=\"meta-auth\" refines=\"#subject-1\">LOC_URL_1</meta>\s*<meta property=\"meta-auth\" refines=\"#subject-2\">LOC_URL_2</meta>", "\t\t" + subject_xhtml.strip(), metadata_xhtml)

			metadata_xhtml = metadata_xhtml.replace("<dc:language>LANG</dc:language>", "<dc:language>{}</dc:language>".format(pg_language))
			metadata_xhtml = metadata_xhtml.replace("<dc:source>PG_URL</dc:source>", "<dc:source>{}</dc:source>".format(args.pg_url))

		file.seek(0)
		file.write(metadata_xhtml)
		file.truncate()

	# Set up local git repo
	repo = git.Repo.init(repo_name)

	if args.email:
		with repo.config_writer() as config:
			config.set_value("user", "email", args.email)

	# Set up remote git repos
	if args.create_se_repo:
		git_command = git.cmd.Git(repo_name)
		git_command.remote("add", "origin", "standardebooks.org:/standardebooks.org/ebooks/{}.git".format(repo_name))

		# Set git to automatically push to SE
		git_command.config("branch.master.remote", "origin")
		git_command.config("branch.master.merge", "refs/heads/master")

		github_option = ""
		if args.create_github_repo:
			github_option = "--github"

		return_code = call(["ssh", "standardebooks.org", "/standardebooks.org/scripts/init-se-repo --repo-name={} --title-string=\"{}\" {}".format(repo_name, title_string, github_option)])
		if return_code != 0:
			se.print_error("Failed to create repository on Standard Ebooks server: ssh returned code {}.".format(return_code))
			return se.RemoteCommandErrorException.code

	return 0
