"""
This module implements the `se create_draft` command.
"""

import argparse
from io import StringIO
import shutil
import urllib.parse
from argparse import Namespace
from pathlib import Path
from typing import Optional, Tuple, Union, List, Dict

import git
import importlib_resources
import regex
import requests
from rich.console import Console
from ftfy import fix_text
from lxml import etree
from unidecode import unidecode

import se
import se.formatting
from se.se_epub import SeEpub


COVER_TITLE_BOX_Y = 1620 # In px; note that in SVG, Y starts from the TOP of the image
COVER_TITLE_BOX_HEIGHT = 430
COVER_TITLE_BOX_WIDTH = 1300
COVER_TITLE_BOX_PADDING = 100
COVER_TITLE_MARGIN = 20
COVER_TITLE_HEIGHT = 80
COVER_TITLE_SMALL_HEIGHT = 60
COVER_TITLE_XSMALL_HEIGHT = 50
COVER_AUTHOR_SPACING = 60
COVER_AUTHOR_HEIGHT = 40
COVER_AUTHOR_MARGIN = 20
TITLEPAGE_VERTICAL_PADDING = 50
TITLEPAGE_HORIZONTAL_PADDING = 100
TITLEPAGE_TITLE_HEIGHT = 80 # Height of each title line
TITLEPAGE_TITLE_MARGIN = 20 # Space between consecutive title lines
TITLEPAGE_AUTHOR_SPACING = 100 # Space between last title line and first author line
TITLEPAGE_AUTHOR_HEIGHT = 60 # Height of each author line
TITLEPAGE_AUTHOR_MARGIN = 20 # Space between consecutive author lines
TITLEPAGE_CONTRIBUTORS_SPACING = 150 # Space between last author line and first contributor descriptor
TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_HEIGHT = 40 # Height of each contributor descriptor line
TITLEPAGE_CONTRIBUTOR_HEIGHT = 40 # Height of each contributor line
TITLEPAGE_CONTRIBUTOR_MARGIN = 20 # Space between contributor descriptor and contributor line, and between sequential contributor lines
TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_MARGIN = 80 # Space between last contributor line and next contributor descriptor (if more than one contributor descriptor)
LEAGUE_SPARTAN_KERNING = 5 # In px
LEAGUE_SPARTAN_AVERAGE_SPACING = 7 # Guess at average default spacing between letters, in px
LEAGUE_SPARTAN_100_WIDTHS = {" ": 40.0, "A": 98.245, "B": 68.1875, "C": 83.97625, "D": 76.60875, "E": 55.205, "F": 55.79, "G": 91.57875, "H": 75.0875, "I": 21.98875, "J": 52.631254, "K": 87.83625, "L": 55.205, "M": 106.9, "N": 82.5725, "O": 97.1925, "P": 68.1875, "Q": 98.83, "R": 79.41599, "S": 72.63125, "T": 67.83625, "U": 75.32125, "V": 98.245, "W": 134.62, "X": 101.28625, "Y": 93.1, "Z": 86.19875, ".": 26.78375, ",": 26.78375, "/": 66.08125, "\\": 66.08125, "-": 37.66125, ":": 26.78375, ";": 26.78375, "’": 24.3275, "!": 26.78375, "?": 64.3275, "&": 101.87125, "0": 78.48, "1": 37.895, "2": 75.205, "3": 72.04625, "4": 79.29875, "5": 70.175, "6": 74.26875, "7": 76.95875, "8": 72.16375, "9": 74.26875}

CONTRIBUTOR_BLOCK_TEMPLATE = """<dc:contributor id="CONTRIBUTOR_ID">CONTRIBUTOR_NAME</dc:contributor>
		<meta property="file-as" refines="#CONTRIBUTOR_ID">CONTRIBUTOR_SORT</meta>
		<meta property="se:name.person.full-name" refines="#CONTRIBUTOR_ID">CONTRIBUTOR_FULL_NAME</meta>
		<meta property="se:url.encyclopedia.wikipedia" refines="#CONTRIBUTOR_ID">CONTRIBUTOR_WIKI_URL</meta>
		<meta property="se:url.authority.nacoaf" refines="#CONTRIBUTOR_ID">CONTRIBUTOR_NACOAF_URI</meta>
		<meta property="role" refines="#CONTRIBUTOR_ID" scheme="marc:relators">CONTRIBUTOR_MARC</meta>"""

def _replace_in_file(file_path: Path, search: Union[str, list], replace: Union[str, list]) -> None:
	"""
	Helper function to replace in a file.
	"""

	with open(file_path, "r+", encoding="utf-8") as file:
		data = file.read()
		processed_data = data

		if isinstance(search, list):
			for index, val in enumerate(search):
				if replace[index] is not None:
					processed_data = processed_data.replace(val, replace[index])
		else:
			processed_data = processed_data.replace(search, str(replace))

		if processed_data != data:
			file.seek(0)
			file.write(processed_data)
			file.truncate()

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
			char = unidecode(char)
			width += int(LEAGUE_SPARTAN_100_WIDTHS[char] * target_height / 100) + LEAGUE_SPARTAN_KERNING + LEAGUE_SPARTAN_AVERAGE_SPACING

		width = width - LEAGUE_SPARTAN_KERNING - LEAGUE_SPARTAN_AVERAGE_SPACING

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
			current_width = current_width + (LEAGUE_SPARTAN_100_WIDTHS[" "] * target_height / 100) + word["width"]

		if current_width < canvas_width:
			current_line = word["word"] + " " + current_line
		else:
			if current_line.strip() != "":
				lines.append(current_line.strip())
			current_line = word["word"]
			current_width = word["width"]

	lines.append(current_line.strip())

	lines.reverse()

	# If the first line is a single short word, move up the first word of the next line
	if len(lines[0]) <= 3 and len(lines) > 1:
		first_word = regex.match(r"^[\p{Letter}]+(?=\s)", lines[1])

		if first_word:
			lines[0] = lines[0] + " " + first_word.group(0)
			lines[1] = regex.sub(rf"^{regex.escape(first_word.group(0))}\s+", "", lines[1])

	return lines

