"""
This module implements the `se create_draft` command.
"""

import argparse
from io import StringIO
import shutil
import urllib.parse
from argparse import Namespace
from html import escape
from pathlib import Path
import importlib.resources
import tempfile

from git.repo import Repo as Repo # pylint: disable=useless-import-alias # Import in this style to silence `mypy` type checking, see <https://github.com/microsoft/pyright/issues/5929#issuecomment-1714815796>.
import regex
import requests
from ftfy import fix_text
from lxml import etree

import se
import se.formatting
import se.easy_xml
from se.se_epub import SeEpub

CONTRIBUTOR_BLOCK_TEMPLATE = """<dc:contributor id="CONTRIBUTOR_ID">CONTRIBUTOR_NAME</dc:contributor>
		<meta property="file-as" refines="#CONTRIBUTOR_ID">CONTRIBUTOR_SORT</meta>
		<meta property="se:name.person.full-name" refines="#CONTRIBUTOR_ID">CONTRIBUTOR_FULL_NAME</meta>
		<meta property="se:url.encyclopedia.wikipedia" refines="#CONTRIBUTOR_ID">CONTRIBUTOR_WIKI_URL</meta>
		<meta property="se:url.authority.nacoaf" refines="#CONTRIBUTOR_ID">CONTRIBUTOR_NACOAF_URI</meta>
		<meta property="role" refines="#CONTRIBUTOR_ID" scheme="marc:relators">CONTRIBUTOR_MARC</meta>"""

USER_AGENT = "Standard Ebooks toolset <https://standardebooks.org/tools>"
XPATH_NAMESPACES = {"re": "http://exslt.org/regular-expressions"}

console = se.init_console()

def _replace_in_file(file_path: Path, search: str | list, replace: str | list) -> None:
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

def _get_wikipedia_url(string: str, get_nacoaf_uri: bool) -> tuple[str | None, str | None]:
	"""
	Given a string, try to see if there's a Wikipedia page entry, and an optional NACOAF entry, for that string.

	INPUTS
	string: The string to find on Wikipedia.
	get_nacoaf_uri: Include NACOAF URI in resulting tuple, if found?

	OUTPUTS
	A tuple of two strings. The first string is the Wikipedia URL, the second is the NACOAF URI.
	"""

	# We try to get the Wikipedia URL by the subject by taking advantage of the fact that Wikipedia's special search will redirect you immediately if there's an article match. So if the search page tries to redirect us, we use that redirect link as the Wiki URL. If the search page returns HTTP 200, then we didn't find a direct match and return nothing.

	try:
		# Wikipedia requires a `User-Agent` header, otherwise it returns HTTP 403 Forbidden.
		response = requests.get("https://en.wikipedia.org/wiki/Special:Search", params={"search": string, "go": "Go", "ns0": "1"}, allow_redirects=False, timeout=60, headers={'User-Agent': USER_AGENT})
	except Exception as ex:
		raise se.RemoteCommandErrorException(f"Couldn’t contact Wikipedia. Exception: {ex}") from ex

	if response.status_code == 302:
		nacoaf_uri = None
		wiki_url = response.headers["Location"]
		if urllib.parse.urlparse(wiki_url).path == "/wiki/Special:Search":
			# Redirected back to search URL, no match.
			return None, None

		if get_nacoaf_uri:
			try:
				response = requests.get(wiki_url, timeout=60, headers={'User-Agent': USER_AGENT})
			except Exception as ex:
				raise se.RemoteCommandErrorException(f"Couldn’t contact Wikipedia. Exception: {ex}") from ex

			for match in regex.findall(r"https?://id\.loc\.gov/authorities/(?:names/)?(n[a-z0-9]+)", response.text):
				nacoaf_uri = "http://id.loc.gov/authorities/names/" + match

		return wiki_url, nacoaf_uri

	return None, None

def _copy_template_file(filename: str, dest_path: Path) -> None:
	"""
	Copy a template file to the given destination `Path`.
	"""
	if dest_path.is_dir():
		dest_path = dest_path / filename
	with importlib.resources.as_file(importlib.resources.files("se.data.templates").joinpath(filename)) as src_path:
		shutil.copyfile(src_path, dest_path)

def _add_name_abbr(contributor: str) -> str:
	"""
	Add `<abbr epub:type="z3998:given-name">` around contributor names.
	"""

	contributor = regex.sub(r"([\p{Uppercase_Letter}]\.(?:\s*[\p{Uppercase_Letter}]\.)*)", r"""<abbr epub:type="z3998:given-name">\1</abbr>""", contributor)

	return contributor

