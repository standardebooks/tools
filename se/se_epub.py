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

	def lint(self):
		messages = []

		license_file_path = os.path.join(self.__tools_root_directory, "templates", "LICENSE.md")
		core_css_file_path = os.path.join(self.__tools_root_directory, "templates", "core.css")
		logo_svg_file_path = os.path.join(self.__tools_root_directory, "templates", "logo.svg")
		uncopyright_file_path = os.path.join(self.__tools_root_directory, "templates", "uncopyright.xhtml")

		with open(os.path.join(self.directory, "src", "epub", "content.opf"), "r+", encoding="utf-8") as file:
			metadata_xhtml = file.read()

		# Get the ebook language, for later use
		language = regex.search(r"<dc:language>([^>]+?)</dc:language>", metadata_xhtml).group(1)

		# Check local.css for various items, for later use
		abbr_elements = []
		with open(os.path.join(self.directory, "src", "epub", "css", "local.css"), "r", encoding="utf-8") as file:
			css = file.read()

			local_css_has_subtitle_style = "span[epub|type~=\"subtitle\"]" in css

			abbr_styles = regex.findall(r"abbr\.[a-z]+", css)

		# Check if there are non-typogrified quotes or em-dashes in metadata descriptions
		if regex.search(r"#description\">[^<]+?(['\"]|\-\-)[^<]+?</meta>", metadata_xhtml.replace("\"&gt;", "").replace("=\"", "")) is not None:
			messages.append(LintMessage("Non-typogrified \", ', or -- detected in metadata long description", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for double spacing
		regex_string = r"[{}{} ]{{2,}}".format(se.NO_BREAK_SPACE, se.HAIR_SPACE)
		matches = regex.findall(regex_string, metadata_xhtml)
		if matches:
			messages.append(LintMessage("Double spacing detected in file. Sentences should be single-spaced.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		if regex.search(r"<dc:description id=\"description\">[^<]+?(['\"]|\-\-)[^<]+?</meta>", metadata_xhtml) is not None:
			messages.append(LintMessage("Non-typogrified \", ', or -- detected in metadata dc:description.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		#Check for HTML entities in long-description
		if regex.search(r"&amp;[a-z]+?;", metadata_xhtml):
			messages.append(LintMessage("HTML entites detected in metadata. Use Unicode equivalents instead.", se.MESSAGE_TYPE_ERROR, "content.opf"))

		# Check for illegal em-dashes in <dc:subject>
		if regex.search(r"<dc:subject id=\"[^\"]+?\">[^<]+?—[^<]+?</meta>", metadata_xhtml) is not None:
			messages.append(LintMessage("Illegal em-dash detected in dc:subject; use --", se.MESSAGE_TYPE_ERROR, "content.opf"))

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

		# Check for malformed URLs
		for message in self.__get_malformed_urls(metadata_xhtml):
			message.filename = "content.opf"
			messages.append(message)

		if regex.search(r"id\.loc\.gov/authorities/names/[^\.]+\.html", metadata_xhtml):
			messages.append(LintMessage("id.loc.gov URL ending with illegal .html", se.MESSAGE_TYPE_ERROR, "content.opf"))

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

				if filename == ".DS_Store" or filename == ".gitignore" or filename.startswith("README"):
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

						# Check for empty <h2> missing epub:type="title" attribute
						if "<h2>" in file_contents:
							messages.append(LintMessage("<h2> tag without epub:type=\"title\" attribute.", se.MESSAGE_TYPE_WARNING, filename))

						# Check for empty <p> tags
						if "<p/>" in file_contents or "<p></p>" in file_contents:
							messages.append(LintMessage("Empty <p/> tag.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for Roman numerals in <title> tag
						if regex.findall(r"<title>[Cc]hapter [XxIiVv]+", file_contents):
							messages.append(LintMessage("No Roman numerals allowed in <title> tag; use decimal numbers.", se.MESSAGE_TYPE_ERROR, filename))

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
								subtitle_matches = regex.findall(r"(.*?)<span epub:type=\"subtitle\">(.*?)</span>(.*?)", title, regex.DOTALL)
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

						# Check for non-typogrified img alt attributes
						matches = regex.findall(r"alt=\"[^\"]*?('|--|&quot;)[^\"]*?\"", file_contents)
						if matches:
							messages.append(LintMessage("Non-typogrified ', \" (as &quot;), or -- in image alt attribute.", se.MESSAGE_TYPE_ERROR, filename))

						# Check alt attributes not ending in punctuation
						if filename not in se.IGNORED_FILENAMES:
							matches = regex.findall(r"alt=\"[^\"]*?[a-zA-Z]\"", file_contents)
							if matches:
								messages.append(LintMessage("Alt attribute doesn't appear to end with puncutation. Alt attributes must be composed of complete sentences ending in appropriate punctuation.", se.MESSAGE_TYPE_ERROR, filename))

						# Check for nbsp in measurements, for example: 90 mm
						matches = regex.findall(r"[0-9]+[\- ][mck][mgl]", file_contents)
						if matches:
							messages.append(LintMessage("Measurements must be separated by a no-break space, not a dash or regular space.", se.MESSAGE_TYPE_ERROR, filename))
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
							matches = regex.findall(r"(?<!</blockquote>\s*<p>\s*)(?:[^\s]|\s{2,})<a href=\"[^[\"]+?\" epub:type=\"se:referrer\">↩</a>", file_contents)
							if matches:
								messages.append(LintMessage("Endnote referrer link not preceded by exactly one space, or a <p> tag if preceded by a <blockquote> tag.", se.MESSAGE_TYPE_WARNING, filename))
								for match in matches:
									messages.append(LintMessage(match[1:], se.MESSAGE_TYPE_WARNING, filename, True))

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
						messages.append(LintMessage("No frontmatter semantic inflection for what looks like a frontmatter file.", se.MESSAGE_TYPE_WARNING, filename))

					if filename in se.BACKMATTER_FILENAMES and "backmatter" not in file_contents:
						messages.append(LintMessage("No backmatter semantic inflection for what looks like a backmatter file.", se.MESSAGE_TYPE_WARNING, filename))

		for element in abbr_elements:
			try:
				css_class = regex.search(r"class=\"([^\"]+?)\"", element).group(1)
			except Exception:
				continue
			if css_class and (css_class == "name" or css_class == "temperature" or css_class == "era" or css_class == "compass" or css_class == "acronym") and "abbr." + css_class not in abbr_styles:
				messages.append(LintMessage("abbr.{} element found, but no style in local.css".format(css_class), se.MESSAGE_TYPE_ERROR, "local.css"))

		return messages
