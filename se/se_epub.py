#!/usr/bin/env python3

import os
import filecmp
import glob
import regex
import se
import se.formatting
import roman
import lxml.cssselect
import lxml.etree as etree
from bs4 import BeautifulSoup, NavigableString


class LintMessage:
	text = ""
	filename = ""
	message_type = se.MESSAGE_TYPE_WARNING
	is_submessage = False

	def __init__(self, text, message_type=se.MESSAGE_TYPE_WARNING, filename="", is_submessage=False):
		self.text = text.strip()
		self.filename = filename
		self.message_type = message_type
		self.is_submessage = is_submessage

class SeEpub:
	directory = ""
	__tools_root_directory = ""

	def __init__(self, directory, tools_root_directory):
		if not os.path.isdir(directory):
			raise NotADirectoryError("Not a directory: {}".format(directory))

		if not os.path.isfile(os.path.join(directory, "src", "epub", "content.opf")):
			raise NotADirectoryError("Not a Standard Ebooks source directory: {}".format(directory))

		self.directory = os.path.abspath(directory)
		self.__tools_root_directory = os.path.abspath(tools_root_directory)

	def __get_malformed_urls(self, xhtml):
		messages = []

		# Check for non-https URLs
		if "http://www.gutenberg.org" in xhtml:
			messages.append(LintMessage("Non-https gutenberg.org URL.", se.MESSAGE_TYPE_ERROR))

		if "http://www.pgdp.net" in xhtml:
			messages.append(LintMessage("Non-https pgdp.net URL.", se.MESSAGE_TYPE_ERROR))

		if "http://catalog.hathitrust.org" in xhtml:
			messages.append(LintMessage("Non-https hathitrust.org URL.", se.MESSAGE_TYPE_ERROR))

		if "http://archive.org" in xhtml:
			messages.append(LintMessage("Non-https archive.org URL.", se.MESSAGE_TYPE_ERROR))

		if "www.archive.org" in xhtml:
			messages.append(LintMessage("archive.org URL should not have leading www.", se.MESSAGE_TYPE_ERROR))

		if "http://en.wikipedia.org" in xhtml:
			messages.append(LintMessage("Non-https en.wikipedia.org URL.", se.MESSAGE_TYPE_ERROR))

		# Check for malformed canonical URLs
		if regex.search(r"books\.google\.com/books\?id=.+?[&#]", xhtml):
			messages.append(LintMessage("Non-canonical Google Books URL. Google Books URLs must look exactly like https://books.google.com/books?id=<BOOK-ID>"))

		if "babel.hathitrust.org" in xhtml:
			messages.append(LintMessage("Non-canonical Hathi Trust URL. Hathi Trust URLs must look exactly like https://catalog.hathitrust.org/Record/<BOOK-ID>"))

		if ".gutenberg.org/files/" in xhtml:
			messages.append(LintMessage("Non-canonical Project Gutenberg URL. Project Gutenberg URLs must look exactly like https://www.gutenberg.org/ebooks/<BOOK-ID>"))

		if "archive.org/stream" in xhtml:
			messages.append(LintMessage("Non-canonical archive.org URL. Internet Archive URLs must look exactly like https://archive.org/details/<BOOK-ID>"))

		return messages

	def __get_unused_selectors(self):
		try:
			with open(os.path.join(self.directory, "src", "epub", "css", "local.css"), encoding="utf-8") as file:
				css = file.read()
		except Exception:
			raise FileNotFoundError("Couldn't open {}".format(os.path.join(self.directory, "src", "epub", "css", "local.css")))

		# Remove actual content of css selectors
		css = regex.sub(r"{[^}]+}", "", css, flags=regex.MULTILINE)

		# Remove trailing commas
		css = regex.sub(r",", "", css)

		# Remove comments
		css = regex.sub(r"/\*.+?\*/", "", css, flags=regex.DOTALL)

		# Remove @ defines
		css = regex.sub(r"^@.+", "", css, flags=regex.MULTILINE)

		# Construct a dictionary of selectors
		selectors = set([line for line in css.splitlines() if line != ""])
		unused_selectors = set(selectors)

		# Get a list of .xhtml files to search
		filenames = glob.glob(os.path.join(self.directory, "src", "epub", "text") + os.sep + "*.xhtml")

		# Now iterate over each CSS selector and see if it's used in any of the files we found
		for selector in selectors:
			try:
				sel = lxml.cssselect.CSSSelector(selector, translator="html", namespaces=se.XHTML_NAMESPACES)
			except lxml.cssselect.ExpressionError:
				# This gets thrown if we use pseudo-elements, which lxml doesn't support
				unused_selectors.remove(selector)
				continue

			for filename in filenames:
				if not filename.endswith("titlepage.xhtml") and not filename.endswith("imprint.xhtml") and not filename.endswith("uncopyright.xhtml"):
					# We have to remove the default namespace declaration from our document, otherwise
					# xpath won't find anything at all.  See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python
					with open(filename, "r") as file:
						xhtml = file.read().replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")

					try:
						tree = etree.fromstring(str.encode(xhtml))
					except Exception:
						se.print_error("Couldn't parse XHTML in file: {}".format(filename))
						exit(1)

					if tree.xpath(sel.path, namespaces=se.XHTML_NAMESPACES):
						unused_selectors.remove(selector)
						break

		return unused_selectors

	def generate_manifest(self):
		manifest = []

		# Add CSS
		for _, _, filenames in os.walk(os.path.join(self.directory, "src", "epub", "css")):
			for filename in filenames:
				manifest.append("<item href=\"css/{}\" id=\"{}\" media-type=\"text/css\"/>".format(filename, filename))

		# Add images
		for _, _, filenames in os.walk(os.path.join(self.directory, "src", "epub", "images")):
			for filename in filenames:
				media_type = "image/jpeg"
				properties = ""

				if filename.endswith(".svg"):
					media_type = "image/svg+xml"

				if filename.endswith(".png"):
					media_type = "image/png"

				if filename == "cover.svg":
					properties = " properties=\"cover-image\""

				manifest.append("<item href=\"images/{}\" id=\"{}\" media-type=\"{}\"{}/>".format(filename, filename, media_type, properties))

		# Add XHTML files
		for root, _, filenames in os.walk(os.path.join(self.directory, "src", "epub", "text")):
			for filename in filenames:
				properties = ""

				with open(os.path.join(root, filename), "r", encoding="utf-8") as file:
					file_contents = file.read()
					if ".svg" in file_contents:
						properties = " properties=\"svg\""

				manifest.append("<item href=\"text/{}\" id=\"{}\" media-type=\"application/xhtml+xml\"{}/>".format(filename, filename, properties))

		manifest = se.natural_sort(manifest)

		manifest_xhtml = "<manifest>\n\t<item href=\"toc.xhtml\" id=\"toc.xhtml\" media-type=\"application/xhtml+xml\" properties=\"nav\"/>\n"

		for line in manifest:
			manifest_xhtml = manifest_xhtml + "\t" + line + "\n"

		manifest_xhtml = manifest_xhtml + "</manifest>"

		return manifest_xhtml

	def generate_spine(self):
		excluded_files = se.IGNORED_FILENAMES + ["dedication.xhtml", "introduction.xhtml", "foreword.xhtml", "preface.xhtml", "epigraph.xhtml", "endnotes.xhtml"]
		spine = ["<itemref idref=\"titlepage.xhtml\"/>", "<itemref idref=\"imprint.xhtml\"/>"]

		filenames = se.natural_sort(os.listdir(os.path.join(self.directory, "src", "epub", "text")))

		if "dedication.xhtml" in filenames:
			spine.append("<itemref idref=\"dedication.xhtml\"/>")

		if "introduction.xhtml" in filenames:
			spine.append("<itemref idref=\"introduction.xhtml\"/>")

		if "foreword.xhtml" in filenames:
			spine.append("<itemref idref=\"foreword.xhtml\"/>")

		if "preface.xhtml" in filenames:
			spine.append("<itemref idref=\"preface.xhtml\"/>")

		if "epigraph.xhtml" in filenames:
			spine.append("<itemref idref=\"epigraph.xhtml\"/>")

		if "halftitle.xhtml" in filenames:
			spine.append("<itemref idref=\"halftitle.xhtml\"/>")

		for filename in filenames:
			if filename not in excluded_files:
				spine.append("<itemref idref=\"{}\"/>".format(filename))

		if "endnotes.xhtml" in filenames:
			spine.append("<itemref idref=\"endnotes.xhtml\"/>")

		if "loi.xhtml" in filenames:
			spine.append("<itemref idref=\"loi.xhtml\"/>")

		spine.append("<itemref idref=\"colophon.xhtml\"/>")
		spine.append("<itemref idref=\"uncopyright.xhtml\"/>")

		spine_xhtml = "<spine>\n"
		for line in spine:
			spine_xhtml = spine_xhtml + "\t" + line + "\n"

		spine_xhtml = spine_xhtml + "</spine>"

		return spine_xhtml

	def lint(self):
		messages = []

		license_file_path = os.path.join(self.__tools_root_directory, "templates", "LICENSE.md")
		core_css_file_path = os.path.join(self.__tools_root_directory, "templates", "core.css")
		logo_svg_file_path = os.path.join(self.__tools_root_directory, "templates", "logo.svg")
		uncopyright_file_path = os.path.join(self.__tools_root_directory, "templates", "uncopyright.xhtml")
		has_halftitle = False
		has_frontmatter = False
		xhtml_css_classes = []
		headings = []

		with open(os.path.join(self.directory, "src", "epub", "content.opf"), "r+", encoding="utf-8") as file:
			metadata_xhtml = file.read()

		# Get the ebook language, for later use
		language = regex.search(r"<dc:language>([^>]+?)</dc:language>", metadata_xhtml).group(1)

		# Check local.css for various items, for later use
		abbr_elements = []
		css = ""
		with open(os.path.join(self.directory, "src", "epub", "css", "local.css"), "r", encoding="utf-8") as file:
			css = file.read()

			local_css_has_subtitle_style = "span[epub|type~=\"subtitle\"]" in css

			abbr_styles = regex.findall(r"abbr\.[a-z]+", css)

		# Check for presence of ./dist/ folder
		if os.path.exists(os.path.join(self.directory, "dist")):
			messages.append(LintMessage("Illegal ./dist/ folder. Do not commit compiled versions of the source.", se.MESSAGE_TYPE_ERROR, "./dist/"))

		# Check if there are non-typogrified quotes or em-dashes in metadata descriptions
		if regex.search(r"#description\">[^<]+?(['\"]|\-\-)[^<]+?</meta>", metadata_xhtml.replace("\"&gt;", "").replace("=\"", "")) is not None:
			messages.append(LintMessage("Non-typogrified \", ', or -- detected in metadata long description", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for double spacing
		regex_string = r"[{}{} ]{{2,}}".format(se.NO_BREAK_SPACE, se.HAIR_SPACE)
		matches = regex.findall(regex_string, metadata_xhtml)
		if matches:
			messages.append(LintMessage("Double spacing detected in file. Sentences should be single-spaced.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		if regex.search(r"<dc:description id=\"description\">[^<]+?(['\"]|\-\-)[^<]+?</dc:description>", metadata_xhtml) is not None:
			messages.append(LintMessage("Non-typogrified \", ', or -- detected in metadata dc:description.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
		matches = regex.findall(r"[a-zA-Z][”][,.]", metadata_xhtml)
		if matches:
			messages.append(LintMessage("Comma or period outside of double quote. Generally punctuation should go within single and double quotes.", se.MESSAGE_TYPE_WARNING, "content.opf"))

		#Check for HTML entities in long-description
		if regex.search(r"&amp;[a-z]+?;", metadata_xhtml):
			messages.append(LintMessage("HTML entites detected in metadata. Use Unicode equivalents instead.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for illegal em-dashes in <dc:subject>
		if regex.search(r"<dc:subject id=\"[^\"]+?\">[^<]+?—[^<]+?</dc:subject>", metadata_xhtml) is not None:
			messages.append(LintMessage("Illegal em-dash detected in dc:subject; use --", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for illegal VCS URLs
		matches = regex.findall(r"<meta property=\"se:url\.vcs\.github\">([^<]+?)</meta>", metadata_xhtml)
		if matches:
			for match in matches:
				if not match.startswith("https://github.com/standardebooks/"):
					messages.append(LintMessage("Illegal se:url.vcs.github. VCS URLs must begin with https://github.com/standardebooks/: {}".format(match), se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for illegal se:subject tags
		matches = regex.findall(r"<meta property=\"se:subject\">([^<]+?)</meta>", metadata_xhtml)
		if matches:
			for match in matches:
				if match not in se.SE_GENRES:
					messages.append(LintMessage("Illegal se:subject: {}".format(match), se.MESSAGE_TYPE_ERROR, "content.opf"))
		else:
			messages.append(LintMessage("No se:subject <meta> tag found.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for CDATA tags
		if "<![CDATA[" in metadata_xhtml:
			messages.append(LintMessage("<![CDATA[ detected. Run `clean` to canonicalize <![CDATA[ sections.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check if se:name.person.full-name matches their titlepage name
		matches = regex.findall(r"<meta property=\"se:name\.person\.full-name\" refines=\"#([^\"]+?)\">([^<]*?)</meta>", metadata_xhtml)
		duplicate_names = []
		for match in matches:
			name_matches = regex.findall(r"<([a-z:]+)[^<]+?id=\"{}\"[^<]*?>([^<]*?)</\1>".format(match[0]), metadata_xhtml)
			for name_match in name_matches:
				if name_match[1] == match[1]:
					duplicate_names.append(name_match[1])

		if duplicate_names:
			messages.append(LintMessage("se:name.person.full-name property identical to regular name. If the two are identical the full name <meta> element must be removed.", se.MESSAGE_TYPE_ERROR, "content.opf"))
			for duplicate_name in duplicate_names:
				messages.append(LintMessage(duplicate_name, se.MESSAGE_TYPE_ERROR, "", True))

		# Check for malformed URLs
		for message in self.__get_malformed_urls(metadata_xhtml):
			message.filename = "content.opf"
			messages.append(message)

		if regex.search(r"id\.loc\.gov/authorities/names/[^\.]+\.html", metadata_xhtml):
			messages.append(LintMessage("id.loc.gov URL ending with illegal .html", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Does the manifest match the generated manifest?
		for manifest in regex.findall(r"<manifest>.*?</manifest>", metadata_xhtml, flags=regex.DOTALL):
			manifest = regex.sub(r"[\n\t]", "", manifest)
			expected_manifest = regex.sub(r"[\n\t]", "", self.generate_manifest())

			if manifest != expected_manifest:
				messages.append(LintMessage("<manifest> does not match expected structure.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Make sure some static files are unchanged
		try:
			if not filecmp.cmp(license_file_path, os.path.join(self.directory, "LICENSE.md")):
				messages.append(LintMessage("LICENSE.md does not match {}".format(license_file_path), se.MESSAGE_TYPE_ERROR, "LICENSE.md"))
		except Exception:
			messages.append(LintMessage("Missing ./LICENSE.md", se.MESSAGE_TYPE_ERROR, "LICENSE.md"))

		if not filecmp.cmp(core_css_file_path, os.path.join(self.directory, "src", "epub", "css", "core.css")):
			messages.append(LintMessage("core.css does not match {}".format(core_css_file_path), se.MESSAGE_TYPE_ERROR, "core.css"))

		if not filecmp.cmp(logo_svg_file_path, os.path.join(self.directory, "src", "epub", "images", "logo.svg")):
			messages.append(LintMessage("logo.svg does not match {}".format(logo_svg_file_path), se.MESSAGE_TYPE_ERROR, "logo.svg"))

		if not filecmp.cmp(uncopyright_file_path, os.path.join(self.directory, "src", "epub", "text", "uncopyright.xhtml")):
			messages.append(LintMessage("uncopyright.xhtml does not match {}".format(uncopyright_file_path), se.MESSAGE_TYPE_ERROR, "uncopyright.xhtml"))

		# Check for unused selectors
		unused_selectors = self.__get_unused_selectors()
		if unused_selectors:
			messages.append(LintMessage("Unused CSS selectors:", se.MESSAGE_TYPE_ERROR, "local.css"))
			for selector in unused_selectors:
				messages.append(LintMessage(selector, se.MESSAGE_TYPE_ERROR, "", True))

		# Now iterate over individual files for some checks
		for root, _, filenames in os.walk(self.directory):
			for filename in sorted(filenames, key=se.natural_sort_key):
				if ".git/" in os.path.join(root, filename) or filename.endswith(tuple(se.BINARY_EXTENSIONS)):
					continue

				if filename.startswith(".") or filename.startswith("README"):
					messages.append(LintMessage("Illegal {} file detected in {}".format(filename, root), se.MESSAGE_TYPE_ERROR))

				with open(os.path.join(root, filename), "r", encoding="utf-8") as file:
					try:
						file_contents = file.read()
					except UnicodeDecodeError:
						# This is more to help developers find weird files that might choke 'lint', hopefully unnecessary for end users
						messages.append(LintMessage("Problem decoding file as utf-8", se.MESSAGE_TYPE_ERROR, filename))
						continue

					if "UTF-8" in file_contents:
						messages.append(LintMessage("String \"UTF-8\" must always be lowercase.", se.MESSAGE_TYPE_ERROR, filename))

					if filename == "halftitle.xhtml":
						has_halftitle = True

					if filename.endswith(".svg"):
						if "<title>" not in file_contents:
							messages.append(LintMessage("SVG file missing <title> tag. Usually the SVG <title> matches the corresponding <img> tag's alt attribute.", se.MESSAGE_TYPE_ERROR, filename))

						if os.sep + "src" + os.sep not in root:
							# Check that cover and titlepage images are in all caps
							if filename == "cover.svg":
								matches = regex.findall(r"<text[^>]+?>.*[a-z].*</text>", file_contents)
								if matches:
									messages.append(LintMessage("Lowercase letters in cover. Cover text must be all uppercase.", se.MESSAGE_TYPE_ERROR, filename))

							if filename == "titlepage.svg":
								matches = regex.findall(r"<text[^>]+?>(.*[a-z].*)</text>", file_contents)
								if matches:
									for match in matches:
										if match != "translated by" and match != "illustrated by" and match != "and":
											messages.append(LintMessage("Lowercase letters in titlepage. Titlepage text must be all uppercase except \"translated by\", \"illustrated by\", and \"and\" joining translators/illustrators.", se.MESSAGE_TYPE_ERROR, filename))
					if filename.endswith(".css"):
						# Check CSS style

						# No space before CSS opening braces
						matches = regex.findall(r".+\s\{", file_contents)
						if matches:
							messages.append(LintMessage("CSS opening braces must not be preceded by space.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# CSS closing braces on their own line
						matches = regex.findall(r"^\s*[^\s+]\s*.+\}", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append(LintMessage("CSS closing braces must be on their own line.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# White space before CSS closing braces
						matches = regex.findall(r"^\s+\}", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append(LintMessage("No white space before CSS closing braces.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Properties not indented with tabs
						matches = regex.findall(r"^[^\t@/].+:[^\{,]+?;$", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append(LintMessage("CSS properties must be indented with exactly one tab.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Blank space between selectors
						matches = regex.findall(r"\}\n[^\s]+", file_contents)
						if matches:
							messages.append(LintMessage("CSS selectors must have exactly one blank line between them.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						matches = regex.findall(r"\}\n\s{2,}[^\s]+", file_contents)
						if matches:
							messages.append(LintMessage("CSS selectors must have exactly one blank line between them.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Properties indented with multiple tabs
						matches = regex.findall(r"^\t{2,}.+:[^\{,]+?;$", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append(LintMessage("CSS properties must be indented with exactly one tab.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

					if filename.endswith(".xhtml"):
						for message in self.__get_malformed_urls(file_contents):
							message.filename = filename
							messages.append(message)

						# Check if this is a frontmatter file
						if filename != "titlepage.xhtml" and filename != "imprint.xhtml" and filename != "toc.xhtml":
							matches = regex.findall(r"epub:type=\"[^\"]*?frontmatter[^\"]*?\"", file_contents)
							if matches:
								has_frontmatter = True

						# Add new CSS classes to global list
						if filename not in se.IGNORED_FILENAMES:
							matches = regex.findall(r"(?:class=\")[^\"]+?(?:\")", file_contents)
							for match in matches:
								xhtml_css_classes = xhtml_css_classes + match.replace("class=", "").replace("\"", "").split()

						# Read file contents into a DOM for querying
						dom = BeautifulSoup(file_contents, "lxml")

						# Store all headings to check for ToC references later
						if filename != "toc.xhtml":
							matches = dom.select('h1,h2,h3,h4,h5,h6')
							for match in matches:

								# Remove any links to the endnotes
								endnote_ref = match.find('a', attrs={"epub:type": regex.compile("^.*noteref.*$")})
								if endnote_ref:
									endnote_ref.extract()

								# Remove any subtitles on halftitle pages
								if match.find_parent(attrs={"epub:type": regex.compile("^.*halftitlepage.*$")}):
									halftitle_subtitle = match.find(attrs={"epub:type": regex.compile("^.*subtitle.*$")})
									if halftitle_subtitle:
										halftitle_subtitle.extract()

								# Remove any subtitles from headings that don’t have a preceding roman number)
								heading_first_child = match.find('span',recursive=False)
								if heading_first_child:
									epub_type = heading_first_child.get('epub:type')
									if epub_type is None or len(regex.findall(r"z3998:roman", epub_type)) == 0:
										unnumbered_subtitle = match.find(attrs={"epub:type": regex.compile("^.*subtitle.*$")})
										if unnumbered_subtitle:
											unnumbered_subtitle.extract()

								normalised_text = ' '.join(match.get_text().split())
								headings = headings + [(normalised_text, filename)]

						# Check for direct z3998:roman spans that should have their semantic pulled into the parent element
						matches = regex.findall(r"<([a-z0-9]+)[^>]*?>\s*(<span epub:type=\"z3998:roman\">[^<]+?</span>)\s*</\1>", file_contents, flags=regex.DOTALL)
						if matches:
							messages.append(LintMessage("If <span> exists only for the z3998:roman semantic, then z3998:roman should be pulled into parent tag instead.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match[1], se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for numeric entities
						matches = regex.findall(r"&#[0-9]+?;", file_contents)
						if matches:
							messages.append(LintMessage("Illegal numeric entity (like &#913;) in file.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for nbsp before times
						matches = regex.findall(r"[0-9]+[^{}]<abbr class=\"time".format(se.NO_BREAK_SPACE), file_contents)
						if matches:
							messages.append(LintMessage("Required nbsp not found before <abbr class=\"time\">", se.MESSAGE_TYPE_WARNING, filename))

						# Check for money not separated by commas
						matches = regex.findall(r"[£\$][0-9]{4,}", file_contents)
						if matches:
							messages.append(LintMessage("Numbers not grouped by commas. Separate numbers greater than 1,000 with commas at every three numerals.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for trailing commas inside <i> tags at the close of dialog
						if ",</i>”" in file_contents:
							messages.append(LintMessage("Comma inside <i> tag before closing dialog. (Search for ,</i>”)", se.MESSAGE_TYPE_WARNING, filename))

						# Check for period following Roman numeral, which is an old-timey style we must fix
						# But ignore the numeral if it's the first item in a <p> tag, as that suggests it might be a kind of list item.
						matches = regex.findall(r"(?<!<p[^>]*?>)<span epub:type=\"z3998:roman\">[^<]+?</span>\.\s+[a-z]", file_contents)
						if matches:
							messages.append(LintMessage("Roman numeral followed by a period. When in mid-sentence Roman numerals must not be followed by a period.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for two em dashes in a row
						matches = regex.findall(r"—{}*—+".format(se.WORD_JOINER), file_contents)
						if matches:
							messages.append(LintMessage("Two or more em-dashes in a row detected. Elided words should use the two- or three-em-dash Unicode character, and dialog ending in em-dashes should only end in a single em-dash.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for <abbr class="name"> that does not contain spaces
						matches = regex.findall(r"<abbr class=\"name\">[^<]*?[A-Z]\.[A-Z]\.[^<]*?</abbr>", file_contents)
						if matches:
							messages.append(LintMessage("Initials in <abbr class=\"name\"> not separated by spaces.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for empty <h2> missing epub:type="title" attribute
						if "<h2>" in file_contents:
							messages.append(LintMessage("<h2> tag without epub:type=\"title\" attribute.", se.MESSAGE_TYPE_WARNING, filename))

						# Check for empty <p> tags
						matches = regex.findall(r"<p>\s*</p>", file_contents)
						if "<p/>" in file_contents or matches:
							messages.append(LintMessage("Empty <p> tag. Use <hr/> for scene breaks if appropriate.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for style attributes
						matches = regex.findall(r"<.+?style=\"", file_contents)
						if matches:
							messages.append(LintMessage("Illegal style attribute. Do not use inline styles, any element can be targeted with a clever enough selector.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for uppercase HTML tags
						if regex.findall(r"<[A-Z]+", file_contents):
							messages.append(LintMessage("One or more uppercase HTML tags.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for Roman numerals in <title> tag
						if regex.findall(r"<title>[Cc]hapter [XxIiVv]+", file_contents):
							messages.append(LintMessage("No Roman numerals allowed in <title> tag; use decimal numbers.", se.MESSAGE_TYPE_ERROR, filename))

						# If the chapter has a number and no subtitle, check the <title> tag
						matches = regex.findall(r"<h([0-6]) epub:type=\"title z3998:roman\">([^<]+)</h\1>", file_contents, flags=regex.DOTALL)

						# But only make the correction if there's one <h#> tag.  If there's more than one, then the xhtml file probably requires an overarching title
						if matches and len(regex.findall(r"<h(?:[0-6])", file_contents)) == 1:
							try:
								chapter_number = roman.fromRoman(matches[0][1].upper())

								regex_string = r"<title>(Chapter|Section|Part) {}".format(chapter_number)
								if not regex.findall(regex_string, file_contents):
									messages.append(LintMessage("<title> tag doesn't match expected value; should be \"Chapter {}\". (Beware hidden Unicode characters!)".format(chapter_number), se.MESSAGE_TYPE_ERROR, filename))
							except Exception:
								messages.append(LintMessage("<h#> tag is marked with z3998:roman, but is not a Roman numeral", se.MESSAGE_TYPE_ERROR, filename))

						# If the chapter has a number and subtitle, check the <title> tag
						matches = regex.findall(r"<h([0-6]) epub:type=\"title\">\s*<span epub:type=\"z3998:roman\">([^<]+)</span>\s*<span epub:type=\"subtitle\">(.+?)</span>\s*</h\1>", file_contents, flags=regex.DOTALL)

						# But only make the correction if there's one <h#> tag.  If there's more than one, then the xhtml file probably requires an overarching title
						if matches and len(regex.findall(r"<h(?:[0-6])", file_contents)) == 1:
							chapter_number = roman.fromRoman(matches[0][1].upper())

							# First, remove endnotes in the subtitle, then remove all other tags (but not tag contents)
							chapter_title = regex.sub(r"<a[^<]+?epub:type=\"noteref\"[^<]*?>[^<]+?</a>", "", matches[0][2]).strip()
							chapter_title = regex.sub(r"<[^<]+?>", "", chapter_title)

							regex_string = r"<title>(Chapter|Section|Part) {}: {}".format(chapter_number, regex.escape(chapter_title))
							if not regex.findall(regex_string, file_contents):
								messages.append(LintMessage("<title> tag doesn't match expected value; should be \"Chapter {}: {}\". (Beware hidden Unicode characters!)".format(chapter_number, chapter_title), se.MESSAGE_TYPE_ERROR, filename))

						# Check for missing subtitle styling
						if "epub:type=\"subtitle\"" in file_contents and not local_css_has_subtitle_style:
							messages.append(LintMessage("Subtitles detected, but no subtitle style detected in local.css.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for <li> elements that don't have a direct block child
						if filename != "toc.xhtml":
							matches = regex.findall(r"<li(?:\s[^>]*?>|>)\s*[^\s<]", file_contents)
							if matches:
								messages.append(LintMessage("<li> without direct block-level child.", se.MESSAGE_TYPE_WARNING, filename))
								for match in matches:
									messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for IDs on <h#> tags
						matches = regex.findall(r"<h[0-6][^>]*?id=[^>]*?>", file_contents, flags=regex.DOTALL)
						if matches:
							messages.append(LintMessage("<h#> tag with id attribute. <h#> tags should be wrapped in <section> tags, which should hold the id attribute.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check to see if <h#> tags are correctly titlecased
						matches = regex.finditer(r"<h([0-6])([^>]*?)>(.*?)</h\1>", file_contents, flags=regex.DOTALL)
						for match in matches:
							if "z3998:roman" not in match.group(2):
								title = match.group(3).strip()

								# Remove leading roman numerals first
								title = regex.sub(r"^<span epub:type=\"[^\"]*?z3998:roman[^\"]*?\">(.*?)</span>", "", title, flags=regex.DOTALL)

								# Remove leading leftover spacing and punctuation
								title = regex.sub(r"^[\s\.\,\!\?\:\;]*", "", title)

								# Remove endnotes
								title = regex.sub(r"<a[^>]*?epub:type=\"noteref\"[^>]*?>[0-9]+</a>", "", title)

								# Normalize whitespace
								title = regex.sub(r"\s+", " ", title, flags=regex.DOTALL).strip()

								# Do we have a subtitle? If so the first letter of that must be capitalized, so we pull that out
								subtitle_matches = regex.findall(r"(.*?)<span epub:type=\"subtitle\">(.*?)</span>(.*?)", title, flags=regex.DOTALL)
								if subtitle_matches:
									for title_header, subtitle, title_footer in subtitle_matches:
										title_header = se.formatting.remove_tags(title_header).strip()
										subtitle = se.formatting.remove_tags(subtitle).strip()
										title_footer = se.formatting.remove_tags(title_footer).strip()

										titlecased_title = se.formatting.titlecase(title_header) + " " + se.formatting.titlecase(subtitle) + " " + se.formatting.titlecase(title_footer)
										titlecased_title = titlecased_title.strip()

										title = se.formatting.remove_tags(title).strip()
										if title != titlecased_title:
											messages.append(LintMessage("Title \"{}\" not correctly titlecased. Expected: {}".format(title, titlecased_title), se.MESSAGE_TYPE_WARNING, filename))

								# No subtitle? Much more straightforward
								else:
									title = se.formatting.remove_tags(title)
									titlecased_title = se.formatting.titlecase(title)
									if title != titlecased_title:
										messages.append(LintMessage("Title \"{}\" not correctly titlecased. Expected: {}".format(title, titlecased_title), se.MESSAGE_TYPE_WARNING, filename))

						# Check for <figure> tags without id attributes
						if "<figure>" in file_contents:
							messages.append(LintMessage("<figure> tag without ID attribute; <figure> tags should have the ID attribute, not their children <img> tags.", se.MESSAGE_TYPE_WARNING, filename))

						# Check for closing dialog without comma
						matches = regex.findall(r"[a-z]+?” [a-zA-Z]+? said", file_contents)
						if matches:
							messages.append(LintMessage("Dialog without ending comma.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_WARNING, filename, True))

						# Check for non-typogrified img alt attributes
						matches = regex.findall(r"alt=\"[^\"]*?('|--|&quot;)[^\"]*?\"", file_contents)
						if matches:
							messages.append(LintMessage("Non-typogrified ', \" (as &quot;), or -- in image alt attribute.", se.MESSAGE_TYPE_ERROR, filename))

						# Check alt attributes not ending in punctuation
						if filename not in se.IGNORED_FILENAMES:
							matches = regex.findall(r"alt=\"[^\"]*?[a-zA-Z]\"", file_contents)
							if matches:
								messages.append(LintMessage("Alt attribute doesn't appear to end with puncutation. Alt attributes must be composed of complete sentences ending in appropriate punctuation.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for punctuation after endnotes
						regex_string = r"<a[^>]*?epub:type=\"noteref\"[^>]*?>[0-9]+</a>[^\s<–\]\)—{}]".format(se.WORD_JOINER)
						matches = regex.findall(regex_string, file_contents)
						if matches:
							messages.append(LintMessage("Endnote links must be outside of punctuation, including quotation marks.", se.MESSAGE_TYPE_WARNING, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for nbsp in measurements, for example: 90 mm
						matches = regex.findall(r"[0-9]+[\- ][mck][mgl]", file_contents)
						if matches:
							messages.append(LintMessage("Measurements must be separated by a no-break space, not a dash or regular space.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for line breaks after <br/> tags
						matches = regex.findall(r"<br\s*?/>[^\n]", file_contents, flags=regex.DOTALL | regex.MULTILINE)
						if matches:
							messages.append(LintMessage("<br/> tags must be followed by a newline, and subsequent content must be indented to the same level.", se.MESSAGE_TYPE_ERROR, filename))
							for match in matches:
								messages.append(LintMessage(match, se.MESSAGE_TYPE_ERROR, filename, True))

						# Check for <pre> tags
						if "<pre" in file_contents:
							messages.append(LintMessage("Illegal <pre> tag.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for double spacing
						regex_string = r"[{}{} ]{{2,}}".format(se.NO_BREAK_SPACE, se.HAIR_SPACE)
						matches = regex.findall(regex_string, file_contents)
						if matches:
							messages.append(LintMessage("Double spacing detected in file. Sentences should be single-spaced. (Note that double spaces might include Unicode no-break spaces!)", se.MESSAGE_TYPE_ERROR, filename))

						# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
						matches = regex.findall(r"[a-zA-Z][”][,.]", file_contents)
						if matches:
							messages.append(LintMessage("Comma or period outside of double quote. Generally punctuation should go within single and double quotes.", se.MESSAGE_TYPE_WARNING, filename))

						# Did someone use colons instead of dots for SE identifiers? e.g. se:name:vessel:ship
						matches = regex.findall(r"\bse:[a-z]+:(?:[a-z]+:?)*", file_contents)
						if matches:
							messages.append(LintMessage("Illegal colon (:) detected in SE identifier. SE identifiers are separated by dots (.) not colons (:). Identifier: {}".format(matches), se.MESSAGE_TYPE_ERROR, filename))

						# Check for space before endnote backlinks
						if filename == "endnotes.xhtml":
							endnotes_soup = BeautifulSoup(file_contents, "lxml")
							endnote_referrers = endnotes_soup.select("li[data-se-note-number] a")

							bad_referrers = []

							for referrer in endnote_referrers:
								if "epub:type" in referrer.attrs:
									is_first_sib = True
									for sib in referrer.previous_siblings:
										if is_first_sib:
											is_first_sib = False
											if isinstance(sib, NavigableString):
												if sib == "\n": # Referrer preceded by newline. Check if all previous sibs are tags.
													continue
												elif sib == " " or str(sib) == se.NO_BREAK_SPACE or regex.search(r"[^\s] $", str(sib)): # Referrer preceded by a single space; we're OK
													break
												else: # Referrer preceded by a string that is not a newline and does not end with a single space
													bad_referrers.append(referrer)
													break

										else:
											# We got here because the first sib was a newline, or not a string. So, check all previous sibs.
											if isinstance(sib, NavigableString) and sib != "\n":
												bad_referrers.append(referrer)
												break

							if bad_referrers:
								messages.append(LintMessage("Endnote referrer link not preceded by exactly one space, or a newline if all previous siblings are elements.", se.MESSAGE_TYPE_WARNING, filename))
								for referrer in bad_referrers:
									messages.append(LintMessage(str(referrer), se.MESSAGE_TYPE_WARNING, filename, True))

						# If we're in the imprint, are the sources represented correctly?
						# We don't have a standard yet for more than two sources (transcription and scan) so just ignore that case for now.
						if filename == "imprint.xhtml":
							matches = regex.findall(r"<dc:source>([^<]+?)</dc:source>", metadata_xhtml)
							if len(matches) <= 2:
								for link in matches:
									if "gutenberg.org" in link and "<a href=\"{}\">Project Gutenberg</a>".format(link) not in file_contents:
										messages.append(LintMessage("Source not represented in imprint.xhtml. It should read: <a href=\"{}\">Project Gutenberg</a>".format(link), se.MESSAGE_TYPE_WARNING, filename))

									if "hathitrust.org" in link and "the <a href=\"{}\">Hathi Trust Digital Library</a>".format(link) not in file_contents:
										messages.append(LintMessage("Source not represented in imprint.xhtml. It should read: the <a href=\"{}\">Hathi Trust Digital Library</a>".format(link), se.MESSAGE_TYPE_WARNING, filename))

									if "archive.org" in link and "the <a href=\"{}\">Internet Archive</a>".format(link) not in file_contents:
										messages.append(LintMessage("Source not represented in imprint.xhtml. It should read: the <a href=\"{}\">Internet Archive</a>".format(link), se.MESSAGE_TYPE_WARNING, filename))

									if "books.google.com" in link and "<a href=\"{}\">Google Books</a>".format(link) not in file_contents:
										messages.append(LintMessage("Source not represented in imprint.xhtml. It should read: <a href=\"{}\">Google Books</a>".format(link), se.MESSAGE_TYPE_WARNING, filename))

						# Collect abbr elements for later check
						result = regex.findall("<abbr[^<]+?>", file_contents)
						result = [item.replace("eoc", "").replace(" \"", "").strip() for item in result]
						abbr_elements = list(set(result + abbr_elements))

						# Check if language tags in individual files match the language in content.opf
						if filename not in se.IGNORED_FILENAMES:
							file_language = regex.search(r"<html[^<]+xml\:lang=\"([^\"]+)\"", file_contents).group(1)
							if language != file_language:
								messages.append(LintMessage("File language is {}, but content.opf language is {}".format(file_language, language), se.MESSAGE_TYPE_ERROR, filename))

					# Check for missing MARC relators
					if filename == "introduction.xhtml" and ">aui<" not in metadata_xhtml and ">win<" not in metadata_xhtml:
						messages.append(LintMessage("introduction.xhtml found, but no MARC relator 'aui' (Author of introduction, but not the chief author) or 'win' (Writer of introduction)", se.MESSAGE_TYPE_WARNING, filename))

					if filename == "preface.xhtml" and ">wpr<" not in metadata_xhtml:
						messages.append(LintMessage("preface.xhtml found, but no MARC relator 'wpr' (Writer of preface)", se.MESSAGE_TYPE_WARNING, filename))

					if filename == "afterword.xhtml" and ">aft<" not in metadata_xhtml:
						messages.append(LintMessage("afterword.xhtml found, but no MARC relator 'aft' (Author of colophon, afterword, etc.)", se.MESSAGE_TYPE_WARNING, filename))

					if filename == "endnotes.xhtml" and ">ann<" not in metadata_xhtml:
						messages.append(LintMessage("endnotes.xhtml found, but no MARC relator 'ann' (Annotator)", se.MESSAGE_TYPE_WARNING, filename))

					if filename == "loi.xhtml" and ">ill<" not in metadata_xhtml:
						messages.append(LintMessage("loi.xhtml found, but no MARC relator 'ill' (Illustrator)", se.MESSAGE_TYPE_WARNING, filename))

					# Check for wrong semantics in frontmatter/backmatter
					if filename in se.FRONTMATTER_FILENAMES and "frontmatter" not in file_contents:
						messages.append(LintMessage("No frontmatter semantic inflection for what looks like a frontmatter file", se.MESSAGE_TYPE_WARNING, filename))

					if filename in se.BACKMATTER_FILENAMES and "backmatter" not in file_contents:
						messages.append(LintMessage("No backmatter semantic inflection for what looks like a backmatter file", se.MESSAGE_TYPE_WARNING, filename))

		if has_frontmatter and not has_halftitle:
			messages.append(LintMessage("Frontmatter found, but no halftitle. Halftitle is required when frontmatter is present.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		xhtml_css_classes = list(set(xhtml_css_classes))
		for css_class in xhtml_css_classes:
			if css_class != "name" and css_class != "temperature" and css_class != "era" and css_class != "compass" and css_class != "acronym" and css_class != "postal" and css_class != "eoc" and css_class != "initialism" and css_class != "degree" and css_class != "time" and css_class != "compound" and css_class != "timezone":
				if "." + css_class not in css:
					messages.append(LintMessage("class {} found in xhtml, but no style in local.css".format(css_class), se.MESSAGE_TYPE_ERROR, "local.css"))

		headings = list(set(headings))
		with open(os.path.join(self.directory, "src", "epub", "toc.xhtml"), "r", encoding="utf-8") as toc:
			toc_entries = BeautifulSoup(toc.read(), "lxml").find_all('a')
			# ToC headers have a ‘:’ after the chapter number that main headings don’t
			for index, entry in enumerate(toc_entries):
				toc_entries[index] = ' '.join(entry.get_text().replace(":", "").split())
			for heading in headings:
				if heading[0] not in toc_entries:
					messages.append(LintMessage("Heading ‘{}’ found, but not present in the ToC".format(heading[0]), se.MESSAGE_TYPE_ERROR, heading[1]))

		for element in abbr_elements:
			try:
				css_class = regex.search(r"class=\"([^\"]+?)\"", element).group(1)
			except Exception:
				continue
			if css_class and (css_class == "name" or css_class == "temperature" or css_class == "era" or css_class == "compass" or css_class == "acronym") and "abbr." + css_class not in abbr_styles:
				messages.append(LintMessage("abbr.{} element found, but no required style in local.css (See semantics manual for style)".format(css_class), se.MESSAGE_TYPE_ERROR, "local.css"))

		return messages
