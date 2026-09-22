#!/usr/bin/env python3
"""
Defines the SeEpub class, the master class for representing and operating on Standard Ebooks epub3 files.
"""

import base64
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from math import floor
import os
from pathlib import Path
import importlib.resources
from unicodedata import normalize
from urllib.parse import quote as url_quote, unquote, urlsplit

from git import cmd
from git.repo import Repo
from lxml import etree
from natsort import natsorted
import regex
import rich.markup
import tinycss2
from tinycss2.ast import AtRule, Node, ParseError, QualifiedRule

import se
import se.css
import se.easy_xml
from se.easy_xml import EasyXmlElement, EasyXmlTree
import se.formatting
import se.images
from se.se_epub_lint import LintMessage

@dataclass
class SplitFile:
	"""
	A section of a larger file which has been split during the build process.
	"""

	filename: str
	id: str
	title: str
	descendant_id_attrs: list[str]

@dataclass
class MetadataContributor:
	"""
	A contributor as listed in the metadata.
	"""

	name: str
	include: bool # Is this contributor included in the S.E. identifier?
	display_seq: int|None = None

@dataclass
class ContributorsBlock:
	"""
	A block of related contributors with a descriptor, like `translated by` and [`Alymer Maude`, `Louise Maude`].
	"""

	descriptor: str # Like `Translated by`.
	names: list[str] # Like [`Alymer Maude`, `Louise Maude`].

@dataclass
class GitCommit:
	"""
	Object used to represent the last Git commit.
	"""

	sha: str
	short_sha: str
	timestamp: datetime

@dataclass
class Endnote:
	"""
	Class to hold information on endnotes.
	"""

	node: EasyXmlElement | None = None
	number = 0
	anchor = ""
	contents = []  # The strings and tags inside an `<li>` element.
	back_link = ""
	source_file = ""
	matched = False

@dataclass
class EndnoteChange:
	"""
	Class to hold a record of what changes have been made to endnote numbers.
	"""

	old_anchor: str # The previous anchor.
	new_anchor: str # The anchor it has been changed to.
	filename: str # The file in which it was changed.

