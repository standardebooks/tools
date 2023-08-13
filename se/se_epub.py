#!/usr/bin/env python3
"""
Defines the SeEpub class, the master class for representing and operating on
Standard Ebooks epub3 files.
"""

import base64
import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import git
from lxml import etree
from natsort import natsorted
import regex

import se
import se.easy_xml
import se.formatting
import se.images


class GitCommit:
	"""
	Object used to represent the last Git commit.
	"""

	short_sha = ""
	timestamp = None

	def __init__(self, short_sha: str, timestamp: datetime.datetime):
		self.short_sha = short_sha
		self.timestamp = timestamp

class Endnote:
	"""
	Class to hold information on endnotes
	"""

	def __init__(self):
		self.node = None
		self.number = 0
		self.anchor = ""
		self.contents = []  # The strings and tags inside an <li> element
		self.back_link = ""
		self.source_file = ""
		self.matched = False

class EndnoteChange:
	"""
	Class to hold a record of what changes have been made to endnote numbers
	"""

	def __init__(self, old_anchor, new_anchor, filename):
		self.old_anchor = old_anchor  # the previous anchor
		self.new_anchor = new_anchor  # the anchor it has been changed to
		self.filename = filename	# the file in which it was changed

class SeEpub:
	"""
	An object representing an SE epub file.

	An SE epub can have various operations performed on it, including recomposing and linting.
	"""

	path: Path = Path() # The path to the base of the ebook repo, i.e., a folder containing ./images/ and ./src/
	epub_root_path = Path() # The path to the epub source root, i.e. self.path / src
	content_path: Path = Path() # The path to the epub content base, i.e. self.epub_root_path / epub
	metadata_file_path: Path = Path() # The path to the metadata file, i.e. self.content_path / content.opf
	toc_path: Path = Path()  # The path to the metadata file, i.e. self.content_path / toc.xhtml
	glossary_search_key_map_path = None # The path to the glossary search key map, or None
	local_css = ""
	is_se_ebook = True
	_file_cache: Dict[str, str] = {}
	_dom_cache: Dict[str, se.easy_xml.EasyXmlTree] = {}
	_generated_identifier = None
	_generated_github_repo_url = None
	_repo = None # git.Repo object
	_last_commit = None # GitCommit object
	_endnotes: Optional[List[Endnote]] = None # List of Endnote objects
	_endnotes_path = None
	_loi_path = None
	_cover_path = None
	_spine_file_paths: Optional[List[Path]] = None # List of Path objects

	def __init__(self, epub_root_directory: Union[str, Path]):
		try:
			self.path = Path(epub_root_directory).resolve()

			if not self.path.is_dir():
				raise NotADirectoryError

		except Exception as ex:
			raise se.InvalidSeEbookException(f"Not a directory: [path][link=file://{self.path}]{self.path}[/][/].") from ex

		# Decide if this is an SE epub, or a white-label epub
		# SE epubs have a ./src dir and the identifier looks like an SE identifier
		if (self.path / "src" / "META-INF" / "container.xml").is_file():
			self.epub_root_path = self.path / "src"
		else:
			self.epub_root_path = self.path
			self.is_se_ebook = False

		try:
			container_tree = self.get_dom(self.epub_root_path / "META-INF" / "container.xml")

			self.metadata_file_path = self.epub_root_path / container_tree.xpath("/container/rootfiles/rootfile[@media-type=\"application/oebps-package+xml\"]/@full-path")[0]
		except Exception as ex:
			raise se.InvalidSeEbookException("Target doesn’t appear to be an epub: no [path]container.xml[/] or no metadata file.") from ex

		self.content_path = self.metadata_file_path.parent

		try:
			self.metadata_dom = self.get_dom(self.metadata_file_path)
		except Exception as ex:
			raise se.InvalidXmlException(f"Couldn’t parse [path][link=file://{self.metadata_file_path}]{self.metadata_file_path}[/][/]. Exception: {ex}") from ex

		toc_href = self.metadata_dom.xpath("/package/manifest/item[contains(@properties, 'nav')]/@href", True)
		if toc_href:
			self.toc_path = self.content_path / toc_href
		else:
			raise se.InvalidSeEbookException("Couldn’t find table of contents.")

		gskm_href = self.metadata_dom.xpath("/package/manifest/item[contains(@properties, 'search-key-map')]/@href", True)
		if gskm_href:
			self.glossary_search_key_map_path = self.content_path / gskm_href

		# If our identifier isn't SE-style, we're not an SE ebook
		identifier = self.metadata_dom.xpath("/package/metadata/dc:identifier/text()", True)
		if not identifier or not identifier.startswith("url:https://standardebooks.org/ebooks/"):
			self.is_se_ebook = False

	@property
	def cover_path(self):
		"""
		Accessor
		"""

		if not self._cover_path:
			for file_href in self.metadata_dom.xpath("/package/manifest/item[contains(@properties, 'cover-image')]/@href"):
				self._cover_path = self.content_path / file_href

		return self._cover_path

	@property
	def endnotes_path(self):
		"""
		Accessor
		"""

		if not self._endnotes_path:
			for file_path in self.content_path.glob("**/*.xhtml"):
				dom = self.get_dom(file_path)
				if dom.xpath("/html/body/section[contains(@epub:type, 'endnotes')]"):
					self._endnotes_path = file_path
					break

		return self._endnotes_path

	@property
	def loi_path(self):
		"""
		Accessor
		"""

		if not self._loi_path:
			for file_path in self.content_path.glob("**/*.xhtml"):
				dom = self.get_dom(file_path)
				if dom.xpath("/html/body/nav[contains(@epub:type, 'loi')]"):
					self._loi_path = file_path
					break

		return self._loi_path

	@property
	def repo(self) -> git.Repo:
		"""
		Accessor
		"""

		if not self._repo:
			try:
				self._repo = git.Repo(self.path)
			except Exception as ex:
				raise se.InvalidSeEbookException("Couldn’t access this ebook’s Git repository.") from ex

		return self._repo

	@property
	def last_commit(self) -> Optional[GitCommit]:
		"""
		Accessor
		"""

		if not self._last_commit:
			# We use git command instead of using gitpython's commit object because we want the short hash
			try:
				# We have to clear this environmental variable or else GitPython will think the repo is "." instead
				# of the dir we actually pass, if we're called from a git hook (like post-receive).
				# See https://stackoverflow.com/questions/42328426/gitpython-not-working-from-git-hook
				if "GIT_DIR" in os.environ:
					del os.environ["GIT_DIR"]

				git_command = git.cmd.Git(self.path)
				output = git_command.show("-s", "--format=%h %ct", "HEAD").split()

				self._last_commit = GitCommit(output[0], datetime.datetime.fromtimestamp(int(output[1]), datetime.timezone.utc))
			except Exception:
				self._last_commit = None

		return self._last_commit

	@property
	def generated_identifier(self) -> str:
		"""
		Accessor

		Generate an SE identifer based on the metadata in the metadata file.
		"""

		if not self._generated_identifier:
			identifier = "url:https://standardebooks.org/ebooks/"

			if not self.is_se_ebook:
				identifier = ""
				for publisher in self.metadata_dom.xpath("/package/metadata/dc:publisher"):
					identifier += se.formatting.make_url_safe(publisher.text) + "_"

			# Add authors
			authors = []
			for author in self.metadata_dom.xpath("/package/metadata/dc:creator"):
				authors.append(author.text)
				identifier += se.formatting.make_url_safe(author.text) + "_"

			identifier = identifier.strip("_") + "/"

			# Add title
			for title in self.metadata_dom.xpath("/package/metadata/dc:title[@id=\"title\"]"):
				identifier += se.formatting.make_url_safe(title.text) + "/"

			# For contributors, we add both translators and illustrators.
			# However, we may not include specific translators or illustrators in certain cases, namely
			# if *some* contributors have a `display-seq` property, and others do not.
			# According to the epub spec, if that is the case, we should only add those that *do* have the attribute.
			# By SE convention, any contributor with `display-seq == 0` will be excluded from the identifier string.
			translators = []
			illustrators = []
			translators_have_display_seq = False
			illustrators_have_display_seq = False
			for role in self.metadata_dom.xpath("/package/metadata/meta[@property='role']"):
				contributor_id = role.get_attr("refines").lstrip("#")
				contributor_element = self.metadata_dom.xpath("/package/metadata/dc:contributor[@id=\"" + contributor_id + "\"]")
				if contributor_element:
					contributor = {"name": contributor_element[0].text, "include": True, "display_seq": None}
					display_seq = self.metadata_dom.xpath("/package/metadata/meta[@property=\"display-seq\"][@refines=\"#" + contributor_id + "\"]")

					if display_seq and int(display_seq[0].text) == 0:
						contributor["include"] = False
						display_seq = []

					if role.text == "trl":
						if display_seq:
							contributor["display_seq"] = display_seq[0]
							translators_have_display_seq = True

						translators.append(contributor)

					if role.text == "ill":
						if display_seq:
							contributor["display_seq"] = display_seq[0]
							illustrators_have_display_seq = True

						illustrators.append(contributor)

			for translator in translators:
				if (not translators_have_display_seq and translator["include"]) or translator["display_seq"]:
					identifier += se.formatting.make_url_safe(translator["name"]) + "_"

			if translators:
				identifier = identifier.strip("_") + "/"

			for illustrator in illustrators:
				include_illustrator = True

				# If the translator is also the illustrator, don't include them twice
				for translator in translators:
					if illustrator["name"] == translator["name"]:
						include_illustrator = False
						break

				if (include_illustrator and not illustrators_have_display_seq and illustrator["include"]) or illustrator["display_seq"]:
					identifier += se.formatting.make_url_safe(illustrator["name"]) + "_"

			identifier = identifier.strip("_/")

			self._generated_identifier = identifier

		return self._generated_identifier

	@property
	def generated_github_repo_url(self) -> str:
		"""
		Accessor

		Generate a GitHub repository URL based on the *generated* SE identifier,
		*not* the SE identifier in the metadata file.

		INPUTS
		None

		OUTPUTS
		A string representing the GitHub repository URL (capped at maximum 100 characters).
		"""

		if not self._generated_github_repo_url:
			self._generated_github_repo_url = "https://github.com/standardebooks/" + self.generated_identifier.replace("url:https://standardebooks.org/ebooks/", "").replace("/", "_")[0:100]

		return self._generated_github_repo_url

	@property
	def endnotes(self) -> list:
		"""
		Accessor

		Return a list of Endnote objects representing the endnotes file for this ebook.

		INPUTS
		None

		OUTPUTS
		A list of Endnote objects representing the endnotes file for this ebook.
		"""

		if not self._endnotes:
			self._endnotes = []

			dom = self.get_dom(self.endnotes_path)

			for node in dom.xpath("/html/body/section[contains(@epub:type, 'endnotes')]/ol/li[contains(@epub:type, 'endnote')]"):
				note = Endnote()
				note.node = node
				try:
					note.number = int(node.get_attr("id").replace("note-", ""))
				except ValueError:
					note.number = 0
				note.contents = node.xpath("./*")
				note.anchor = node.get_attr("id") or ""

				for back_link in node.xpath(".//a[contains(@epub:type, 'backlink')]/@href"):
					note.back_link = back_link
				if not note.back_link:
					raise se.InvalidInputException(f"No backlink found in note {note.anchor} in existing endnotes file.")
				self._endnotes.append(note)
		return self._endnotes

	@property
	def spine_file_paths(self) -> List[Path]:
		"""
		Reads the spine from the metadata file to obtain a list of content files, in the order wanted for the ToC.
		It assumes this has already been manually ordered by the producer.

		INPUTS:
		None

		OUTPUTS:
		list of content files paths in the order given in the spine in the metadata file
		"""

		if not self._spine_file_paths:

			self._spine_file_paths = []

			for idref in self.metadata_dom.xpath("/package/spine/itemref/@idref"):
				try:
					self._spine_file_paths.append(self.content_path / self.metadata_dom.xpath(f"/package/manifest/item[@id='{idref}']/@href", True))
				except Exception as ex:
					raise se.InvalidSeEbookException(f"Couldn’t find spine item: {idref}") from ex

		return self._spine_file_paths

	def get_file(self, file_path: Path) -> str:
		"""
		Get raw file contents of a file in the epub.
		Contents are cached so that we don't hit the disk repeatedly

		INPUTS
		file_path: A Path pointing to the file

		OUTPUTS
		A string representing the file contents
		"""

		file_path_str = str(file_path)

		if file_path_str not in self._file_cache:
			try:
				with open(file_path, "r", encoding="utf-8") as file:
					file_contents = file.read()
			except Exception as ex:
				raise se.InvalidFileException(f"Couldn’t read file: [path]{file_path_str}[/]") from ex

			self._file_cache[file_path_str] = file_contents

		return self._file_cache[file_path_str]

	def flush_dom_cache_entry(self, file_path: Path) -> None:
		"""
		Remove a dom cache entry for the given file, regardless of whether comments were removed.

		INPUTS
		file_path: A Path pointing to the file
		"""

		keys_to_delete = []

		for key in self._dom_cache:
			if key.startswith(str(file_path)):
				keys_to_delete.append(key)

		for key in keys_to_delete:
			del self._dom_cache[key]

		try:
			del self._file_cache[str(file_path)]
		except Exception:
			pass

	# Cache dom objects so we don't have to create them multiple times
	def get_dom(self, file_path: Path, remove_comments=False) -> se.easy_xml.EasyXmlTree:
		"""
		Get an EasyXmlTree DOM object for a given file.
		Contents are cached so that we don't hit the disk or re-parse DOMs repeatedly

		INPUTS
		file_path: A Path pointing to the file

		OUTPUTS
		A string representing the file contents
		"""
		file_path_str = str(file_path) + "_" + str(remove_comments)

		if file_path_str not in self._dom_cache:
			file_contents = self.get_file(file_path)

			try:
				self._dom_cache[file_path_str] = se.easy_xml.EasyXmlTree(file_contents)

				# Remove comments
				if remove_comments:
					for node in self._dom_cache[file_path_str].xpath("//comment()"):
						node.remove()

			except etree.XMLSyntaxError as ex:
				raise se.InvalidXhtmlException(f"Couldn’t parse XML in [path][link=file://{file_path.resolve()}]{file_path}[/][/]. Exception: {ex}") from ex
			except FileNotFoundError as ex:
				raise ex
			except se.InvalidXmlException as ex:
				raise se.InvalidXhtmlException(f"Couldn’t parse XML in [path][link=file://{file_path.resolve()}]{file_path}[/][/]. Exception: {ex.__cause__}") from ex
			except Exception as ex:
				raise se.InvalidXhtmlException(f"Couldn’t parse XML in [path][link=file://{file_path.resolve()}]{file_path}[/][/].") from ex

		return self._dom_cache[file_path_str]

	def _recompose_xhtml(self, section: se.easy_xml.EasyXmlElement, output_dom: se.easy_xml.EasyXmlTree) -> None:
		"""
		Helper function used in self.recompose()

		INPUTS
		section: An EasyXmlElement to inspect
		output_dom: A EasyXmlTree representing the entire output dom

		OUTPUTS
		None
		"""

		# Quick sanity check before we begin
		if not section.get_attr("id") or (section.parent.tag.lower() != "body" and not section.parent.get_attr("id")):
			raise se.InvalidXhtmlException(f"Section without [attr]id[/] attribute: [html]{section.to_tag_string()}[/]")

		if section.parent.tag.lower() == "body" and not section.get_attr("data-parent"):
			section.set_attr("epub:type", f"{section.get_attr('epub:type')} {section.parent.get_attr('epub:type')}".strip())

		# Try to find our parent element in the current output dom, by ID.
		# If it's not in the output, then append this element to the elements's closest parent by ID (or <body>), then iterate over its children and do the same.
		existing_section = None
		existing_section = output_dom.xpath(f"//*[@id='{section.get_attr('data-parent')}']")

		if existing_section:
			existing_section[0].append(section)
		else:
			output_dom.xpath("/html/body")[0].append(section)

		# Convert all <img> references to inline base64
		# We even convert SVGs instead of inlining them, because CSS won't allow us to style inlined SVGs
		# (for example if we want to apply max-width or filter: invert())
		for img in section.xpath("//img[starts-with(@src, '../images/')]"):
			img.set_attr("src", se.images.get_data_url(self.content_path / img.get_attr("src").replace("../", "")))

	def recompose(self, output_xhtml5: bool, extra_css_file: Union[Path,None] = None) -> str:
		"""
		Iterate over the XHTML files in this epub and "recompose" them into a single XHTML string representing this ebook.

		INPUTS
		output_xhtml5: true to output XHTML5 instead of HTML5

		OUTPUTS
		A string of HTML5 representing the entire recomposed ebook.
		"""

		# Get some header data: title, core and local css
		title = self.metadata_dom.xpath("/package/metadata/dc:title/text()")[0]
		language = self.metadata_dom.xpath("/package/metadata/dc:language/text()")[0]
		css = ""
		namespaces: List[str] = []

		css_filenames = list(self.content_path.glob("**/*.css"))

		# If we have standard SE CSS files, attempt to sort them in the order we expect them to appear in the ebook.
		# core.css -> se.css -> local.css
		sorted_css_filenames = {}
		for filepath in css_filenames:
			if filepath.name == "core.css":
				sorted_css_filenames[0] = filepath
			if filepath.name == "se.css":
				sorted_css_filenames[1] = filepath
			if filepath.name == "local.css":
				sorted_css_filenames[2] = filepath

		# Turn the dict into a list, sorting by key
		sorted_css_filenames_list = [sorted_css_filenames[key] for key in sorted(sorted_css_filenames.keys())]

		# If we hit all 3 files then we're probably an SE ebook, replace our list of CSS files with the sorted list
		if len(sorted_css_filenames_list) == 3:
			css_filenames = sorted_css_filenames_list

		# Add the extra CSS file if present
		if extra_css_file:
			css_filenames.append(extra_css_file)

		# Now recompose the CSS
		for filepath in css_filenames:
			file_css = self.get_file(filepath)

			namespaces = namespaces + regex.findall(r"@namespace.+?;", file_css)

			file_css = regex.sub(r"\s*@(charset|namespace).+?;\s*", "\n", file_css).strip()

			# Convert background-image URLs to base64
			for image in regex.finditer(pattern=r"""url\("(.+?\.(?:svg|png|jpg))"\)""", string=file_css):
				url = image.captures(1)[0].replace("../", "")
				url = regex.sub(r"^/", "", url)
				try:
					data_url = se.images.get_data_url(self.content_path / url)
					file_css = file_css.replace(image.group(0), f"""url("{data_url}")""")
				except FileNotFoundError:
					# If the file isn't found, continue silently.
					# File may not be found for example in web.css, which points to an image on the web
					# server, not in the ebook.
					pass

			css = css + f"\n\n\n/* {filepath.name} */\n" + file_css

		css = css.strip()

		namespaces = sorted(list(set(namespaces)), reverse=True)

		if namespaces:
			css = "\n" + css

			for namespace in namespaces:
				css = namespace + "\n" + css

		css = "\t\t\t".join(css.splitlines(True)) + "\n"

		# Remove min-height from CSS since it doesn't really apply to the single page format.
		# It occurs at least in se.css
		css = regex.sub(r"\s*min-height: [^;]+?;", "", css)

		# Remove -epub-* CSS as it's invalid in a browser context
		css = regex.sub(r"\s*\-epub\-[^;]+?;", "", css)

		output_xhtml = f"<?xml version=\"1.0\" encoding=\"utf-8\"?><html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\" epub:prefix=\"z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0\" xml:lang=\"{language}\"><head><meta charset=\"utf-8\"/><title>{title}</title><style/></head><body></body></html>"
		output_dom = se.formatting.EasyXmlTree(output_xhtml)
		output_dom.is_css_applied = True # We will apply CSS recursively to nodes that will be attached to output_dom, so set the bit here

		# Iterate over spine items in order and recompose them into our output
		needs_wrapper_css = False
		for file_path in self.spine_file_paths:
			dom = self.get_dom(file_path)

			# Apply the stylesheet to see if we have `position: absolute` on any items. If so, apply `position: relative` to its closest <section> ancestor
			# See https://standardebooks.org/ebooks/jean-toomer/cane for an example of this in action
			dom.apply_css(css)

			# Select deepest sections or articles with id attributes that have ONLY figure or img children, and one of those children has position: absolute
			for node in dom.xpath("/html/body//*[@id and (name() = 'section' or name = 'article') and not(.//*[(name() = 'section' or name() = 'article') and not(preceding-sibling::* or following-sibling::*)]) and count(./*[(name() = 'figure' or name() = 'img')]) = count(./*) and .//*[(name() = 'figure' or name() = 'img') and @data-css-position = 'absolute']]"):
				needs_wrapper_css = True

				# Wrap the sections in a div that we style later
				wrapper_element = etree.SubElement(node.lxml_element, "div")
				wrapper_element.set("class", "positioning-wrapper")
				for child in node.xpath("./*[(name() = 'figure' or name() = 'img')]"):
					wrapper_element.append(child.lxml_element) # .append() will *move* the element to the end of wrapper_element

			# Now, recompose the children
			for node in dom.xpath("/html/body/*"):
				try:
					self._recompose_xhtml(node, output_dom)
				except se.SeException as ex:
					raise se.SeException(f"[path][link=file://{file_path}]{file_path}[/][/]: {ex}") from ex

		# Remove data-parent attributes
		for node in output_dom.xpath("//*[@data-parent]"):
			node.remove_attr("data-parent")

		# Did we add wrappers? If so add the CSS
		# We also have to give the wrapper a height, because it may have siblings that were recomposed in from other files
		if needs_wrapper_css:
			css = css + "\n\t\t\t.positioning-wrapper{\n\t\t\t\tposition: relative; height: 100vh;\n\t\t\t}\n"

		# Add the ToC after the titlepage
		toc_dom = self.get_dom(self.toc_path)
		titlepage_node = output_dom.xpath("//*[contains(concat(' ', @epub:type, ' '), ' titlepage ')]")[0]

		for node in toc_dom.xpath("//nav[1]"):
			titlepage_node.lxml_element.addnext(node.lxml_element)

		# Replace all <a href> links with internal links
		for link in output_dom.xpath("//a[not(re:test(@href, '^https?://')) and contains(@href, '#')]"):
			link.set_attr("href", regex.sub(r".+(#.+)$", r"\1", link.get_attr("href")))

		# Replace all <a href> links to entire files
		for link in output_dom.xpath("//a[not(re:test(@href, '^https?://')) and not(contains(@href, '#'))]"):
			href = link.get_attr("href")
			href = regex.sub(r".+/([^/]+)$", r"#\1", href)
			href = regex.sub(r"\.xhtml$", "", href)
			link.set_attr("href", href)

		for node in output_dom.xpath("/html/body//a[re:test(@href, '^(\\.\\./)?text/(.+?)\\.xhtml$')]"):
			node.set_attr("href", regex.sub(r"(\.\./)?text/(.+?)\.xhtml", r"#\2", node.get_attr("href")))

		for node in output_dom.xpath("/html/body//a[re:test(@href, '^(\\.\\./)?text/.+?\\.xhtml#(.+?)$')]"):
			node.set_attr("href", regex.sub(r"(\.\./)?text/.+?\.xhtml#(.+?)", r"#\2", node.get_attr("href")))

		# Make some compatibility adjustments
		if output_xhtml5:
			for node in output_dom.xpath("/html/head/meta[@charset]"):
				node.remove()

			for node in output_dom.xpath("//*[@xml:lang]"):
				node.set_attr("lang", node.get_attr("xml:lang"))
		else:
			for node in output_dom.xpath("/html[@epub:prefix]"):
				node.remove_attr("epub:prefix")

			for node in output_dom.xpath("//*[@xml:lang]"):
				node.set_attr("lang", node.get_attr("xml:lang"))
				node.remove_attr("xml:lang")

			for node in output_dom.xpath("//*[@epub:type]"):
				node.set_attr("data-epub-type", node.get_attr("epub:type"))
				node.remove_attr("epub:type")

		# Get the output XHTML as a string
		output_xhtml = output_dom.to_string()

		# All done, clean the output
		output_xhtml = se.formatting.format_xhtml(output_xhtml)

		# Insert our CSS. We do this after `clean` because `clean` will escape > in the CSS
		output_xhtml = regex.sub(r"<style/>", "<style><![CDATA[\n\t\t\t" + css + "\t\t]]></style>", output_xhtml)

		if output_xhtml5:
			output_xhtml = output_xhtml.replace("\t\t<style/>\n", "")

			# Re-add a doctype
			output_xhtml = output_xhtml.replace("<?xml version=\"1.0\" encoding=\"utf-8\"?>", "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<!DOCTYPE html>")
		else:
			# Remove xml declaration and re-add the doctype
			output_xhtml = regex.sub(r"<\?xml.+?\?>", "<!doctype html>", output_xhtml)

			# Remove CDATA
			output_xhtml = output_xhtml.replace("<![CDATA[", "")
			output_xhtml = output_xhtml.replace("]]>", "")

			# Make some replacements for HTML5 compatibility
			output_xhtml = output_xhtml.replace("epub|type", "data-epub-type")
			output_xhtml = output_xhtml.replace("xml|lang", "lang")
			output_xhtml = regex.sub(r" xmlns.+?=\".+?\"", "", output_xhtml)
			output_xhtml = regex.sub(r"@namespace (epub|xml).+?\s+", "", output_xhtml, flags=regex.MULTILINE)

			# The Nu HTML5 Validator barfs if non-void elements are self-closed (like <td/>)
			# Try to un-self-close them for HTML5 output.
			output_xhtml = regex.sub(r"<(colgroup|td|th|span)( [^/>]*?)?/>", r"<\1\2></\1>", output_xhtml)

		return output_xhtml

	def generate_titlepage_svg(self) -> None:
		"""
		Generate a distributable titlepage SVG in ./src/epub/images/ based on the titlepage file in ./images/

		INPUTS
		None

		OUTPUTS
		None.
		"""
		source_images_directory = self.path / "images"
		source_titlepage_svg_filename = source_images_directory / "titlepage.svg"
		dest_images_directory = self.content_path / "images"
		dest_titlepage_svg_filename = dest_images_directory / "titlepage.svg"

		if source_titlepage_svg_filename.is_file():
			# Convert text to paths
			se.images.svg_text_to_paths(source_titlepage_svg_filename, dest_titlepage_svg_filename)

	def generate_cover_svg(self) -> None:
		"""
		Generate a distributable cover SVG in ./src/epub/images/ based on the cover file in ./images/

		INPUTS
		None

		OUTPUTS
		None.
		"""

		source_images_directory = self.path / "images"
		source_cover_jpg_filename = source_images_directory / "cover.jpg"
		source_cover_svg_filename = source_images_directory / "cover.svg"
		dest_images_directory = self.content_path / "images"
		dest_cover_svg_filename = self.cover_path

		# Create output directory if it doesn't exist
		dest_images_directory.mkdir(parents=True, exist_ok=True)

		if source_cover_jpg_filename.is_file() and source_cover_svg_filename.is_file():
			# base64 encode cover.jpg
			with open(source_cover_jpg_filename, "rb") as binary_file:
				source_cover_jpg_base64 = base64.b64encode(binary_file.read()).decode()

			# Convert text to paths
			if source_cover_svg_filename.is_file():
				se.images.svg_text_to_paths(source_cover_svg_filename, dest_cover_svg_filename, remove_style=False)

			# Embed cover.jpg
			dom = self.get_dom(dest_cover_svg_filename)

			# Embed the file
			for node in dom.xpath("//*[re:test(@xlink:href, 'cover\\.jpg$')]"):
				node.set_attr("xlink:href", "data:image/jpeg;base64," + source_cover_jpg_base64)

			# For the cover we want to keep the path.title-box style, and add an additional
			# style to color our new paths white
			for node in dom.xpath("/svg/style"):
				node.set_text("\n\t\tpath{\n\t\t\tfill: #fff;\n\t\t}\n\n\t\t.title-box{\n\t\t\tfill: #000;\n\t\t\tfill-opacity: .75;\n\t\t}\n\t")

			with open(dest_cover_svg_filename, "w", encoding="utf-8") as file:
				file.write(dom.to_string())

	def shift_endnotes(self, target_endnote_number: int, step: int = 1) -> None:
		"""
		Shift endnotes starting at target_endnote_number.

		INPUTS:
		target_endnote_number: The endnote to start shifting at
		step: 1 to increment or -1 to decrement

		OUTPUTS:
		None.
		"""

		increment = step > 0
		endnote_count = 0

		if step == 0:
			return

		dom = self.get_dom(self.endnotes_path)

		endnote_count = len(dom.xpath("//li[contains(@epub:type, 'endnote')]"))
		if increment:
			# Range is from COUNT -> target_endnote_number
			note_range = range(endnote_count, target_endnote_number - 1, -1)
		else:
			# Range is from target_endnote_number -> COUNT
			note_range = range(target_endnote_number, endnote_count + 1, 1)

		for endnote_number in note_range:
			new_endnote_number = endnote_number + step

			# Update all the actual endnotes in the endnotes file
			for node in dom.xpath(f"/html/body//li[contains(@epub:type, 'endnote') and @id='note-{endnote_number}']"):
				node.set_attr("id", f"note-{new_endnote_number}")

			# Update all backlinks in the endnotes file
			for node in dom.xpath(f"/html/body//a[re:test(@href, '#noteref-{endnote_number}$')]"):
				node.set_attr("href", node.get_attr("href").replace(f"#noteref-{endnote_number}", f"#noteref-{new_endnote_number}"))

		# Write the endnotes file
		try:
			with open(self.endnotes_path, "w", encoding="utf-8") as file:
				file.write(dom.to_string())

		except Exception as ex:
			raise se.InvalidSeEbookException(f"Couldn’t open endnotes file: [path][link=file://{self.endnotes_path}]{self.endnotes_path}[/][/].") from ex

		# Now update endnotes in all other files. We also do a pass over the endnotes file itself.
		# again just in case there are endnotes within endnotes.
		for file_path in self.content_path.glob("**/*.xhtml"):
			dom = self.get_dom(file_path)

			for endnote_number in note_range:
				new_endnote_number = endnote_number + step

				# We don't use an xpath matching epub:type="noteref" because we can have hrefs that are not noterefs pointing to endnotes (like "see here")
				for node in dom.xpath(f"/html/body//a[re:test(@href, '(endnotes\\.xhtml)?#note-{endnote_number}$')]"):
					# Update the `id` attribute of the link, if we have one (sometimes hrefs point to endnotes but they are not noterefs themselves)
					if node.get_attr("id"):
						# Use a regex instead of just replacing the entire ID so that we don't mess up IDs that do not fit this pattern
						node.set_attr("id", regex.sub(r"noteref-\d+$", f"noteref-{new_endnote_number}", node.get_attr("id")))

					node.set_attr("href", regex.sub(fr"#note-{endnote_number}$", f"#note-{new_endnote_number}", node.get_attr("href")))
					node.set_text(regex.sub(fr"\b{endnote_number}\b", f"{new_endnote_number}", node.text))

			with open(file_path, "w", encoding="utf-8") as file:
				file.write(dom.to_string())

	def shift_illustrations(self, target_illustration_number: int, step: int = 1) -> None:
		"""
		Shift illustrations starting at target_illustration_number.

		INPUTS:
		target_illustration_number: The illustration to start shifting at
		step: 1 to increment or -1 to decrement

		OUTPUTS:
		None.
		"""

		increment = step > 0
		illustration_count = 0

		if step == 0:
			return

		dom = self.get_dom(self.loi_path)

		illustration_count = len(dom.xpath("/html/body/nav/ol/li"))
		if increment:
			# Range is from COUNT -> target_illustration_number
			illustration_range = range(illustration_count, target_illustration_number - 1, -1)
		else:
			# Range is from target_illustration_number -> COUNT
			illustration_range = range(target_illustration_number, illustration_count + 1, 1)

		# Update image files
		for illustration_number in illustration_range:
			new_illustration_number = illustration_number + step

			# Test for previously existing file
			for illustration_path in [self.path / "images", self.content_path / "images"]:
				existing_file = None

				try:
					existing_file = next(illustration_path.glob(f"illustration-{new_illustration_number}.*"))
				except Exception:
					pass

				if existing_file:
					raise se.FileExistsException(f"Couldn’t rename illustration to already existing file: [path][link=file://{existing_file}]{existing_file}[/][/]")

				file_to_rename = next(illustration_path.glob(f"illustration-{illustration_number}.*"))
				file_to_rename.rename(illustration_path / f"illustration-{new_illustration_number}{file_to_rename.suffix}")

		# Update the LoI file
		for illustration_number in illustration_range:
			new_illustration_number = illustration_number + step

			# Update all the illustrations in the illustrations file
			for node in dom.xpath(f"/html/body//a[re:test(@href, '#illustration-{illustration_number}$')]"):
				node.set_attr("href", node.get_attr("href").replace(f"#illustration-{illustration_number}", f"#illustration-{new_illustration_number}"))

		# Write the LoI file
		try:
			with open(self.loi_path, "w", encoding="utf-8") as file:
				file.write(dom.to_string())

		except Exception as ex:
			raise se.InvalidSeEbookException(f"Couldn’t open LoI file: [path][link=file://{self.loi_path}]{self.loi_path}[/][/].") from ex

		# Now update illustrations in all other files.
		for file_path in self.content_path.glob("**/*.xhtml"):
			dom = self.get_dom(file_path)

			for illustration_number in illustration_range:
				new_illustration_number = illustration_number + step

				for node in dom.xpath(f"/html/body//figure[@id='illustration-{illustration_number}']"):
					node.set_attr("id", f"illustration-{new_illustration_number}")
					for img in node.xpath("./img"):
						img.set_attr("src", img.get_attr("src").replace(f"illustration-{illustration_number}", f"illustration-{new_illustration_number}"))

			with open(file_path, "w", encoding="utf-8") as file:
				file.write(dom.to_string())

	def set_release_timestamp(self) -> None:
		"""
		If this ebook has not yet been released, set the first release timestamp in the metadata file.
		"""

		if self.metadata_dom.xpath("/package/metadata/dc:date[text() = '1900-01-01T00:00:00Z']"):
			now = datetime.datetime.utcnow()
			now_iso = regex.sub(r"\.[0-9]+$", "", now.isoformat()) + "Z"
			now_iso = regex.sub(r"\+.+?Z$", "Z", now_iso)
			now_friendly = f"{now:%B %e, %Y, %l:%M <abbr class=\"eoc\">%p</abbr>}"
			now_friendly = regex.sub(r"\s+", " ", now_friendly).replace("AM", "a.m.").replace("PM", "p.m.").replace(" <abbr", " <abbr")

			for node in self.metadata_dom.xpath("/package/metadata/dc:date"):
				node.set_text(now_iso)

			for node in self.metadata_dom.xpath("/package/metadata/meta[@property='dcterms:modified']"):
				node.set_text(now_iso)

			with open(self.metadata_file_path, "w", encoding="utf-8") as file:
				file.write(self.metadata_dom.to_string())

			for file_path in self.content_path.glob("**/*.xhtml"):
				dom = self.get_dom(file_path)

				if dom.xpath("/html/body/section[contains(@epub:type, 'colophon')]"):
					for node in dom.xpath("/html/body/section[contains(@epub:type, 'colophon')]//b[contains(text(), 'January 1, 1900')]"):
						node.replace_with(se.easy_xml.EasyXmlElement(etree.fromstring(str.encode("<b>" + now_friendly + "</b>"))))

					with open(file_path, "w", encoding="utf-8") as file:
						file.write(dom.to_string())

	def update_flesch_reading_ease(self) -> None:
		"""
		Calculate a new reading ease for this ebook and update the metadata file.
		Ignores SE boilerplate files like the imprint.

		INPUTS
		None

		OUTPUTS
		None.
		"""

		text = ""

		for filename in se.get_target_filenames([self.path], ".xhtml"):
			xhtml = self.get_file(filename)

			is_ignored, _ = se.get_dom_if_not_ignored(xhtml, ["colophon", "titlepage", "imprint", "copyright-page", "halftitlepage", "toc", "loi"])

			if not is_ignored:
				text += xhtml

		for node in self.metadata_dom.xpath("/package/metadata/meta[@property='se:reading-ease.flesch']"):
			node.set_text(str(se.formatting.get_flesch_reading_ease(text)))

		with open(self.metadata_file_path, "w", encoding="utf-8") as file:
			file.write(self.metadata_dom.to_string())

	def get_word_count(self) -> int:
		"""
		Calculate the word count of this ebook.
		Ignores SE boilerplate files like the imprint, as well as any endnotes.

		INPUTS
		None

		OUTPUTS
		The number of words in the ebook.
		"""
		word_count = 0

		for filename in se.get_target_filenames([self.path], ".xhtml"):
			xhtml = self.get_file(filename)

			is_ignored, _ = se.get_dom_if_not_ignored(xhtml, ["colophon", "titlepage", "imprint", "copyright-page", "halftitlepage", "toc", "loi", "endnotes"])

			if not is_ignored:
				word_count += se.formatting.get_word_count(xhtml)

		return word_count

	def update_word_count(self) -> None:
		"""
		Calculate a new word count for this ebook and update the metadata file.
		Ignores SE boilerplate files like the imprint, as well as any endnotes.

		INPUTS
		None

		OUTPUTS
		None.
		"""

		for node in self.metadata_dom.xpath("/package/metadata/meta[@property='se:word-count']"):
			node.set_text(str(self.get_word_count()))

		with open(self.metadata_file_path, "r+", encoding="utf-8") as file:
			file.seek(0)
			file.write(self.metadata_dom.to_string())
			file.truncate()

	def generate_manifest(self) -> se.easy_xml.EasyXmlElement:
		"""
		Return the <manifest> element for this ebook as an EasyXmlElement.

		INPUTS
		None

		OUTPUTS
		An EasyXmlElement representing the manifest.
		"""

		manifest = []

		for file_path in self.content_path.glob("**/*"):
			if file_path.name == self.metadata_file_path.name:
				# Don't add the metadata file to the manifest
				continue

			if file_path.stem.startswith("."):
				# Skip dotfiles
				continue

			mime_type = None
			properties = []

			if file_path.suffix == ".css":
				mime_type="text/css"

			if file_path.suffix in (".ttf", ".otf", ".woff", ".woff2"):
				mime_type="application/vnd.ms-opentype"

			if file_path.suffix == ".svg":
				mime_type = "image/svg+xml"

			if file_path.suffix == ".png":
				mime_type = "image/png"

			if file_path.suffix == ".jpg":
				mime_type = "image/jpeg"

			if file_path.stem == "cover":
				properties.append("cover-image")

			if file_path.suffix == ".xhtml":
				dom = self.get_dom(file_path)

				mime_type = "application/xhtml+xml"

				# the `glossary` semantic may also appear in the ToC landmarks, so specifically exclude that
				if dom.xpath("//*[contains(@epub:type, 'glossary') and not(ancestor-or-self::nav)]"):
					properties.append("glossary")
				if dom.xpath("/html[namespace::*='http://www.w3.org/1998/Math/MathML']"):
					properties.append("mathml")

				if dom.xpath("//img[re:test(@src, '\\.svg$')]"):
					properties.append("svg")

				if dom.xpath("//nav[contains(@epub:type, 'toc')]"):
					properties.append("nav")

			if file_path.suffix == ".xml":
				dom = self.get_dom(file_path)

				# Do we have a glossary search key map?
				if dom.xpath("/search-key-map"):
					mime_type = "application/vnd.epub.search-key-map+xml"
					properties.append("glossary")
					properties.append("search-key-map")

			if mime_type:
				# Put together any properties we have
				properties_attr = ""
				for prop in properties:
					properties_attr += prop + " "

				properties_attr = properties_attr.strip()

				if properties_attr:
					properties_attr = f" properties=\"{properties_attr}\""

				# Add the manifest item
				# Replace the path separator because if run on Windows we will get the wrong slash direction from pathlib
				manifest.append(f"""<item href="{str(file_path.relative_to(self.content_path)).replace(os.sep, "/")}" id="{file_path.name}" media-type="{mime_type}"{properties_attr}/>""")

		manifest = natsorted(manifest)

		# Assemble the manifest XML string
		manifest_xml = "<manifest>\n"

		for line in manifest:
			manifest_xml = manifest_xml + "\t" + line + "\n"

		manifest_xml = manifest_xml + "</manifest>"

		return se.easy_xml.EasyXmlElement(etree.fromstring(str.encode(manifest_xml)))

	def __add_to_spine(self, spine: List[str], items: List[Path], semantic: str) -> Tuple[List[str], List[Path]]:
		"""
		Given a spine and a list of items, add the item to the spine if it contains the specified semantic.
		If an item is added to the spine, remove it from the original list.

		Returns an updated spine and item list.
		"""

		filtered_items = []
		spine_additions = []

		for file_path in items:
			dom = self.get_dom(file_path)

			# Match against \b because we might have `titlepage` and `halftitlepage`
			if dom.xpath(f"/html/body//section[re:test(@epub:type, '\\b{semantic}\\b')]"):
				spine_additions.append(file_path.name)
			else:
				filtered_items.append(file_path)

		# Sort the additions, for example if we have more than one dedication or introduction
		spine_additions = natsorted(spine_additions)

		return (spine + spine_additions, filtered_items)

	def generate_spine(self) -> se.easy_xml.EasyXmlElement:
		"""
		Return the <spine> element of this ebook as an EasyXmlElement, with a best guess as to the correct order. Manual review is required.

		INPUTS
		None

		OUTPUTS
		An EasyXmlElement representing the spine.
		"""

		spine: List[str] = []
		frontmatter = []
		bodymatter = []
		backmatter = []

		for file_path in self.content_path.glob("**/*.xhtml"):
			dom = self.get_dom(file_path)

			# Exclude the ToC from the spine
			if dom.xpath("/html/body//nav[contains(@epub:type, 'toc')]"):
				continue

			if dom.xpath("/html/*[contains(@epub:type, 'frontmatter')]"):
				frontmatter.append(file_path)
			elif dom.xpath("/html/*[contains(@epub:type, 'backmatter')]"):
				backmatter.append(file_path)
			else:
				bodymatter.append(file_path)

		# Add frontmatter
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "titlepage")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "imprint")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "dedication")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "preamble")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "introduction")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "foreword")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "preface")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "epigraph")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "z3998:dramatis-personae")

		# Extract half title page for subsequent addition
		halftitlepage, frontmatter = self.__add_to_spine([], frontmatter, "halftitlepage")

		# Add any remaining frontmatter
		spine = spine + natsorted([file_path.name for file_path in frontmatter])

		# The half title page is always the last front matter
		spine = spine + halftitlepage

		# Add bodymatter
		spine, bodymatter = self.__add_to_spine(spine, bodymatter, "prologue")

		spine = spine + natsorted([file_path.name for file_path in bodymatter])

		# Add backmatter
		spine, backmatter = self.__add_to_spine(spine, backmatter, "afterword")
		spine, backmatter = self.__add_to_spine(spine, backmatter, "appendix")
		spine, backmatter = self.__add_to_spine(spine, backmatter, "glossary")
		spine, backmatter = self.__add_to_spine(spine, backmatter, "endnotes")
		spine, backmatter = self.__add_to_spine(spine, backmatter, "loi")

		# Extract colophon and copyright page for subsequent addition
		colophon, backmatter = self.__add_to_spine([], backmatter, "colophon")
		copyright_page, backmatter = self.__add_to_spine([], backmatter, "copyright-page")

		# Add any remaining backmatter
		spine = spine + natsorted([file_path.name for file_path in backmatter])

		# Colophon and copyright page are always last
		spine = spine + colophon
		spine = spine + copyright_page

		# Now build the spine output
		spine_xml = "<spine>\n"
		for filename in spine:
			spine_xml = spine_xml + f"""\t<itemref idref="{filename}"/>\n"""

		spine_xml = spine_xml + "</spine>"

		return se.easy_xml.EasyXmlElement(etree.fromstring(str.encode(spine_xml)))

	def get_work_type(self) -> str:
		"""
		Returns either "fiction" or "non-fiction", based on analysis of se:subjects in the metadata file

		INPUTS:
		None

		OUTPUTS:
		The fiction or non-fiction type
		"""

		worktype = "fiction"  # default

		subjects = self.metadata_dom.xpath("/package/metadata/meta[@property='se:subject']/text()")
		if not subjects:
			return worktype

		# Unfortunately, some works are tagged "Philosophy" but are nevertheless fiction, so we have to double-check
		if "Nonfiction" in subjects:
			return "non-fiction"

		nonfiction_types = ["Autobiography", "Memoir", "Philosophy", "Spirituality", "Travel"]
		for nonfiction_type in nonfiction_types:
			if nonfiction_type in subjects:
				worktype = "non-fiction"

		fiction_types = ["Fantasy", "Fiction", "Horror", "Mystery", "Science Fiction"]
		for fiction_type in fiction_types:
			if fiction_type in subjects:
				worktype = "fiction"

		return worktype

	def get_work_title(self) -> str:
		"""
		Returns the title of the book from the metadata file, which we assume has already been correctly completed.

		INPUTS:
		None

		OUTPUTS:
		Either the title of the book or the default WORKING_TITLE
		"""

		return self.metadata_dom.xpath("/package/metadata/dc:title/text()", True) or "WORK_TITLE"

	def lint(self, skip_lint_ignore: bool, allowed_messages: Optional[List[str]] = None) -> list:
		"""
		The lint() function is very big so for readability and maintainability
		it's broken out to a separate file. Strictly speaking that file can be inlined
		into this class.
		"""

		from se.se_epub_lint import lint # pylint: disable=import-outside-toplevel

		return lint(self, skip_lint_ignore, allowed_messages)

	def build(self, run_epubcheck: bool, check_only: bool, build_kobo: bool, build_kindle: bool, output_directory: Path, proof: bool) -> None:
		"""
		The build() function is very big so for readability and maintainability
		it's broken out to a separate file. Strictly speaking that file can be inlined
		into this class.
		"""

		from se.se_epub_build import build # pylint: disable=import-outside-toplevel

		build(self, run_epubcheck, check_only, build_kobo, build_kindle, output_directory, proof)

	def generate_toc(self) -> str:
		"""
		The generate_toc() function is very big so for readability and maintainability
		it's broken out to a separate file. Strictly speaking that file can be inlined
		into this class.
		"""

		from se.se_epub_generate_toc import generate_toc  # pylint: disable=import-outside-toplevel

		toc_xhtml = generate_toc(self)

		# Word joiners and nbsp don't go in the ToC
		toc_xhtml = toc_xhtml.replace(se.WORD_JOINER, "")
		toc_xhtml = toc_xhtml.replace(se.NO_BREAK_SPACE, " ")

		return toc_xhtml

	def _check_endnotes(self) -> list:
		"""
		Initial check to see if all note references in the body have matching endnotes
		in endnotes.xhtml and no duplicates.

		Returns string of failures if any. If these are empty, all was well.
		"""
		missing = []
		duplicates = []
		orphans = []
		references = []
		response = []
		for file_path in self.spine_file_paths:
			dom = self.get_dom(file_path)

			for link in dom.xpath("/html/body//a[contains(@epub:type, 'noteref')]"):
				anchor = ""
				href = link.get_attr("href") or ""
				if href:
					# Extract just the anchor from a URL (i.e., what follows a hash symbol)
					hash_position = href.find("#") + 1  # we want the characters AFTER the hash
					if hash_position > 0:
						anchor = href[hash_position:]
				references.append(anchor)  # keep these for later reverse check
				# Now try to find anchor in endnotes
				matches = list(filter(lambda x, old=anchor: x.anchor == old, self.endnotes)) # type: ignore [arg-type]
				if not matches:
					missing.append(anchor)
				if len(matches) > 1:
					duplicates.append(anchor)
		for miss in missing:
			response.append(f"Missing endnote with anchor: {miss}")
		for dupe in duplicates:
			response.append(f"Duplicate endnotes with anchor: {dupe}")
		# reverse check: look for orphaned endnotes
		for note in self.endnotes:
			# try to find it in our references collection
			if note.anchor not in references:
				orphans.append(note.anchor)
		for orphan in orphans:
			response.append(f"Orphan endnote with anchor: {orphan}")
		if len(orphans) > 0:
			response.append("Is your spine generated and valid?")
		return response

	def recreate_endnotes(self) -> None:
		"""
		Renumber all noterefs starting from 1, and renumber all endnotes starting from 1.
		Does not perform any sanity checks or do any rearranging; may result in more noterefs than endnotes, or more endnotes than noterefs.
		Changes are written to disk.
		"""

		noteref_locations = {}

		current_note_number = 1

		# Renumber all noterefs starting from 1
		for file_path in self.spine_file_paths:
			dom = self.get_dom(file_path)

			for node in dom.xpath("/html/body//a[contains(@epub:type, 'noteref')]"):
				node.set_attr("href", f"endnotes.xhtml#note-{current_note_number}")
				node.set_attr("id", f"noteref-{current_note_number}")
				node.set_text(str(current_note_number))
				noteref_locations[current_note_number] = file_path

				current_note_number += 1

			with open(file_path, "w", encoding="utf-8") as file:
				file.write(dom.to_string())

		# Renumber all endnotes starting from 1
		current_note_number = 1
		endnotes_dom = self.get_dom(self.endnotes_path)
		for node in endnotes_dom.xpath("/html/body//li[contains(@epub:type, 'endnote')]"):
			node.set_attr("id", f"note-{current_note_number}")
			for backlink in node.xpath(".//a[contains(@epub:type, 'backlink')]"):
				filename = noteref_locations[current_note_number].name if current_note_number in noteref_locations else ""
				backlink.set_attr("href", f"{filename}#noteref-{current_note_number}")

			current_note_number += 1

		with open(self.endnotes_path, "w", encoding="utf-8") as file:
			file.write(endnotes_dom.to_string())

	def generate_endnotes(self) -> Tuple[int, int, list]:
		"""
		Read the epub spine to regenerate all endnotes in order of appearance, starting from 1.
		Changes are written to disk.

		Returns a tuple of (found_endnote_count, changed_endnote_count, change_list)
		"""

		# Do a safety check first, throw exception if it failed
		results = self._check_endnotes()
		if results:
			report = "\n".join(results)
			raise se.InvalidInputException(f"Endnote error(s) found:\n{report}")

		# If we get here, it's safe to proceed
		processed = 0
		current_note_number = 1
		notes_changed = 0
		change_list: List[EndnoteChange] = []

		for file_path in self.spine_file_paths:
			dom = self.get_dom(file_path)

			# Skip the actual endnotes file, we'll handle that later
			if dom.xpath("/html/body//*[contains(@epub:type, 'endnotes')]"):
				continue

			processed += 1

			needs_rewrite = False
			for link in dom.xpath("/html/body//a[contains(@epub:type, 'noteref')]"):
				needs_rewrite, notes_changed = self.__process_noteref_link(change_list, current_note_number, file_path.name, link, needs_rewrite, notes_changed)
				current_note_number += 1

			# If we need to write back the body text file
			if needs_rewrite:
				with open(file_path, "w", encoding="utf-8") as file:
					file.write(se.formatting.format_xhtml(dom.to_string()))

		# Now process any endnotes WITHIN the endnotes
		for source_note in self.endnotes:
			node = source_note.node
			needs_rewrite = False
			for link in node.xpath(".//a[contains(@epub:type, 'noteref')]"):
				needs_rewrite, notes_changed = self.__process_noteref_link(change_list, current_note_number, self.endnotes_path.name, link, needs_rewrite, notes_changed)
				current_note_number += 1

		if processed == 0:
			raise se.InvalidInputException("No files processed. Did you update the manifest and order the spine?")

		if notes_changed > 0:
			# Now we need to recreate the endnotes file
			endnotes_dom = self.get_dom(self.endnotes_path)
			for ol_node in endnotes_dom.xpath("/html/body/section[contains(@epub:type, 'endnotes')]/ol[1]"):
				for node in ol_node.xpath("./li[contains(@epub:type, 'endnote')]"):
					node.remove()

				self.endnotes.sort(key=lambda endnote: endnote.number)

				for endnote in self.endnotes:
					if endnote.matched:
						endnote.node.set_attr("id", f"note-{endnote.number}")

						for node in endnote.node.xpath(".//a[contains(@epub:type, 'backlink')]"):
							node.set_attr("href", f"{endnote.source_file}#noteref-{endnote.number}")

						ol_node.append(endnote.node)

			with open(self.endnotes_path, "w", encoding="utf-8") as file:
				file.write(se.formatting.format_xhtml(endnotes_dom.to_string()))

			# now trawl through the body files to locate any direct links to endnotes (not in an actual endnote reference)
			# example: (see <a href="endnotes.xhtml#note-1553">this note</a>.)
			# most but not all such are likely to be in the newly re-written endnotes.xhtml
			for file_path in self.spine_file_paths:
				needs_rewrite = False
				dom = self.get_dom(file_path)
				for link in dom.xpath("/html/body//a[contains(@href, 'endnotes.xhtml#note-')]"):
					needs_rewrite = self.__process_direct_link(change_list, link)
				if needs_rewrite:
					with open(file_path, "w", encoding="utf-8") as file:
						file.write(se.formatting.format_xhtml(dom.to_string()))

		return current_note_number - 1, notes_changed, change_list

	def __process_direct_link(self, change_list, link) -> bool:
		"""
		Checks all hyperlinks to the endnotes to see if the existing anchor needs to be updated with a new number

		Returns a boolean of needs_write (whether object needs to be re-written)
		"""
		epub_type = link.get_attr("epub:type") or ""
		if not epub_type: # it wasn't an actual endnote reference but a direct link (we hope!)
			href = link.get_attr("href") or ""
			if href:
				# Extract just the anchor from a URL (ie, what follows a hash symbol)
				hash_position = href.find("#") + 1  # we want the characters AFTER the hash
				if hash_position > 0:
					old_anchor = href[hash_position:]
					try:
						change = next(ch for ch in change_list if ch.old_anchor == old_anchor)
						link.set_attr("href", f"{self.endnotes_path.name}#{change.new_anchor}")
						return True
					except StopIteration:  # didn't find the old anchor, keep going
						pass
		return False

	def __process_noteref_link(self, change_list, current_note_number, file_name, link, needs_rewrite, notes_changed) -> Tuple[bool, int]:
		"""
		Checks each endnote link to see if the existing anchor needs to be updated with a new number

		Returns a tuple of needs_write (whether object needs to be re-written), and the number of notes_changed
		"""

		old_anchor = ""
		href = link.get_attr("href") or ""
		if href:
			# Extract just the anchor from a URL (ie, what follows a hash symbol)
			hash_position = href.find("#") + 1  # we want the characters AFTER the hash
			if hash_position > 0:
				old_anchor = href[hash_position:]

		new_anchor = f"note-{current_note_number:d}"
		if new_anchor != old_anchor:
			endnote_change = EndnoteChange(old_anchor, new_anchor, file_name)
			change_list.append(endnote_change)
			notes_changed += 1
			# Update the link in the dom
			link.set_attr("href", f"{self.endnotes_path.name}#{new_anchor}")
			link.set_attr("id", f"noteref-{current_note_number:d}")
			link.lxml_element.text = str(current_note_number)
			needs_rewrite = True
		# Now try to find this in endnotes
		matches = list(filter(lambda x, old=old_anchor: x.anchor == old, self.endnotes)) # type: ignore [arg-type]
		if not matches:
			raise se.InvalidInputException(f"Couldn’t find endnote with anchor [attr]{old_anchor}[/].")
		if len(matches) > 1:
			raise se.InvalidInputException(f"Duplicate anchors in endnotes file for anchor [attr]{old_anchor}[/].")
		# Found a single match, which is what we want
		endnote = matches[0]
		endnote.number = current_note_number
		endnote.matched = True
		# We don't change the anchor or the back ref just yet
		endnote.source_file = file_name
		return needs_rewrite, notes_changed
