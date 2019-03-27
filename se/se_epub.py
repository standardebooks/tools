#!/usr/bin/env python3
"""
Defines the SeEpub class, the master class for representing and operating on
Standard Ebooks epub3 files.
"""

import os
import html
import tempfile
import errno
import shutil
import fnmatch
import datetime
import concurrent.futures
import base64
import subprocess
import regex
import git
from bs4 import Tag, BeautifulSoup
import se
import se.formatting
import se.easy_xml
import se.images

def _process_endnotes_in_file(filename: str, root: str, note_range: range, step: int) -> None:
	"""
	Helper function for reordering endnotes.

	This has to be outside of the class to be able to be called by `executor`.
	"""

	with open(os.path.join(root, filename), "r+", encoding="utf-8") as file:
		xhtml = file.read()
		processed_xhtml = xhtml
		processed_xhtml_is_modified = False

		for endnote_number in note_range:
			# If we’ve already changed some notes and can’t find the next then we don’t need to continue searching
			if not "id=\"noteref-{}\"".format(endnote_number) in processed_xhtml and processed_xhtml_is_modified:
				break
			processed_xhtml = processed_xhtml.replace("id=\"noteref-{}\"".format(endnote_number), "id=\"noteref-{}\"".format(endnote_number + step), 1)
			processed_xhtml = processed_xhtml.replace("#note-{}\"".format(endnote_number), "#note-{}\"".format(endnote_number + step), 1)
			processed_xhtml = processed_xhtml.replace(">{}</a>".format(endnote_number), ">{}</a>".format(endnote_number + step), 1)
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

