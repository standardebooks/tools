#!/usr/bin/env python3
"""
Defines the SeEpub class, the master class for representing and operating on
Standard Ebooks epub3 files.
"""

import base64
import concurrent.futures
import datetime
import fnmatch
import os
from pathlib import Path
from typing import List, Optional, Tuple, Union

import git
from natsort import natsorted
import regex

import se
import se.easy_xml
import se.formatting
import se.images


def _process_endnotes_in_file(filename: str, root: Path, note_range: range, step: int) -> None:
	"""
	Helper function for reordering endnotes.

	This has to be outside of the class to be able to be called by `executor`.
	"""

	with open(root / filename, "r+", encoding="utf-8") as file:
		xhtml = file.read()
		processed_xhtml = xhtml
		processed_xhtml_is_modified = False

		for endnote_number in note_range:
			# If we’ve already changed some notes and can’t find the next then we don’t need to continue searching
			if not f"id=\"noteref-{endnote_number}\"" in processed_xhtml and processed_xhtml_is_modified:
				break
			processed_xhtml = processed_xhtml.replace(f"id=\"noteref-{endnote_number}\"", f"id=\"noteref-{endnote_number + step}\"", 1)
			processed_xhtml = processed_xhtml.replace(f"#note-{endnote_number}\"", f"#note-{endnote_number + step}\"", 1)
			processed_xhtml = processed_xhtml.replace(f">{endnote_number}</a>", f">{endnote_number + step}</a>", 1)
			processed_xhtml_is_modified = processed_xhtml_is_modified or (processed_xhtml != xhtml)

		if processed_xhtml_is_modified:
			file.seek(0)
			file.write(processed_xhtml)
			file.truncate()

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