def _generate_titlepage_svg(title: str, authors: List[str], contributors: dict, title_string: str) -> str:
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

	# Don't include "anonymous" authors in the cover
	authors = [author for author in authors if author.lower() != "anonymous"]

	svg = ""
	canvas_width = se.TITLEPAGE_WIDTH - (TITLEPAGE_HORIZONTAL_PADDING * 2)

	# Read our template SVG to get some values before we begin
	with importlib_resources.open_text("se.data.templates", "titlepage.svg", encoding="utf-8") as file:
		svg = file.read()

	# Remove the template text elements from the SVG source, we'll write out to it later
	svg = regex.sub(r"\s*<text.+</svg>", "</svg>", svg, flags=regex.DOTALL).strip()

	# Calculate the title lines
	title_lines = _calculate_image_lines(title.upper(), TITLEPAGE_TITLE_HEIGHT, canvas_width)

	# Calculate the author lines
	authors_lines = []
	for author in authors:
		authors_lines.append(_calculate_image_lines(author.upper(), TITLEPAGE_AUTHOR_HEIGHT, canvas_width))

	# Calculate the contributor lines
	contributor_lines = []
	for descriptor, contributor in contributors.items():
		contributor_lines.append([descriptor, _calculate_image_lines(contributor.upper(), TITLEPAGE_CONTRIBUTOR_HEIGHT, canvas_width)])

	# Construct the output
	text_elements = ""
	element_y = TITLEPAGE_VERTICAL_PADDING

	# Add the title
	for line in title_lines:
		element_y += TITLEPAGE_TITLE_HEIGHT
		text_elements += f"\t<text class=\"title\" x=\"700\" y=\"{element_y:.0f}\">{line}</text>\n"
		element_y += TITLEPAGE_TITLE_MARGIN

	element_y -= TITLEPAGE_TITLE_MARGIN

	# Add the author(s)
	if authors:
		element_y += TITLEPAGE_AUTHOR_SPACING

	for author_lines in authors_lines:
		for line in author_lines:
			element_y += TITLEPAGE_AUTHOR_HEIGHT
			text_elements += f"\t<text class=\"author\" x=\"700\" y=\"{element_y:.0f}\">{line}</text>\n"
			element_y += TITLEPAGE_AUTHOR_MARGIN

	if authors:
		element_y -= TITLEPAGE_AUTHOR_MARGIN

	# Add the contributor(s)
	if contributor_lines:
		element_y += TITLEPAGE_CONTRIBUTORS_SPACING
		for contributor in contributor_lines:
			element_y += TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_HEIGHT
			text_elements += f"\t<text class=\"contributor-descriptor\" x=\"700\" y=\"{element_y:.0f}\">{contributor[0]}</text>\n"
			element_y += TITLEPAGE_CONTRIBUTOR_MARGIN

			for person in contributor[1]:
				element_y += TITLEPAGE_CONTRIBUTOR_HEIGHT
				text_elements += f"\t<text class=\"contributor\" x=\"700\" y=\"{element_y:.0f}\">{person}</text>\n"
				element_y += TITLEPAGE_CONTRIBUTOR_MARGIN

			element_y -= TITLEPAGE_CONTRIBUTOR_MARGIN

			element_y += TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_MARGIN

		element_y -= TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_MARGIN
	else:
		# Remove unused CSS
		svg = regex.sub(r"\n\t\t\.contributor-descriptor{.+?}\n", "", svg, flags=regex.DOTALL)
		svg = regex.sub(r"\n\t\t\.contributor{.+?}\n", "", svg, flags=regex.DOTALL)

	element_y += TITLEPAGE_VERTICAL_PADDING

	svg = svg.replace("</svg>", "\n" + text_elements + "</svg>\n").replace("TITLE_STRING", title_string)
	svg = regex.sub(r"viewBox=\".+?\"", f"viewBox=\"0 0 {se.TITLEPAGE_WIDTH} {element_y:.0f}\"", svg)

	return svg