class SeEpub:
	"""
	An object representing an SE epub file.

	An SE epub can have various operations performed on it, including recomposing and linting.
	"""

	path: Path = Path() # The path to the base of the ebook repo, i.e., a folder containing `./images/` and `./src/`.
	epub_root_path = Path() # The path to the epub source root, i.e. `self.path / src`.
	content_path: Path = Path() # The path to the epub content base, i.e. `self.epub_root_path / epub`.
	metadata_file_path: Path = Path() # The path to the metadata file, i.e. `self.content_path / content.opf`.
	toc_path: Path = Path()  # The path to the ToC file, i.e. `self.content_path / toc.xhtml`.
	glossary_search_key_map_path = None # The path to the glossary search key map, or `None` if there isn't one.
	identifier: str|None = None
	local_css = ""
	is_se_ebook = True
	_language = None
	_file_cache: dict[str, str] = {}
	_dom_cache: dict[str, EasyXmlTree] = {}
	_repo = None # git.Repo object
	_last_commit = None # GitCommit object
	_endnotes: list[Endnote] | None = None
	_endnotes_path: Path | None = None
	_loi_path: Path | None = None
	_cover_path: Path | None = None
	_spine_file_paths: list[Path] | None = None
	_title: str | None = None

	def __init__(self, epub_root_directory: str | Path):
		try:
			self.path = Path(epub_root_directory).resolve()

			if not self.path.is_dir():
				raise NotADirectoryError

		except Exception as ex:
			raise se.InvalidSeEbookException(f"Not a directory: [path][link=file://{self.path}]{self.path}[/][/].") from ex

		# Decide if this is an SE epub, or a white-label epub.
		# SE epubs have a `./src` directory and the identifier looks like an SE identifier.
		if (self.path / "src" / "META-INF" / "container.xml").is_file():
			self.epub_root_path = self.path / "src"
		else:
			self.epub_root_path = self.path
			self.is_se_ebook = False

		try:
			container_tree = self.get_dom(self.epub_root_path / "META-INF" / "container.xml")
			path = container_tree.xpath("/container/rootfiles/rootfile[@media-type=\"application/oebps-package+xml\"]/@full-path", str)[0]
		except FileNotFoundError as ex:
			raise se.InvalidSeEbookException(f"Not a valid ebook, file not found: [path]{self.epub_root_path / 'META-INF' / 'container.xml'}[/].") from ex
		except IndexError as ex:
			raise se.InvalidSeEbookException("Target doesn’t appear to be an epub: no [path]container.xml[/] or no metadata file.") from ex

		self.metadata_file_path = self.epub_root_path / path

		try:
			self.content_path = self.metadata_file_path.parent
			self.metadata_dom = self.get_dom(self.metadata_file_path)
		except Exception as ex:
			raise se.InvalidXmlException(f"Couldn’t parse [path][link=file://{self.metadata_file_path}]{self.metadata_file_path}[/][/]: {ex}") from ex

		try:
			toc_href = self.metadata_dom.xpath("/package/manifest/item[contains(@properties, 'nav')]/@href", str)[0]
			self.toc_path = self.content_path / toc_href
		except IndexError as ex:
			raise se.InvalidSeEbookException("Couldn’t find table of contents.") from ex

		try:
			gskm_href = self.metadata_dom.xpath("/package/manifest/item[contains(@properties, 'search-key-map')]/@href", str)[0]
			self.glossary_search_key_map_path = self.content_path / gskm_href
		except IndexError:
			pass

		# If our identifier isn't SE-style, we're not an SE ebook.
		try:
			self.identifier = self.metadata_dom.xpath("/package/metadata/dc:identifier/text()", str)[0]

			if not self.identifier.startswith("https://standardebooks.org/ebooks/"):
				self.is_se_ebook = False
		except IndexError:
			self.is_se_ebook = False

	@property
	def title(self) -> str|None:
		"""
		Accessor
		"""

		if not self._title:
			try:
				self._title = self.metadata_dom.xpath("/package/metadata/dc:title/text()", str)[0]
			except IndexError:
				pass

		return self._title

	@property
	def language(self) -> str|None:
		"""
		Accessor
		"""

		if not self._language:
			try:
				self._language = self.metadata_dom.xpath("/package/metadata/dc:language/text()", str)[0]
			except IndexError:
				pass

		return self._language

	@property
	def cover_path(self) -> Path|None:
		"""
		Accessor.
		"""

		if not self._cover_path:
			try:
				self._cover_path = self.content_path / self.metadata_dom.xpath("/package/manifest/item[contains(@properties, 'cover-image')]/@href", str)[0]
			except IndexError:
				pass

		return self._cover_path

	@property
	def endnotes_path(self) -> Path|None:
		"""
		Accessor.
		"""

		if not self._endnotes_path:
			for file_path in self.content_path.glob("**/*.xhtml"):
				dom = self.get_dom(file_path)
				if dom.xpath("/html/body/section[contains(@epub:type, 'endnotes')]"):
					self._endnotes_path = file_path
					break

		return self._endnotes_path

	@property
	def loi_path(self) -> Path|None:
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
	def repo(self) -> Repo:
		"""
		Accessor.
		"""

		if not self._repo:
			try:
				self._repo = Repo(self.path)
			except Exception as ex:
				raise se.InvalidSeEbookException("Couldn’t access this ebook’s Git repository.") from ex

		return self._repo

	@property
	def last_commit(self) -> GitCommit | None:
		"""
		Accessor.
		"""

		if not self._last_commit:
			# We use a `git` command instead of using `gitpython`'s `commit` object because we want the short hash.
			try:
				# We have to clear this environmental variable or else `gitpython` will think the repo is `.` instead of the dir we actually pass, if we're called from a git hook (like `post-receive`).
				# See <https://stackoverflow.com/questions/42328426/gitpython-not-working-from-git-hook>.
				if "GIT_DIR" in os.environ:
					del os.environ["GIT_DIR"]

				git_command = cmd.Git(self.path)
				output = git_command.show("-s", "--format=%H %h %ct", "HEAD").split()

				self._last_commit = GitCommit(output[0], output[1], datetime.fromtimestamp(int(output[2]), timezone.utc))
			except Exception:
				self._last_commit = None

		return self._last_commit

	@property
	def endnotes(self) -> list[Endnote]:
		"""
		Accessor

		Return a list of Endnote objects representing the endnotes file for this ebook.

		INPUTS
		None.

		OUTPUTS
		A list of Endnote objects representing the endnotes file for this ebook.
		"""

		if not self._endnotes:
			self._endnotes = []

			if self.endnotes_path is not None:
				dom = self.get_dom(self.endnotes_path)

				for node in dom.xpath("/html/body//section[re:test(@epub:type, '\\bendnotes\\b')]/ol/li"):
					note = Endnote()
					note.node = node
					try:
						note.number = int(node.get_attr("id").replace("note-", ""))
					except ValueError:
						note.number = 0
					note.contents = node.xpath("./*")
					note.anchor = node.get_attr("id")

					try:
						note.back_link = node.xpath(".//a[contains(@epub:type, 'backlink')]/@href", str)[0]
					except IndexError as ex:
						raise se.InvalidInputException(f"No backlink found in note {note.anchor} in existing endnotes file.") from ex

					self._endnotes.append(note)

		return self._endnotes

	@property
	def spine_file_paths(self) -> list[Path]:
		"""
		Reads the spine from the metadata file to obtain a list of content files, in the order wanted for the ToC.

		It assumes this has already been manually ordered by the producer.

		INPUTS:
		None.

		OUTPUTS:
		List of content files paths in the order given in the spine in the metadata file.
		"""

		if not self._spine_file_paths:
			self._spine_file_paths = []

			for idref in self.metadata_dom.xpath("/package/spine/itemref/@idref", str):
				try:
					path = self.metadata_dom.xpath(f"/package/manifest/item[@id='{idref}']/@href", str)[0]
				except IndexError as ex:
					raise se.InvalidSeEbookException(f"Couldn’t find spine item: {idref}") from ex

				self._spine_file_paths.append(self.content_path / path)

		return self._spine_file_paths

	def generate_repo_name(self) -> str:
		"""
		Generate a repo name like `omar-khayyam_the-rubaiyat-of-omar-khayyam_edward-fitzgerald`.
		"""

		identifier = self.generate_identifier()

		if self.is_se_ebook:
			identifier = regex.sub(r"^https://standardebooks\.org/ebooks/", "", identifier)

		return identifier.replace("/", "_")

	def generate_url_slug(self) -> str:
		"""
		Generate a URL slug like `omar-khayyam/the-rubaiyat-of-omar-khayyam/edward-fitzgerald`.
		"""

		slug = self.generate_identifier()

		if self.is_se_ebook:
			slug = regex.sub(r"^https://standardebooks\.org/ebooks/", "", slug)

		return slug

	def generate_identifier(self) -> str:
		"""
		Generate an ebook identifier based on the metadata in the metadata file.
		"""

		identifier = "https://standardebooks.org/ebooks/"

		if not self.is_se_ebook:
			identifier = ""

		# Add authors.
		authors: list[str] = []
		for author in self.metadata_dom.xpath("/package/metadata/dc:creator"):
			authors.append(author.text)
			identifier += se.formatting.make_url_safe(author.text) + "_"

		identifier = identifier.strip("_") + "/"

		# Add title.
		for title in self.metadata_dom.xpath("/package/metadata/dc:title[@id=\"title\"]"):
			identifier += se.formatting.make_url_safe(title.text) + "/"

		# If a book is a collection/omnibus and has more than 1 translator, or if any book has more than 3 translators, combine them into `various-translators` in the identifier.
		has_various_translators = self.is_se_ebook and len(self.metadata_dom.xpath("//metadata[ (count(./meta[text()='trl']) > 1 and ./meta[@property='schema:additionalType' and text()='http://schema.org/Collection']) or (count(./meta[text()='trl']) > 3)]")) > 0
		process_translators = True
		if has_various_translators:
			identifier += "various-translators/"
			process_translators = False

		# For contributors, we always add translators except in certain cases, namely if *some* translators have a `display-seq` property, and others do not.
		# According to the epub spec, if that is the case, we should only add those that *do* have the attribute.
		# We only add illustrators and editors if they have `display-seq` set to a nonzero value.
		# By SE convention, any contributor with `display-seq == 0` will be excluded from the identifier string.
		translators: list[MetadataContributor] = []
		illustrators: list[MetadataContributor] = []
		editors: list[MetadataContributor] = []
		translators_have_display_seq = False
		for role in self.metadata_dom.xpath("/package/metadata/meta[@property='role']"):
			contributor_id = role.get_attr("refines").lstrip("#")
			contributor_element = self.metadata_dom.xpath("/package/metadata/dc:contributor[@id=\"" + contributor_id + "\"]")
			if contributor_element:
				contributor = MetadataContributor(contributor_element[0].text, True, None)
				display_seq = self.metadata_dom.xpath("/package/metadata/meta[@property=\"display-seq\"][@refines=\"#" + contributor_id + "\"]")

				if display_seq and int(display_seq[0].text) == 0:
					contributor.include = False
					display_seq = []

				if role.text == "trl" and process_translators:
					if display_seq:
						contributor.display_seq = int(display_seq[0].text)
						translators_have_display_seq = True

					translators.append(contributor)

				if role.text == "ill" and display_seq:
					contributor.display_seq = int(display_seq[0].text)

					illustrators.append(contributor)

				if role.text == "edt" and display_seq:
					contributor.display_seq = int(display_seq[0].text)

					editors.append(contributor)

		for translator in translators:
			if (not translators_have_display_seq and translator.include) or translator.display_seq:
				identifier += se.formatting.make_url_safe(translator.name) + "_"

		if translators:
			identifier = identifier.strip("_") + "/"

		for editor in editors:
			identifier += se.formatting.make_url_safe(editor.name) + "_"

		for illustrator in illustrators:
			include_illustrator = True

			# If the translator or editor is also the illustrator, don't include them twice.
			for translator in translators:
				if illustrator.name == translator.name:
					include_illustrator = False
					break

			for editor in editors:
				if illustrator.name == editor.name:
					include_illustrator = False
					break

			if include_illustrator and (illustrator.include or illustrator.display_seq):
				identifier += se.formatting.make_url_safe(illustrator.name) + "_"

		identifier = identifier.strip("_/")

		return identifier

	def generate_vcs_url(self) -> str:
		"""
		Generate a GitHub repository URL based on the *generated* SE identifier, *not* the SE identifier in the metadata file.

		OUTPUTS
		A string representing the GitHub repository URL (capped at maximum 100 characters).
		"""

		if not self.is_se_ebook:
			return "https://github.com/PUBLISHER/" + self.generate_repo_name()[0:100]

		return "https://github.com/standardebooks/" + self.generate_repo_name()[0:100]

	def generate_title_string(self) -> str:
		"""
		Return a string representing the book's title string, like `The Rubáiyát of Omar Khayyám. Translated by Edward Fitzgerald. Illustrated by Edmund Dulac`.
		"""

		output = self.get_title()

		authors = self.get_display_contributors("aut")

		if authors and authors[0] != "Anonymous":
			output += ", by " + se.formatting.format_list(authors)

		translators = self.get_display_contributors("trl", ignore_list=authors)

		if translators:
			output += ". Translated by " + se.formatting.format_list(translators)

		editors = self.get_display_contributors("edt", ignore_list=authors)

		if editors:
			output += ". Edited by " + se.formatting.format_list(editors)

		illustrators = self.get_display_contributors("ill", ignore_list=authors + translators + editors)

		if illustrators:
			output += ". Illustrated by " + se.formatting.format_list(illustrators)

		return output

	def get_display_contributors(self, marc_role: str, use_nbsp: bool=False, ignore_list: list[str]|None=None) -> list[str]:
		"""
		Return a list of strings representing contributors of the given MARC role, displayed and ordered according to their `display-seq` property.

		With `use_nbsp`, use no-break spaces in each contributor name.

		With `ignore_list`, don't include contributors who are in this list.
		"""

		contributors: list[str] = []
		raw_contributors: list[MetadataContributor] = []
		contributors_have_display_seq = False
		for role in self.metadata_dom.xpath(f"/package/metadata/meta[@property='role' and @scheme='marc:relators' and text()='{marc_role}']"):
			contributor_id = role.get_attr("refines").lstrip("#")
			contributor_element = (self.metadata_dom.xpath("/package/metadata/*[@id=\"" + contributor_id + "\"]") or [None])[0]
			if contributor_element:
				add_contributor = True
				contributor_name = contributor_element.text

				if ignore_list:
					for item in ignore_list:
						if item.replace(se.NO_BREAK_SPACE, " ") == contributor_name.replace(se.NO_BREAK_SPACE, " "):
							add_contributor = False
							break

				if not add_contributor:
					continue

				if use_nbsp:
					contributor_name = contributor_name.replace(" ", se.NO_BREAK_SPACE)

				contributor = MetadataContributor(contributor_name, True, 0)
				display_seq: EasyXmlElement | None = (self.metadata_dom.xpath("/package/metadata/meta[@property='display-seq'][@refines='#" + contributor_id + "']") or [None])[0]

				# Only include illustrators and editors if they have a `display-seq` set.
				if not display_seq and marc_role in ("ill", "edt"):
					contributor.include = False
					display_seq = None

				if display_seq and int(display_seq.text) == 0:
					contributor.include = False
					display_seq = None

				if display_seq:
					contributor.display_seq = int(display_seq.text)
					contributors_have_display_seq = True

				raw_contributors.append(contributor)

		raw_contributors.sort(key=lambda x: x.display_seq or 0)

		for raw_contributor in raw_contributors:
			if (not contributors_have_display_seq and raw_contributor.include) or raw_contributor.display_seq:
				contributors.append(raw_contributor.name)

		return contributors

	def write_dom(self, file_path: Path) -> None:
		"""
		Write the DOM for the given `Path` to disk.

		INPUTS
		file_path: A `Path` pointing to the file.
		"""
		with open(file_path, "w", encoding="utf-8") as file:
			file.write(self.get_dom(file_path).to_string())

	def get_file(self, file_path: Path) -> str:
		"""
		Get raw file contents of a file in the epub.

		Contents are cached so that we don't hit the disk repeatedly.

		INPUTS
		file_path: A `Path` pointing to the file.

		OUTPUTS
		A string representing the file contents.
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

	def flush_dom(self, file_path: Path) -> None:
		"""
		Remove a DOM cache entry for the given file, regardless of whether comments were removed.

		INPUTS
		file_path: A `Path` pointing to the file.
		"""

		keys_to_delete: list[str] = []

		for key in self._dom_cache:
			if key.startswith(str(file_path)):
				keys_to_delete.append(key)

		for key in keys_to_delete:
			del self._dom_cache[key]

		try:
			del self._file_cache[str(file_path)]
		except Exception:
			pass

	def get_dom(self, file_path: Path, remove_comments: bool=False) -> EasyXmlTree:
		"""
		Get an `EasyXmlTree` DOM object for a given file.

		Contents are cached so that we don't hit the disk or re-parse DOMs repeatedly.

		INPUTS
		file_path: A Path pointing to the file.

		OUTPUTS
		A string representing the file contents.
		"""
		file_path_str = str(file_path) + "_" + str(remove_comments)

		if file_path_str not in self._dom_cache:
			try:
				with open(file_path, "rb") as file:
					self._dom_cache[file_path_str] = EasyXmlTree(file.read())

				# Remove comments.
				if remove_comments:
					for node in self._dom_cache[file_path_str].xpath("//comment()"):
						node.remove()

			except etree.XMLSyntaxError as ex:
				raise se.InvalidXhtmlException(f"Couldn’t parse XML in [path][link=file://{file_path.resolve()}]{file_path}[/][/]: {ex}") from ex
			except FileNotFoundError as ex:
				raise ex
			except se.InvalidXmlException as ex:
				raise se.InvalidXhtmlException(f"Couldn’t parse XML in [path][link=file://{file_path.resolve()}]{file_path}[/][/]: {ex.__cause__}") from ex
			except Exception as ex:
				raise se.InvalidXhtmlException(f"Couldn’t parse XML in [path][link=file://{file_path.resolve()}]{file_path}[/][/].") from ex

		return self._dom_cache[file_path_str]

	def simplify_cfis(self) -> None:
		"""
		Replace intra-publication EPUB CFI links with links to `@id` attributes.

		If the CFI points to a range, link it to the parent element of the range starting point. If the CFI points to an element, link to that element directly with an `@id` attribute.

		If the target already has an `@id` attribute, it's re-used, otherwise a new `@id` attribute is generated based on the CFI and added to the target element.
		"""

		# Resolve intra-publication EPUB CFI links to ordinary fragment links.
		cfi_links: list[tuple[Path, EasyXmlElement, str]] = []
		for file_path in self.epub_root_path.glob("**/*.xhtml"):
			# Get a list of `@href` attributes that are *intra-publication* EPUB CFIs, i.e. they point to a metadata file instead of a separate epub file.
			for link in self.get_dom(file_path).xpath("//a[re:test(@href, '\\.opf#epubcfi\\(')]"):
				href = link.get_attr("href")
				uri = urlsplit(href)
				if not uri.scheme and not uri.netloc and not uri.query and unquote(uri.fragment).startswith("epubcfi(") and (file_path.parent / unquote(uri.path)).resolve() == self.metadata_file_path:
					cfi_links.append((file_path, link, href))

		if cfi_links:
			cfi_documents = {path: self.get_dom(path) for path in self.epub_root_path.glob("**/*") if path.suffix in (".xhtml", ".html", ".svg", ".xml", ".opf")}
			cfi_documents[self.metadata_file_path] = self.metadata_dom
			used_ids = {value for dom in cfi_documents.values() for value in dom.xpath("//@id", str)}
			changed_documents: set[Path] = set()
			for file_path, link, href in cfi_links:
				try:
					target = self.resolve_epub_cfi(href)
				except Exception as ex:
					raise se.InvalidInputException(f"Couldn’t parse EPUB CFI [text]{rich.markup.escape(href)}[/] in [path][link={url_quote(str(file_path))}]{rich.markup.escape(str(file_path))}[/][/]: {rich.markup.escape(str(ex))}")

				# Get the path for the specified target.
				target_root = target.lxml_element.getroottree().getroot()
				target_path = next((path for path, dom in cfi_documents.items() if dom.etree is target_root), None)
				if target_path is None:
					raise se.InvalidInputException(f"Couldn’t locate the EPUB CFI target document: [text]{rich.markup.escape(href)}[/].")

				# Does the target currently have an `@id` attribute?
				target_id = target.get_attr("id")

				if not target_id:
					# Create a new `@id` attribute for the target, using the original EPUB CFI but modifying it to point to the actual element we're targeting.
					cfi = unquote(urlsplit(href).fragment)[8:-1]
					paths = regex.split(r"\[(?:\^.|[^\]^])*\](*SKIP)(*FAIL)|,", cfi)
					endpoint = paths[0] + (paths[1] if len(paths) == 3 else "")

					for step in regex.finditer(r"\[(?:\^.|[^\]^])*\](*SKIP)(*FAIL)|/([0-9]+)(?:\[(?:\^.|[^\]^])*\])?", endpoint):
						if int(step[1]) == 0 or int(step[1]) % 2:
							continue

						candidate_id = f"epubcfi({endpoint[:step.end()]})"

						if self.resolve_epub_cfi(candidate_id).lxml_element is target.lxml_element:
							target_id = candidate_id
							break

					if not target_id:
						raise se.InvalidInputException(f"Couldn’t determine the EPUB CFI target's element path: [text]{rich.markup.escape(href)}[/].")

					if target_id in used_ids:
						raise se.InvalidInputException(f"The EPUB CFI target ID is already in use: [attr]{rich.markup.escape(target_id)}[/]: [text]{rich.markup.escape(href)}[/].")

					target.set_attr("id", target_id)
					used_ids.add(target_id)
					changed_documents.add(target_path)

				relative_path = url_quote(os.path.relpath(target_path, file_path.parent)) if target_path != file_path else ""
				fragment = url_quote(target_id, safe="/?:@!$&'()*+,;=")
				link.set_attr("href", f"{relative_path}#{fragment}")
				changed_documents.add(file_path)

			for file_path in changed_documents:
				file_path.write_text(cfi_documents[file_path].to_string(), encoding="utf-8")

	def resolve_epub_cfi(self, epub_cfi: str) -> EasyXmlElement:
		"""
		Resolve an intra-publication EPUB CFI to its element, or the closest parent element of a text position.
		If the EPUB CFI points to a range, return the start element, or if the start point is a text position, the closest parent element of the start point.

		INPUTS:
		epub_cfi: A bare `epubcfi(...)` or a URI referencing this ebook's package document.
		"""

		package_path = self.metadata_file_path.resolve()
		fragment = epub_cfi
		# Validate `epub_cfi` before continuing.
		if not fragment.startswith("epubcfi("):
			# Intra-publication links can be relative to a content document in a subdirectory.
			uri = urlsplit(epub_cfi)
			package_reference = Path(unquote(uri.path))
			if uri.scheme or uri.netloc or uri.query or package_reference.is_absolute() or not uri.fragment:
				raise se.InvalidInputException("Expected an intra-publication EPUB CFI.")
			if uri.path and not any(
				(base / package_reference).resolve() == package_path
				for base in [self.content_path, self.epub_root_path, *[(self.content_path / unquote(urlsplit(href).path)).parent for href in self.metadata_dom.xpath("/package/manifest/item/@href", str)]]
			):
				raise se.InvalidInputException("EPUB CFI doesn’t reference this ebook’s package document.")
			fragment = unquote(uri.fragment, errors="strict")

		# Validate the grammar.
		grammar = r"""(?x)
			(?(DEFINE)
				(?P<integer>0|[1-9][0-9]*)
				(?P<number>(?&integer)(?:\.[0-9]*[1-9])?)
				(?P<value>(?:\^[\^\[\](),;=]|[^\^\[\](),;=])+)
				(?P<name>(?:\^[\^\[\](),;=]|[^\^\[\](),;= ])+)
				(?P<parameter>;(?&name)=(?&value)(?:,(?&value))*)
				(?P<assertion>\[(?:(?&value)(?:,(?&value))?|,(?&value)|(?&parameter))(?&parameter)*\])
				(?P<step>/(?&integer)(?&assertion)?)
				(?P<offset>(?::(?&integer)|@(?&number):(?&number)|~(?&number)(?:@(?&number):(?&number))?)(?&assertion)?)
				(?P<local>(?&step)*(?:!(?:(?&offset)|(?&path))|(?&offset)?))
				(?P<path>(?&step)(?&local))
			)
			epubcfi\((?&path)(?:,(?&local),(?&local))?\)
		"""
		if regex.search(r"[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]", fragment) or not regex.fullmatch(grammar, fragment):
			raise se.InvalidInputException("Invalid EPUB CFI syntax.")

		tokens = regex.findall(r"\[(?:\^.|[^\]^])*\]|[@/~:][0-9]+(?:\.[0-9]+)?|[!,]", fragment[8:-1])
		paths: list[list[str]] = [[]]
		for token in tokens:
			if token == ",":
				paths.append([])
			else:
				paths[-1].append(token)

		is_range = len(paths) == 3
		if is_range and any(token.startswith((":", "~", "@")) for token in paths[0]):
			raise se.InvalidInputException("Range parent must end at a step.")

		def resolve_path(path: list[str]) -> tuple[EasyXmlElement, Path, tuple[tuple[int, float], ...]]:
			"""
			Resolve a complete endpoint.
			"""

			document_path = package_path
			dom = self.metadata_dom
			node = dom.xpath("/*")[0]
			text: str | None = None
			text_prefix = ""
			is_virtual = False
			position_step: int | None = None
			offset = 0
			last_token_type = ""
			order: list[tuple[int, float]] = []
			for index, token in enumerate(path):
				token_type = token[0]
				if token_type == "[":
					# Split before unescaping so escaped commas and semicolons remain literal text.
					parts = regex.split(r"\^.(*SKIP)(*FAIL)|;", token[1:-1])
					values = [regex.sub(r"\^(.)", r"\1", value) for value in regex.split(r"\^.(*SKIP)(*FAIL)|,", parts[0])]
					for parameter in parts[1:]:
						if parameter.startswith("s=") and (parameter not in ("s=a", "s=b") or is_range or index != len(path) - 1 or any(item.startswith("@") for item in path)):
							raise se.InvalidInputException("Invalid side bias.")
					if parts[0]:
						if last_token_type == "/" and text is None and not is_virtual and len(values) == 1:
							if values[0] not in (node.get_attr("id"), node.get_attr("xml:id")):
								matches = dom.xpath(f"//*[@id={se.easy_xml.escape_xpath(values[0])} or @xml:id={se.easy_xml.escape_xpath(values[0])}]")
								if len(matches) != 1:
									raise se.InvalidInputException("Unresolvable ID assertion.")
								node = matches[0]
						elif last_token_type == ":" and text is not None:
							before = text_prefix + text.encode("utf-16-le")[:offset * 2].decode("utf-16-le", errors="surrogatepass")
							after = "".join(dom.xpath("//text()", str))[len(before):]
							if node.tag == "img":
								after = text.encode("utf-16-le")[offset * 2:].decode("utf-16-le", errors="surrogatepass")
							before = regex.sub(r"[\x20\t\r\n]+", " ", before)
							after = regex.sub(r"[\x20\t\r\n]+", " ", after)
							if not before.endswith(values[0]) or (len(values) == 2 and not after.startswith(values[1])):
								raise se.InvalidInputException("Unresolvable text assertion.")
						else:
							raise se.InvalidInputException("Invalid assertion for this location.")
					continue
				if token_type == "/":
					if text is not None or is_virtual:
						raise se.InvalidInputException("An EPUB CFI can’t descend from a text or virtual location.")
					step = int(token[1:])
					children = node.xpath("./*")
					if step % 2:
						if step > len(children) * 2 + 1:
							raise se.InvalidInputException("Text location doesn’t exist.")
						# Comments and processing instructions do not divide character-data chunks.
						chunks = [node.lxml_element.text or ""]
						for child in node.children:
							if isinstance(child.lxml_element.tag, str):
								chunks.append("")
							chunks[-1] += child.lxml_element.tail or ""
						text = chunks[step // 2]
						position_step = step
						text_prefix = "".join(node.xpath("preceding::text()", str))
						for child_index in range(step // 2):
							text_prefix += chunks[child_index] + "".join(children[child_index].xpath(".//text()", str))
					elif step in (0, len(children) * 2 + 2):
						is_virtual = True
						position_step = step
					elif step > len(children) * 2:
						raise se.InvalidInputException("Element doesn’t exist.")
					else:
						node = children[step // 2 - 1]
				elif token_type == "!":
					if text is not None or is_virtual:
						raise se.InvalidInputException("Invalid indirection.")
					reference = ""
					if node.tag == "itemref" and document_path == package_path and node.xpath("parent::spine"):
						items = self.metadata_dom.xpath(f"/package/manifest/item[@id={se.easy_xml.escape_xpath(node.get_attr('idref'))}]")
						if len(items) == 1:
							reference = items[0].get_attr("href")
					elif node.tag in ("iframe", "embed"):
						reference = node.get_attr("src")
					elif node.tag == "object":
						reference = node.get_attr("data")
					elif node.tag in ("image", "use", "{http://www.w3.org/2000/svg}image", "{http://www.w3.org/2000/svg}use"):
						reference = node.lxml_element.get("{http://www.w3.org/1999/xlink}href", "")
					if not reference:
						raise se.InvalidInputException("The element has no supported embedded reference.")
					# Resolve the local resource reference without leaving the publication.
					uri = urlsplit(reference)
					if uri.scheme or uri.netloc or uri.query or uri.path.startswith("/"):
						raise se.InvalidInputException("References must remain inside the publication.")
					document_path = (document_path.parent / unquote(uri.path)).resolve() if uri.path else document_path
					if not document_path.is_relative_to(self.epub_root_path.resolve()):
						raise se.InvalidInputException("References must remain inside the publication.")
					target_id = unquote(uri.fragment, errors="strict")
					dom = self.get_dom(document_path)
					matches = dom.xpath(f"//*[@id={se.easy_xml.escape_xpath(target_id)} or @xml:id={se.easy_xml.escape_xpath(target_id)}]") if target_id else dom.xpath("/*")
					if len(matches) != 1:
						raise se.InvalidInputException("Embedded fragment doesn’t exist.")
					node = matches[0]
				elif token_type == ":" and last_token_type != "@":
					if text is None and node.tag == "img" and not is_virtual:
						text = node.get_attr("alt", False)
					if text is None or is_virtual:
						raise se.InvalidInputException("Character offset requires text or an image’s [attr]@alt[/] text.")
					offset = int(token[1:])
					if offset > len(text.encode("utf-16-le")) // 2:
						raise se.InvalidInputException("Character offset exceeds the available text.")
					order.append((0, offset))
				else:
					if text is not None or is_virtual:
						raise se.InvalidInputException("Media offset requires an element.")
					value = float(token[1:])
					if token_type in ("@", ":") and value > 100:
						raise se.InvalidInputException("Spatial coordinates must be between 0 and 100.")
					if token_type == "~" and node.tag not in ("audio", "video"):
						raise se.InvalidInputException("Temporal offset requires audio or video.")
					if token_type == "@" and node.tag not in ("img", "image", "svg", "video", "{http://www.w3.org/2000/svg}image", "{http://www.w3.org/2000/svg}svg"):
						raise se.InvalidInputException("Spatial offset requires an image or video.")
					order.append((2, value))
					if token_type == ":":
						order[-2:] = [order[-1], order[-2]]
				last_token_type = token_type
			if text is not None and last_token_type == "/":
				order.append((0, 0))

			# Compare resolved document locations so ID correction can't conceal a reversed range.
			ancestors = [*node.xpath("ancestor::*"), node]
			steps = [(1, len(ancestor.xpath("preceding-sibling::*")) * 2 + 2) for ancestor in ancestors[1:]]
			if position_step is not None:
				steps.append((1, position_step))
			return node, document_path, tuple([*steps, *order])

		if not is_range:
			return resolve_path(paths[0])[0]

		start, start_document, start_order = resolve_path(paths[0] + paths[1])
		_, end_document, end_order = resolve_path(paths[0] + paths[2])

		if start_document != end_document or start_order > end_order:
			raise se.InvalidInputException("Range must have ordered endpoints in the same document.")

		return start

	def _recompose_xhtml(self, section: EasyXmlElement, output_dom: EasyXmlTree, use_image_files: bool = False) -> None:
		"""
		Helper function used in `self.recompose()`.

		INPUTS
		section: An `EasyXmlElement` to inspect
		output_dom: An `EasyXmlTree` representing the entire output dom
		use_image_files: If `True`, leave image `src` attributes as relative URLs instead of inlining as `data:` URIs.

		OUTPUTS
		None.
		"""

		# Quick sanity check before we begin.
		if not section.get_attr("id") or (section.parent and section.parent.tag.lower() != "body" and not section.parent.get_attr("id")):
			raise se.InvalidXhtmlException(f"Section without [attr]@id[/] attribute: [xhtml]{section.to_tag_string()}[/]")

		if section.parent and section.parent.tag.lower() == "body" and not section.get_attr("data-parent"):
			section.set_attr("epub:type", f"{section.get_attr('epub:type')} {section.parent.get_attr('epub:type')}".strip())

		# Try to find our parent element in the current output DOM, by ID.
		# If it's not in the output, then append this element to the elements's closest parent by ID (or `<body>`), then iterate over its children and do the same.
		existing_section = None
		existing_section = output_dom.xpath(f"//*[@id='{section.get_attr('data-parent')}']")

		if existing_section:
			existing_section[0].append(section)
		else:
			output_dom.xpath("/html/body")[0].append(section)

		# Convert all `<img>` references to inline base64, unless use_image_files is `True`.
		# We even convert SVGs instead of inlining them, because CSS won't allow us to style inlined SVGs (for example if we want to apply `max-width` or `filter: invert()`).
		if not use_image_files:
			for img in section.xpath("//img[starts-with(@src, '../images/')]"):
				img.set_attr("src", se.images.get_data_url(self.content_path / img.get_attr("src").replace("../", "")))

	def _scope_recompose_css_selector(self, selector: str, css_class: str) -> str:
		"""
		Prefix a selector with the stylesheet scoping class used during recomposition.
		"""

		selector = selector.strip()

		if not selector:
			return selector

		if selector == "body":
			return f".{css_class}"

		selector = regex.sub(r"^body\s*>\s*", "", selector)
		selector = regex.sub(r"^body\s+", "", selector)

		if regex.match(r"^(section|article)(?=$|[#\.\[:\s>+~])", selector):
			return regex.sub(r"^(section|article)", rf"\1.{css_class}", selector, count=1)

		return f".{css_class} {selector}"

	def _scope_recompose_css_selectors(self, selectors: str, css_class: str) -> str:
		"""
		Prefix each selector in a selector list with the stylesheet scoping class.
		"""

		current_selector = ""
		depth = 0
		quote = ""
		scoped_selectors: list[str] = []

		for character in selectors:
			if quote:
				current_selector += character
				if character == quote:
					quote = ""
			elif character in ("'", '"'):
				current_selector += character
				quote = character
			elif character in ("(", "["):
				current_selector += character
				depth += 1
			elif character in (")", "]"):
				current_selector += character
				depth -= 1
			elif character == "," and depth == 0:
				scoped_selectors.append(self._scope_recompose_css_selector(current_selector, css_class))
				current_selector = ""
			else:
				current_selector += character

		if current_selector:
			scoped_selectors.append(self._scope_recompose_css_selector(current_selector, css_class))

		return ", ".join(scoped_selectors)

	def _scope_recompose_css_tokens(self, tokens: list[Node], css_class: str) -> str:
		"""
		Return CSS serialized from parsed tokens after scoping qualified-rule selectors.
		"""

		output = ""

		for token in tokens:
			if isinstance(token, ParseError):
				raise se.InvalidCssException(token.message)

			if isinstance(token, QualifiedRule):
				selectors = tinycss2.serializer.serialize(token.prelude).strip()
				output += self._scope_recompose_css_selectors(selectors, css_class) + "{" + tinycss2.serializer.serialize(token.content) + "}"
			elif isinstance(token, AtRule) and token.content is not None and token.lower_at_keyword in ("container", "media", "supports"):
				rules = tinycss2.parser.parse_rule_list(token.content, skip_comments=False, skip_whitespace=False)
				output += "@" + token.lower_at_keyword + " " + tinycss2.serializer.serialize(token.prelude).strip() + "{" + self._scope_recompose_css_tokens(rules, css_class) + "}"
			else:
				output += tinycss2.serializer.serialize([token])

		return output

	def recompose(self, output_xhtml5: bool, extra_css_file: Path | None = None, use_image_files: bool = False) -> str:
		"""
		Iterate over the XHTML files in this epub and "recompose" them into a single XHTML string representing this ebook.

		INPUTS
		output_xhtml5: `True` to output XHTML5 instead of HTML5.
		extra_css_file: path to an additional CSS file to include.
		use_image_files: if `True`, leave image `src` attributes as relative URLs instead of inlining as `data:` URIs.

		OUTPUTS
		A string of HTML5 representing the entire recomposed ebook.
		"""

		# Get some header data.
		try:
			title = self.metadata_dom.xpath("/package/metadata/dc:title/text()", str)[0]
		except IndexError as ex:
			raise se.InvalidSeEbookException("Couldn’t determine ebook title.") from ex

		css = ""
		namespaces: list[str] = []
		css_filenames: list[Path] = []
		css_classes_by_file_path: dict[Path, list[str]] = {}

		# Collect stylesheets in spine order, keeping each stylesheet's first occurrence.
		for file_path in self.spine_file_paths:
			dom = self.get_dom(file_path)
			css_classes_by_file_path[file_path] = []

			for node in dom.xpath("/html/head/link[re:test(@rel, '\\bstylesheet\\b') and @href]"):
				href = regex.sub(r"[?#].*$", "", node.get_attr("href"))
				css_filename = (file_path.parent / href).resolve()

				if css_filename not in css_filenames:
					css_filenames.append(css_filename)

				css_classes_by_file_path[file_path].append(se.formatting.make_url_safe(css_filename.name))

		# Add the extra CSS file if present.
		if extra_css_file:
			css_filenames.append(extra_css_file)

		# Now recompose the CSS.
		for filepath in css_filenames:
			file_css = self.get_file(filepath)

			namespaces += regex.findall(r"@namespace.+?;", file_css)

			file_css = regex.sub(r"\s*@(charset|namespace).+?;\s*", "\n", file_css).strip()

			# Convert `background-image` URLs to base64, unless `use_image_files` is `True`.
			if not use_image_files:
				for image in regex.finditer(pattern=r"""url\("(.+?\.(?:svg|png|jpg))"\)""", string=file_css):
					url = image.captures(1)[0].replace("../", "")
					url = regex.sub(r"^/", "", url)
					try:
						data_url = se.images.get_data_url(self.content_path / url)
						file_css = file_css.replace(image.group(0), f"""url("{data_url}")""")
					except FileNotFoundError:
						# If the file isn't found, continue silently.
						# File may not be found for example in `web.css`, which points to an image on the web server, not in the ebook.
						pass

			if not extra_css_file or filepath != extra_css_file:
				tokens = tinycss2.parser.parse_stylesheet(file_css, skip_comments=False, skip_whitespace=False)
				file_css = self._scope_recompose_css_tokens(tokens, se.formatting.make_url_safe(filepath.name))

			css = css + f"\n\n\n/* {filepath.name} */\n" + file_css

		css = css.strip()

		namespaces = sorted(list(set(namespaces)), reverse=True)

		if namespaces:
			css = "\n" + css

			for namespace in namespaces:
				css = namespace + "\n" + css

		css = "\t\t\t".join(css.splitlines(True)) + "\n"

		# Remove `min-height` from CSS since it doesn't really apply to the single page format.
		# It occurs at least in `se.css`.
		css = regex.sub(r"\s*min-height: [^;]+?;", "", css)

		# Remove `-epub-*` CSS as it's invalid in a browser context.
		css = regex.sub(r"\s*\-epub\-[^;]+?;", "", css)

		output_xhtml = f"<?xml version=\"1.0\" encoding=\"utf-8\"?><html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\" epub:prefix=\"z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0\" xml:lang=\"{self.language}\"><head><meta charset=\"utf-8\"/><title>{title}</title><style/></head><body></body></html>"
		output_dom = se.formatting.EasyXmlTree(output_xhtml)
		output_dom.is_css_applied = True # We will apply CSS recursively to nodes that will be attached to `output_dom`, so set the bit here.

		# Iterate over spine items in order and recompose them into our output.
		needs_wrapper_css = False
		for file_path in self.spine_file_paths:
			dom = self.get_dom(file_path)

			# Add stylesheet scoping classes to top-level sectioning nodes in the DOM.
			for node in dom.xpath("/html/body/*[name() = 'section' or name() = 'article']"):
				for css_class in css_classes_by_file_path[file_path]:
					if not se.formatting.has_css_class(node.get_attr("class"), css_class):
						node.add_attr_value("class", css_class)

			# Apply the stylesheet to see if we have `position: absolute` on any items. If so, apply `position: relative` to its closest `<section`> ancestor.
			# See <https://standardebooks.org/ebooks/jean-toomer/cane> for an example of this in action.
			dom.apply_css(css)

			# Select deepest sections or articles with `id` attributes that have *only* `<figure>` or `<img>` children, and one of those children has `position: absolute`.
			for node in dom.xpath("/html/body//*[@id and (name() = 'section' or name = 'article') and not(.//*[(name() = 'section' or name() = 'article') and not(preceding-sibling::* or following-sibling::*)]) and count(./*[(name() = 'figure' or name() = 'img')]) = count(./*) and .//*[(name() = 'figure' or name() = 'img') and @data-css-position = 'absolute']]"):
				needs_wrapper_css = True

				# Wrap the sections in a `<div>` that we style later.
				wrapper_element = etree.SubElement(node.lxml_element, "div")
				wrapper_element.set("class", "positioning-wrapper")
				for child in node.xpath("./*[(name() = 'figure' or name() = 'img')]"):
					wrapper_element.append(child.lxml_element) # `.append()` will *move* the element to the end of `wrapper_element`.

			# Now, recompose the children.
			for node in dom.xpath("/html/body/*"):
				try:
					self._recompose_xhtml(node, output_dom, use_image_files)
				except se.SeException as ex:
					raise se.SeException(f"[path][link=file://{file_path}]{file_path}[/][/]: {ex}") from ex

		# Remove `data-parent` attributes.
		for node in output_dom.xpath("//*[@data-parent]"):
			node.remove_attr("data-parent")

		# Did we add wrappers? If so add the CSS.
		# We also have to give the wrapper a height, because it may have siblings that were recomposed in from other files.
		if needs_wrapper_css:
			css = css + "\n\t\t\t.positioning-wrapper{\n\t\t\t\tposition: relative; height: 100vh;\n\t\t\t}\n"

		# Add the ToC after the titlepage.
		toc_dom = self.get_dom(self.toc_path)
		titlepage_node = output_dom.xpath("//*[contains(concat(' ', @epub:type, ' '), ' titlepage ')]")[0]

		for node in toc_dom.xpath("//nav[1]"):
			titlepage_node.lxml_element.addnext(node.lxml_element)

		# Replace all `<a href>` links with internal links.
		for link in output_dom.xpath("//a[not(re:test(@href, '^https?://')) and contains(@href, '#')]"):
			link.set_attr("href", regex.sub(r".+(#.+)$", r"\1", link.get_attr("href")))

		# Replace all `<a href>` links to entire files.
		for link in output_dom.xpath("//a[not(re:test(@href, '^https?://')) and not(contains(@href, '#'))]"):
			href = link.get_attr("href")
			href = regex.sub(r".+/([^/]+)$", r"#\1", href)
			href = regex.sub(r"\.xhtml$", "", href)
			link.set_attr("href", href)

		for node in output_dom.xpath("/html/body//a[re:test(@href, '^(\\.\\./)?text/(.+?)\\.xhtml$')]"):
			node.set_attr("href", regex.sub(r"(\.\./)?text/(.+?)\.xhtml", r"#\2", node.get_attr("href")))

		for node in output_dom.xpath("/html/body//a[re:test(@href, '^(\\.\\./)?text/.+?\\.xhtml#(.+?)$')]"):
			node.set_attr("href", regex.sub(r"(\.\./)?text/.+?\.xhtml#(.+?)", r"#\2", node.get_attr("href")))

		# Make some compatibility adjustments.
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

		# Get the output XHTML as a string.
		output_xhtml = output_dom.to_string()

		# All done, clean the output.
		output_xhtml = se.formatting.format_xhtml(output_xhtml)

		# Insert our CSS. We do this after `clean` because `clean` will escape `>` in the CSS.
		output_xhtml = regex.sub(r"<style/>", "<style><![CDATA[\n\t\t\t" + css + "\t\t]]></style>", output_xhtml)

		if output_xhtml5:
			output_xhtml = output_xhtml.replace("\t\t<style/>\n", "")

			# Re-add a `doctype`.
			output_xhtml = output_xhtml.replace("<?xml version=\"1.0\" encoding=\"utf-8\"?>", "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<!DOCTYPE html>")
		else:
			# Remove XML declaration and re-add the doctype.
			output_xhtml = regex.sub(r"<\?xml.+?\?>", "<!DOCTYPE html>", output_xhtml)

			# Remove `CDATA`.
			output_xhtml = output_xhtml.replace("<![CDATA[", "")
			output_xhtml = output_xhtml.replace("]]>", "")

			# Make some replacements for HTML5 compatibility.
			output_xhtml = output_xhtml.replace("epub|type", "data-epub-type")
			output_xhtml = output_xhtml.replace("xml|lang", "lang")
			output_xhtml = regex.sub(r" xmlns.+?=\".+?\"", "", output_xhtml)
			output_xhtml = regex.sub(r"@namespace (epub|xml).+?\s+", "", output_xhtml)

			# The Nu HTML5 Validator barfs if non-void elements are self-closed (like `<td/>`).
			# Try to un-self-close them for HTML5 output.
			output_xhtml = regex.sub(r"<(colgroup|td|th|span)( [^/>]*?)?/>", r"<\1\2></\1>", output_xhtml)

		return output_xhtml

	def _does_line_require_vertical_offset(self, line: str, previous_line:str|None) -> bool:
		"""
		Return `True` if the previous line contains a low diacritic like `ç`, or if there was a previous line and this line contains a high diacritic like `ö`.
		"""

		# U+0327 = combining cedilla
		# U+0328 = combining okonek
		# In the regex we first normalize the text to separate out diacritics, then use `\p{M}` to match any combining mark.

		if previous_line and (regex.search(r"[\u0327\u0328]", normalize("NFD", previous_line), flags=regex.IGNORECASE) or regex.search(r"[aeiou]\p{M}", normalize("NFD", line), flags=regex.IGNORECASE)):
			return True

		return False

	def generate_titlepage_svg(self) -> None:
		"""
		Generate the titlepage SVG and place it in `./images/titlepage.svg`.

		The function tries to build the title with the widest line at the bottom, moving up.

		We approximate a few values, like the width of a space, which are variable in the font.

		Some useful test ebooks:

		- <https://standardebooks.org/ebooks/anonymous/beowulf/john-lesslie-hall>

		- <https://standardebooks.org/ebooks/edgar-allan-poe/the-narrative-of-arthur-gordon-pym-of-nantucket>

		- <https://standardebooks.org/ebooks/omar-khayyam/the-rubaiyat-of-omar-khayyam/edward-fitzgerald>

		- <https://standardebooks.org/ebooks/selma-lagerlof/the-story-of-gosta-berling/pauline-bancroft-flach>

		- <https://standardebooks.org/ebooks/william-wordsworth_samuel-taylor-coleridge/lyrical-ballads>

		- <https://standardebooks.org/ebooks/karl-marx_friedrich-engels/the-communist-manifesto/samuel-moore>

		- <https://standardebooks.org/ebooks/abu-al-ala-al-maarri/the-luzumiyat/ameen-rihani>

		- <https://standardebooks.org/ebooks/hans-jakob-christoffel-von-grimmelshausen/the-adventurous-simplicissimus/alfred-thomas-scrope-goodrick>
		"""

		authors = self.get_display_contributors("aut", False)
		title = self.title or ""
		title_string = self.generate_title_string()

		contributors: dict[str, str] = {}

		translators = self.get_display_contributors("trl", True, authors)

		if translators:
			contributors["translated by"] = se.formatting.format_list(translators)

		editors = self.get_display_contributors("edt", True, authors)

		if editors:
			contributors["edited by"] = se.formatting.format_list(editors)

		illustrators = self.get_display_contributors("ill", True, authors + translators + editors)

		if illustrators:
			contributors["illustrated by"] = se.formatting.format_list(illustrators)

		# Don't include "anonymous" authors in the cover.
		# League Spartan doesn't have good character support for turned commas, so replace them with single quotes.
		authors = [author.replace("ʻ", "‘").replace("ʼ", "’") for author in authors if author.lower() != "anonymous"]

		svg = ""

		# Read our template SVG to get some values before we begin.
		with importlib.resources.files("se.data.templates").joinpath("titlepage.svg").open("r", encoding="utf-8") as file:
			svg = file.read()

		# Remove the template text elements from the SVG source, we'll write out to it later.
		svg = regex.sub(r"\s*<text.+</svg>", "</svg>", svg, flags=regex.DOTALL).strip()

		# Calculate the title lines.
		# We use the cover title box canvas width here, because we want the titlepage to roughly match the cover arrangement.
		# Note that we can't *always* match the cover layout because the cover text is allowed to be resized, while the titlepage text is not.
		canvas_width = se.images.COVER_TITLE_BOX_WIDTH - (se.images.COVER_TITLE_BOX_HORIZONTAL_PADDING * 2)
		title_lines = se.images.calculate_image_lines(title.upper(), se.images.COVER_TITLE_HEIGHT, canvas_width)

		# Now reset the canvas width to the full width of the titlepage canvas for author/contributor lines.
		canvas_width = se.TITLEPAGE_WIDTH - (se.images.TITLEPAGE_HORIZONTAL_PADDING * 2)

		# Calculate the author lines.
		authors_lines: list[list[str]] = []
		for author in authors:
			authors_lines.append(se.images.calculate_image_lines(author.upper(), se.images.TITLEPAGE_AUTHOR_HEIGHT, canvas_width))

		# Calculate the contributor lines.
		contributor_blocks: list[ContributorsBlock] = []
		for descriptor, contributor_name in contributors.items():
			contributor_blocks.append(ContributorsBlock(descriptor, se.images.calculate_image_lines(contributor_name.upper(), se.images.TITLEPAGE_CONTRIBUTOR_HEIGHT, canvas_width)))

		# Construct the output.
		text_elements = ""
		element_y = se.images.TITLEPAGE_VERTICAL_PADDING

		# Add the title.
		i = 0
		for line in title_lines:
			if self._does_line_require_vertical_offset(line, title_lines[i - 1] if i > 0 else None):
				element_y += floor(se.images.COVER_TITLE_HEIGHT / se.images.LEAGUE_SPARTAN_DIACRITIC_RATIO)

			element_y += se.images.TITLEPAGE_TITLE_HEIGHT
			text_elements += f"\t<text class=\"title\" x=\"700\" y=\"{element_y:.0f}\">{escape(line)}</text>\n"
			element_y += se.images.TITLEPAGE_TITLE_MARGIN

			i = i + 1

		element_y -= se.images.TITLEPAGE_TITLE_MARGIN

		# Add the author(s).
		if authors:
			element_y += se.images.TITLEPAGE_AUTHOR_SPACING

		for author_lines in authors_lines:
			for line in author_lines:
				element_y += se.images.TITLEPAGE_AUTHOR_HEIGHT
				text_elements += f"\t<text class=\"author\" x=\"700\" y=\"{element_y:.0f}\">{escape(line)}</text>\n"
				element_y += se.images.TITLEPAGE_AUTHOR_MARGIN

		if authors:
			element_y -= se.images.TITLEPAGE_AUTHOR_MARGIN

		# Add the contributor(s).
		if contributor_blocks:
			element_y += se.images.TITLEPAGE_CONTRIBUTORS_SPACING
			for contributor_block in contributor_blocks:
				element_y += se.images.TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_HEIGHT
				text_elements += f"\t<text class=\"contributor-descriptor\" x=\"700\" y=\"{element_y:.0f}\">{escape(contributor_block.descriptor)}</text>\n"
				element_y += se.images.TITLEPAGE_CONTRIBUTOR_MARGIN

				for person in contributor_block.names:
					element_y += se.images.TITLEPAGE_CONTRIBUTOR_HEIGHT
					line = person.replace(se.NO_BREAK_SPACE, " ")
					text_elements += f"\t<text class=\"contributor\" x=\"700\" y=\"{element_y:.0f}\">{escape(line)}</text>\n"
					element_y += se.images.TITLEPAGE_CONTRIBUTOR_MARGIN

				element_y -= se.images.TITLEPAGE_CONTRIBUTOR_MARGIN

				element_y += se.images.TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_MARGIN

			element_y -= se.images.TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_MARGIN
		else:
			# Remove unused CSS.
			svg = regex.sub(r"\n\t\t\.contributor-descriptor{.+?}\n", "", svg, flags=regex.DOTALL)
			svg = regex.sub(r"\n\t\t\.contributor{.+?}\n", "", svg, flags=regex.DOTALL)

		element_y += se.images.TITLEPAGE_VERTICAL_PADDING

		svg = svg.replace("</svg>", "\n" + text_elements + "</svg>\n").replace("TITLE_STRING", escape(title_string))
		svg = regex.sub(r"viewBox=\".+?\"", f"viewBox=\"0 0 {se.TITLEPAGE_WIDTH} {element_y:.0f}\"", svg)

		with open(self.path / "images" / "titlepage.svg" , "w", encoding="utf-8") as file:
			file.write(svg)
			file.truncate()

	def build_titlepage_svg(self) -> None:
		"""
		Generate a distributable titlepage SVG in `./src/epub/images/` based on the titlepage file in `./images/`.

		INPUTS
		None.

		OUTPUTS
		None.
		"""
		source_images_directory = self.path / "images"
		source_titlepage_svg_filename = source_images_directory / "titlepage.svg"
		dest_images_directory = self.content_path / "images"
		dest_titlepage_svg_filename = dest_images_directory / "titlepage.svg"

		if source_titlepage_svg_filename.is_file():
			# Convert text to paths.
			se.images.svg_text_to_paths(source_titlepage_svg_filename, dest_titlepage_svg_filename)

	def _get_cover_title_box_contents_height(self, title_lines: list[str], title_line_height: int, author_lines: list[list[str]]) -> int:
		title_line_count = len(title_lines)
		# author_lines can have multiple authors with multiple lines per author, so flatten before counting
		author_line_count = len([y for x in author_lines for y in x])

		spacing = se.images.COVER_AUTHOR_SPACING
		if author_line_count == 0:
			spacing = 0

		additional_author_line_count = max(author_line_count - 1, 0)

		lines_with_diacritic_offset = 0

		# xsmall sizing doesn't require an offset.
		if title_line_height != se.images.COVER_TITLE_XSMALL_HEIGHT:
			i = 0
			for line in title_lines:
				if self._does_line_require_vertical_offset(line, title_lines[i - 1] if i > 0 else None):
					lines_with_diacritic_offset = lines_with_diacritic_offset + 1

				i = i + 1

		return (title_line_count * title_line_height) \
			+ lines_with_diacritic_offset * floor(title_line_height / se.images.LEAGUE_SPARTAN_DIACRITIC_RATIO) \
 			+ ( (title_line_count - 1) * se.images.COVER_TITLE_MARGIN) \
 			+ spacing \
 			+ (author_line_count * se.images.COVER_AUTHOR_HEIGHT) \
 			+ ( additional_author_line_count * se.images.COVER_AUTHOR_MARGIN)

	def generate_cover_svg(self) -> None:
		"""
		Generate the cover SVG and place it in `./images/cover.svg`.

		The function tries to build the title box with the widest line at the bottom, moving up.

		We approximate a few values, like the width of a space, which are variable in the font.

		Some useful test ebooks:

		- <https://standardebooks.org/ebooks/anonymous/beowulf/john-lesslie-hall>

		- <https://standardebooks.org/ebooks/edgar-allan-poe/the-narrative-of-arthur-gordon-pym-of-nantucket>

		- <https://standardebooks.org/ebooks/omar-khayyam/the-rubaiyat-of-omar-khayyam/edward-fitzgerald>

		- <https://standardebooks.org/ebooks/selma-lagerlof/the-story-of-gosta-berling/pauline-bancroft-flach>

		- <https://standardebooks.org/ebooks/william-wordsworth_samuel-taylor-coleridge/lyrical-ballads>

		- <https://standardebooks.org/ebooks/karl-marx_friedrich-engels/the-communist-manifesto/samuel-moore>

		- <https://standardebooks.org/ebooks/abu-al-ala-al-maarri/the-luzumiyat/ameen-rihani>

		- <https://standardebooks.org/ebooks/hans-jakob-christoffel-von-grimmelshausen/the-adventurous-simplicissimus/alfred-thomas-scrope-goodrick>
		"""

		authors = self.get_display_contributors("aut", False)
		title = self.title or ""
		title_string = self.generate_title_string()

		# Don't include "anonymous" authors in the cover.
		# League Spartan doesn't have good character support for turned commas, so replace them with single quotes.
		authors = [author.replace("ʻ", "‘").replace("ʼ", "’") for author in authors if author.lower() != "anonymous"]

		svg = ""
		canvas_width = se.images.COVER_TITLE_BOX_WIDTH - (se.images.COVER_TITLE_BOX_HORIZONTAL_PADDING * 2)

		# Read our template SVG to get some values before we begin.
		with importlib.resources.files("se.data.templates").joinpath("cover.svg").open("r", encoding="utf-8") as file:
			svg = file.read()

		# Remove the template text elements from the SVG source, we'll write out to it later.
		svg = regex.sub(r"\s*<text.+</svg>", "</svg>", svg, flags=regex.DOTALL).strip()

		# Calculate the author lines.
		authors_lines: list[list[str]] = []
		for author in authors:
			authors_lines.append(se.images.calculate_image_lines(author.upper(), se.images.COVER_AUTHOR_HEIGHT, canvas_width))

		# Calculate the title lines.
		title_upper = title.upper()
		title_height = se.images.COVER_TITLE_HEIGHT
		title_class = "title"
		title_lines = se.images.calculate_image_lines(title_upper, title_height, canvas_width)

		# Construct the output.
		text_elements = ""

		# Decide if we have to shrink the title text to fit the title box.
		max_cover_title_box_canvas_height = se.images.COVER_TITLE_BOX_HEIGHT - (se.images.COVER_TITLE_BOX_VERTICAL_PADDING * 2)
		cover_title_box_contents_height = self._get_cover_title_box_contents_height(title_lines, title_height, authors_lines)
		cover_title_box_contents_width = se.images.get_image_lines_width(title_lines, title_height)

		while (cover_title_box_contents_height > max_cover_title_box_canvas_height or cover_title_box_contents_width > canvas_width) and title_class != "title-xsmall":
			if title_class == "title-small":
				title_class = "title-xsmall"
				title_height = se.images.COVER_TITLE_XSMALL_HEIGHT

			if title_class == "title":
				title_class = "title-small"
				title_height = se.images.COVER_TITLE_SMALL_HEIGHT

			title_lines = se.images.calculate_image_lines(title_upper, title_height, canvas_width)
			cover_title_box_contents_height = self._get_cover_title_box_contents_height(title_lines, title_height, authors_lines)
			cover_title_box_contents_width = se.images.get_image_lines_width(title_lines, title_height)

		element_y = se.images.COVER_TITLE_BOX_Y + \
			+ ((se.images.COVER_TITLE_BOX_HEIGHT \
				- cover_title_box_contents_height \
			) / 2)

		# Add the title.
		i = 0
		for line in title_lines:
			# xsmall sizing doesn't require an offset.
			if title_height != se.images.COVER_TITLE_XSMALL_HEIGHT:
				if self._does_line_require_vertical_offset(line, title_lines[i - 1] if i > 0 else None):
					element_y += floor(title_height / se.images.LEAGUE_SPARTAN_DIACRITIC_RATIO)

			element_y += title_height
			text_elements += f"\t<text class=\"{title_class}\" x=\"700\" y=\"{element_y:.0f}\">{escape(line)}</text>\n"
			element_y += se.images.COVER_TITLE_MARGIN
			i = i + 1

		element_y -= se.images.COVER_TITLE_MARGIN

		# Add the author(s).
		if authors:
			element_y += se.images.COVER_AUTHOR_SPACING

			for author_lines in authors_lines:
				for line in author_lines:
					element_y += se.images.COVER_AUTHOR_HEIGHT
					text_elements += f"\t<text class=\"author\" x=\"700\" y=\"{element_y:.0f}\">{escape(line)}</text>\n"
					element_y += se.images.COVER_AUTHOR_MARGIN

			element_y -= se.images.COVER_AUTHOR_MARGIN

		# Remove unused CSS.
		if title_class != "title":
			svg = regex.sub(r"\n\n\t\t\.title\{.+?\}", "", svg, flags=regex.DOTALL)

		if title_class != "title-small":
			svg = regex.sub(r"\n\n\t\t\.title-small\{.+?\}", "", svg, flags=regex.DOTALL)

		if title_class != "title-xsmall":
			svg = regex.sub(r"\n\n\t\t\.title-xsmall\{.+?\}", "", svg, flags=regex.DOTALL)

		svg = svg.replace("</svg>", "\n" + text_elements + "</svg>\n").replace("TITLE_STRING", escape(title_string))

		with open(self.path / "images" / "cover.svg" , "w", encoding="utf-8") as file:
			file.write(svg)
			file.truncate()

	def build_cover_svg(self) -> None:
		"""
		Generate a distributable cover SVG in `./src/epub/images/` based on the cover file in `./images/`.

		INPUTS
		None.

		OUTPUTS
		None.
		"""

		source_images_directory = self.path / "images"
		source_cover_jpg_filename = source_images_directory / "cover.jpg"
		source_cover_svg_filename = source_images_directory / "cover.svg"
		dest_images_directory = self.content_path / "images"
		dest_cover_svg_filename = self.cover_path

		if dest_cover_svg_filename is None:
			return

		# Create output directory if it doesn't exist.
		dest_images_directory.mkdir(parents=True, exist_ok=True)

		if source_cover_jpg_filename.is_file() and source_cover_svg_filename.is_file():
			# base64 encode `cover.jpg`.
			with open(source_cover_jpg_filename, "rb") as binary_file:
				source_cover_jpg_base64 = base64.b64encode(binary_file.read()).decode()

			# Convert text to paths.
			if source_cover_svg_filename.is_file():
				se.images.svg_text_to_paths(source_cover_svg_filename, dest_cover_svg_filename, remove_style=False)

			# Embed `cover.jpg`.
			dom = self.get_dom(dest_cover_svg_filename)

			# Embed the file.
			for node in dom.xpath("//*[re:test(@xlink:href, 'cover\\.jpg$')]"):
				node.set_attr("xlink:href", "data:image/jpeg;base64," + source_cover_jpg_base64)

			# For the cover we want to keep the `path.title-box` style, and add an additional style to color our new paths white.
			for node in dom.xpath("/svg/style"):
				node.set_text("\n\t\tpath{\n\t\t\tfill: #fff;\n\t\t}\n\n\t\t.title-box{\n\t\t\tfill: #000;\n\t\t\tfill-opacity: .75;\n\t\t}\n\t")

			with open(dest_cover_svg_filename, "w", encoding="utf-8") as file:
				file.write(dom.to_string())
				file.truncate()

	def shift_endnotes(self, target_endnote_number: int, step: int = 1) -> None:
		"""
		Shift endnotes starting at `target_endnote_number`.

		INPUTS:
		target_endnote_number: The endnote to start shifting at.
		step: X to increment or -X to decrement.

		OUTPUTS:
		None.
		"""

		increment = step > 0
		endnote_numbers: list[int]

		if step == 0 or self.endnotes_path is None:
			return

		dom = self.get_dom(self.endnotes_path)

		# Get a list of all the integer endnote IDs (we have books with non-integer endnote ids; this command won't work on them).
		all_endnote_numbers: list[int] = []
		for node in dom.xpath("/html/body//section[re:test(@epub:type, '\\bendnotes\\b')]/ol/li"):
			endnote_number = regex.sub("note-", "", node.get_attr("id"))
			if endnote_number.isdigit():
				all_endnote_numbers.append(int(endnote_number))

		# The shift begins at `target_endnote_number`, so remove the endnote numbers before it.
		orig_endnote_numbers: list[int] = [n for n in all_endnote_numbers if n >= target_endnote_number]

		# If incrementing, start at the end and work backwards to keep from duplicating IDs.
		if increment:
			endnote_numbers = orig_endnote_numbers[::-1]
		else:
			endnote_numbers = orig_endnote_numbers

		for endnote_number in endnote_numbers:
			new_endnote_number = endnote_number + step

			# Update all the actual endnotes in the endnotes file.
			for node in dom.xpath(f"/html/body//section[re:test(@epub:type, '\\bendnotes\\b')]/ol/li[@id='note-{endnote_number}']"):
				node.set_attr("id", f"note-{new_endnote_number}")

			# Update all backlinks in the endnotes file.
			for node in dom.xpath(f"/html/body//a[re:test(@href, '#noteref-{endnote_number}$')]"):
				node.set_attr("href", node.get_attr("href").replace(f"#noteref-{endnote_number}", f"#noteref-{new_endnote_number}"))

		# Write the endnotes file.
		try:
			with open(self.endnotes_path, "w", encoding="utf-8") as file:
				file.write(dom.to_string())

		except Exception as ex:
			raise se.InvalidSeEbookException(f"Couldn’t open endnotes file: [path][link=file://{self.endnotes_path}]{self.endnotes_path}[/][/].") from ex

		# Now update endnotes in all other files. We also do another pass over the endnotes file in case there are endnotes within endnotes.
		for file_path in self.content_path.glob("**/*.xhtml"):
			dom = self.get_dom(file_path)

			for endnote_number in endnote_numbers:
				new_endnote_number = endnote_number + step

				# We don't use an xpath matching `epub:type="noteref"` because we can have `href`s that are not noterefs pointing to endnotes (like "see here").
				for node in dom.xpath(f"/html/body//a[re:test(@href, '(endnotes\\.xhtml)?#note-{endnote_number}$')]"):
					# Update the `id` attribute of the link, if we have one (sometimes `href`s point to endnotes but they are not noterefs themselves).
					if node.get_attr("id"):
						# Use a regex instead of just replacing the entire ID so that we don't mess up IDs that do not fit this pattern.
						node.set_attr("id", regex.sub(r"noteref-\d+$", f"noteref-{new_endnote_number}", node.get_attr("id")))

					node.set_attr("href", regex.sub(fr"#note-{endnote_number}$", f"#note-{new_endnote_number}", node.get_attr("href")))
					node.set_text(regex.sub(fr"\b{endnote_number}\b", f"{new_endnote_number}", node.text))

			with open(file_path, "w", encoding="utf-8") as file:
				file.write(dom.to_string())

	def shift_illustrations(self, target_illustration_number: int, step: int = 1) -> None:
		"""
		Shift illustrations starting at `target_illustration_number`.

		INPUTS:
		target_illustration_number: The illustration to start shifting at.
		step: X to increment or -X to decrement.

		OUTPUTS:
		None.
		"""

		if self.loi_path is None:
			return

		increment = step > 0

		if step == 0:
			return

		dom = self.get_dom(self.loi_path)

		# Get a list of all the integer illustration IDs.
		all_illustration_numbers: list[int] = []
		for node in dom.xpath("/html/body//a[re:test(@href,'#illustration-[0-9]+$')]"):
			illustration_number = regex.sub("^.*?#illustration-", "", node.get_attr("href"))
			if illustration_number.isdigit():
				all_illustration_numbers.append(int(illustration_number))

		# The shift begins at `target_illustration_number`, so remove the illustration numbers before it.
		orig_illustration_numbers = [n for n in all_illustration_numbers if n >= target_illustration_number]

		# If incrementing, start at the end and work backwards to keep from duplicating IDs.
		if increment:
			illustration_numbers = orig_illustration_numbers[::-1]
		else:
			illustration_numbers = orig_illustration_numbers

		# Update image files.
		for illustration_number in illustration_numbers:
			new_illustration_number = illustration_number + step

			# Test for previously existing file.
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

		# Update the LoI file.
		for illustration_number in illustration_numbers:
			new_illustration_number = illustration_number + step

			# Update all the illustrations in the illustrations file.
			for node in dom.xpath(f"/html/body//a[re:test(@href, '#illustration-{illustration_number}$')]"):
				node.set_attr("href", node.get_attr("href").replace(f"#illustration-{illustration_number}", f"#illustration-{new_illustration_number}"))

		# Write the LoI file.
		try:
			with open(self.loi_path, "w", encoding="utf-8") as file:
				file.write(dom.to_string())

		except Exception as ex:
			raise se.InvalidSeEbookException(f"Couldn’t open LoI file: [path][link=file://{self.loi_path}]{self.loi_path}[/][/].") from ex

		# Now update illustrations in all other files.
		for file_path in self.content_path.glob("**/*.xhtml"):
			dom = self.get_dom(file_path)

			for illustration_number in illustration_numbers:
				new_illustration_number = illustration_number + step

				for node in dom.xpath(f"/html/body//figure[@id='illustration-{illustration_number}']"):
					node.set_attr("id", f"illustration-{new_illustration_number}")
					for img in node.xpath("./img"):
						img.set_attr("src", img.get_attr("src").replace(f"illustration-{illustration_number}", f"illustration-{new_illustration_number}"))

			with open(file_path, "w", encoding="utf-8") as file:
				file.write(dom.to_string())

	def generate_loi(self) -> str:
		"""
		Generate an LoI DOM based on all `<figure>` elements that contain an `<img>`. Text from the `<figcaption>`, if any, is preferred over that from the `<img>`'s alt attribute.
		"""

		loi_dom = None
		if not self.loi_path:
			with importlib.resources.files("se.data.templates").joinpath("loi.xhtml").open("rb") as file:
				loi_dom = EasyXmlTree(file.read())

			if self.language:
				loi_dom.xpath("/html")[0].set_attr("xml:lang", self.language)
		else:
			loi_dom = self.get_dom(self.loi_path)

		ols = loi_dom.xpath("/html/body/nav/ol")
		if len(ols) != 1:
			raise se.InvalidSeEbookException(f"LoI contains unexpected number of [xhtml]<ol/>[/]: [path][link=file://{self.loi_path}]{self.loi_path}[/][/].")

		etree.strip_elements(ols[0].lxml_element, "li")

		for file_path in self.spine_file_paths:
			dom = self.get_dom(file_path)

			for figure in dom.xpath("/html/body//figure[@id and ./img]"):
				figure_id = figure.get_attr("id")

				entry = figure.xpath("./img")[0].get_attr("alt").strip()

				figcaption = figure.xpath("./figcaption")
				if figcaption:
					figcaption_text = figcaption[0].inner_text()
					# The alt text is probably more useful to the reader in this case.
					if figcaption_text and not regex.search(r"^[Ff]igure\s+\d+$", figcaption_text):
						has_block = False
						for tag in se.css.CSS_BLOCK_ELEMENTS:
							if figcaption[0].xpath(f"./{tag}"):
								has_block = True
								break

						# Try to retain semantic phrasing structure.
						if not has_block:
							entry = deepcopy(figcaption[0])

							# Remove endnote references.
							for noteref in entry.xpath("a[contains(@epub:type, 'noteref')]"):
								noteref.remove()

							# For other links, keep only the contents.
							for a in entry.xpath("a"):
								a.unwrap()

				a = EasyXmlElement("<a/>")
				a.set_attr("href", f"{file_path.name}#{figure_id}")

				if isinstance(entry, str):
					a.set_text(entry or f"Unable to auto-generate LoI text for #{figure_id}.")
				else:
					a.append(entry)
					entry.unwrap()

				p = EasyXmlElement("<p/>")
				p.append(a)

				li = EasyXmlElement("<li/>")
				li.append(p)
				ols[0].append(li)

		return se.formatting.format_xhtml(loi_dom.to_string())

	def set_release_timestamp(self) -> None:
		"""
		If this ebook has not yet been released, set the first release timestamp in the metadata file.
		"""

		if self.metadata_dom.xpath("/package/metadata/dc:date[text() = '1900-01-01T00:00:00Z' or text() = '']"):
			now = datetime.now(timezone.utc)
			now_iso = se.formatting.generate_iso_timestamp(now)
			now_friendly = se.formatting.generate_colophon_timestamp(now)

			for node in self.metadata_dom.xpath("/package/metadata/dc:date"):
				node.set_text(now_iso)

			for node in self.metadata_dom.xpath("/package/metadata/meta[@property='dcterms:modified']"):
				node.set_text(now_iso)

			self.write_dom(self.metadata_file_path)

			for file_path in self.content_path.glob("**/*.xhtml"):
				dom = self.get_dom(file_path)

				save_file = False

				for node in dom.xpath("/html/body/section[contains(@epub:type, 'colophon')]//time[contains(text(), 'January 1, 1900')]"):
					node.replace_with(EasyXmlElement(etree.fromstring(str.encode(f"<time datetime=\"{now_iso}\">{now_friendly}</time>"))))
					save_file = True

				if save_file:
					with open(file_path, "w", encoding="utf-8") as file:
						file.write(dom.to_string())

	def update_flesch_reading_ease(self) -> None:
		"""
		Calculate a new reading ease for this ebook and update the metadata file.

		Ignores SE boilerplate files like the imprint.

		INPUTS
		None.

		OUTPUTS
		None.
		"""

		text = ""

		for filename in se.get_target_filenames([self.path], ".xhtml"):
			xhtml = self.get_file(filename)

			is_ignored, _ = se.get_dom_if_not_ignored(xhtml, ["colophon", "titlepage", "imprint", "copyright-page", "halftitlepage", "toc", "loi"])

			if not is_ignored:
				text += xhtml

		for node in self.metadata_dom.xpath("/package/metadata/meta[@property='schema:educationalLevel']"):
			node.set_text(str(se.formatting.get_flesch_reading_ease(text)))

		self.write_dom(self.metadata_file_path)

	def get_word_count(self) -> int:
		"""
		Calculate the word count of this ebook.

		Ignores SE boilerplate files like the imprint, as well as any endnotes.

		INPUTS
		None.

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
		None.

		OUTPUTS
		None.
		"""

		for node in self.metadata_dom.xpath("/package/metadata/meta[@property='schema:wordCount']"):
			node.set_text(str(self.get_word_count()))

		self.write_dom(self.metadata_file_path)

	def generate_manifest(self) -> EasyXmlElement:
		"""
		Return the `<manifest>` element for this ebook as an `EasyXmlElement`.

		INPUTS
		None.

		OUTPUTS
		An `EasyXmlElement` representing the manifest.
		"""

		manifest: list[str] = []

		for file_path in self.content_path.glob("**/*"):
			if file_path.name == self.metadata_file_path.name:
				# Don't add the metadata file to the manifest.
				continue

			if file_path.stem.startswith("."):
				# Skip dotfiles.
				continue

			mime_type = None
			properties: list[str] = []

			# Add core media types: https://www.w3.org/TR/epub/#sec-core-media-types
			if file_path.suffix == ".gif":
				mime_type = "image/gif"

			if file_path.suffix == ".jpg":
				mime_type = "image/jpeg"

			if file_path.suffix == ".png":
				mime_type = "image/png"

			if file_path.suffix == ".svg":
				mime_type = "image/svg+xml"

			if file_path.suffix == ".webp":
				mime_type = "image/webp"

			if file_path.suffix == ".mp3":
				mime_type = "audio/mpeg"

			if file_path.suffix == ".mp4":
				mime_type = "audio/mp4"

			if file_path.suffix == ".ogg":
				mime_type = "audio/ogg; codecs=opus"

			if file_path.suffix == ".css":
				mime_type="text/css"

			if file_path.suffix == ".ttf":
				mime_type="application/font-sfnt"

			if file_path.suffix == ".otf":
				mime_type="application/vnd.ms-opentype"

			if file_path.suffix == ".woff":
				mime_type="font/woff"

			if file_path.suffix == ".woff2":
				mime_type="font/woff2"

			if file_path.stem == "cover":
				properties.append("cover-image")

			if file_path.suffix == ".xhtml":
				dom = self.get_dom(file_path)

				mime_type = "application/xhtml+xml"

				# The `glossary` semantic may also appear in the ToC landmarks, so specifically exclude that.
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
				# Put together any properties we have.
				properties_attr = ""
				for prop in properties:
					properties_attr += prop + " "

				properties_attr = properties_attr.strip()

				if properties_attr:
					properties_attr = f" properties=\"{properties_attr}\""

				# Add the manifest item.
				# Replace the path separator because if run on Windows we will get the wrong slash direction from `pathlib`.
				manifest.append(f"""<item href="{str(file_path.relative_to(self.content_path)).replace(os.sep, "/")}" id="{file_path.name}" media-type="{mime_type}"{properties_attr}/>""")

		manifest = natsorted(manifest)

		# Assemble the manifest XML string.
		manifest_xml = "<manifest>\n"

		for line in manifest:
			manifest_xml = manifest_xml + "\t" + line + "\n"

		manifest_xml = manifest_xml + "</manifest>"

		return EasyXmlElement(etree.fromstring(str.encode(manifest_xml)))

	def __add_to_spine(self, spine: list[str], items: list[Path], semantic: str) -> tuple[list[str], list[Path]]:
		"""
		Given a spine and a list of items, add the item to the spine if it contains the specified semantic.

		If an item is added to the spine, remove it from the original list.

		Returns an updated spine and item list.
		"""

		filtered_items: list[Path] = []
		spine_additions: list[str] = []

		for file_path in items:
			dom = self.get_dom(file_path)

			# Match against `\b` because we might have `titlepage` and `halftitlepage`.
			if dom.xpath(f"/html/body//section[re:test(@epub:type, '\\b{semantic}\\b')]"):
				spine_additions.append(file_path.name)
			else:
				filtered_items.append(file_path)

		# Sort the additions, for example if we have more than one dedication or introduction.
		spine_additions = natsorted(spine_additions)

		return (spine + spine_additions, filtered_items)

	def __add_hierarchy_to_spine(self, spine: list[str], items: list[Path]) -> list[str]:
		"""
		Given a spine and a list of items, add the item to the spine in sorted hierarchical order.

		Ensures that each file comes directly after its `data-parent`.

		Returns an updated spine.
		"""

		file_path_to_id: dict[Path, str] = {}
		id_to_parent: dict[str, str] = {}
		sort_keys: dict[str, str] = {}

		# Index all files.
		for file_path in items:
			dom = self.get_dom(file_path)

			# Get the `id` and `data-parent` for the top-level element.
			top_level = dom.xpath("/html/body/*[@id and @data-parent]")
			if top_level:
				section_id = top_level[0].get_attr("id")
				file_path_to_id[file_path] = section_id
				id_to_parent[section_id] = top_level[0].get_attr("data-parent")

		# Compute sort keys.
		for file_path in items:
			section_id = file_path_to_id.get(file_path, file_path.name)
			key: list[str] = []
			# Add `id` for all parents.
			while section_id:
				key.append(section_id)
				section_id = id_to_parent.get(section_id)
			# Concatenate `id`s to create hierarchical sort key.
			sort_keys[file_path.name] = '/'.join(reversed(key))

		# Sort using sort keys, using filename as fallback option.
		spine_additions = natsorted(
			[file_path.name for file_path in items],
			key=lambda name: sort_keys.get(name, name)
		)

		return spine + spine_additions

	def generate_spine(self) -> EasyXmlElement:
		"""
		Return the `<spine>` element of this ebook as an `EasyXmlElement`, with a best guess as to the correct order. Manual review is required.

		INPUTS
		None

		OUTPUTS
		An `EasyXmlElement` representing the spine.
		"""

		spine: list[str] = []
		frontmatter: list[Path] = []
		bodymatter: list[Path] = []
		backmatter: list[Path] = []

		for file_path in self.content_path.glob("**/*.xhtml"):
			dom = self.get_dom(file_path)

			# Exclude the ToC from the spine.
			if dom.xpath("/html/body//nav[contains(@epub:type, 'toc')]"):
				continue

			if dom.xpath("/html/*[contains(@epub:type, 'frontmatter')]"):
				frontmatter.append(file_path)
			elif dom.xpath("/html/*[contains(@epub:type, 'backmatter')]"):
				backmatter.append(file_path)
			else:
				bodymatter.append(file_path)

		# Add frontmatter.
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "titlepage")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "imprint")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "dedication")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "preamble")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "introduction")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "foreword")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "preface")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "epigraph")
		spine, frontmatter = self.__add_to_spine(spine, frontmatter, "z3998:dramatis-personae")

		# Extract half title page for subsequent addition.
		halftitlepage, frontmatter = self.__add_to_spine([], frontmatter, "halftitlepage")

		# Add any remaining frontmatter.
		spine += natsorted([file_path.name for file_path in frontmatter])

		# The half title page is always the last front matter.
		spine += halftitlepage

		# The prologue comes at the start of the bodymatter.
		spine, bodymatter = self.__add_to_spine(spine, bodymatter, "prologue")

		# Add bodymatter in hierarchical order.
		spine = self.__add_hierarchy_to_spine(spine, bodymatter)

		# Add backmatter.
		spine, backmatter = self.__add_to_spine(spine, backmatter, "afterword")
		spine, backmatter = self.__add_to_spine(spine, backmatter, "appendix")
		spine, backmatter = self.__add_to_spine(spine, backmatter, "glossary")
		spine, backmatter = self.__add_to_spine(spine, backmatter, "endnotes")
		spine, backmatter = self.__add_to_spine(spine, backmatter, "loi")

		# Extract colophon and copyright page for subsequent addition.
		colophon, backmatter = self.__add_to_spine([], backmatter, "colophon")
		copyright_page, backmatter = self.__add_to_spine([], backmatter, "copyright-page")

		# Add any remaining backmatter.
		spine += natsorted([file_path.name for file_path in backmatter])

		# Colophon and copyright page are always last.
		spine += colophon
		spine += copyright_page

		# Now build the spine output.
		spine_xml = "<spine>\n"
		for filename in spine:
			spine_xml = spine_xml + f"""\t<itemref idref="{filename}"/>\n"""

		spine_xml = spine_xml + "</spine>"

		return EasyXmlElement(etree.fromstring(str.encode(spine_xml)))

	def get_title(self) -> str:
		"""
		Returns the title of the book from the metadata file, which we assume has already been correctly completed.

		INPUTS:
		None.

		OUTPUTS:
		Either the title of the book, or `TITLE` if the required metadata element doesn't exist.
		"""
		try:
			return self.metadata_dom.xpath("/package/metadata/dc:title/text()", str)[0]
		except IndexError:
			return "TITLE"

	def get_subtitle(self) -> str | None:
		"""
		Returns the subtitle of the book from the metadata file, which we assume has already been correctly completed.

		INPUTS:
		None.

		OUTPUTS:
		Either the title of the book, or `None` if there is no subtitle.
		"""
		subtitle = None
		try:
			subtitle_anchor = self.metadata_dom.xpath("/package/metadata/meta[@property='title-type' and text()='subtitle']/@refines", str)[0]
			subtitle_element_id = subtitle_anchor.replace("#", "")
			subtitle = self.metadata_dom.xpath(f"/package/metadata/dc:title[@id='{subtitle_element_id}']/text()", str)[0]
		except IndexError:
			pass

		return subtitle

	def lint(self, skip_lint_ignore: bool, allowed_messages: list[str] | None = None) -> list[LintMessage]:
		"""
		The `self.lint()` function is very big so for readability and maintainability it's broken out to a separate file. Strictly speaking that file can be inlined into this class.
		"""

		from se.se_epub_lint import lint # pylint: disable=import-outside-toplevel,cyclic-import

		return lint(self, skip_lint_ignore, allowed_messages)

	def build(self, run_epubcheck: bool, check_only: bool, build_kobo: bool, build_kindle: bool, output_directory: Path, proof: bool, build_cache_directory: Path|None) -> None:
		"""
		The `self.build()` function is very big so for readability and maintainability it's broken out to a separate file. Strictly speaking that file can be inlined into this class.
		"""

		from se.se_epub_build import build # pylint: disable=import-outside-toplevel

		build(self, run_epubcheck, check_only, build_kobo, build_kindle, output_directory, proof, build_cache_directory)

	def generate_toc(self) -> str:
		"""
		The generate_toc() function is very big so for readability and maintainability
		it's broken out to a separate file. Strictly speaking that file can be inlined
		into this class.
		"""

		from se.se_epub_generate_toc import generate_toc  # pylint: disable=import-outside-toplevel

		toc_xhtml = generate_toc(self)

		# Word joiners and `nbsp` don't go in the ToC.
		toc_xhtml = toc_xhtml.replace(se.WORD_JOINER, "")
		toc_xhtml = toc_xhtml.replace(se.NO_BREAK_SPACE, " ")

		return toc_xhtml

	def _check_endnotes(self) -> list[str]:
		"""
		Initial check to see if all note references in the body have matching endnotes in `endnotes.xhtml` and no duplicates.

		Returns string of failures if any. If these are empty, all was well.
		"""
		missing: list[str] = []
		duplicates: list[str] = []
		orphans: list[str] = []
		references: list[str] = []
		response: list[str] = []
		for file_path in self.spine_file_paths:
			dom = self.get_dom(file_path)

			for link in dom.xpath("/html/body//a[contains(@epub:type, 'noteref')]"):
				anchor = ""
				href = link.get_attr("href")
				# Extract just the anchor from a URL (i.e., what follows a hash symbol).
				hash_position = href.find("#") + 1  # We want the characters *after* the hash.
				if hash_position > 0:
					anchor = href[hash_position:]
				references.append(anchor)  # Keep these for later reverse check.
				# Now try to find anchor in endnotes.
				matches = list(filter(lambda x, old=anchor: x.anchor == old, self.endnotes)) # type: ignore [arg-type, var-annotated]
				if not matches:
					missing.append(anchor)
				if len(matches) > 1:
					duplicates.append(anchor)
		for miss in missing:
			response.append(f"Missing endnote with anchor: {miss}")
		for dupe in duplicates:
			response.append(f"Duplicate endnotes with anchor: {dupe}")
		# Reverse check: look for orphaned endnotes.
		for note in self.endnotes:
			# Try to find it in our references collection.
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

		if self.endnotes_path is None:
			return

		noteref_locations: dict[int, Path] = {}

		current_note_number = 1

		# Renumber all noterefs starting from 1.
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

		# Renumber all endnotes starting from 1.
		current_note_number = 1
		endnotes_dom = self.get_dom(self.endnotes_path)
		for node in endnotes_dom.xpath("/html/body//section[re:test(@epub:type, '\\bendnotes\\b')]/ol/li"):
			node.set_attr("id", f"note-{current_note_number}")
			for backlink in node.xpath(".//a[contains(@epub:type, 'backlink')]"):
				filename = noteref_locations[current_note_number].name if current_note_number in noteref_locations else ""
				backlink.set_attr("href", f"{filename}#noteref-{current_note_number}")

			current_note_number += 1

		with open(self.endnotes_path, "w", encoding="utf-8") as file:
			file.write(endnotes_dom.to_string())

	def generate_endnotes(self) -> tuple[int, int, list[EndnoteChange]]:
		"""
		Read the epub spine to regenerate all endnotes in order of appearance, starting from 1.

		Changes are written to disk.

		Returns a tuple of `(found_endnote_count, changed_endnote_count, change_list)`.
		"""

		if self.endnotes_path is None:
			return (0, 0, [])

		# Do a safety check first, throw exception if it failed.
		results = self._check_endnotes()
		if results:
			report = "\n".join(results)
			raise se.InvalidInputException(f"Endnote error(s) found:\n{report}")

		# If we get here, it's safe to proceed.
		processed = 0
		current_note_number = 1
		notes_changed = 0
		change_list: list[EndnoteChange] = []

		for file_path in self.spine_file_paths:
			dom = self.get_dom(file_path)

			# Skip the actual endnotes file, we'll handle that later.
			if dom.xpath("/html/body//section[re:test(@epub:type, '\\bendnotes\\b')]"):
				continue

			processed += 1

			needs_rewrite = False
			for link in dom.xpath("/html/body//a[contains(@epub:type, 'noteref')]"):
				needs_rewrite, notes_changed = self.__process_noteref_link(change_list, current_note_number, file_path.name, link, needs_rewrite, notes_changed)
				current_note_number += 1

			# If we need to write back the body text file.
			if needs_rewrite:
				with open(file_path, "w", encoding="utf-8") as file:
					file.write(se.formatting.format_xhtml(dom.to_string()))

		# Now process any endnotes *within* the endnotes.
		for source_note in self.endnotes:
			if source_note.node:
				needs_rewrite = False
				for link in source_note.node.xpath(".//a[contains(@epub:type, 'noteref')]"):
					needs_rewrite, notes_changed = self.__process_noteref_link(change_list, current_note_number, self.endnotes_path.name, link, needs_rewrite, notes_changed)
					current_note_number += 1

		if processed == 0:
			raise se.InvalidInputException("No files processed. Did you update the manifest and order the spine?")

		if notes_changed > 0:
			# Now we need to recreate the endnotes file.
			endnotes_dom = self.get_dom(self.endnotes_path)
			for ol_node in endnotes_dom.xpath("/html/body//section[re:test(@epub:type, '\\bendnotes\\b')]/ol[1]"):
				for node in ol_node.xpath("./li"):
					node.remove()

				self.endnotes.sort(key=lambda endnote: endnote.number)

				for endnote in self.endnotes:
					if endnote.matched and endnote.node:
						endnote.node.set_attr("id", f"note-{endnote.number}")

						for node in endnote.node.xpath(".//a[contains(@epub:type, 'backlink')]"):
							node.set_attr("href", f"{endnote.source_file}#noteref-{endnote.number}")

						ol_node.append(endnote.node)

			with open(self.endnotes_path, "w", encoding="utf-8") as file:
				file.write(se.formatting.format_xhtml(endnotes_dom.to_string()))

			# Now trawl through the body files to locate any direct links to endnotes (not in an actual endnote reference).
			# Example: `(see <a href="endnotes.xhtml#note-1553">this note</a>.)`.
			# Most but not all such are likely to be in the newly re-written `endnotes.xhtml`.
			for file_path in self.spine_file_paths:
				needs_rewrite = False
				dom = self.get_dom(file_path)
				for link in dom.xpath("/html/body//a[contains(@href, 'endnotes.xhtml#note-')]"):
					needs_rewrite = self.__process_direct_link(change_list, link)
				if needs_rewrite:
					with open(file_path, "w", encoding="utf-8") as file:
						file.write(se.formatting.format_xhtml(dom.to_string()))

		return current_note_number - 1, notes_changed, change_list

	def generate_onix(self, metadata_dom: EasyXmlTree | None = None) -> EasyXmlTree:
		"""
		Return an ONIX file describing this ebook, as an `EasyXmlTree`.

		INPUTS
		metadata_dom: The DOM of the OPF file to base the ONIX record on; defaults to `self.metadata_dom`.

		OUTPUTS
		An `EasyXmlTree` representing the ebook's ONIX record.
		"""

		if not metadata_dom:
			metadata_dom = self.metadata_dom

		with importlib.resources.as_file(importlib.resources.files("se.data").joinpath("opf2onix.xsl")) as opf2onix_xsl_filename:
			with open(opf2onix_xsl_filename, "rb") as file:
				transform = etree.XSLT(etree.parse(file))
			onix_dom = EasyXmlTree(transform(etree.fromstring(str.encode(metadata_dom.to_string())), cwd=f"'{self.epub_root_path.as_posix()}/'"))

		return onix_dom

	def __process_direct_link(self, change_list: list[EndnoteChange], link: EasyXmlElement) -> bool:
		"""
		Checks all hyperlinks to the endnotes to see if the existing anchor needs to be updated with a new number.

		Returns a boolean of `needs_write` (whether object needs to be re-written).
		"""

		if self.endnotes_path is None:
			return False

		epub_type = link.get_attr("epub:type", True)
		if not epub_type: # It wasn't an actual endnote reference but a direct link (we hope!).
			href = link.get_attr("href")
			# Extract just the anchor from a URL (i.e., what follows a hash symbol).
			hash_position = href.find("#") + 1  # We want the characters *after* the hash.
			if hash_position > 0:
				old_anchor = href[hash_position:]
				try:
					change = next(ch for ch in change_list if ch.old_anchor == old_anchor)
					link.set_attr("href", f"{self.endnotes_path.name}#{change.new_anchor}")
					return True
				except StopIteration:  # Didn't find the old anchor, keep going.
					pass
		return False

	def __process_noteref_link(self, change_list: list[EndnoteChange], current_note_number: int, file_name: str, link: EasyXmlElement, needs_rewrite: bool, notes_changed: int) -> tuple[bool, int]:
		"""
		Checks each endnote link to see if the existing anchor needs to be updated with a new number.

		Returns a tuple of `needs_write` (whether object needs to be re-written), and the number of notes changed.
		"""

		if self.endnotes_path is None:
			return (False, 0)

		old_anchor = ""
		href = link.get_attr("href")
		# Extract just the anchor from a URL (i.e., what follows a hash symbol).
		hash_position = href.find("#") + 1  # We want the characters *after* the hash.
		if hash_position > 0:
			old_anchor = href[hash_position:]

		new_anchor = f"note-{current_note_number:d}"
		if new_anchor != old_anchor:
			endnote_change = EndnoteChange(old_anchor, new_anchor, file_name)
			change_list.append(endnote_change)
			notes_changed += 1
			# Update the link in the DOM.
			link.set_attr("href", f"{self.endnotes_path.name}#{new_anchor}")
			link.set_attr("id", f"noteref-{current_note_number:d}")
			link.lxml_element.text = str(current_note_number)
			needs_rewrite = True
		# Now try to find this in endnotes.
		matches = list(filter(lambda x, old=old_anchor: x.anchor == old, self.endnotes)) # type: ignore [arg-type, var-annotated]
		if not matches:
			raise se.InvalidInputException(f"Couldn’t find endnote with anchor [val]{old_anchor}[/].")
		if len(matches) > 1:
			raise se.InvalidInputException(f"Duplicate anchors in endnotes file for anchor [val]{old_anchor}[/].")
		# Found a single match, which is what we want.
		endnote = matches[0]
		endnote.number = current_note_number
		endnote.matched = True
		# We don't change the anchor or the back ref just yet.
		endnote.source_file = file_name
		return needs_rewrite, notes_changed

	def split_collection_files(self) -> None:
		"""
		If this ebook looks like a collection, split the collection file into multiple different files.

		For example, a file called `poetry.xhtml` containing `poetry.xhtml#poem-1` and `poetry.xhtml#poem-2` would be split into `poem-1.xhtml` and `poem-2.xhtml`.

		This is useful because eink Kobos don't support CSS `break-*` properties, so creating different files forces a page break on Kobos.

		Note that the new ToC won't include subheaders of new files, because the producer may have hand-edited the ToC. Currently, the `self.generate_toc()` function only creates a ToC wholesale, instead of exposing a function to create ToC entries for individual `<section>`s.

		See <https://github.com/kobolabs/epub-spec#css> for the CSS that Kobos support.
		"""

		for file_path in self.content_path.glob("**/*.xhtml"):
			dom = self.get_dom(file_path)

			# Does this file looks like a possible collection file?
			# It does if the only children of `<body>` are `<article>`s and `<section>`s, and there is more than one child.
			if dom.xpath("/html/body[contains(@epub:type, 'bodymatter') and count(./*[name() = 'article' or name() = 'section']) > 1 and count(./*[name() != 'article' and name() != 'section']) = 0]"):
				# Yes!

				# Apply any CSS files in the DOM to this file.
				for node in dom.xpath("/html/head/link[@rel='stylesheet']"):
					css_filename = (file_path.parent / node.get_attr("href")).resolve()
					dom.apply_css(self.get_file(css_filename), str(css_filename))

				# Do all of the `<article>`s/`<section>`s have `break-*: page` CSS?
				if dom.xpath("/html/body[count(./*[name() = 'article' or name() = 'section']) = count(./*[(name() = 'article' or name() = 'section') and @id and attribute::*[re:test(local-name(), '^data-css-break-(before|after)$')]])]"):
					# Yes. Now split this file!

					# A list of `{"filename": filename, "title": title}`.
					new_files: list[SplitFile] = []
					dom_template = deepcopy(dom)
					delete_original_file = True
					# Remove the children of `<body>`.
					for node in dom_template.xpath("/html/body/*"):
						node.remove()

					for article_node in dom.xpath("/html/body/*[name() = 'article' or name() = 'section']"):
						new_filename = article_node.get_attr("id") + ".xhtml"

						# Create a new DOM that we write to a new file.
						new_dom = deepcopy(dom_template)

						new_dom.xpath("/html/body")[0].append(article_node)

						title = se.formatting.generate_title(new_dom)
						for node in new_dom.xpath("/html/head/title"):
							node.set_text(title)

						with open(file_path.parent / new_filename, "w", encoding="utf-8") as xhtml_file:
							xhtml_file.write(new_dom.to_string())
							xhtml_file.truncate() # Truncate the file in case we're overwriting the original filename.

						se.formatting.format_xml_file(file_path.parent / new_filename)

						# Get a list of all IDs contained in this new DOM, so we can adjust any links in the ebook later.
						id_attrs = new_dom.xpath("/html/body/*[name() = 'article' or name() = 'section']//@id", str)

						new_files.append(SplitFile(new_filename, article_node.get_attr("id"), title, id_attrs))

						if new_filename == file_path.name:
							# We may run in to the case where the new filename is the same as the old filename, like `sonnets.xhtml`.
							delete_original_file = False

					# Replace the original file with the new files in the metadata spine.
					original_spine_node = self.metadata_dom.xpath(f"/package/spine/itemref[@idref='{file_path.name}']")[0]
					for new_file in new_files:
						original_spine_node.insert_before(EasyXmlElement(f"<itemref idref=\"{new_file.filename}\"/>"))

					original_spine_node.remove()

					# Generate the new ToC.
					# Don't use `self.generate_toc()` because the producer may have edited the ToC by hand.
					if delete_original_file:
						toc_dom = self.get_dom(self.toc_path)
						toc_node = toc_dom.xpath(f"/html/body/nav[@epub:type='toc']/ol//li[./a[re:test(@href, '^text/{file_path.name}')]]")[0]
						for new_file in new_files:
							li_node = EasyXmlElement("<li/>")
							li_node.append(EasyXmlElement(f"""<a href="text/{new_file.filename}">{se.formatting.escape_xml(new_file.title)}</a>"""))
							toc_node.insert_before(li_node)

						# Remove any ToC nodes that mention this file.
						for node in toc_dom.xpath(f"/html/body/nav[@epub:type='toc']/ol//li[./a[re:test(@href, '^text/{file_path.name}')]]"):
							node.remove()

						# If the ToC has a landmark node mentioning this file, replace it with the first `<article>`.
						for node in toc_dom.xpath(f"/html/body/nav[@epub:type='landmarks']/ol//li/a[re:test(@href, '^text/{file_path.name}')]"):
							node.set_attr("href", f"text/{new_files[0].filename}")

						with open(self.toc_path, "w", encoding="utf-8") as file:
							file.write(toc_dom.to_string())

					se.formatting.format_xml_file(self.toc_path)

					# Remove the original file.
					if delete_original_file:
						file_path.unlink()
					else:
						# Flush the DOM cache entry because since the filename is the same, we changed the DOM earlier.
						self.flush_dom(file_path)

					# Generate the new manifest.
					for node in self.metadata_dom.xpath("/package/manifest"):
						node.replace_with(self.generate_manifest())

					self.write_dom(self.metadata_file_path)

					se.formatting.format_xml_file(self.metadata_file_path)

					# Now iterate over all files in the ebook to update any links that might refer to the file we just split.
					for nested_file_path in self.content_path.glob("**/*.xhtml"):
						dom = self.get_dom(nested_file_path)

						# Replace links to the original file with no anchor with a link to the first `<article>`.
						for node in dom.xpath(f"/html/body//a[re:test(@href, '^(.+/)?{file_path.name}$')]"):
							node.set_attr("href", node.get_attr("href").replace(file_path.name, new_files[0].filename))

						# Replace anchored links with the new file.
						for node in dom.xpath(f"/html/body//a[re:test(@href, '^(.+/)?{file_path.name}#')]"):
							old_target_id = regex.sub(fr"^(.+/)?{file_path.name}#", "", node.get_attr("href"))

							for new_file in new_files:
								# Does the old target ID point to the top of a new file? If so, link directly to the new file, without an anchor.
								if old_target_id == new_file.id:
									node.set_attr("href", regex.sub(fr"^(.+/)?{file_path.name}#.+", fr"\1{new_file.filename}", node.get_attr("href")))
									break

								# Does the old target ID exist as a descendent of this new file?
								if old_target_id in new_file.descendant_id_attrs:
									node.set_attr("href", regex.sub(fr"^(.+/)?{file_path.name}#(.+)", fr"\1{new_file.filename}#\2", node.get_attr("href")))
									break

						with open(nested_file_path, "w", encoding="utf-8") as file:
							file.write(dom.to_string())
