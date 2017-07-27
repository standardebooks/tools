#!/usr/bin/env python3

import os
import filecmp
import glob
import regex
import se
import roman
import lxml.cssselect
import lxml.etree as etree


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
			messages.append("Non-https gutenberg.org URL.")

		if "http://www.pgdp.net" in xhtml:
			messages.append("Non-https pgdp.net URL.")

		if "http://catalog.hathitrust.org" in xhtml:
			messages.append("Non-https hathitrust.org URL.")

		if "http://archive.org" in xhtml:
			messages.append("Non-https archive.org URL.")

		if "www.archive.org" in xhtml:
			messages.append("archive.org URL should not have leading www.")

		if "http://en.wikipedia.org" in xhtml:
			messages.append("Non-https en.wikipedia.org URL.")

		# Check for malformed canonical URLs
		if regex.search(r"books\.google\.com/books\?id=.+?[&#]", xhtml):
			messages.append("Non-canonical Google Books URL.  Google Books URLs must look exactly like https://books.google.com/books?id=<BOOK-ID>")

		if "babel.hathitrust.org" in xhtml:
			messages.append("Non-canonical Hathi Trust URL.  Hathi Trust URLs must look exactly like https://catalog.hathitrust.org/Record/<BOOK-ID>")

		if ".gutenberg.org/files/" in xhtml:
			messages.append("Non-canonical Project Gutenberg URL.  Project Gutenberg URLs must look exactly like https://www.gutenberg.org/ebooks/<BOOK-ID>")

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

					tree = etree.fromstring(str.encode(xhtml))
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
			messages.append("Non-typogrified \", ', or -- detected in metadata long description")

		# Check for double spacing
		regex_string = r"[{}{} ]{{2,}}".format(se.NO_BREAK_SPACE, se.HAIR_SPACE)
		matches = regex.findall(regex_string, metadata_xhtml)
		if matches:
			messages.append("Double spacing detected in file. Sentences should be single-spaced. File: content.opf")

		if regex.search(r"<dc:description id=\"description\">[^<]+?(['\"]|\-\-)[^<]+?</meta>", metadata_xhtml) is not None:
			messages.append("Non-typogrified \", ', or -- detected in metadata dc:description")

		#Check for HTML entities in long-description
		if regex.search(r"&amp;[a-z]+?;", metadata_xhtml):
			messages.append("HTML entites detected in metadata.  Use Unicode equivalents instead")

		# Check for illegal em-dashes in <dc:subject>
		if regex.search(r"<dc:subject id=\"[^\"]+?\">[^<]+?—[^<]+?</meta>", metadata_xhtml) is not None:
			messages.append("Illegal em-dash detected in dc:subject; use --")

		# Check for illegal se:subject tags
		matches = regex.findall(r"<meta property=\"se:subject\">([^<]+?)</meta>", metadata_xhtml)
		if matches:
			for match in matches:
				if match not in se.SE_GENRES:
					messages.append("Illegal se:subject in content.opf: {}".format(match))
		else:
			messages.append("No se:subject <meta> tag found. File: content.opf")

		for message in self.__get_malformed_urls(metadata_xhtml):
			messages.append("{} File: content.opf".format(message))

		if regex.search(r"id\.loc\.gov/authorities/names/[^\.]+\.html", metadata_xhtml):
			messages.append("id.loc.gov URL ending with .html in content.opf; remove ending .html")

		# Make sure some static files are unchanged
		try:
			if not filecmp.cmp(license_file_path, os.path.join(self.directory, "LICENSE.md")):
				messages.append("LICENSE.md does not match {}".format(license_file_path))
		except Exception:
			messages.append("Missing ./LICENSE.md")

		if not filecmp.cmp(core_css_file_path, os.path.join(self.directory, "src", "epub", "css", "core.css")):
			messages.append("core.css does not match {}".format(core_css_file_path))

		if not filecmp.cmp(logo_svg_file_path, os.path.join(self.directory, "src", "epub", "images", "logo.svg")):
			messages.append("logo.svg does not match {}".format(logo_svg_file_path))

		if not filecmp.cmp(uncopyright_file_path, os.path.join(self.directory, "src", "epub", "text", "uncopyright.xhtml")):
			messages.append("uncopyright.xhtml does not match {}".format(uncopyright_file_path))

		# Check for unused selectors
		unused_selectors = self.__get_unused_selectors()
		if unused_selectors:
			messages.append("Unused CSS selectors in local.css:")
			for selector in unused_selectors:
				messages.append(" {}".format(selector))

		# Now iterate over individual files for some checks
		for root, _, filenames in os.walk(self.directory):
			for filename in filenames:
				if ".git/" in os.path.join(root, filename) or filename.endswith(tuple(se.BINARY_EXTENSIONS)):
					continue

				if filename == ".DS_Store" or filename == ".gitignore" or filename.startswith("README"):
					messages.append("Illegal {} file detected in {}".format(filename, root))

				with open(os.path.join(root, filename), "r", encoding="utf-8") as file:
					try:
						file_contents = file.read()
					except UnicodeDecodeError:
						# This is more to help developers find weird files that might choke 'lint', hopefully unnecessary for end users
						messages.append("Problem decoding file as utf-8: {}".format(filename))
						continue

					if "UTF-8" in file_contents:
						messages.append("String \"UTF-8\" must always be lowercase. File: {}".format(filename))

					if filename.endswith(".css"):
						# Check CSS style

						# No space before CSS opening braces
						matches = regex.findall(r".+\s\{", file_contents)
						if matches:
							messages.append("CSS opening braces must not be preceded by space. File: {}".format(filename))
							for match in matches:
								messages.append(" {}".format(match))

						# CSS closing braces on their own line
						matches = regex.findall(r"^\s*[^\s+]\s*.+\}", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append("CSS closing braces must be on their own line. File: {}".format(filename))
							for match in matches:
								messages.append(" {}".format(match))

						# White space before CSS closing braces
						matches = regex.findall(r"^\s+\}", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append("No white space before CSS closing braces. File: {}".format(filename))
							for match in matches:
								messages.append(" {}".format(match))

						# Properties not indented with tabs
						matches = regex.findall(r"^[^\t@/].+:[^\{,]+?;$", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append("CSS properties must be indented with exactly one tab. File: {}".format(filename))
							for match in matches:
								messages.append(" {}".format(match))

						# Properties indented with multiple tabs
						matches = regex.findall(r"^\t{2,}.+:[^\{,]+?;$", file_contents, flags=regex.MULTILINE)
						if matches:
							messages.append("CSS properties must be indented with exactly one tab. File: {}".format(filename))
							for match in matches:
								messages.append(" {}".format(match))

					if filename.endswith(".xhtml"):
						for message in self.__get_malformed_urls(file_contents):
							messages.append("{} File: {}".format(message, filename))

						# Check for empty <h2> missing epub:type="title" attribute
						if "<h2>" in file_contents:
							messages.append("<h2> tag without epub:type=\"title\" attribute in {}".format(filename))

						# Check for empty <p> tags
						if "<p/>" in file_contents or "<p></p>" in file_contents:
							messages.append("Empty <p/> tag in {}".format(filename))

						# Check for Roman numerals in <title> tag
						if regex.findall(r"<title>[Cc]hapter [XxIiVv]+", file_contents):
							messages.append("No Roman numerals allowed in <title> tag; use decimal numbers. File: {}".format(filename))

						# If the chapter has a number and subtitle, check the <title> tag
						matches = regex.findall(r"<h([0-6]) epub:type=\"title\">\s*<span epub:type=\"z3998:roman\">([^<]+)</span>\s*<span epub:type=\"subtitle\">(.+?)</span>\s*</h\1>", file_contents, flags=regex.DOTALL)

						# But only make the correction if there's one <h#> tag.  If there's more than one, then the xhtml file probably requires an overarching title
						if len(matches) == 1:
							chapter_number = roman.fromRoman(matches[0][1].upper())

							# First, remove endnotes in the subtitle, then remove all other tags (but not tag contents)
							chapter_title = regex.sub(r"<a[^<]+?epub:type=\"noteref\"[^<]*?>[^<]+?</a>", "", matches[0][2]).strip()
							chapter_title = regex.sub(r"<[^<]+?>", "", chapter_title)

							regex_string = r"<title>(Chapter|Section|Part) {}: {}".format(chapter_number, regex.escape(chapter_title))
							if not regex.findall(regex_string, file_contents):
								messages.append("<title> tag doesn't match expected value; should be \"Chapter {}: {}\". (Beware hidden Unicode characters!) File: {}".format(chapter_number, chapter_title, filename))

						# Check for missing subtitle styling
						if "epub:type=\"subtitle\"" in file_contents and not local_css_has_subtitle_style:
							messages.append("Subtitles detected, but no subtitle style detected in local.css. File: {}".format(filename))

						# Check for <figure> tags without id attributes
						if "<figure>" in file_contents:
							messages.append("<figure> tag without ID attribute; <figure> tags should have the ID attribute, not their children <img> tags. File: {}".format(filename))

						# Check for non-typogrified img alt attributes
						matches = regex.findall(r"alt=\"[^\"]*?('|--|&quot;)[^\"]*?\"", file_contents)
						if matches:
							messages.append("Non-typogrified ', \" (as &quot;), or -- in image alt attribute. File: {}".format(filename))

						# Check alt attributes not ending in punctuation
						if filename not in se.IGNORED_FILENAMES:
							matches = regex.findall(r"alt=\"[^\"]*?[a-zA-Z]\"", file_contents)
							if matches:
								messages.append("Alt attribute doesn't appear to end with puncutation. Alt attributes must be composed of complete sentences ending in appropriate punctuation. File: {}".format(filename))

						# Check for nbsp in measurements, for example: 90 mm
						matches = regex.findall(r"[0-9]+[\- ][mck][mgl]", file_contents)
						if matches:
							messages.append("Measurements must be separated by a no-break space, not a dash or regular space.")
							for match in matches:
								messages.append(" {}".format(match))

						# Check for <pre> tags
						if "<pre" in file_contents:
							messages.append("Illegal <pre> tag. File: {}".format(filename))

						# Check for double spacing
						regex_string = r"[{}{} ]{{2,}}".format(se.NO_BREAK_SPACE, se.HAIR_SPACE)
						matches = regex.findall(regex_string, file_contents)
						if matches:
							messages.append("Double spacing detected in file. Sentences should be single-spaced. File: {}".format(filename))

						# Check for punctuation outside quotes. We don't check single quotes because contractions are too common.
						matches = regex.findall(r"[a-zA-Z][”][,.]", file_contents)
						if matches:
							messages.append("Comma or period outside of double quote. Generally punctuation should go within single and double quotes. (Note that double spaces might be with no-break spaces!) File: {}".format(filename))

						# Did someone use colons instead of dots for SE identifiers? e.g. se:name:vessel:ship
						matches = regex.findall(r"\bse:[a-z]+:(?:[a-z]+:?)*", file_contents)
						if matches:
							messages.append("Illegal colon (:) detected in SE identifier.  SE identifiers are separated by dots (.) not colons (:). Identifier: {} File: {}".format(matches, filename))

						# Check for space before endnote backlinks
						if filename == "endnotes.xhtml":
							matches = regex.findall(r"(?<!</blockquote>\s*<p>\s*)(?:[^\s]|\s{2,})<a href=\"[^[\"]+?\" epub:type=\"se:referrer\">↩</a>", file_contents)
							if matches:
								messages.append("Endnote referrer link in endnotes.xhtml not preceded by exactly one space, or a <p> tag if preceded by a <blockquote> tag.")
								for match in matches:
									messages.append(" {}".format(match[1:]))

						# If we're in the imprint, are the sources represented correctly?
						if filename == "imprint.xhtml":
							for match in regex.finditer(r"<dc:source>([^<]+?)</dc:source>", metadata_xhtml):
								link = match.group(1)

								if "gutenberg.org" in link and "<a href=\"{}\">Project Gutenberg</a>".format(link) not in file_contents:
									messages.append("Source not represented in imprint.xhtml. It should read: <a href=\"{}\">Project Gutenberg</a>".format(link))

								if "hathitrust.org" in link and "the <a href=\"{}\">Hathi Trust Digital Library</a>".format(link) not in file_contents:
									messages.append("Source not represented in imprint.xhtml. It should read: the <a href=\"{}\">Hathi Trust Digital Library</a>".format(link))

								if "archive.org" in link and "the <a href=\"{}\">Internet Archive</a>".format(link) not in file_contents:
									messages.append("Source not represented in imprint.xhtml. It should read: the <a href=\"{}\">Internet Archive</a>".format(link))

								if "books.google.com" in link and "<a href=\"{}\">Google Books</a>".format(link) not in file_contents:
									messages.append("Source not represented in imprint.xhtml. It should read: <a href=\"{}\">Google Books</a>".format(link))

						# Collect abbr elements for later check
						result = regex.findall("<abbr[^<]+?>", file_contents)
						result = [item.replace("eoc", "").replace(" \"", "").strip() for item in result]
						abbr_elements = list(set(result + abbr_elements))

						# Check if language tags in individual files match the language in content.opf
						if filename not in se.IGNORED_FILENAMES:
							file_language = regex.search(r"<html[^<]+xml\:lang=\"([^\"]+)\"", file_contents).group(1)
							if language != file_language:
								messages.append("{} language is {}, but content.opf language is {}".format(filename, file_language, language))

					# Check for missing MARC relators
					if filename == "introduction.xhtml" and ">aui<" not in metadata_xhtml and ">win<" not in metadata_xhtml:
						messages.append("introduction.xhtml found, but no MARC relator 'aui' (Author of introduction, but not the chief author) or 'win' (Writer of introduction)")

					if filename == "preface.xhtml" and ">wpr<" not in metadata_xhtml:
						messages.append("preface.xhtml found, but no MARC relator 'wpr' (Writer of preface)")

					if filename == "afterword.xhtml" and ">aft<" not in metadata_xhtml:
						messages.append("afterword.xhtml found, but no MARC relator 'aft' (Author of colophon, afterword, etc.)")

					if filename == "endnotes.xhtml" and ">ann<" not in metadata_xhtml:
						messages.append("endnotes.xhtml found, but no MARC relator 'ann' (Annotator)")

					if filename == "loi.xhtml" and ">ill<" not in metadata_xhtml:
						messages.append("loi.xhtml found, but no MARC relator 'ill' (Illustrator)")

					# Check for wrong semantics in frontmatter/backmatter
					if filename in se.FRONTMATTER_FILENAMES and "frontmatter" not in file_contents:
						messages.append("No frontmatter semantic inflection in what looks like a frontmatter file. File: {}".format(filename))

					if filename in se.BACKMATTER_FILENAMES and "backmatter" not in file_contents:
						messages.append("No backmatter semantic inflection in what looks like a backmatter file. File: {}".format(filename))

		for element in abbr_elements:
			try:
				css_class = regex.search(r"class=\"([^\"]+?)\"", element).group(1)
			except Exception:
				continue
			if css_class and (css_class == "name" or css_class == "temperature" or css_class == "era") and "abbr." + css_class not in abbr_styles:
				messages.append("abbr.{} element found, but no style in local.css".format(css_class))

		return messages