def _generate_cover_svg(title: str, authors: List[str], title_string: str) -> str:
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

	# Don't include "anonymous" authors in the cover
	authors = [author for author in authors if author.lower() != "anonymous"]

	svg = ""
	canvas_width = COVER_TITLE_BOX_WIDTH - (COVER_TITLE_BOX_PADDING * 2)

	# Read our template SVG to get some values before we begin
	with importlib_resources.open_text("se.data.templates", "cover.svg", encoding="utf-8") as file:
		svg = file.read()

	# Remove the template text elements from the SVG source, we'll write out to it later
	svg = regex.sub(r"\s*<text.+</svg>", "</svg>", svg, flags=regex.DOTALL).strip()

	# Calculate the title lines
	title_height = COVER_TITLE_HEIGHT
	title_class = "title"
	title_lines = _calculate_image_lines(title.upper(), title_height, canvas_width)

	if len(title_lines) > 2:
		title_height = COVER_TITLE_SMALL_HEIGHT
		title_class = "title-small"
		title_lines = _calculate_image_lines(title.upper(), title_height, canvas_width)

	if len(title_lines) > 2:
		title_height = COVER_TITLE_XSMALL_HEIGHT
		title_class = "title-xsmall"
		title_lines = _calculate_image_lines(title.upper(), title_height, canvas_width)

	# Calculate the author lines
	authors_lines = []
	for author in authors:
		authors_lines.append(_calculate_image_lines(author.upper(), COVER_AUTHOR_HEIGHT, canvas_width))

	# Construct the output
	text_elements = ""
	spacing = COVER_AUTHOR_SPACING
	if not authors:
		spacing = 0
	element_y = COVER_TITLE_BOX_Y + \
		+ ((COVER_TITLE_BOX_HEIGHT \
			- ((len(title_lines) * title_height) \
				+ ((len(title_lines) - 1) * COVER_TITLE_MARGIN) \
				+ spacing \
				+ (len(authors_lines) * COVER_AUTHOR_HEIGHT) \
		)) / 2)

	# Add the title
	for line in title_lines:
		element_y += title_height
		text_elements += f"\t<text class=\"{title_class}\" x=\"700\" y=\"{element_y:.0f}\">{line}</text>\n"
		element_y += COVER_TITLE_MARGIN

	element_y -= COVER_TITLE_MARGIN

	# Add the author(s)
	if authors:
		element_y += COVER_AUTHOR_SPACING

		for author_lines in authors_lines:
			for line in author_lines:
				element_y += COVER_AUTHOR_HEIGHT
				text_elements += f"\t<text class=\"author\" x=\"700\" y=\"{element_y:.0f}\">{line}</text>\n"
				element_y += COVER_AUTHOR_MARGIN

		element_y -= COVER_AUTHOR_MARGIN

	# Remove unused CSS
	if title_class != "title":
		svg = regex.sub(r"\n\n\t\t\.title\{.+?\}", "", svg, flags=regex.DOTALL)

	if title_class != "title-small":
		svg = regex.sub(r"\n\n\t\t\.title-small\{.+?\}", "", svg, flags=regex.DOTALL)

	if title_class != "title-xsmall":
		svg = regex.sub(r"\n\n\t\t\.title-xsmall\{.+?\}", "", svg, flags=regex.DOTALL)

	svg = svg.replace("</svg>", "\n" + text_elements + "</svg>\n").replace("TITLE_STRING", title_string)

	return svg

def _get_wikipedia_url(string: str, get_nacoaf_uri: bool) -> Tuple[Optional[str], Optional[str]]:
	"""
	Given a string, try to see if there's a Wikipedia page entry, and an optional NACOAF entry, for that string.

	INPUTS
	string: The string to find on Wikipedia
	get_nacoaf_uri: Include NACOAF URI in resulting tuple, if found?

	OUTPUTS
	A tuple of two strings. The first string is the Wikipedia URL, the second is the NACOAF URI.
	"""

	# We try to get the Wikipedia URL by the subject by taking advantage of the fact that Wikipedia's special search will redirect you immediately
	# if there's an article match.  So if the search page tries to redirect us, we use that redirect link as the Wiki URL.  If the search page
	# returns HTTP 200, then we didn't find a direct match and return nothing.

	try:
		response = requests.get("https://en.wikipedia.org/wiki/Special:Search", params={"search": string, "go": "Go", "ns0": "1"}, allow_redirects=False)
	except Exception as ex:
		se.print_error(f"Couldn’t contact Wikipedia. Exception: {ex}")

	if response.status_code == 302:
		nacoaf_uri = None
		wiki_url = response.headers["Location"]
		if urllib.parse.urlparse(wiki_url).path == "/wiki/Special:Search":
			# Redirected back to search URL, no match
			return None, None

		if get_nacoaf_uri:
			try:
				response = requests.get(wiki_url)
			except Exception as ex:
				se.print_error(f"Couldn’t contact Wikipedia. Exception: {ex}")

			for match in regex.findall(r"https?://id\.loc\.gov/authorities/names/n[0-9]+", response.text):
				nacoaf_uri = match.replace("https:","http:")

		return wiki_url, nacoaf_uri

	return None, None

def _copy_template_file(filename: str, dest_path: Path) -> None:
	"""
	Copy a template file to the given destination Path
	"""
	with importlib_resources.path("se.data.templates", filename) as src_path:
		shutil.copy(src_path, dest_path)

def _add_name_abbr(contributor: str) -> str:
	"""
	Add <abbr class="name"> around contributor names
	"""

	contributor = regex.sub(r"([\p{Uppercase_Letter}]\.(?:\s*[\p{Uppercase_Letter}]\.)*)", r"""<abbr class="name">\1</abbr>""", contributor)

	return contributor