def _generate_contributor_string(contributors: list[dict], include_xhtml: bool, use_nbsp: bool=False) -> str:
	"""
	Given a list of contributors, generate a contributor string like `Bob Smith, Jane Doe, and Sam Johnson`.

	With `include_xhtml`, the string looks like: `<b epub:type="z3998:personal-name">Bob Smith</b>, <a href="https://en.wikipedia.org/wiki/Jane_Doe">Jane Doe</a>, and <b epub:type="z3998:personal-name">Sam Johnson</b>`

	INPUTS
	contributors: A list of contributor dicts.
	include_xhtml: Include `<b>` or `<a>` for each contributor, making the output suitable for the colophon.
	use_nbsp: If `True`, use no-break spaces in contributor names. Only has effect if `include_xhtml` is `False`.

	OUTPUTS
	A string of XML representing the contributors.
	"""

	output = ""

	# Don't include "anonymous" contributors.
	contributors = [contributor for contributor in contributors if contributor["name"].lower() != "anonymous"]

	if len(contributors) == 1:
		if include_xhtml:
			if contributors[0]["wiki_url"]:
				output += f"""<a href="{contributors[0]['wiki_url']}">{_add_name_abbr(escape(contributors[0]['name']))}</a>"""
			else:
				output += f"""<b epub:type="z3998:personal-name">{_add_name_abbr(escape(contributors[0]['name']))}</b>"""
		else:
			if use_nbsp:
				output += contributors[0]["name"].replace(" ", se.NO_BREAK_SPACE)
			else:
				output += contributors[0]["name"]

	elif len(contributors) == 2:
		if include_xhtml:
			if contributors[0]["wiki_url"]:
				output += f"""<a href="{contributors[0]['wiki_url']}">{_add_name_abbr(escape(contributors[0]['name']))}</a>"""
			else:
				output += f"""<b epub:type="z3998:personal-name">{_add_name_abbr(escape(contributors[0]['name']))}</b>"""

			output += " and "

			if contributors[1]["wiki_url"]:
				output += f"""<a href="{contributors[1]['wiki_url']}">{_add_name_abbr(escape(contributors[1]['name']))}</a>"""
			else:
				output += f"""<b epub:type="z3998:personal-name">{_add_name_abbr(escape(contributors[1]['name']))}</b>"""
		else:
			if use_nbsp:
				output += contributors[0]["name"].replace(" ", se.NO_BREAK_SPACE) + " and " + contributors[1]["name"].replace(" ", se.NO_BREAK_SPACE)
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
					output += f"""<a href="{contributor['wiki_url']}">{_add_name_abbr(escape(contributor['name']))}</a>"""
				else:
					output += f"""<b epub:type="z3998:personal-name">{_add_name_abbr(escape(contributor['name']))}</b>"""
			else:
				if use_nbsp:
					output += contributor["name"].replace(" ", se.NO_BREAK_SPACE)
				else:
					output += contributor["name"]

	return output