class SeEpub:
	"""
	An object representing an SE epub file.

	An SE epub can have various operations performed on it, including recomposing and linting.
	"""

	directory = ""
	metadata_xhtml = None
	_metadata_tree = None
	_generated_identifier = None
	_generated_github_repo_url = None
	_last_commit = None # GitCommit object

	def __init__(self, epub_root_directory: str):
		if not os.path.isdir(epub_root_directory):
			raise se.InvalidSeEbookException("Not a directory: {}".format(epub_root_directory))

		self.directory = os.path.abspath(epub_root_directory)

		try:
			with open(os.path.join(self.directory, "src", "epub", "content.opf"), "r+", encoding="utf-8") as file:
				self.metadata_xhtml = file.read()

			if "<dc:identifier id=\"uid\">url:https://standardebooks.org/ebooks/" not in self.metadata_xhtml:
				raise se.InvalidSeEbookException
		except:
			raise se.InvalidSeEbookException("Not a Standard Ebooks source directory: {}".format(self.directory))

	@property
	def last_commit(self) -> GitCommit:
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

				git_command = git.cmd.Git(self.directory)
				output = git_command.show("-s", "--format=%h %ct", "HEAD").split()

				self._last_commit = GitCommit(output[0], datetime.datetime.fromtimestamp(int(output[1]), datetime.timezone.utc))
			except Exception:
				self._last_commit = None

		return self._last_commit

	@property
	def generated_identifier(self) -> str:
		"""
		Accessor
		"""

		if not self._generated_identifier:
			self._generated_identifier = self._generate_identifier()

		return self._generated_identifier

	@property
	def generated_github_repo_url(self) -> str:
		"""
		Accessor
		"""

		if not self._generated_github_repo_url:
			self._generated_github_repo_url = self._generate_github_repo_url()

		return self._generated_github_repo_url

	@staticmethod
	def _new_bs4_tag(section: Tag, output_soup: BeautifulSoup) -> Tag:
		"""
		Helper function used in self.recompose()
		Create a new BS4 tag given the current section.

		INPUTS
		section: A BS4 tag
		output_soup: A BS4 object representing the entire soup

		OUTPUTS
		A new BS4 tag.
		"""

		tag = output_soup.new_tag(section.name)
		for name, value in section.attrs.items():
			tag.attrs[name] = value

		return tag

	def _get_metadata_tree(self) -> se.easy_xml.EasyXmlTree:
		"""
		Accessor
		"""

		if self._metadata_tree is None:
			try:
				self._metadata_tree = se.easy_xml.EasyXmlTree(self.metadata_xhtml)
			except Exception as ex:
				raise se.InvalidSeEbookException("Couldn’t parse content.opf: {}".format(ex))

		return self._metadata_tree

	def _recompose_xhtml(self, section: Tag, output_soup: BeautifulSoup) -> None:
		"""
		Helper function used in self.recompose()
		Recursive function for recomposing a series of XHTML files into a single XHTML file.

		INPUTS
		section: A BS4 tag to inspect
		output_soup: A BS4 object representing the entire soup

		OUTPUTS
		None
		"""

		# Quick sanity check before we begin
		if "id" not in section.attrs or (section.parent.name.lower() != "body" and "id" not in section.parent.attrs):
			raise se.InvalidXhtmlException("Section without ID attribute.")

		# Try to find our parent tag in the output, by ID.
		# If it's not in the output, then append it to the tag's closest parent by ID (or <body>), then iterate over its children and do the same.
		existing_section = output_soup.select("#" + section["id"])
		if not existing_section:
			if section.parent.name.lower() == "body":
				output_soup.body.append(self._new_bs4_tag(section, output_soup))
			else:
				output_soup.select("#" + section.parent["id"])[0].append(self._new_bs4_tag(section, output_soup))

			existing_section = output_soup.select("#" + section["id"])

		for child in section.children:
			if not isinstance(child, str):
				tag_name = child.name.lower()
				if tag_name == "section" or tag_name == "article":
					self._recompose_xhtml(child, output_soup)
				else:
					existing_section[0].append(child)

	def _generate_github_repo_url(self) -> str:
		"""
		Generate a GitHub repository URL based on the *generated* SE identifier,
		*not* the SE identifier in the metadata file.

		INPUTS
		None

		OUTPUTS
		A string representing the GitHub repository URL (capped at maximum 100 characters).
		"""

		return "https://github.com/standardebooks/" + self.generated_identifier.replace("url:https://standardebooks.org/ebooks/", "").replace("/", "_")[0:100]

	def _generate_identifier(self) -> str:
		"""
		Generate an SE identifer based on the metadata in content.opf

		To access this value, use the property self.generated_identifier.

		INPUTS
		None

		OUTPUTS
		A string representing the SE identifier.
		"""

		metadata_tree = self._get_metadata_tree()

		# Add authors
		identifier = "url:https://standardebooks.org/ebooks/"
		authors = []
		for author in metadata_tree.xpath("//dc:creator"):
			authors.append(author.inner_html())
			identifier += se.formatting.make_url_safe(author.inner_html()) + "_"

		identifier = identifier.strip("_") + "/"

		# Add title
		for title in metadata_tree.xpath("//dc:title[@id=\"title\"]"):
			identifier += se.formatting.make_url_safe(title.inner_html()) + "/"

		# For contributors, we add both translators and illustrators.
		# However, we may not include specific translators or illustrators in certain cases, namely
		# if *some* contributors have a `display-seq` property, and others do not.
		# According to the epub spec, if that is the case, we should only add those that *do* have the attribute.
		# By SE convention, any contributor with `display-seq == 0` will be excluded from the identifier string.
		translators = []
		illustrators = []
		translators_have_display_seq = False
		illustrators_have_display_seq = False
		for role in metadata_tree.xpath("//opf:meta[@property=\"role\"]"):
			contributor_id = role.attribute("refines").lstrip("#")
			contributor_element = metadata_tree.xpath("//dc:contributor[@id=\"" + contributor_id + "\"]")
			if contributor_element:
				contributor = {"name": contributor_element[0].inner_html(), "include": True, "display_seq": None}
				display_seq = metadata_tree.xpath("//opf:meta[@property=\"display-seq\"][@refines=\"#" + contributor_id + "\"]")

				if display_seq and int(display_seq[0].inner_html()) == 0:
					contributor["include"] = False
					display_seq = None

				if role.inner_html() == "trl":
					if display_seq:
						contributor["display_seq"] = display_seq[0]
						translators_have_display_seq = True

					translators.append(contributor)

				if role.inner_html() == "ill":
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

		return identifier

	def recompose(self) -> str:
		"""
		Iterate over the XHTML files in this epub and "recompose" them into a single HTML5 string representing this ebook.

		INPUTS
		None

		OUTPUTS
		A string of HTML5 representing the entire recomposed ebook.
		"""

		# Get the ordered list of spine items
		with open(os.path.join(self.directory, "src", "epub", "content.opf"), "r", encoding="utf-8") as file:
			metadata_soup = BeautifulSoup(file.read(), "lxml")

		# Get some header data: title, core and local css
		title = html.escape(metadata_soup.find("dc:title").contents[0])
		css = ""
		with open(os.path.join(self.directory, "src", "epub", "css", "core.css"), "r", encoding="utf-8") as file:
			css = regex.sub(r"@.+?;", "", file.read()).strip()

		with open(os.path.join(self.directory, "src", "epub", "css", "local.css"), "r", encoding="utf-8") as file:
			css = css + "\n\n\n/* local.css */" + regex.sub(r"@.+?;", "", file.read())
			css = "\t\t\t".join(css.splitlines(True))

		output_xhtml = "<?xml version=\"1.0\" encoding=\"utf-8\"?><html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\" epub:prefix=\"z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0\"><head><meta charset=\"utf-8\"/><title>" + title + "</title><style/></head><body></body></html>"
		output_soup = BeautifulSoup(output_xhtml, "lxml")

		# Iterate over spine items in order and recompose them into our output
		for element in metadata_soup.select("spine itemref"):
			filename = metadata_soup.select("item#" + element["idref"])[0]["href"]

			with open(os.path.join(self.directory, "src", "epub", filename), "r", encoding="utf-8") as file:
				xhtml_soup = BeautifulSoup(file.read(), "lxml")

				for child in xhtml_soup.select("body > *"):
					self._recompose_xhtml(child, output_soup)

		# Add the ToC after the titlepage
		with open(os.path.join(self.directory, "src", "epub", "toc.xhtml"), "r", encoding="utf-8") as file:
			toc_soup = BeautifulSoup(file.read(), "lxml")
			output_soup.select("#titlepage")[0].insert_after(toc_soup.find("nav"))

		# Get the output XHTML as a string
		output_xhtml = str(output_soup)
		output_xhtml = regex.sub(r"\"(\.\./)?text/(.+?)\.xhtml\"", "\"#\\2\"", output_xhtml)
		output_xhtml = regex.sub(r"\"(\.\./)?text/.+?\.xhtml#(.+?)\"", "\"#\\2\"", output_xhtml)

		# Replace SVG images hrefs with inline SVG
		for match in regex.findall(r"src=\"../images/(.+?)\.svg\"", output_xhtml):
			with open(os.path.join(self.directory, "src", "epub", "images", match + ".svg"), "r", encoding="utf-8") as file:
				svg = file.read()

				# Remove XML declaration
				svg = regex.sub(r"<\?xml.+?\?>", "", svg)

				output_xhtml = regex.sub(r"<img.+?src=\"\.\./images/{}\.svg\".*?/>".format(match), svg, output_xhtml)

		with tempfile.NamedTemporaryFile(mode="w+", delete=False) as file:
			file.write(output_xhtml)
			file_name = file.name
			file_name_xhtml = file_name + ".xhtml"

		os.rename(file_name, file_name_xhtml)

		# All done, clean the output
		se.formatting.format_xhtml_file(file_name_xhtml, False, file_name_xhtml.endswith("content.opf"), file_name_xhtml.endswith("endnotes.xhtml"))

		with open(file_name_xhtml, "r", encoding="utf-8") as file:
			xhtml = file.read()

			# Remove xml declaration and re-add the doctype
			xhtml = regex.sub(r"<\?xml.+?\?>", "<!doctype html>", xhtml)
			xhtml = regex.sub(r" epub:prefix=\".+?\"", "", xhtml)

			# Insert our CSS. We do this after `clean` because `clean` will escape > in the CSS
			xhtml = regex.sub(r"<style/>", "<style>\n\t\t\t" + css + "\t\t</style>", xhtml)

			# Make some replacements for HTML5 compatibility
			xhtml = xhtml.replace("epub:type", "data-epub-type")
			xhtml = xhtml.replace("epub|type", "data-epub-type")
			xhtml = xhtml.replace("xml:lang", "lang")
			xhtml = xhtml.replace("<html", "<html lang=\"{}\"".format(metadata_soup.find("dc:language").string))
			xhtml = regex.sub(" xmlns.+?=\".+?\"", "", xhtml)

		os.remove(file_name_xhtml)

		return xhtml

	def generate_titlepage_svg(self) -> None:
		"""
		Generate a distributable titlepage SVG in ./src/epub/images/ based on the titlepage file in ./images/

		INPUTS
		None

		OUTPUTS
		None.
		"""

		inkscape_path = shutil.which("inkscape")

		if inkscape_path is None:
			raise se.MissingDependencyException("Couldn’t locate Inkscape. Is it installed?")

		source_images_directory = os.path.join(self.directory, "images")
		source_titlepage_svg_filename = os.path.join(source_images_directory, "titlepage.svg")
		dest_images_directory = os.path.join(self.directory, "src", "epub", "images")
		dest_titlepage_svg_filename = os.path.join(dest_images_directory, "titlepage.svg")

		if os.path.isfile(source_titlepage_svg_filename):
			# Convert text to paths
			# inkscape adds a ton of crap to the SVG and we clean that crap a little later
			subprocess.run([inkscape_path, source_titlepage_svg_filename, "--without-gui", "--export-text-to-path", "--export-plain-svg", dest_titlepage_svg_filename])

			se.images.format_inkscape_svg(dest_titlepage_svg_filename)

			# For the titlepage we want to remove all styles, since they are not used anymore
			with open(dest_titlepage_svg_filename, "r+", encoding="utf-8") as file:
				svg = regex.sub(r"<style.+?</style>[\n\t]+", "", file.read(), flags=regex.DOTALL)

				file.seek(0)
				file.write(svg)
				file.truncate()

	def generate_cover_svg(self) -> None:
		"""
		Generate a distributable cover SVG in ./src/epub/images/ based on the cover file in ./images/

		INPUTS
		None

		OUTPUTS
		None.
		"""

		inkscape_path = shutil.which("inkscape")

		if inkscape_path is None:
			raise se.MissingDependencyException("Couldn’t locate Inkscape. Is it installed?")

		source_images_directory = os.path.join(self.directory, "images")
		source_cover_jpg_filename = os.path.join(source_images_directory, "cover.jpg")
		source_cover_svg_filename = os.path.join(source_images_directory, "cover.svg")
		dest_images_directory = os.path.join(self.directory, "src", "epub", "images")
		dest_cover_svg_filename = os.path.join(dest_images_directory, "cover.svg")

		# Create output directory if it doesn't exist
		try:
			os.makedirs(dest_images_directory)
		except OSError as ex:
			if ex.errno != errno.EEXIST:
				raise ex

		# Remove useless metadata from cover source files
		for root, _, filenames in os.walk(source_images_directory):
			for filename in fnmatch.filter(filenames, "cover.source.*"):
				se.images.remove_image_metadata(os.path.join(root, filename))

		if os.path.isfile(source_cover_jpg_filename):
			se.images.remove_image_metadata(source_cover_jpg_filename)

			if os.path.isfile(source_cover_svg_filename):
				# base64 encode cover.jpg
				with open(source_cover_jpg_filename, "rb") as file:
					source_cover_jpg_base64 = base64.b64encode(file.read()).decode()

				# Convert text to paths
				# Inkscape adds a ton of crap to the SVG and we clean that crap a little later
				subprocess.run([inkscape_path, source_cover_svg_filename, "--without-gui", "--export-text-to-path", "--export-plain-svg", dest_cover_svg_filename])

				# Embed cover.jpg
				with open(dest_cover_svg_filename, "r+", encoding="utf-8") as file:
					svg = regex.sub(r"xlink:href=\".*?cover\.jpg", "xlink:href=\"data:image/jpeg;base64," + source_cover_jpg_base64, file.read(), flags=regex.DOTALL)

					file.seek(0)
					file.write(svg)
					file.truncate()

				se.images.format_inkscape_svg(dest_cover_svg_filename)

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
		source_directory = os.path.join(self.directory, "src")

		try:
			endnotes_filename = os.path.join(source_directory, "epub", "text", "endnotes.xhtml")
			with open(endnotes_filename, "r+", encoding="utf-8") as file:
				xhtml = file.read()
				soup = BeautifulSoup(xhtml, "lxml")

				endnote_count = len(soup.select("li[id^=note-]"))

				if increment:
					note_range = range(endnote_count, target_endnote_number - 1, -1)
				else:
					note_range = range(target_endnote_number, endnote_count + 1, 1)

				for endnote_number in note_range:
					xhtml = xhtml.replace("id=\"note-{}\"".format(endnote_number), "id=\"note-{}\"".format(endnote_number + step), 1)
					xhtml = xhtml.replace("#noteref-{}\"".format(endnote_number), "#noteref-{}\"".format(endnote_number + step), 1)

				# There may be some links within the notes that refer to other endnotes.
				# These potentially need incrementing / decrementing too. This code assumes
				# a link that looks something like <a href="#note-1">note 1</a>.
				endnote_links = regex.findall(r"href=\"#note-(\d+)\"(.*?) (\d+)</a>", xhtml)
				for link in endnote_links:
					link_number = int(link[0])
					if (link_number < target_endnote_number and increment) or (link_number > target_endnote_number and not increment):
						continue
					xhtml = xhtml.replace("href=\"#note-{0}\"{1} {0}</a>".format(link[0], link[1]), "href=\"#note-{0}\"{1} {0}</a>".format(link_number + step, link[1]))

				file.seek(0)
				file.write(xhtml)
				file.truncate()

		except Exception:
			raise se.InvalidSeEbookException("Couldn’t open endnotes file: {}".format(endnotes_filename))

		with concurrent.futures.ProcessPoolExecutor() as executor:
			for root, _, filenames in os.walk(source_directory):
				for filename in fnmatch.filter(filenames, "*.xhtml"):
					# Skip endnotes.xhtml since we already processed it
					if filename == "endnotes.xhtml":
						continue

					executor.submit(_process_endnotes_in_file, filename, root, note_range, step)

	def set_release_timestamp(self) -> None:
		"""
		If this ebook has not yet been released, set the first release timestamp in content.opf.
		"""

		if "<dc:date>1900-01-01T00:00:00Z</dc:date>" in self.metadata_xhtml:
			now = datetime.datetime.utcnow()
			now_iso = regex.sub(r"\.[0-9]+$", "", now.isoformat()) + "Z"
			now_iso = regex.sub(r"\+.+?Z$", "Z", now_iso)
			now_friendly = "{0:%B %e, %Y, %l:%M <abbr class=\"time eoc\">%p</abbr>}".format(now)
			now_friendly = regex.sub(r"\s+", " ", now_friendly).replace("AM", "a.m.").replace("PM", "p.m.").replace(" <abbr", " <abbr")

			self.metadata_xhtml = regex.sub(r"<dc:date>[^<]+?</dc:date>", "<dc:date>{}</dc:date>".format(now_iso), self.metadata_xhtml)
			self.metadata_xhtml = regex.sub(r"<meta property=\"dcterms:modified\">[^<]+?</meta>", "<meta property=\"dcterms:modified\">{}</meta>".format(now_iso), self.metadata_xhtml)

			with open(os.path.join(self.directory, "src", "epub", "content.opf"), "w", encoding="utf-8") as file:
				file.seek(0)
				file.write(self.metadata_xhtml)
				file.truncate()

			self._metadata_tree = None

			with open(os.path.join(self.directory, "src", "epub", "text", "colophon.xhtml"), "r+", encoding="utf-8") as file:
				xhtml = file.read()
				xhtml = xhtml.replace("<b>January 1, 1900, 12:00 <abbr class=\"time eoc\">a.m.</abbr></b>", "<b>{}</b>".format(now_friendly))

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

		for filename in se.get_target_filenames([self.directory], (".xhtml")):
			with open(filename, "r", encoding="utf-8") as file:
				text += " " + file.read()

		self.metadata_xhtml = regex.sub(r"<meta property=\"se:reading-ease\.flesch\">[^<]*</meta>", "<meta property=\"se:reading-ease.flesch\">{}</meta>".format(se.formatting.get_flesch_reading_ease(text)), self.metadata_xhtml)

		with open(os.path.join(self.directory, "src", "epub", "content.opf"), "w", encoding="utf-8") as file:
			file.seek(0)
			file.write(self.metadata_xhtml)
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

		for filename in se.get_target_filenames([self.directory], (".xhtml")):
			if filename.endswith("endnotes.xhtml"):
				continue

			with open(filename, "r", encoding="utf-8") as file:
				word_count += se.formatting.get_word_count(file.read())

		self.metadata_xhtml = regex.sub(r"<meta property=\"se:word-count\">[^<]*</meta>", "<meta property=\"se:word-count\">{}</meta>".format(word_count), self.metadata_xhtml)

		with open(os.path.join(self.directory, "src", "epub", "content.opf"), "r+", encoding="utf-8") as file:
			file.seek(0)
			file.write(self.metadata_xhtml)
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
				# Skip dotfiles, because .DS_Store might be binary and then we'd crash when we try to read it below
				if filename.startswith("."):
					continue

				properties = "properties=\""

				with open(os.path.join(root, filename), "r", encoding="utf-8") as file:
					file_contents = file.read()
					if "http://www.w3.org/1998/Math/MathML" in file_contents:
						properties += "mathml "
					if ".svg" in file_contents:
						properties += "svg "

				properties = " " + properties.strip() + "\""

				if properties == " properties=\"\"":
					properties = ""

				manifest.append("<item href=\"text/{}\" id=\"{}\" media-type=\"application/xhtml+xml\"{}/>".format(filename, filename, properties))

		manifest = se.natural_sort(manifest)

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

	def lint(self) -> list:
		"""
		The lint() function is very big so for readability and maintainability
		it's broken out to a separate file. Strictly speaking that file can be inlined
		into this class.
		"""

		from se.se_epub_lint import lint

		return lint(self, self.metadata_xhtml)

	def build(self, run_epubcheck, build_kobo, build_kindle, output_directory, proof, build_covers, verbose):
		"""
		The build() function is very big so for readability and maintainability
		it's broken out to a separate file. Strictly speaking that file can be inlined
		into this class.
		"""

		from se.se_epub_build import build

		build(self, self.metadata_xhtml, self._get_metadata_tree(), run_epubcheck, build_kobo, build_kindle, output_directory, proof, build_covers, verbose)

	def generate_toc(self) -> str:
		"""
		The generate_toc() function is very big so for readability and maintainability
		it's broken out to a separate file. Strictly speaking that file can be inlined
		into this class.
		"""

		from se.se_epub_generate_toc import generate_toc

		return generate_toc(self)