def _generate_contributor_string(contributors: List[Dict], include_xhtml: bool) -> str:
	"""
	Given a list of contributors, generate a contributor string like `Bob Smith, Jane Doe, and Sam Johnson`.
	With include_xhtml, the string looks like: `<b class="name">Bob Smith</b>, <a href="https://en.wikipedia.org/wiki/Jane_Doe">Jane Doe</a>, and <b class="name">Sam Johnson</b>`

	INPUTS
	contributors: A list of contributor dicts
	include_xhtml: Include <b> or <a> for each contributor, making the output suitable for the coloiphon

	OUTPUTS
	A string of XML representing the contributors
	"""

	output = ""

	# Don't include "anonymous" contributors
	contributors = [contributor for contributor in contributors if contributor["name"].lower() != "anonymous"]

	if len(contributors) == 1:
		if include_xhtml:
			if contributors[0]["wiki_url"]:
				output += f"<a href=\"{contributors[0]['wiki_url']}\">{_add_name_abbr(contributors[0]['name'])}</a>"
			else:
				output += f"<b class=\"name\">{_add_name_abbr(contributors[0]['name'])}</b>"
		else:
			output += contributors[0]["name"]

	elif len(contributors) == 2:
		if include_xhtml:
			if contributors[0]["wiki_url"]:
				output += f"<a href=\"{contributors[0]['wiki_url']}\">{_add_name_abbr(contributors[0]['name'])}</a>"
			else:
				output += f"<b class=\"name\">{_add_name_abbr(contributors[0]['name'])}</b>"

			output += " and "

			if contributors[1]["wiki_url"]:
				output += f"<a href=\"{contributors[1]['wiki_url']}\">{_add_name_abbr(contributors[1]['name'])}</a>"
			else:
				output += f"<b class=\"name\">{_add_name_abbr(contributors[1]['name'])}</b>"
		else:
			output += contributors[0]["name"] + " and " + contributors[1]["name"]

	else:
		for i, contributor in enumerate(contributors):
			if 0 < i <= len(contributors) - 2:
				output += ", "

			if i > 0 and i == len(contributors) - 1:
				output += ", and "

			if include_xhtml:
				if contributor["wiki_url"]:
					output += f"<a href=\"{contributor['wiki_url']}\">{_add_name_abbr(contributor['name'])}</a>"
				else:
					output += f"<b class=\"name\">{_add_name_abbr(contributor['name'])}</b>"
			else:
				output += contributor["name"]

	return output

def _generate_metadata_contributor_xml(contributors: List[Dict], contributor_type: str) -> str:
	"""
	Given a list of contributors, generate a metadata XML block.

	INPUTS
	contributors: A list of contributor dicts
	contributor_type: Either `author`, `translator`, or `illustrator`

	OUTPUTS
	A string of XML representing the contributor block
	"""

	output = ""

	for i, contributor in enumerate(contributors):
		contributor_block = CONTRIBUTOR_BLOCK_TEMPLATE

		if contributor["wiki_url"]:
			contributor_block = contributor_block.replace(">CONTRIBUTOR_WIKI_URL<", f">{contributor['wiki_url']}<")

		if contributor["nacoaf_uri"]:
			contributor_block = contributor_block.replace(">CONTRIBUTOR_NACOAF_URI<", f">{contributor['nacoaf_uri']}<")

		# Make an attempt at figuring out the file-as name. We check for some common two-word last names.
		matches = regex.findall(r"^(.+?)\s+((?:(?:Da|Das|De|Del|Della|Di|Du|El|La|Le|Van|Van Der|Von)\s+)?[^\s]+)$", contributor["name"])
		if matches:
			contributor_block = contributor_block.replace(">CONTRIBUTOR_SORT<", f">{matches[0][1]}, {matches[0][0]}<")

		if contributor["name"].lower() == "anonymous":
			contributor_block = contributor_block.replace(">CONTRIBUTOR_SORT<", ">Anonymous<")
			contributor_block = contributor_block.replace("""<meta property="se:name.person.full-name" refines="#ID">CONTRIBUTOR_FULL_NAME</meta>""", "")
			contributor_block = contributor_block.replace("""<meta property="se:url.encyclopedia.wikipedia" refines="#ID">CONTRIBUTOR_WIKI_URL</meta>""", "")
			contributor_block = contributor_block.replace("""<meta property="se:url.authority.nacoaf" refines="#ID">CONTRIBUTOR_NACOAF_URI</meta>""", "")

		contributor_block = contributor_block.replace(">CONTRIBUTOR_NAME<", f">{contributor['name']}<")
		contributor_block = contributor_block.replace("id=\"CONTRIBUTOR_ID\"", f"id=\"{contributor_type}-{i + 1}\"")
		contributor_block = contributor_block.replace("#CONTRIBUTOR_ID", f"#{contributor_type}-{i + 1}")

		if contributor_type == "author":
			contributor_block = contributor_block.replace("CONTRIBUTOR_MARC", "aut")

		if contributor_type == "translator":
			contributor_block = contributor_block.replace("CONTRIBUTOR_MARC", "trl")

		if contributor_type == "illustrator":
			contributor_block = contributor_block.replace("CONTRIBUTOR_MARC", "ill")

		output += contributor_block + "\n\t\t"

	if len(contributors) == 1:
		output = output.replace(f"{contributor_type}-1", contributor_type)

	return output.strip()