def _generate_metadata_contributor_xml(contributors: list[dict], contributor_type: str) -> str:
	"""
	Given a list of contributors, generate a metadata XML block.

	INPUTS
	contributors: A list of contributor dicts.
	contributor_type: Either `author`, `translator`, or `illustrator`.

	OUTPUTS
	A string of XML representing the contributor block.
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
			contributor_block = contributor_block.replace(">CONTRIBUTOR_SORT<", f">{escape(matches[0][1])}, {escape(matches[0][0])}<")

		if contributor["name"].lower() == "anonymous":
			contributor_block = contributor_block.replace(">CONTRIBUTOR_SORT<", ">Anonymous<")
			contributor_block = contributor_block.replace("""<meta property="se:name.person.full-name" refines="#ID">CONTRIBUTOR_FULL_NAME</meta>""", "")
			contributor_block = contributor_block.replace("""<meta property="se:url.encyclopedia.wikipedia" refines="#ID">CONTRIBUTOR_WIKI_URL</meta>""", "")
			contributor_block = contributor_block.replace("""<meta property="se:url.authority.nacoaf" refines="#ID">CONTRIBUTOR_NACOAF_URI</meta>""", "")

		contributor_block = contributor_block.replace(">CONTRIBUTOR_NAME<", f">{escape(contributor['name'])}<")
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

def _generate_titlepage_string(contributors: list[dict], contributor_type: str) -> str:
	output = _generate_contributor_string(contributors, True)
	output = regex.sub(r"<a href[^<>]+?>", "<b epub:type=\"z3998:personal-name\">", output)
	output = output.replace("</a>", "</b>")

	if contributor_type != "illustrator":
		# There's no `z3998:illustrator` term.
		output = output.replace("\"z3998:personal-name", f"\"z3998:{contributor_type} z3998:personal-name")

	return output

def _create_draft(args: Namespace, plain_output: bool):
	"""
	Implementation for `se create-draft`.
	"""

	# Put together some variables for later use.
	authors = []
	translators = []
	illustrators = []
	transcription_producers = []
	transcription_subjects = []
	transcription_ebook_html = None
	transcription_url = None
	transcription_publication_year = None
	transcription_language = None
	transcription_local_path = None
	transcription_source = None
	html_parser = etree.HTMLParser()
	title = se.formatting.titlecase(args.title.replace("'", "’").replace("...", f"{se.HAIR_SPACE}…"))
	sorted_title = regex.sub(r"^(A|An|The) (.+)$", "\\2, \\1", title)

	for author in args.author:
		authors.append({"name": author.replace("'", "’"), "wiki_url": None, "nacoaf_uri": None})

	if args.translator:
		for translator in args.translator:
			translators.append({"name": translator.replace("'", "’"), "wiki_url": None, "nacoaf_uri": None})

	if args.illustrator:
		for illustrator in args.illustrator:
			illustrators.append({"name": illustrator.replace("'", "’"), "wiki_url": None, "nacoaf_uri": None})

	# Get more metadata on contributors.
	if not args.white_label:
		# Get data on authors.
		for _, author in enumerate(authors):
			if not args.offline and author["name"].lower() != "anonymous":
				author["wiki_url"], author["nacoaf_uri"] = _get_wikipedia_url(author["name"], True)

		# Get data on translators.
		for _, translator in enumerate(translators):
			if not args.offline and translator["name"].lower() != "anonymous":
				translator["wiki_url"], translator["nacoaf_uri"] = _get_wikipedia_url(translator["name"], True)

		# Get data on illustrators.
		for _, illustrator in enumerate(illustrators):
			if not args.offline and illustrator["name"].lower() != "anonymous":
				illustrator["wiki_url"], illustrator["nacoaf_uri"] = _get_wikipedia_url(illustrator["name"], True)

	# Create a temp directory and copy all template files over.
	with tempfile.TemporaryDirectory() as directory_name:
		work_path = Path(directory_name)
		content_path = Path(work_path) / "src"

		if args.verbose:
			console.print(se.prep_output("Building ebook structure ...", plain_output))

		(content_path / "epub" / "css").mkdir(parents=True)
		(content_path / "epub" / "images").mkdir()
		(content_path / "epub" / "text").mkdir()
		(content_path / "META-INF").mkdir()

		if not args.white_label:
			(work_path / "images").mkdir()

		# Copy over templates.
		if args.verbose:
			console.print(se.prep_output("Copying in standard files ...", plain_output))

		_copy_template_file("gitignore", work_path / ".gitignore")
		_copy_template_file("container.xml", content_path / "META-INF")
		_copy_template_file("mimetype", content_path)
		_copy_template_file("core.css", content_path / "epub" / "css")

		if args.white_label:
			_copy_template_file("content-white-label.opf", content_path / "epub" / "content.opf")
			_copy_template_file("titlepage-white-label.xhtml", content_path / "epub" / "text" / "titlepage.xhtml")
			_copy_template_file("cover.jpg", content_path / "epub" / "images")
			_copy_template_file("local-white-label.css", content_path / "epub" / "css" / "local.css")
			_copy_template_file("toc-white-label.xhtml", content_path / "epub" / "toc.xhtml")

		else:
			_copy_template_file("cover.jpg", work_path / "images")
			_copy_template_file("cover.svg", work_path / "images")
			_copy_template_file("titlepage.svg", work_path / "images")
			_copy_template_file("local.css", content_path / "epub" / "css")
			_copy_template_file("se.css", content_path / "epub" / "css")
			_copy_template_file("logo.svg", content_path / "epub" / "images")
			_copy_template_file("colophon.xhtml", content_path / "epub" / "text")
			_copy_template_file("imprint.xhtml", content_path / "epub" / "text")
			_copy_template_file("uncopyright.xhtml", content_path / "epub" / "text")
			_copy_template_file("titlepage.xhtml", content_path / "epub" / "text")
			_copy_template_file("content.opf", content_path / "epub")
			_copy_template_file("toc.xhtml", content_path / "epub")
			_copy_template_file("LICENSE.md", work_path)

		# Fill out some basic data in the metadata file that will let is generate further variables.
		with open(content_path / "epub" / "content.opf", "r+", encoding="utf-8") as file:
			metadata_xml = file.read()

			metadata_xml = metadata_xml.replace(">TITLE_SORT<", f">{escape(sorted_title)}<")
			metadata_xml = metadata_xml.replace(">TITLE<", f">{escape(title)}<")

			authors_xml = _generate_metadata_contributor_xml(authors, "author")
			authors_xml = authors_xml.replace("dc:contributor", "dc:creator")
			metadata_xml = regex.sub(r"<dc:creator id=\"author\">AUTHOR_NAME</dc:creator>.+?scheme=\"marc:relators\">aut</meta>", authors_xml, metadata_xml, flags=regex.DOTALL)

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

			file.seek(0)
			file.write(metadata_xml)
			file.truncate()

		# Basic metadata is done, now work on an `SeEpub` object instead of raw files.
		epub = SeEpub(work_path)

		# We have to set this here because we haven't created the epub identifier yet.
		epub.is_se_ebook = not args.white_label

		# Can we create the output directory?
		repo_path = Path(epub.generate_repo_name()).resolve()

		if repo_path.is_dir():
			raise se.InvalidInputException(f"Directory already exists: [path][link=file://{repo_path}]{repo_path}[/][/].")

		for node in epub.metadata_dom.xpath("//*[contains(., 'IDENTIFIER') and not(./*)]"):
			node.set_text(node.inner_text().replace('IDENTIFIER', epub.generate_identifier()))

		if epub.is_se_ebook:
			for node in epub.metadata_dom.xpath("//*[contains(., 'VCS_URL') and not(./*)]"):
				node.set_text(node.inner_text().replace('VCS_URL', epub.generate_vcs_url()))

			# Try to find Wikipedia links if possible.
			ebook_wiki_url = None

			if not args.offline and title not in ("Short Fiction", "Poetry", "Essays", "Plays"):
				ebook_wiki_url, _ = _get_wikipedia_url(title, False)

			if ebook_wiki_url:
				for node in epub.metadata_dom.xpath("//*[contains(., 'EBOOK_WIKI_URL') and not(./*)]"):
					node.set_text(node.inner_text().replace('EBOOK_WIKI_URL', ebook_wiki_url))

		# Download transcriptions if required.
		if args.fp_id:
			transcription_url = f"https://www.fadedpage.com/showbook.php?pid={args.fp_id}"

			# Get the ebook metadata.
			if args.verbose:
				console.print(se.prep_output(f"Downloading ebook metadata from [path][link={transcription_url}]{transcription_url}[/][/] ...", plain_output))
			try:
				response = requests.get(transcription_url, timeout=60, headers={'User-Agent': USER_AGENT})
				fp_metadata_html = response.text
				fp_cookie = response.cookies['PHPSESSID']
			except Exception as ex:
				raise se.RemoteCommandErrorException(f"Couldn’t download Faded Page ebook metadata page. Exception: {ex}") from ex

			dom = etree.parse(StringIO(fp_metadata_html), html_parser)

			# Get the ebook HTML URL from the metadata.
			fp_ebook_url = None
			for node in dom.xpath(f"/html/body//a[contains(@href, '{args.fp_id}.html')]"):
				fp_ebook_url = "https://www.fadedpage.com/" + node.get("href")

			if not fp_ebook_url:
				raise se.RemoteCommandErrorException("Could download ebook metadata, but couldn’t find URL for the ebook HTML.")

			# Get the actual ebook transcription.
			# Faded Page requires you to set a session cookie at the ebook's metadata page before you can access the actual ebook transcription.
			# We got that session cookie earlier, and we pass it below in order to actually be able to download the ebook.
			if args.verbose:
				console.print(se.prep_output(f"Downloading ebook transcription from [path][link={fp_ebook_url}]{fp_ebook_url}[/][/] ...", plain_output))
			try:
				response = requests.get(fp_ebook_url, timeout=60, cookies={"PHPSESSID": fp_cookie}, headers={'User-Agent': USER_AGENT})
				transcription_ebook_html = response.text
			except Exception as ex:
				raise se.RemoteCommandErrorException(f"Couldn’t download Faded Page ebook HTML. Exception: {ex}") from ex

			fp_html_dom = etree.parse(StringIO(transcription_ebook_html), html_parser)

			# Make sure we actually got the ebook HTML, and didn't get redirected by Faded Page.
			if not fp_html_dom.xpath("/html/head/meta[re:test(@http-equiv, '^Content-Type$', 'i') and re:test(@content, 'text/html;\\s*charset=utf-8', 'i')]", namespaces=XPATH_NAMESPACES):
				raise se.RemoteCommandErrorException("Tried to download Faded Page ebook HTML, but response doesn't look like a Faded Page ebook.")

			# Get the FP publication date.
			for node in fp_html_dom.xpath("//p[re:test(., '^\\s*Date first posted:', 'i')]", namespaces=XPATH_NAMESPACES):
				text = etree.tostring(node, encoding=str, method="text", with_tail=False)
				transcription_publication_year = regex.sub(r".+?([0-9]{4})$", "\\1", text)
				# Quit on the first match.
				break

			try:
				fixed_external_ebook_html = fix_text(transcription_ebook_html, uncurl_quotes=False)
				transcription_ebook_html = se.strip_bom(fixed_external_ebook_html)
			except Exception as ex:
				raise se.InvalidEncodingException(f"Couldn’t determine text encoding of Faded Page HTML file. Exception: {ex}") from ex

			transcription_source = "Faded Page"

		if args.pg_id:
			transcription_url = f"https://www.gutenberg.org/ebooks/{args.pg_id}"

			# Get the ebook metadata.
			if args.verbose:
				console.print(se.prep_output(f"Downloading ebook metadata from [path][link={transcription_url}]{transcription_url}[/][/] ...", plain_output))
			try:
				response = requests.get(transcription_url, timeout=60, headers={'User-Agent': USER_AGENT})
				pg_metadata_html = response.text
			except Exception as ex:
				raise se.RemoteCommandErrorException(f"Couldn’t download Project Gutenberg ebook metadata page. Exception: {ex}") from ex

			dom = etree.parse(StringIO(pg_metadata_html), html_parser)

			# Get the ebook HTML URL from the metadata.
			pg_ebook_url = None
			for node in dom.xpath("/html/body//a[contains(@type, 'text/html')]"):
				pg_ebook_url = regex.sub(r"^//", "https://", node.get("href"))
				pg_ebook_url = regex.sub(r"^/", "https://www.gutenberg.org/", pg_ebook_url)

			if not pg_ebook_url:
				raise se.RemoteCommandErrorException("Could download ebook metadata, but couldn’t find URL for the ebook HTML.")

			# Get the ebook LCSH categories.
			for node in dom.xpath("/html/body//td[contains(@property, 'dcterms:subject')]"):
				if node.get("datatype") == "dcterms:LCSH":
					for subject_link in node.xpath("./a"):
						transcription_subjects.append(subject_link.text.strip())

			# Get the PG publication date.
			for node in dom.xpath("//td[@itemprop='datePublished']"):
				transcription_publication_year = regex.sub(r".+?([0-9]{4})", "\\1", node.text)

			# Get the actual ebook URL.
			if args.verbose:
				console.print(se.prep_output(f"Downloading ebook transcription from [path][link={pg_ebook_url}]{pg_ebook_url}[/][/] ...", plain_output))
			try:
				response = requests.get(pg_ebook_url, timeout=60, headers={'User-Agent': USER_AGENT})
				transcription_ebook_html = response.text
			except Exception as ex:
				raise se.RemoteCommandErrorException(f"Couldn’t download Project Gutenberg ebook HTML. Exception: {ex}") from ex

			try:
				fixed_external_ebook_html = fix_text(transcription_ebook_html, uncurl_quotes=False)
				transcription_ebook_html = se.strip_bom(fixed_external_ebook_html)
			except Exception as ex:
				raise se.InvalidEncodingException(f"Couldn’t determine text encoding of Project Gutenberg HTML file. Exception: {ex}") from ex

			transcription_source = "Project Gutenberg"

		if transcription_ebook_html:
			# Try to guess the ebook language.
			transcription_language = "en-US"
			if "colour" in transcription_ebook_html or "favour" in transcription_ebook_html or "honour" in transcription_ebook_html:
				transcription_language = "en-GB"

			for node in epub.metadata_dom.xpath("//*[contains(., 'LANG') and not(./*)]"):
				node.set_text(node.inner_text().replace("LANG", transcription_language))

			for node in epub.get_dom(epub.toc_path).xpath("//*[contains(., 'LANG') and not(./*)]"):
				node.set_text(node.inner_text().replace("LANG", transcription_language))

		if transcription_url:
			for node in epub.metadata_dom.xpath("//*[contains(., 'TRANSCRIPTION_URL') and not(./*)]"):
				node.set_text(node.inner_text().replace("TRANSCRIPTION_URL", transcription_url))

		if transcription_subjects:
			# First, remove existing subjects.
			for node in epub.metadata_dom.xpath("//dc:subject | //meta[@property='authority' or @property='term']"):
				node.remove()

			i = 1
			for subject in transcription_subjects:
				# Get the LCSH ID by querying LCSH directly.
				try:
					search_url = "https://id.loc.gov/search/?q=cs:http://id.loc.gov/authorities/{}&q=\"" + urllib.parse.quote(subject) + "\""
					record_link = "<a title=\"Click to view record\" href=\"/authorities/{}/([^\"]+?)\">" + regex.escape(subject.replace(' -- ', '--')) + "</a>"
					loc_id = "Unknown"

					response = requests.get(search_url.format("subjects"), timeout=60, headers={'User-Agent': USER_AGENT})
					result = regex.search(record_link.format("subjects"), response.text, regex.IGNORECASE)

					# If Subject authority does not exist we can also check the Names authority.
					if result is None:
						response = requests.get(search_url.format("names"), timeout=60, headers={'User-Agent': USER_AGENT})
						result = regex.search(record_link.format("names"), response.text)

					if result:
						loc_id = result.group(1)

					etree.register_namespace("dc", "http://purl.org/dc/elements/1.1/")
					element = etree.Element(etree.QName("http://purl.org/dc/elements/1.1/", "subject"))
					subject_node = se.easy_xml.EasyXmlElement(element)
					subject_node.set_attr("id", f"subject-{i}")
					subject_node.set_text(subject)
					authority_node = se.easy_xml.EasyXmlElement(f"<meta property=\"authority\" refines=\"subject-{i}\">LCHS</meta>")
					term_node = se.easy_xml.EasyXmlElement(f"<meta property=\"term\" refines=\"subject-{i}\">{loc_id}</meta>")

					for node in epub.metadata_dom.xpath("//meta[@property='se:subject'][1]"):
						node.insert_before(subject_node)
						node.insert_before(authority_node)
						node.insert_before(term_node)

				except Exception as ex:
					raise se.RemoteCommandErrorException(f"Couldn’t connect to [url][link=https://id.loc.gov]https://id.loc.gov[/][/]. Exception: {ex}") from ex

				i = i + 1

		is_external_html_parsed = True

		# Write transcription XHTML, if we have it.
		if transcription_ebook_html:
			if args.verbose:
				console.print(se.prep_output("Cleaning transcription ...", plain_output))

			transcription_local_path = content_path / "epub" / "text" / "body.xhtml"
			output = ""

			if args.fp_id:
				try:
					dom = etree.parse(StringIO(regex.sub(r"encoding=(?P<quote>[\'\"]).+?(?P=quote)", "", transcription_ebook_html)), html_parser)

					for node in dom.xpath("//*[re:test(., 'ebook was produced by.+', 'i')]", namespaces=XPATH_NAMESPACES):
						node_html = etree.tostring(node, encoding=str, method="html", with_tail=False)

						# Sometimes, lxml returns the entire HTML instead of the node HTML for a node.
						# It's unclear why this happens. An example is <https://www.gutenberg.org/ebooks/21721>.
						# If the HTML is larger than some large size, abort trying to find producers.
						if len(node_html) > 3000:
							continue

						# Strip tags.
						producers_text = node_html
						producers_text = regex.sub(r"<.+?>", " ", producers_text, flags=regex.DOTALL)

						producers_text = regex.sub(r"^<[^>]+?>", "", producers_text)
						producers_text = regex.sub(r"<[^>]+?>$", "", producers_text)

						producers_text = regex.sub(r"^\s*This eBook was produced by:\s*", "", producers_text, flags=regex.IGNORECASE)
						producers_text = regex.sub(r" \s+", " ", producers_text, flags=regex.DOTALL)
						producers_text = regex.sub(r"(at )?https?://www\.pgdp(canada)?\.net", "", producers_text)
						producers_text = regex.sub(r"[\r\n]+", " ", producers_text)
						producers_text = regex.sub(r",? (and|&amp;) ", ", and ", producers_text)
						producers_text = producers_text.replace(", and ", ", ").strip()

						transcription_producers = [producer.strip() for producer in regex.split(',|;', producers_text)]

					# Strip `<head>` and `<script>`.
					for node in dom.xpath("/html/head | /html//script"):
						easy_node = se.easy_xml.EasyXmlElement(node)
						easy_node.remove()

					# Try to strip out the header and footer.
					for node in dom.xpath("//p[re:test(., 'This eBook was produced by', 'i')]", namespaces=XPATH_NAMESPACES):
						for sibling_node in node.xpath("./preceding-sibling::*"):
							easy_node = se.easy_xml.EasyXmlElement(sibling_node)
							easy_node.remove()

						# If there's an `<hr/>` directly following this node, remove it too.
						for hr_node in node.xpath("./following-sibling::*[1][name() = 'hr']"):
							easy_node = se.easy_xml.EasyXmlElement(hr_node)
							easy_node.remove()

						easy_node = se.easy_xml.EasyXmlElement(node)
						easy_node.remove()

					# Try to strip out the footer.
					for node in dom.xpath("/html/body/p[re:test(., '^\\s*\\[The end of')][last()]", namespaces=XPATH_NAMESPACES):
						for sibling_node in node.xpath("./following-sibling::*"):
							easy_node = se.easy_xml.EasyXmlElement(sibling_node)
							easy_node.remove()

						easy_node = se.easy_xml.EasyXmlElement(node)
						easy_node.remove()

					# Strip all comments.
					for node in dom.xpath("//comment()"):
						easy_node = se.easy_xml.EasyXmlElement(node)
						easy_node.remove()

					# lxml will put the XML declaration in a weird place, remove it first.
					output = regex.sub(r"<\?xml.+?\?>", "", etree.tostring(dom, encoding="unicode"))

					# Now re-add it.
					output = """<?xml version="1.0" encoding="utf-8"?>\n""" + output

					# lxml can also output duplicate default namespace declarations so remove the first one only.
					output = regex.sub(r"(xmlns=\".+?\")(\sxmlns=\".+?\")+", r"\1", output)

					# lxml may also create duplicate `xml:lang` attributes on the root element. Not sure why. Remove them.
					output = regex.sub(r'(xml:lang="[^"]+?" lang="[^"]+?") xml:lang="[^"]+?"', r"\1", output)

				except Exception:
					# Save this error for later; we still want to save the book text and complete the `create-draft` process even if we've failed to parse PG's HTML source.
					is_external_html_parsed = False
					output = transcription_ebook_html

			if args.pg_id:
				try:
					dom = etree.parse(StringIO(regex.sub(r"encoding=(?P<quote>[\'\"]).+?(?P=quote)", "", transcription_ebook_html)), html_parser)

					for node in dom.xpath("//*[re:test(text(), '\\*\\*\\*\\s*Produced by.+')] | //section[@id='pg-header' or @id='pg-machine-header']//p[re:test(., 'Credits: ')]", namespaces=XPATH_NAMESPACES):
						node_html = etree.tostring(node, encoding=str, method="html", with_tail=False)

						# Sometimes, lxml returns the entire HTML instead of the node HTML for a node.
						# It's unclear why this happens. An example is <https://www.gutenberg.org/ebooks/21721>.
						# If the HTML is larger than some large size, abort trying to find producers.
						if len(node_html) > 3000:
							continue

						# Strip tags.
						producers_text = node_html
						producers_text = regex.sub(r"<.+?>", " ", producers_text, flags=regex.DOTALL)

						producers_text = regex.sub(r"^<[^>]+?>", "", producers_text)
						producers_text = regex.sub(r"<[^>]+?>$", "", producers_text)

						producers_text = regex.sub(r".+?(Produced by|Credits\s*:\s*) (.+?)\s*$", "\\2", producers_text, flags=regex.DOTALL)
						# Workaround for what appears to be a PG bug where the credits start as `Credits: Produced by Name1`.
						producers_text = regex.sub(r"Produced by ", "", producers_text)
						producers_text = regex.sub(r"\(.+?\)", "", producers_text, flags=regex.DOTALL)
						producers_text = regex.sub(r" \s+", " ", producers_text, flags=regex.DOTALL)
						producers_text = regex.sub(r"(at )?https?://www\.pgdp\.net", "", producers_text)
						producers_text = regex.sub(r"[\r\n]+", " ", producers_text)
						producers_text = regex.sub(r",? and ", ", and ", producers_text)
						producers_text = producers_text.replace(", and ", ", ").strip()

						transcription_producers = [producer.strip() for producer in regex.split(',|;', producers_text)]

					# Strip everything in `<head>`.
					for node in dom.xpath("/html/head//*"):
						easy_node = se.easy_xml.EasyXmlElement(node)
						easy_node.remove()

					# Try to strip out the PG header and footer for new PG ebooks.
					nodes = dom.xpath("//section[contains(@class, 'pg-boilerplate')]")
					if nodes:
						for node in nodes:
							easy_node = se.easy_xml.EasyXmlElement(node)
							easy_node.remove()
					else:
						# Old PG ebooks might have a different structure.
						for node in dom.xpath("//*[re:test(text(), '\\*\\*\\*\\s*START OF (THE|THIS)')]", namespaces=XPATH_NAMESPACES):
							for sibling_node in node.xpath("./preceding-sibling::*"):
								easy_node = se.easy_xml.EasyXmlElement(sibling_node)
								easy_node.remove()

							easy_node = se.easy_xml.EasyXmlElement(node)
							easy_node.remove()

						# Try to strip out the PG license footer.
						for node in dom.xpath("//*[re:test(text(), 'End of (the )?Project Gutenberg')]", namespaces=XPATH_NAMESPACES):
							for sibling_node in node.xpath("./following-sibling::*"):
								easy_node = se.easy_xml.EasyXmlElement(sibling_node)
								easy_node.remove()

							easy_node = se.easy_xml.EasyXmlElement(node)
							easy_node.remove()

					# lxml will put the XML declaration in a weird place, remove it first.
					output = regex.sub(r"<\?xml.+?\?>", "", etree.tostring(dom, encoding="unicode"))

					# Now re-add it.
					output = """<?xml version="1.0" encoding="utf-8"?>\n""" + output

					# lxml can also output duplicate default namespace declarations so remove the first one only.
					output = regex.sub(r"(xmlns=\".+?\")(\sxmlns=\".+?\")+", r"\1", output)

					# lxml may also create duplicate `xml:lang` attributes on the root element. Not sure why. Remove them.
					output = regex.sub(r'(xml:lang="[^"]+?" lang="[^"]+?") xml:lang="[^"]+?"', r"\1", output)

				except Exception:
					# Save this error for later; we still want to save the book text and complete the `create-draft` process even if we've failed to parse PG's HTML source.
					is_external_html_parsed = False
					output = transcription_ebook_html

			if transcription_producers:
				for key, producer in enumerate(transcription_producers):
					if "Distributed Proofreaders Canada" in producer:
						transcription_producers[key] = "Distributed Proofreaders Canada"
					elif "Distributed Proofreader" in producer:
						transcription_producers[key] = "Distributed Proofreaders"

				# Add transcribers to metadata.
				# First remove all placeholder metatata.
				for node in epub.metadata_dom.xpath("//dc:contributor[starts-with(@id, 'transcriber-')] | //meta[starts-with(@refines, '#transcriber-')]"):
					node.remove()

				i = 1
				for producer in transcription_producers:
					etree.register_namespace("dc", "http://purl.org/dc/elements/1.1/")
					element = etree.Element(etree.QName("http://purl.org/dc/elements/1.1/", "subject"))
					transcriber_id = f"transcriber-{i}"
					contributor_node = se.easy_xml.EasyXmlElement(element)
					contributor_node.set_attr("id", transcriber_id)
					contributor_file_as_node = se.easy_xml.EasyXmlElement(f"<meta property=\"file-as\" refines=\"#{transcriber_id}\">TRANSCRIBER_{i}_SORT</meta>")
					contributor_homepage_node = None
					contributor_role_node = se.easy_xml.EasyXmlElement(f"<meta property=\"role\" refines=\"#{transcriber_id}\" scheme=\"marc:relators\">trc</meta>")
					contributor_lccn_node = None

					if "Distributed Proofreaders Canada" in producer:
						contributor_node.set_text("Distributed Proofreaders Canada")
						contributor_file_as_node.set_text("Distributed Proofreaders Canada")
						contributor_homepage_node = se.easy_xml.EasyXmlElement(f"<meta property=\"se:url.homepage\" refines=\"#{transcriber_id}\">https://www.pgdpcanada.net/</meta>")

					elif "Distributed Proofread" in producer:
						contributor_node.set_text("Distributed Proofreaders")
						contributor_file_as_node.set_text("Distributed Proofreaders")
						contributor_homepage_node = se.easy_xml.EasyXmlElement(f"<meta property=\"se:url.homepage\" refines=\"#{transcriber_id}\">https://www.pgdp.net/</meta>")

					elif "anonymous" in producer.lower():
						contributor_node.set_text("An Anonymous Volunteer")
						contributor_file_as_node.set_text("Anonymous Volunteer, An")

					else:
						contributor_node.set_text(producer.strip("."))
						# Try to naively sort the transcriber.
						matches = regex.search(r"^([\p{Letter}]+) ([\p{Letter}]+)$", producer)

						if matches:
							contributor_file_as_node.set_text( f"{matches[1]}, {matches[2]}")

					# Known special cases.
					if "David Widger" in producer:
						contributor_lccn_node = se.easy_xml.EasyXmlElement(f"<meta property=\"se:url.authority.nacoaf\" refines=\"#{transcriber_id}\">http://id.loc.gov/authorities/names/no2011017869</meta>")

					# Add nodes to metadata.
					for node in epub.metadata_dom.xpath("//dc:contributor[@id='producer-1'][1]"):
						node.insert_before(contributor_node)
						node.insert_before(contributor_file_as_node)

						if contributor_homepage_node:
							node.insert_before(contributor_homepage_node)
						if contributor_lccn_node:
							node.insert_before(contributor_lccn_node)

						node.insert_before(contributor_role_node)

					i = i + 1

			try:
				with open(transcription_local_path, "w", encoding="utf-8") as file:
					file.write(output)
			except OSError as ex:
				raise se.InvalidFileException(f"Couldn’t write to ebook directory. Exception: {ex}") from ex

		# Fill out the titlepage.
		with open(content_path / "epub" / "text" / "titlepage.xhtml", "r+", encoding="utf-8") as file:
			titlepage_xhtml = file.read()

			titlepage_xhtml = titlepage_xhtml.replace("TITLE", escape(title))

			titlepage_xhtml = titlepage_xhtml.replace("AUTHOR_NAME", _generate_titlepage_string(authors, "author"))

			if translators:
				titlepage_xhtml = titlepage_xhtml.replace("TRANSLATOR_NAME", _generate_titlepage_string(translators, "translator"))
			else:
				titlepage_xhtml = regex.sub(r"<p>Translated by.+?</p>", "", titlepage_xhtml, flags=regex.DOTALL)

			if illustrators:
				titlepage_xhtml = titlepage_xhtml.replace("ILLUSTRATOR_NAME", _generate_titlepage_string(illustrators, "illustrator"))
			else:
				titlepage_xhtml = regex.sub(r"<p>Illustrated by.+?</p>", "", titlepage_xhtml, flags=regex.DOTALL)

			file.seek(0)
			file.write(se.formatting.format_xhtml(titlepage_xhtml))
			file.truncate()

		# Set the language in the ToC, so that `se modernize-spelling` doesn't crash when we try to run it.
		if transcription_language:
			toc_dom = epub.get_dom(epub.toc_path)
			for node in toc_dom.xpath("//*[contains(@xml:lang, 'LANG')]"):
				node.set_attr("xml:lang", transcription_language)

			epub.write_dom(epub.toc_path)

		if not args.white_label:
			# Fill out the colophon.
			with open(content_path / "epub" / "text" / "colophon.xhtml", "r+", encoding="utf-8") as file:
				colophon_xhtml = file.read()

				colophon_xhtml = colophon_xhtml.replace("SE_SLUG", epub.generate_url_slug())
				colophon_xhtml = colophon_xhtml.replace("TITLE", escape(title))

				contributor_string = _generate_contributor_string(authors, True)

				if contributor_string == "":
					colophon_xhtml = colophon_xhtml.replace(" by<br/>\n\t\t\t<a href=\"AUTHOR_WIKI_URL\">AUTHOR_NAME</a>", escape(contributor_string))
				else:
					colophon_xhtml = colophon_xhtml.replace("<a href=\"AUTHOR_WIKI_URL\">AUTHOR_NAME</a>", contributor_string)

				if translators:
					translator_block = f"It was translated from ORIGINAL_LANGUAGE in <time>TRANSLATION_YEAR</time> by<br/>\n\t\t\t{_generate_contributor_string(translators, True)}.</p>"
					colophon_xhtml = colophon_xhtml.replace("</p>\n\t\t\t<p>This ebook was produced for<br/>", f"<br/>\n\t\t\t{translator_block}\n\t\t\t<p>This ebook was produced for<br/>")

				if transcription_url:
					colophon_xhtml = colophon_xhtml.replace("TRANSCRIPTION_URL", transcription_url)

				if transcription_publication_year:
					colophon_xhtml = colophon_xhtml.replace("TRANSCRIPTION_YEAR", transcription_publication_year)

				if transcription_producers:
					producer_count = len(transcription_producers)
					producers_xhtml = ""
					for i, producer in enumerate(transcription_producers):
						if "Distributed Proofreaders Canada" in producer:
							producers_xhtml = producers_xhtml + """<a href="https://www.pgdpcanada.net/">Distributed Proofreaders Canada</a>"""
						elif "Distributed Proofread" in producer:
							producers_xhtml = producers_xhtml + """<a href="https://www.pgdp.net/">Distributed Proofreaders</a>"""
						elif "anonymous" in producer.lower():
							producers_xhtml = producers_xhtml + """<b epub:type="z3998:personal-name">An Anonymous Volunteer</b>"""
						else:
							producers_xhtml = producers_xhtml + f"""<b epub:type="z3998:personal-name">{_add_name_abbr(escape(producer)).strip('.')}</b>"""

						if i < producer_count - 1:
							# If exactly two producers, we don't want a comma between them.
							if producer_count == 2:
								producers_xhtml = producers_xhtml + " "
							else:
								producers_xhtml = producers_xhtml + ", "

						if i == producer_count - 2:
							producers_xhtml = producers_xhtml + "and "

					producers_xhtml = producers_xhtml + "<br/>"

					colophon_xhtml = colophon_xhtml.replace("""<b epub:type="z3998:personal-name">TRANSCRIBER_1_NAME</b>, <b epub:type="z3998:personal-name">TRANSCRIBER_2_NAME</b>, and <a href="https://www.pgdp.net/">Distributed Proofreaders</a><br/>""", producers_xhtml)

				if transcription_source:
					colophon_xhtml = colophon_xhtml.replace("TRANSCRIPTION_SOURCE", escape(transcription_source))

				file.seek(0)
				file.write(colophon_xhtml)
				file.truncate()

			# Build the cover/titlepage for distribution.
			epub.generate_titlepage_svg()
			epub.build_titlepage_svg()

			epub.generate_cover_svg()
			epub.build_cover_svg()

			if transcription_url:
				_replace_in_file(content_path / "epub" / "text" / "imprint.xhtml", "TRANSCRIPTION_URL", transcription_url)

			if transcription_source:
				_replace_in_file(content_path / "epub" / "text" / "imprint.xhtml", "TRANSCRIPTION_SOURCE", escape(transcription_source))

		metadata_xml = epub.metadata_dom.to_string()
		metadata_xml = se.formatting.format_opf(metadata_xml)
		with open(epub.metadata_file_path, "w", encoding="utf-8") as file:
			file.write(metadata_xml)

		# Set up local Git repo.
		if args.verbose:
			console.print(se.prep_output("Initializing git repository ...", plain_output))

		repo = Repo.init(work_path)

		if args.email:
			with repo.config_writer() as config:
				config.set_value("user", "email", args.email)

		# Move the result to the final destination
		shutil.move(work_path, repo_path)

	if args.pg_id and transcription_ebook_html and not is_external_html_parsed:
		raise se.InvalidXhtmlException(f"Couldn’t parse Project Gutenberg ebook source; this is usually due to invalid HTML in the ebook. The raw text was saved to [path][link={transcription_local_path}]{transcription_local_path}[/][/].")

def create_draft(plain_output: bool) -> int:
	"""
	Entry point for `se create-draft`.
	"""

	parser = argparse.ArgumentParser(description="Create a skeleton of a new Standard Ebook in the current directory.")
	parser.add_argument("-i", "--illustrator", dest="illustrator", nargs="+", help="an illustrator of the ebook")
	parser.add_argument("-r", "--translator", dest="translator", nargs="+", help="a translator of the ebook")
	parser.add_argument("-p", "--pg-id", dest="pg_id", type=se.is_positive_integer, help="the Project Gutenberg ID number of the ebook to download")
	parser.add_argument("-e", "--email", dest="email", help="use this email address as the main committer for the local Git repository")
	parser.add_argument("-o", "--offline", dest="offline", action="store_true", help="create draft without network access")
	parser.add_argument("-a", "--author", dest="author", required=True, nargs="+", help="an author of the ebook")
	parser.add_argument("-t", "--title", dest="title", required=True, help="the title of the ebook")
	parser.add_argument("-w", "--white-label", action="store_true", help="create a generic epub skeleton without S.E. branding")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("-f", "--fp-id", dest="fp_id", type=se.is_positive_integer, help="the Faded Page ID number of the ebook to download")
	args = parser.parse_args()

	try:
		# Before we continue, confirm that there isn't a subtitle passed in with the title.
		if ":" in args.title:
			console.print(se.prep_output("Titles should not include a subtitle, as subtitles are separate metadata elements in [path]content.opf[/]. Are you sure you want to continue? \\[y/N]", plain_output))
			if input().lower() not in {"yes", "y"}:
				return se.InvalidInputException.code

		# `--pg-id` and `--fp-id` are mutually exclusive.
		if args.pg_id and args.fp_id:
			console.print(se.prep_output("Can’t specify [bash]--pg-id[/] and [bash]--fp-id[/] at the same time.", plain_output))
			return se.InvalidArgumentsException.code

		if (args.pg_id or args.fp_id) and args.offline:
			raise se.RemoteCommandErrorException("Can’t specify [bash]--pg-id[/] or [bash]--fp-id[/], and also [bash]--offline[/].")

		_create_draft(args, plain_output)

	except se.SeException as ex:
		se.print_error(ex)
		return ex.code

	return 0