class SeEpub:
	"""
	An object representing an SE epub file.

	An SE epub can have various operations performed on it, including recomposing and linting.
	"""

	path = Path()
	metadata_file_path = Path()
	metadata_xml = ""
	local_css = ""
	_metadata_dom = None
	_generated_identifier = None
	_generated_github_repo_url = None
	_repo = None # git.Repo object
	_last_commit = None # GitCommit object
	__endnotes_dom = None # EasyXhtmlTree object of the endnotes.xhtml file
	_endnotes: Optional[List[Endnote]] = None # List of Endnote objects

	def __init__(self, epub_root_directory: Union[str, Path]):
		try:
			self.path = Path(epub_root_directory).resolve()

			if not self.path.is_dir():
				raise se.InvalidSeEbookException(f"Not a directory: [path][link=file://{self.path}]{self.path}[/][/].")

			with open(self.path / "src" / "META-INF" / "container.xml", "r", encoding="utf-8") as file:
				container_tree = se.easy_xml.EasyXmlTree(file.read())
				self.metadata_file_path = self.path / "src" / container_tree.xpath("/container:container/container:rootfiles/container:rootfile[@media-type=\"application/oebps-package+xml\"]/@full-path")[0]

			with open(self.metadata_file_path, "r", encoding="utf-8") as file:
				self.metadata_xml = file.read()

			if "<dc:identifier id=\"uid\">url:https://standardebooks.org/ebooks/" not in self.metadata_xml:
				raise se.InvalidSeEbookException
		except Exception as ex:
			raise se.InvalidSeEbookException(f"Not a Standard Ebooks source directory: [path][link=file://{self.path}]{self.path}[/][/].") from ex

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
				if 'GIT_DIR' in os.environ:
					del os.environ['GIT_DIR']

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
			# Add authors
			identifier = "url:https://standardebooks.org/ebooks/"
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
			for role in self.metadata_dom.xpath("/package/metadata/meta[@property=\"role\"]"):
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
				if (not illustrators_have_display_seq and illustrator["include"]) or illustrator["display_seq"]:
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
	def _endnotes_dom(self) -> se.easy_xml.EasyXhtmlTree:
		"""
		Accessor

		Return an EasyXmlTree object representing the endnotes.xhtml file for this ebook.

		INPUTS
		None

		OUTPUTS
		A EasyXmlTree object representing the endnotes.xhtml file for this ebook.
		"""

		if not self.__endnotes_dom:
			try:
				with open(self.path / "src" / "epub" / "text" / "endnotes.xhtml") as file:
					self.__endnotes_dom = se.formatting.EasyXhtmlTree(file.read())
			except Exception as ex:
				raise se.InvalidFileException(f"Could't open file: [path][link=file://{self.path / 'src' / 'epub' / 'text' / 'endnotes.xhtml'}]{self.path / 'src' / 'epub' / 'text' / 'endnotes.xhtml'}[/][/].") from ex

		return self.__endnotes_dom

	@property
	def endnotes(self) -> list:
		"""
		Accessor

		Return a list of Endnote objects representing the endnotes.xhtml file for this ebook.

		INPUTS
		None

		OUTPUTS
		A list of Endnote objects representing the endnotes.xhtml file for this ebook.
		"""

		if not self._endnotes:
			self._endnotes = []

			for node in self._endnotes_dom.xpath("/html/body/section[contains(@epub:type, 'endnotes')]/ol/li[contains(@epub:type, 'endnote')]"):
				note = Endnote()
				note.node = node
				note.number = int(node.get_attr("id").replace("note-", ""))
				note.contents = node.xpath("./*")
				note.anchor = node.get_attr("id") or ""

				for back_link in node.xpath("//a[contains(@epub:type, 'backlink')]/@href"):
					note.back_link = back_link

				self._endnotes.append(note)

		return self._endnotes

	@property
	def metadata_dom(self) -> se.easy_xml.EasyXmlTree:
		"""
		Accessor
		"""

		if self._metadata_dom is None:
			try:
				self._metadata_dom = se.easy_xml.EasyOpfTree(self.metadata_xml)
			except Exception as ex:
				raise se.InvalidXmlException(f"Couldn’t parse [path][link=file://{self.metadata_file_path}]{self.metadata_file_path}[/][/]. Exception: {ex}")

		return self._metadata_dom

	def _recompose_xhtml(self, section: se.easy_xml.EasyXmlElement, output_dom: se.easy_xml.EasyXmlTree) -> None:
		"""
		Helper function used in self.recompose()
		Recursive function for recomposing a series of XHTML files into a single XHTML file.

		INPUTS
		section: An EasyXmlElement to inspect
		output_dom: A EasyXmlTree representing the entire output dom

		OUTPUTS
		None
		"""

		# Quick sanity check before we begin
		if not section.get_attr("id") or (section.parent.lxml_element.tag != "body" and not section.parent.get_attr("id")):
			raise se.InvalidXhtmlException("Section without [attr]id[/] attribute.")

		# Try to find our parent tag in the output, by ID.
		# If it's not in the output, then append it to the tag's closest parent by ID (or <body>), then iterate over its children and do the same.
		existing_section = output_dom.xpath(f"//*[@id='{section.get_attr('id')}']")
		if not existing_section:
			if section.parent.tag.lower() == "body":
				output_dom.xpath("/html/body")[0].append(section)
			else:
				output_dom.xpath(f"//*[@id='{section.parent.get_attr('id')}']")[0].append(section)

			existing_section = output_dom.xpath(f"//*[@id='{section.get_attr('id')}']")

		# Convert all <img> references to inline base64
		# We even convert SVGs instead of inlining them, because CSS won't allow us to style inlined SVGs
		# (for example if we want to apply max-width or filter: invert())
		for img in section.xpath("//img[starts-with(@src, '../images/')]"):
			src = img.get_attr("src").replace("../", "")
			with open(self.path / "src" / "epub" / src, "rb") as binary_file:
				image_contents_base64 = base64.b64encode(binary_file.read()).decode()

			if src.endswith(".svg"):
				img.set_attr("src", f"data:image/svg+xml;base64, {image_contents_base64}")

			if src.endswith(".jpg"):
				img.set_attr("src", f"data:image/jpg;base64, {image_contents_base64}")

			if src.endswith(".png"):
				img.set_attr("src", f"data:image/png;base64, {image_contents_base64}")

		for child in section.lxml_element:
			tag_name = child.tag
			if tag_name in ("section", "article"):
				self._recompose_xhtml(se.easy_xml.EasyXmlElement(child), output_dom)
			else:
				existing_section.append(se.easy_xml.EasyXmlElement(child))

	def recompose(self, output_xhtml5: bool) -> str:
		"""
		Iterate over the XHTML files in this epub and "recompose" them into a single XHTML string representing this ebook.

		INPUTS
		output_xhtml5: true to output XHTML5 instead of HTML5

		OUTPUTS
		A string of HTML5 representing the entire recomposed ebook.
		"""

		# Get some header data: title, core and local css
		title = self.metadata_dom.xpath("//dc:title/text()")[0]
		language = self.metadata_dom.xpath("//dc:language/text()")[0]
		css = ""
		for filename in os.scandir(self.path / "src" / "epub" / "css"):
			filepath = Path(filename)
			if filepath.suffix == ".css":
				with open(filepath, "r", encoding="utf-8") as file:
					css = css + f"\n\n\n/* {filepath.name} */" + file.read()

		css = css.strip()

		namespaces = set(regex.findall(r"@namespace.+?;", css))

		css = regex.sub(r"\s*@(charset|namespace).+?;\s*", "\n", css).strip()

		if namespaces:
			css = "\n" + css

		for namespace in namespaces:
			css = namespace + "\n" + css

		css = "\t\t\t".join(css.splitlines(True))

		# Remove min-height from CSS since it doesn't really apply to the single page format.
		# It occurs at least in se.css
		css = regex.sub(r"\s*min-height: [^;]+?;", "", css)

		# Remove -epub-* CSS as it's invalid in a browser context
		css = regex.sub(r"\s*\-epub\-[^;]+?;", "", css)

		output_xhtml = f"<?xml version=\"1.0\" encoding=\"utf-8\"?><html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\" epub:prefix=\"z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0\" xml:lang=\"{language}\"><head><meta charset=\"utf-8\"/><title>{title}</title><style/></head><body></body></html>"
		output_dom = se.formatting.EasyXhtmlTree(output_xhtml)

		# Iterate over spine items in order and recompose them into our output
		for ref in self.metadata_dom.xpath("/package/spine/itemref/@idref"):
			filename = self.metadata_dom.xpath(f"/package/manifest/item[@id='{ref}']/@href")[0]

			with open(self.path / "src" / "epub" / filename, "r", encoding="utf-8") as file:
				dom = se.formatting.EasyXhtmlTree(file.read())

				for node in dom.xpath("/html/body/*"):
					self._recompose_xhtml(node, output_dom)

		# Add the ToC after the titlepage
		with open(self.path / "src" / "epub" / "toc.xhtml", "r", encoding="utf-8") as file:
			toc_dom = se.formatting.EasyXhtmlTree(file.read())
			titlepage_node = output_dom.xpath("//*[contains(concat(' ', @epub:type, ' '), ' titlepage ')]")[0]

			for node in toc_dom.xpath("//nav[1]"):
				titlepage_node.lxml_element.addnext(node.lxml_element)

		# Replace all <a href> links with internal links
		for link in output_dom.xpath("//a[contains(@href, '#')]"):
			link.set_attr("href", regex.sub(r".+(#.+)$", r"\1", link.get_attr("href")))

		# Replace all <a href> links to entire files
		for link in output_dom.xpath("//a[not(contains(@href, '#'))]"):
			href = link.get_attr("href")
			href = regex.sub(r".+/([^/]+)$", r"#\1", href)
			href = regex.sub(r"\.xhtml$", "", href)
			link.set_attr("href", href)

		# Get the output XHTML as a string
		output_xhtml = output_dom.to_string()
		output_xhtml = regex.sub(r"\"(\.\./)?text/(.+?)\.xhtml\"", "\"#\\2\"", output_xhtml)
		output_xhtml = regex.sub(r"\"(\.\./)?text/.+?\.xhtml#(.+?)\"", "\"#\\2\"", output_xhtml)

		# All done, clean the output
		output_xhtml = se.formatting.format_xhtml(output_xhtml)

		# Insert our CSS. We do this after `clean` because `clean` will escape > in the CSS
		output_xhtml = regex.sub(r"<style/>", "<style>\n\t\t\t" + css + "\t\t</style>", output_xhtml)

		if output_xhtml5:
			output_xhtml = output_xhtml.replace("\t\t<meta charset=\"utf-8\"/>\n", "")
			output_xhtml = output_xhtml.replace("\t\t<style/>\n", "")

			output_xhtml = regex.sub(r'xml:lang="([^"]+?)"', r'xml:lang="\1" lang="\1"', output_xhtml)

			# Re-add a doctype
			output_xhtml = output_xhtml.replace("<?xml version=\"1.0\" encoding=\"utf-8\"?>", "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<!DOCTYPE html>")
		else:
			# Remove xml declaration and re-add the doctype
			output_xhtml = regex.sub(r"<\?xml.+?\?>", "<!doctype html>", output_xhtml)
			output_xhtml = regex.sub(r" epub:prefix=\".+?\"", "", output_xhtml)

			# Make some replacements for HTML5 compatibility
			output_xhtml = output_xhtml.replace("epub:type", "data-epub-type")
			output_xhtml = output_xhtml.replace("epub|type", "data-epub-type")
			output_xhtml = output_xhtml.replace("<html", f"<html lang=\"{self.metadata_dom.xpath('/package/metadata/dc:language/text()')[0]}\"")
			output_xhtml = regex.sub(" xmlns.+?=\".+?\"", "", output_xhtml)
			output_xhtml = output_xhtml.replace("xml:lang", "lang")

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
		dest_images_directory = self.path / "src/epub/images"
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
		dest_images_directory = self.path / "src/epub/images"
		dest_cover_svg_filename = dest_images_directory / "cover.svg"

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
			with open(dest_cover_svg_filename, "r+", encoding="utf-8") as file:
				svg = regex.sub(r"xlink:href=\".*?cover\.jpg", "xlink:href=\"data:image/jpeg;base64," + source_cover_jpg_base64, file.read(), flags=regex.DOTALL)

				file.seek(0)
				file.write(svg)
				file.truncate()

			# For the cover we want to keep the path.title-box style, and add an additional
			# style to color our new paths white
			with open(dest_cover_svg_filename, "r+", encoding="utf-8") as file:
				svg = regex.sub(r"<style.+?</style>", "<style type=\"text/css\">\n\t\tpath{\n\t\t\tfill: #fff;\n\t\t}\n\n\t\t.title-box{\n\t\t\tfill: #000;\n\t\t\tfill-opacity: .75;\n\t\t}\n\t</style>", file.read(), flags=regex.DOTALL)

				file.seek(0)
				file.write(svg)
				file.truncate()

	def reorder_endnotes(self, target_endnote_number: int, step: int = 1) -> None:
		"""
		Reorder endnotes starting at target_endnote_number.

		INPUTS:
		target_endnote_number: The endnote to start reordering at
		step: 1 to increment or -1 to decrement

		OUTPUTS:
		None.
		"""

		increment = step == 1
		endnote_count = 0
		source_directory = self.path / "src"

		try:
			endnotes_filename = source_directory / "epub/text/endnotes.xhtml"
			with open(endnotes_filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()

				dom = se.easy_xml.EasyXhtmlTree(xhtml)

				endnote_count = len(dom.xpath("//li[starts-with(@id, 'note-')]"))

				if increment:
					note_range = range(endnote_count, target_endnote_number - 1, -1)
				else:
					note_range = range(target_endnote_number, endnote_count + 1, 1)

				for endnote_number in note_range:
					xhtml = xhtml.replace(f"id=\"note-{endnote_number}\"", f"id=\"note-{endnote_number + step}\"", 1)
					xhtml = xhtml.replace(f"#noteref-{endnote_number}\"", f"#noteref-{endnote_number + step}\"", 1)

				# There may be some links within the notes that refer to other endnotes.
				# These potentially need incrementing / decrementing too. This code assumes
				# a link that looks something like <a href="#note-1">note 1</a>.
				endnote_links = regex.findall(r"href=\"#note-(\d+)\"(.*?) (\d+)</a>", xhtml)
				for link in endnote_links:
					link_number = int(link[0])
					if (link_number < target_endnote_number and increment) or (link_number > target_endnote_number and not increment):
						continue
					xhtml = xhtml.replace(f"href=\"#note-{link[0]}\"{link[1]} {link[0]}</a>", "href=\"#note-{0}\"{1} {0}</a>".format(link_number + step, link[1]))

				file.seek(0)
				file.write(xhtml)
				file.truncate()

		except Exception as ex:
			raise se.InvalidSeEbookException(f"Couldn’t open endnotes file: [path][link=file://{endnotes_filename}]{endnotes_filename}[/][/].") from ex

		with concurrent.futures.ProcessPoolExecutor() as executor:
			for root, _, filenames in os.walk(source_directory):
				for filename in fnmatch.filter(filenames, "*.xhtml"):
					# Skip endnotes.xhtml since we already processed it
					if filename == "endnotes.xhtml":
						continue

					executor.submit(_process_endnotes_in_file, filename, Path(root), note_range, step)

	def set_release_timestamp(self) -> None:
		"""
		If this ebook has not yet been released, set the first release timestamp in the metadata file.
		"""

		if "<dc:date>1900-01-01T00:00:00Z</dc:date>" in self.metadata_xml:
			now = datetime.datetime.utcnow()
			now_iso = regex.sub(r"\.[0-9]+$", "", now.isoformat()) + "Z"
			now_iso = regex.sub(r"\+.+?Z$", "Z", now_iso)
			now_friendly = f"{now:%B %e, %Y, %l:%M <abbr class=\"time eoc\">%p</abbr>}"
			now_friendly = regex.sub(r"\s+", " ", now_friendly).replace("AM", "a.m.").replace("PM", "p.m.").replace(" <abbr", " <abbr")

			self.metadata_xml = regex.sub(r"<dc:date>[^<]+?</dc:date>", f"<dc:date>{now_iso}</dc:date>", self.metadata_xml)
			self.metadata_xml = regex.sub(r"<meta property=\"dcterms:modified\">[^<]+?</meta>", f"<meta property=\"dcterms:modified\">{now_iso}</meta>", self.metadata_xml)

			with open(self.metadata_file_path, "w", encoding="utf-8") as file:
				file.seek(0)
				file.write(self.metadata_xml)
				file.truncate()

			self._metadata_dom = None

			with open(self.path / "src" / "epub" / "text" / "colophon.xhtml", "r+", encoding="utf-8") as file:
				xhtml = file.read()
				xhtml = xhtml.replace("<b>January 1, 1900, 12:00 <abbr class=\"time eoc\">a.m.</abbr></b>", f"<b>{now_friendly}</b>")

				file.seek(0)
				file.write(xhtml)
				file.truncate()

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

		for filename in se.get_target_filenames([self.path], (".xhtml",)):
			with open(filename, "r", encoding="utf-8") as file:
				text += " " + file.read()

		self.metadata_xml = regex.sub(r"<meta property=\"se:reading-ease\.flesch\">[^<]*</meta>", f"<meta property=\"se:reading-ease.flesch\">{se.formatting.get_flesch_reading_ease(text)}</meta>", self.metadata_xml)

		with open(self.metadata_file_path, "w", encoding="utf-8") as file:
			file.seek(0)
			file.write(self.metadata_xml)
			file.truncate()

	def update_word_count(self) -> None:
		"""
		Calculate a new word count for this ebook and update the metadata file.
		Ignores SE boilerplate files like the imprint, as well as any endnotes.

		INPUTS
		None

		OUTPUTS
		None.
		"""

		word_count = 0

		for filename in se.get_target_filenames([self.path], (".xhtml",)):
			if filename.name == "endnotes.xhtml":
				continue

			with open(filename, "r", encoding="utf-8") as file:
				word_count += se.formatting.get_word_count(file.read())

		self.metadata_xml = regex.sub(r"<meta property=\"se:word-count\">[^<]*</meta>", f"<meta property=\"se:word-count\">{word_count}</meta>", self.metadata_xml)

		with open(self.metadata_file_path, "r+", encoding="utf-8") as file:
			file.seek(0)
			file.write(self.metadata_xml)
			file.truncate()

	def generate_manifest(self) -> str:
		"""
		Return the <manifest> element for this ebook as an XML string.

		INPUTS
		None

		OUTPUTS
		An XML fragment string representing the manifest.
		"""

		manifest = []

		# Add CSS
		for _, _, filenames in os.walk(self.path / "src" / "epub" / "css"):
			for filename in filenames:
				manifest.append(f"<item href=\"css/{filename}\" id=\"{filename}\" media-type=\"text/css\"/>")

		# Add fonts
		for _, _, filenames in os.walk(self.path / "src" / "epub" / "fonts"):
			for filename in filenames:
				manifest.append(f"<item href=\"fonts/{filename}\" id=\"{filename}\" media-type=\"application/vnd.ms-opentype\"/>")

		# Add images
		for _, _, filenames in os.walk(self.path / "src" / "epub" /  "images"):
			for filename in filenames:
				media_type = "image/jpeg"
				properties = ""

				if filename.endswith(".svg"):
					media_type = "image/svg+xml"

				if filename.endswith(".png"):
					media_type = "image/png"

				if filename == "cover.svg":
					properties = " properties=\"cover-image\""

				manifest.append(f"<item href=\"images/{filename}\" id=\"{filename}\" media-type=\"{media_type}\"{properties}/>")

		# Add XHTML files
		for root, _, filenames in os.walk(self.path / "src" / "epub" / "text"):
			for filename in filenames:
				# Skip dotfiles, because .DS_Store might be binary and then we'd crash when we try to read it below
				if filename.startswith("."):
					continue

				properties = "properties=\""

				with open(Path(root) / filename, "r", encoding="utf-8") as file:
					file_contents = file.read()

					if regex.search(r"epub:type=\"[^\"]*?glossary[^\"]*?\"", file_contents):
						properties += "glossary "

					if "http://www.w3.org/1998/Math/MathML" in file_contents:
						properties += "mathml "

					if ".svg" in file_contents:
						properties += "svg "

				properties = " " + properties.strip() + "\""

				if properties == " properties=\"\"":
					properties = ""

				manifest.append(f"<item href=\"text/{filename}\" id=\"{filename}\" media-type=\"application/xhtml+xml\"{properties}/>")

		# Do we have a glossary search key map?
		if Path(self.path / "src" / "epub" / "glossary-search-key-map.xml").is_file():
			manifest.append("<item href=\"glossary-search-key-map.xml\" id=\"glossary-search-key-map.xml\" media-type=\"application/vnd.epub.search-key-map+xml\" properties=\"glossary search-key-map\"/>")

		manifest = natsorted(manifest)

		manifest_xhtml = "<manifest>\n\t<item href=\"toc.xhtml\" id=\"toc.xhtml\" media-type=\"application/xhtml+xml\" properties=\"nav\"/>\n"

		for line in manifest:
			manifest_xhtml = manifest_xhtml + "\t" + line + "\n"

		manifest_xhtml = manifest_xhtml + "</manifest>"

		return manifest_xhtml

	def generate_spine(self) -> str:
		"""
		Return the <spine> element of this ebook as an XML string, with a best guess as to the correct order. Manual review is required.

		INPUTS
		None

		OUTPUTS
		An XML fragment string representing the spine.
		"""

		excluded_files = se.IGNORED_FILENAMES + ["dedication.xhtml", "introduction.xhtml", "foreword.xhtml", "preface.xhtml", "epigraph.xhtml", "afterword.xhtml", "endnotes.xhtml"]
		spine = ["<itemref idref=\"titlepage.xhtml\"/>", "<itemref idref=\"imprint.xhtml\"/>"]

		filenames = natsorted(os.listdir(self.path / "src" / "epub" / "text"))

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

		if "prologue.xhtml" in filenames:
			spine.append("<itemref idref=\"prologue.xhtml\"/>")

		for filename in filenames:
			if filename not in excluded_files:
				spine.append(f"<itemref idref=\"{filename}\"/>")

		if "afterword.xhtml" in filenames:
			spine.append("<itemref idref=\"afterword.xhtml\"/>")

		if "endnotes.xhtml" in filenames:
			spine.append("<itemref idref=\"endnotes.xhtml\"/>")

		if "loi.xhtml" in filenames:
			spine.append("<itemref idref=\"loi.xhtml\"/>")

		if "colophon.xhtml" in filenames:
			spine.append("<itemref idref=\"colophon.xhtml\"/>")

		if "uncopyright.xhtml" in filenames:
			spine.append("<itemref idref=\"uncopyright.xhtml\"/>")

		spine_xhtml = "<spine>\n"
		for line in spine:
			spine_xhtml = spine_xhtml + "\t" + line + "\n"

		spine_xhtml = spine_xhtml + "</spine>"

		return spine_xhtml

	def get_content_files(self) -> list:
		"""
		Reads the spine from content.opf to obtain a list of content files, in the order wanted for the ToC.
		It assumes this has already been manually ordered by the producer.

		INPUTS:
		None

		OUTPUTS:
		list of content files in the order given in the spine in content.opf
		"""

		return self.metadata_dom.xpath("/package/spine/itemref/@idref")

	def get_work_type(self) -> str:
		"""
		Returns either "fiction" or "non-fiction", based on analysis of se:subjects in content.opf

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
		Returns the title of the book from content.opf, which we assume has already been correctly completed.

		INPUTS:
		None

		OUTPUTS:
		Either the title of the book or the default WORKING_TITLE
		"""

		match = regex.search(r"<dc:title(?:.*?)>(.*?)</dc:title>", self.metadata_xml)
		if match:
			dc_title = match.group(1)
		else:
			dc_title = "WORK_TITLE"  # default
		return dc_title

	def lint(self, skip_lint_ignore: bool) -> list:
		"""
		The lint() function is very big so for readability and maintainability
		it's broken out to a separate file. Strictly speaking that file can be inlined
		into this class.
		"""

		from se.se_epub_lint import lint # pylint: disable=import-outside-toplevel

		return lint(self, skip_lint_ignore)

	def build(self, run_epubcheck: bool, build_kobo: bool, build_kindle: bool, output_directory: Path, proof: bool, build_covers: bool) -> None:
		"""
		The build() function is very big so for readability and maintainability
		it's broken out to a separate file. Strictly speaking that file can be inlined
		into this class.
		"""

		from se.se_epub_build import build # pylint: disable=import-outside-toplevel

		build(self, run_epubcheck, build_kobo, build_kindle, output_directory, proof, build_covers)

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

	def generate_endnotes(self) -> Tuple[int, int]:
		"""
		Read the epub spine to regenerate all endnotes in order of appearance, starting from 1.
		Changes are written to disk.

		Returns a tuple of (found_endnote_count, changed_endnote_count)
		"""

		processed = 0
		current_note_number = 1
		notes_changed = 0
		change_list = []

		for file_name in self.get_content_files():
			if file_name in ["titlepage.xhtml", "colophon.xhtml", "uncopyright.xhtml", "imprint.xhtml", "halftitle.xhtml", "endnotes.xhtml"]:
				continue

			processed += 1

			file_path = self.path / "src/epub/text" / file_name
			try:
				with open(file_path) as file:
					dom = se.easy_xml.EasyXhtmlTree(file.read())
			except Exception as ex:
				raise se.InvalidFileException(f"Couldn’t open file: [path][link=file://{file_path}]{file_path}[/][/].") from ex

			needs_rewrite = False
			for link in dom.xpath("/html/body//a[contains(@epub:type, 'noteref')]"):
				old_anchor = ""
				href = link.get_attr("href") or ""
				if href:
					# Extract just the anchor from a URL (ie, what follows a hash symbol)
					hash_position = href.find("#") + 1  # we want the characters AFTER the hash
					if hash_position > 0:
						old_anchor = href[hash_position:]

				new_anchor = f"note-{current_note_number:d}"
				if new_anchor != old_anchor:
					change_list.append(f"Changed {old_anchor} to {new_anchor} in {file_name}")
					notes_changed += 1
					# Update the link in the dom
					link.set_attr("href", f"endnotes.xhtml#{new_anchor}")
					link.set_attr("id", f"noteref-{current_note_number:d}")
					link.lxml_element.text = str(current_note_number)
					needs_rewrite = True

				# Now try to find this in endnotes
				match_old = lambda x, old=old_anchor: x.anchor == old
				matches = list(filter(match_old, self.endnotes))
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
				current_note_number += 1

			# If we need to write back the body text file
			if needs_rewrite:
				new_file = open(file_path, "w")
				new_file.write(se.formatting.format_xhtml(dom.to_string()))
				new_file.close()

		if processed == 0:
			raise se.InvalidInputException("No files processed. Did you update the manifest and order the spine?")

		if notes_changed > 0:
			# Now we need to recreate the endnotes file
			for ol_tag in self._endnotes_dom.xpath("/html/body/section[contains(@epub:type, 'endnotes')]/ol[1]"):
				for node in ol_tag.xpath("./li[contains(@epub:type, 'endnote')]"):
					node.remove()

				self.endnotes.sort(key=lambda endnote: endnote.number)

				for endnote in self.endnotes:
					if endnote.matched:
						endnote.node.set_attr("id", f"note-{endnote.number}")

						for node in endnote.node.xpath(".//a[contains(@epub:type, 'backlink')]"):
							node.set_attr("href", f"{endnote.source_file}#noteref-{endnote.number}")

						ol_tag.append(endnote.node)

			with open(self.path / "src" / "epub" / "text" / "endnotes.xhtml", "w") as file:
				file.write(se.formatting.format_xhtml(self._endnotes_dom.to_string()))

		return (current_note_number - 1, notes_changed)