def _create_draft(args: Namespace):
	"""
	Implementation for `se create-draft`
	"""

	# Put together some variables for later use
	authors = []
	translators = []
	illustrators = []
	pg_producers = []
	title = args.title.replace("'", "’")

	for author in args.author:
		authors.append({"name": author.replace("'", "’"), "wiki_url": None, "nacoaf_uri": None})

	if args.translator:
		for translator in args.translator:
			translators.append({"name": translator.replace("'", "’"), "wiki_url": None, "nacoaf_uri": None})

	if args.illustrator:
		for illustrator in args.illustrator:
			illustrators.append({"name": illustrator.replace("'", "’"), "wiki_url": None, "nacoaf_uri": None})

	title_string = title
	if authors and authors[0]["name"].lower() != "anonymous":
		title_string += ", by " + _generate_contributor_string(authors, False)

	identifier = ""
	for author in authors:
		identifier += se.formatting.make_url_safe(author["name"]) + "_"

	identifier = identifier.rstrip("_") + "/" + se.formatting.make_url_safe(title)

	sorted_title = regex.sub(r"^(A|An|The) (.+)$", "\\2, \\1", title)

	if translators:
		title_string = title_string + ". Translated by " + _generate_contributor_string(translators, False)

		identifier = identifier + "/"

		for translator in translators:
			identifier += se.formatting.make_url_safe(translator["name"]) + "_"

		identifier = identifier.rstrip("_")

	if illustrators:
		title_string = title_string + ". Illustrated by " + _generate_contributor_string(illustrators, False)

		identifier = identifier + "/"

		for illustrator in illustrators:
			identifier += se.formatting.make_url_safe(illustrator["name"]) + "_"

		identifier = identifier.rstrip("_")

	repo_name = identifier.replace("/", "_")

	repo_path = Path(repo_name).resolve()

	if repo_path.is_dir():
		raise se.InvalidInputException(f"Directory already exists: [path][link=file://{repo_path}]{repo_path}[/][/].")

	# Get data on authors
	for i, author in enumerate(authors):
		if not args.offline and author["name"].lower() != "anonymous":
			author["wiki_url"], author["nacoaf_uri"] = _get_wikipedia_url(author["name"], True)

	# Get data on translators
	for i, translator in enumerate(translators):
		if not args.offline and translator["name"].lower() != "anonymous":
			translator["wiki_url"], translator["nacoaf_uri"] = _get_wikipedia_url(translator["name"], True)

	# Get data on illlustrators
	for i, illustrator in enumerate(illustrators):
		if not args.offline and illustrator["name"].lower() != "anonymous":
			illustrator["wiki_url"], illustrator["nacoaf_uri"] = _get_wikipedia_url(illustrator["name"], True)

	# Download PG HTML and do some fixups
	if args.pg_url:
		if args.offline:
			raise se.RemoteCommandErrorException("Cannot download Project Gutenberg ebook when offline option is enabled.")

		args.pg_url = args.pg_url.replace("http://", "https://")

		# Get the ebook metadata
		try:
			response = requests.get(args.pg_url)
			pg_metadata_html = response.text
		except Exception as ex:
			raise se.RemoteCommandErrorException(f"Couldn’t download Project Gutenberg ebook metadata page. Exception: {ex}")

		parser = etree.HTMLParser()
		dom = etree.parse(StringIO(pg_metadata_html), parser)

		# Get the ebook HTML URL from the metadata
		pg_ebook_url = None
		for node in dom.xpath("/html/body//a[contains(@type, 'text/html')]"):
			pg_ebook_url = regex.sub(r"^//", "https://", node.get("href"))
			pg_ebook_url = regex.sub(r"^/", "https://www.gutenberg.org/", pg_ebook_url)

		if not pg_ebook_url:
			raise se.RemoteCommandErrorException("Could download ebook metadata, but couldn’t find URL for the ebook HTML.")

		# Get the ebook LCSH categories
		pg_subjects = []
		for node in dom.xpath("/html/body//td[contains(@property, 'dcterms:subject')]"):
			if node.get("datatype") == "dcterms:LCSH":
				for subject_link in node.xpath("./a"):
					pg_subjects.append(subject_link.text.strip())

		# Get the PG publication date
		pg_publication_year = None
		for node in dom.xpath("//td[@itemprop='datePublished']"):
			pg_publication_year = regex.sub(r".+?([0-9]{4})", "\\1", node.text)

		# Get the actual ebook URL
		try:
			response = requests.get(pg_ebook_url)
			pg_ebook_html = response.text
		except Exception as ex:
			raise se.RemoteCommandErrorException(f"Couldn’t download Project Gutenberg ebook HTML. Exception: {ex}")

		try:
			fixed_pg_ebook_html = fix_text(pg_ebook_html, uncurl_quotes=False)
			pg_ebook_html = se.strip_bom(fixed_pg_ebook_html)
		except Exception as ex:
			raise se.InvalidEncodingException(f"Couldn’t determine text encoding of Project Gutenberg HTML file. Exception: {ex}")

		# Try to guess the ebook language
		pg_language = "en-US"
		if "colour" in pg_ebook_html or "favour" in pg_ebook_html or "honour" in pg_ebook_html:
			pg_language = "en-GB"

	# Create necessary directories
	(repo_path / "images").mkdir(parents=True)
	(repo_path / "src" / "epub" / "css").mkdir(parents=True)
	(repo_path / "src" / "epub" / "images").mkdir(parents=True)
	(repo_path / "src" / "epub" / "text").mkdir(parents=True)
	(repo_path / "src" / "META-INF").mkdir(parents=True)

	is_pg_html_parsed = True

	# Write PG data if we have it
	if args.pg_url and pg_ebook_html:
		try:
			dom = etree.parse(StringIO(regex.sub(r"encoding=\".+?\"", "", pg_ebook_html)), parser)
			namespaces = {"re": "http://exslt.org/regular-expressions"}

			for node in dom.xpath("//*[re:test(text(), '\\*\\*\\*\\s*Produced by.+')]", namespaces=namespaces):
				producers_text = regex.sub(r"^<[^>]+?>", "", etree.tostring(node, encoding=str, with_tail=False))
				producers_text = regex.sub(r"<[^>]+?>$", "", producers_text)

				producers_text = regex.sub(r".+?Produced by (.+?)\s*$", "\\1", producers_text, flags=regex.DOTALL)
				producers_text = regex.sub(r"\(.+?\)", "", producers_text, flags=regex.DOTALL)
				producers_text = regex.sub(r"(at )?https?://www\.pgdp\.net", "", producers_text, flags=regex.DOTALL)
				producers_text = regex.sub(r"[\r\n]+", " ", producers_text, flags=regex.DOTALL)
				producers_text = regex.sub(r",? and ", ", and ", producers_text)
				producers_text = producers_text.replace(" and the Online", " and The Online")
				producers_text = producers_text.replace(", and ", ", ").strip()

				pg_producers = [producer.strip() for producer in regex.split(',|;', producers_text)]

			# Try to strip out the PG header
			for node in dom.xpath("//*[re:test(text(), '\\*\\*\\*\\s*START OF THIS')]", namespaces=namespaces):
				for sibling_node in node.xpath("./preceding-sibling::*"):
					easy_node = se.easy_xml.EasyXmlElement(sibling_node)
					easy_node.remove()

				easy_node = se.easy_xml.EasyXmlElement(node)
				easy_node.remove()

			# Try to strip out the PG license footer
			for node in dom.xpath("//*[re:test(text(), 'End of (the )?Project Gutenberg')]", namespaces=namespaces):
				for sibling_node in node.xpath("./following-sibling::*"):
					easy_node = se.easy_xml.EasyXmlElement(sibling_node)
					easy_node.remove()

				easy_node = se.easy_xml.EasyXmlElement(node)
				easy_node.remove()

			# lxml will but the xml declaration in a weird place, remove it first
			output = regex.sub(r"<\?xml.+?\?>", "", etree.tostring(dom, encoding="unicode"))

			# Now re-add it
			output = """<?xml version="1.0" encoding="utf-8"?>\n""" + output

			# lxml can also output duplicate default namespace declarations so remove the first one only
			output = regex.sub(r"(xmlns=\".+?\")(\sxmlns=\".+?\")+", r"\1", output)

			with open(repo_path / "src" / "epub" / "text" / "body.xhtml", "w", encoding="utf-8") as file:
				file.write(output)

		except OSError as ex:
			raise se.InvalidFileException(f"Couldn’t write to ebook directory. Exception: {ex}")
		except Exception as ex:
			# Save this error for later, because it's still useful to complete the create-draft process
			# even if we've failed to parse PG's HTML source.
			is_pg_html_parsed = False
			se.quiet_remove(repo_path / "src" / "epub" / "text" / "body.xhtml")

	# Copy over templates
	_copy_template_file("gitignore", repo_path / ".gitignore")
	_copy_template_file("LICENSE.md", repo_path)
	_copy_template_file("container.xml", repo_path / "src" / "META-INF")
	_copy_template_file("mimetype", repo_path / "src")
	_copy_template_file("content.opf", repo_path / "src" / "epub")
	_copy_template_file("onix.xml", repo_path / "src" / "epub")
	_copy_template_file("toc.xhtml", repo_path / "src" / "epub")
	_copy_template_file("core.css", repo_path / "src" / "epub" / "css")
	_copy_template_file("local.css", repo_path / "src" / "epub" / "css")
	_copy_template_file("se.css", repo_path / "src" / "epub" / "css")
	_copy_template_file("logo.svg", repo_path / "src" / "epub" / "images")
	_copy_template_file("colophon.xhtml", repo_path / "src" / "epub" / "text")
	_copy_template_file("imprint.xhtml", repo_path / "src" / "epub" / "text")
	_copy_template_file("titlepage.xhtml", repo_path / "src" / "epub" / "text")
	_copy_template_file("uncopyright.xhtml", repo_path / "src" / "epub" / "text")
	_copy_template_file("titlepage.svg", repo_path / "images")
	_copy_template_file("cover.jpg", repo_path / "images" / "cover.jpg")
	_copy_template_file("cover.svg", repo_path / "images" / "cover.svg")

	# Try to find Wikipedia links if possible
	ebook_wiki_url = None

	if not args.offline and title != "Short Fiction":
		# There's a "Short Fiction" Wikipedia article, so make an exception for that case
		ebook_wiki_url, _ = _get_wikipedia_url(title, False)

	# Pre-fill titlepage.xhtml
	_replace_in_file(repo_path / "src" / "epub" / "text" / "titlepage.xhtml", "TITLE_STRING", title_string)

	# Create the titlepage SVG
	contributors = {}
	if args.translator:
		contributors["translated by"] = _generate_contributor_string(translators, False)

	if args.illustrator:
		contributors["illustrated by"] = _generate_contributor_string(illustrators, False)

	with open(repo_path / "images" / "titlepage.svg", "w", encoding="utf-8") as file:
		file.write(_generate_titlepage_svg(title, [author["name"] for author in authors], contributors, title_string))

	# Create the cover SVG
	with open(repo_path / "images" / "cover.svg", "w", encoding="utf-8") as file:
		file.write(_generate_cover_svg(title, [author["name"] for author in authors], title_string))

	# Build the cover/titlepage for distribution
	epub = SeEpub(repo_path)
	epub.generate_cover_svg()
	epub.generate_titlepage_svg()

	if args.pg_url:
		_replace_in_file(repo_path / "src" / "epub" / "text" / "imprint.xhtml", "PG_URL", args.pg_url)

	# Fill out the colophon
	with open(repo_path / "src" / "epub" / "text" / "colophon.xhtml", "r+", encoding="utf-8") as file:
		colophon_xhtml = file.read()

		colophon_xhtml = colophon_xhtml.replace("SE_IDENTIFIER", identifier)
		colophon_xhtml = colophon_xhtml.replace("TITLE", title)

		contributor_string =  _generate_contributor_string(authors, True)

		if contributor_string == "":
			colophon_xhtml = colophon_xhtml.replace(" by<br/>\n\t\t\t<a href=\"AUTHOR_WIKI_URL\">AUTHOR</a>", contributor_string)
		else:
			colophon_xhtml = colophon_xhtml.replace("<a href=\"AUTHOR_WIKI_URL\">AUTHOR</a>", contributor_string)

		if translators:
			translator_block = f"It was translated from ORIGINAL_LANGUAGE in TRANSLATION_YEAR by<br/>\n\t\t\t{_generate_contributor_string(translators, True)}.</p>"
			colophon_xhtml = colophon_xhtml.replace("</p>\n\t\t\t<p>This ebook was produced for the<br/>", f"<br/>\n\t\t\t{translator_block}\n\t\t\t<p>This ebook was produced for the<br/>")

		if args.pg_url:
			colophon_xhtml = colophon_xhtml.replace("PG_URL", args.pg_url)

			if pg_publication_year:
				colophon_xhtml = colophon_xhtml.replace("PG_YEAR", pg_publication_year)

			if pg_producers:
				producers_xhtml = ""
				for i, producer in enumerate(pg_producers):
					if "Distributed Proofread" in producer:
						producers_xhtml = producers_xhtml + "<a href=\"https://www.pgdp.net\">The Online Distributed Proofreading Team</a>"
					elif "anonymous" in producer.lower():
						producers_xhtml = producers_xhtml + "<b class=\"name\">An Anonymous Volunteer</b>"
					else:
						producers_xhtml = producers_xhtml + f"<b class=\"name\">{_add_name_abbr(producer).strip('.')}</b>"

					if i < len(pg_producers) - 1:
						producers_xhtml = producers_xhtml + ", "

					if i == len(pg_producers) - 2:
						producers_xhtml = producers_xhtml + "and "

				producers_xhtml = producers_xhtml + "<br/>"

				colophon_xhtml = colophon_xhtml.replace("<b class=\"name\">TRANSCRIBER_1</b>, <b class=\"name\">TRANSCRIBER_2</b>, and <a href=\"https://www.pgdp.net\">The Online Distributed Proofreading Team</a><br/>", producers_xhtml)

		file.seek(0)
		file.write(colophon_xhtml)
		file.truncate()

	# Fill out the metadata file
	with open(repo_path / "src" / "epub" / "content.opf", "r+", encoding="utf-8") as file:
		metadata_xml = file.read()

		metadata_xml = metadata_xml.replace("SE_IDENTIFIER", identifier)
		metadata_xml = metadata_xml.replace(">TITLE_SORT<", f">{sorted_title}<")
		metadata_xml = metadata_xml.replace(">TITLE<", f">{title}<")
		metadata_xml = metadata_xml.replace("VCS_IDENTIFIER", str(repo_name))

		if pg_producers:
			producers_xhtml = ""
			i = 1
			for producer in pg_producers:
				if "Distributed Proofread" in producer:
					producers_xhtml = producers_xhtml + f"\t\t<dc:contributor id=\"transcriber-{i}\">The Online Distributed Proofreading Team</dc:contributor>\n\t\t<meta property=\"file-as\" refines=\"#transcriber-{i}\">Online Distributed Proofreading Team, The</meta>\n\t\t<meta property=\"se:url.homepage\" refines=\"#transcriber-{i}\">https://pgdp.net</meta>\n"
				elif "anonymous" in producer.lower():
					producers_xhtml = producers_xhtml + f"\t\t<dc:contributor id=\"transcriber-{i}\">An Anonymous Volunteer</dc:contributor>\n\t\t<meta property=\"file-as\" refines=\"#transcriber-{i}\">Anonymous Volunteer, An</meta>\n"
				else:
					producers_xhtml = producers_xhtml + f"\t\t<dc:contributor id=\"transcriber-{i}\">{producer.strip('.')}</dc:contributor>\n\t\t<meta property=\"file-as\" refines=\"#transcriber-{i}\">TRANSCRIBER_SORT</meta>\n"

				producers_xhtml = producers_xhtml + f"\t\t<meta property=\"role\" refines=\"#transcriber-{i}\" scheme=\"marc:relators\">trc</meta>\n"

				i = i + 1

			metadata_xml = regex.sub(r"\t\t<dc:contributor id=\"transcriber-1\">TRANSCRIBER</dc:contributor>\s*<meta property=\"file-as\" refines=\"#transcriber-1\">TRANSCRIBER_SORT</meta>\s*<meta property=\"se:url.homepage\" refines=\"#transcriber-1\">TRANSCRIBER_URL</meta>\s*<meta property=\"role\" refines=\"#transcriber-1\" scheme=\"marc:relators\">trc</meta>", "\t\t" + producers_xhtml.strip(), metadata_xml, flags=regex.DOTALL)

		if ebook_wiki_url:
			metadata_xml = metadata_xml.replace(">EBOOK_WIKI_URL<", f">{ebook_wiki_url}<")

		authors_xml = _generate_metadata_contributor_xml(authors, "author")
		authors_xml = authors_xml.replace("dc:contributor", "dc:creator")
		metadata_xml = regex.sub(r"<dc:creator id=\"author\">AUTHOR</dc:creator>.+?scheme=\"marc:relators\">aut</meta>", authors_xml, metadata_xml, flags=regex.DOTALL)

		if translators:
			translators_xml = _generate_metadata_contributor_xml(translators, "translator")
			metadata_xml = regex.sub(r"<dc:contributor id=\"translator\">.+?scheme=\"marc:relators\">trl</meta>", translators_xml, metadata_xml, flags=regex.DOTALL)
		else:
			metadata_xml = regex.sub(r"<dc:contributor id=\"translator\">.+?scheme=\"marc:relators\">trl</meta>\n\t\t", "", metadata_xml, flags=regex.DOTALL)

		if illustrators:
			illustrators_xml = _generate_metadata_contributor_xml(illustrators, "illustrator")
			metadata_xml = regex.sub(r"<dc:contributor id=\"illustrator\">.+?scheme=\"marc:relators\">ill</meta>", illustrators_xml, metadata_xml, flags=regex.DOTALL)
		else:
			metadata_xml = regex.sub(r"<dc:contributor id=\"illustrator\">.+?scheme=\"marc:relators\">ill</meta>\n\t\t", "", metadata_xml, flags=regex.DOTALL)

		if args.pg_url:
			if pg_subjects:
				subject_xhtml = ""

				i = 1
				for subject in pg_subjects:
					subject_xhtml = subject_xhtml + f"\t\t<dc:subject id=\"subject-{i}\">{subject}</dc:subject>\n"
					i = i + 1

				i = 1
				for subject in pg_subjects:
					subject_xhtml = subject_xhtml + f"\t\t<meta property=\"authority\" refines=\"#subject-{i}\">LCSH</meta>\n"

					# Now, get the LCSH ID by querying LCSH directly.
					try:
						response = requests.get(f"https://id.loc.gov/search/?q=cs:http://id.loc.gov/authorities/subjects&q=\"{urllib.parse.quote(subject)}\"")
						result = regex.search(fr"<a title=\"Click to view record\" href=\"/authorities/subjects/([^\"]+?)\">{regex.escape(subject.replace(' -- ', '--'))}</a>", response.text)

						loc_id = "Unknown"
						try:
							loc_id = result.group(1)
						except Exception as ex:
							pass

						subject_xhtml = subject_xhtml + f"\t\t<meta property=\"term\" refines=\"#subject-{i}\">{loc_id}</meta>\n"

					except Exception as ex:
						raise se.RemoteCommandErrorException(f"Couldn’t connect to [url][link=https://id.loc.gov]https://id.loc.gov[/][/]. Exception: {ex}")

					i = i + 1

				metadata_xml = regex.sub(r"\t\t<dc:subject id=\"subject-1\">SUBJECT_1</dc:subject>\s*<dc:subject id=\"subject-2\">SUBJECT_2</dc:subject>\s*<meta property=\"authority\" refines=\"#subject-1\">LCSH</meta>\s*<meta property=\"term\" refines=\"#subject-1\">LCSH_ID_1</meta>\s*<meta property=\"authority\" refines=\"#subject-2\">LCSH</meta>\s*<meta property=\"term\" refines=\"#subject-2\">LCSH_ID_2</meta>", "\t\t" + subject_xhtml.strip(), metadata_xml)

			metadata_xml = metadata_xml.replace("<dc:language>LANG</dc:language>", f"<dc:language>{pg_language}</dc:language>")
			metadata_xml = metadata_xml.replace("<dc:source>PG_URL</dc:source>", f"<dc:source>{args.pg_url}</dc:source>")

		file.seek(0)
		file.write(metadata_xml)
		file.truncate()

	# Set up local git repo
	repo = git.Repo.init(repo_path)

	if args.email:
		with repo.config_writer() as config:
			config.set_value("user", "email", args.email)

	if args.pg_url and pg_ebook_html and not is_pg_html_parsed:
		raise se.InvalidXhtmlException("Couldn’t parse Project Gutenberg ebook source. This is usually due to invalid HTML in the ebook.")

def create_draft() -> int:
	"""
	Entry point for `se create-draft`
	"""

	parser = argparse.ArgumentParser(description="Create a skeleton of a new Standard Ebook in the current directory.")
	parser.add_argument("-i", "--illustrator", dest="illustrator", nargs="+", help="an illustrator of the ebook")
	parser.add_argument("-r", "--translator", dest="translator", nargs="+", help="a translator of the ebook")
	parser.add_argument("-p", "--pg-url", dest="pg_url", help="the URL of the Project Gutenberg ebook to download")
	parser.add_argument("-e", "--email", dest="email", help="use this email address as the main committer for the local Git repository")
	parser.add_argument("-o", "--offline", dest="offline", action="store_true", help="create draft without network access")
	parser.add_argument("-a", "--author", dest="author", required=True, nargs="+", help="an author of the ebook")
	parser.add_argument("-t", "--title", dest="title", required=True, help="the title of the ebook")
	args = parser.parse_args()

	if args.pg_url and not regex.match("^https?://www.gutenberg.org/ebooks/[0-9]+$", args.pg_url):
		se.print_error("Project Gutenberg URL must look like: [url]https://www.gutenberg.org/ebooks/<EBOOK-ID>[url].")
		return se.InvalidArgumentsException.code

	try:
		# Before we continue, confirm that there isn't a subtitle passed in with the title
		if ":" in args.title:
			console = Console(highlight=False, theme=se.RICH_THEME) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel
			console.print("Titles should not include a subtitle, as subtitles are separate metadata elements in [path]content.opf[/]. Are you sure you want to continue? \\[y/N]")
			if input().lower() not in {"yes", "y"}:
				return se.InvalidInputException.code

		_create_draft(args)
	except se.SeException as ex:
		se.print_error(ex)
		return ex.code

	return 0
