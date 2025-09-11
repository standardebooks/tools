"""
This module implements the `se add-file` command.
"""

import argparse
import importlib.resources
import os
from pathlib import Path
import shutil

import se
from se.se_epub import SeEpub

def _copy_file(filename: str, dest_path: Path, force: bool) -> None:
	if not force and os.path.exists(dest_path):
		raise se.FileExistsException(f"File `{dest_path}` exists. Use `--force` to overwrite.")

	with importlib.resources.as_file(importlib.resources.files("se.data.templates").joinpath(filename)) as src_path:
		shutil.copyfile(src_path, dest_path)


def _replace_languague(file_path: Path, language: str | None) -> None:
	if language:
		with open(file_path, "r+", encoding="utf-8") as file:
			xhtml = file.read()
			xhtml = xhtml.replace("\"LANG\"", f"\"{language}\"")

			file.seek(0)
			file.write(xhtml)
			file.truncate()

def _insert_css(se_epub: SeEpub, filename: str) -> None:
	with importlib.resources.as_file(importlib.resources.files("se.data.templates").joinpath(filename)) as src_path:
		template_css = ""
		with open(src_path, "r", encoding="utf-8") as file:
			template_css = file.read()

	with open(se_epub.content_path / "css" / "local.css", "r+", encoding="utf-8") as file:
		css = file.read()
		css += "\n" + template_css

		file.seek(0)
		file.write(css)
		file.truncate()

def add_file(plain_output: bool) -> int: # pylint: disable=unused-argument
	"""
	Entry point for `se add-file`.
	"""

	file_types = ["dedication", "dramatis-personae", "endnotes", "epigraph", "glossary", "halftitlepage", "ignore"]

	parser = argparse.ArgumentParser(description="Add an SE template file and any accompanying CSS.")
	parser.add_argument("-f", "--force", dest="force", action="store_true", help="overwrite any existing files")
	parser.add_argument("file_type", metavar="FILE_TYPE", choices=file_types, help="the type of file to add; one of (" + ", ".join(file_types) + ")")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	return_code = 0

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)
		except se.SeException as ex:
			se.print_error(ex)
			return_code = ex.code
			return return_code

		try:
			match args.file_type:
				case "dedication":
					dest_path = se_epub.content_path / "text/dedication.xhtml"

					_copy_file("dedication.xhtml", dest_path, args.force)

					_replace_languague(dest_path, se_epub.language)

					_insert_css(se_epub, "dedication.css")

				case "dramatis-personae":
					dest_path = se_epub.content_path / "text/dramatis-personae.xhtml"

					_copy_file("dramatis-personae.xhtml", dest_path, args.force)

					_replace_languague(dest_path, se_epub.language)

					_insert_css(se_epub, "dramatis-personae.css")

				case "endnotes":
					dest_path = se_epub.content_path / "text/endnotes.xhtml"

					_copy_file("endnotes.xhtml", dest_path, args.force)

					_replace_languague(dest_path, se_epub.language)

				case "epigraph":
					dest_path = se_epub.content_path / "text/epigraph.xhtml"

					_copy_file("epigraph.xhtml", dest_path, args.force)

					_replace_languague(dest_path, se_epub.language)

					_insert_css(se_epub, "epigraph.css")

				case "glossary":
					dest_path = se_epub.content_path / "text/glossary.xhtml"

					_copy_file("glossary.xhtml", dest_path, args.force)

					_replace_languague(dest_path, se_epub.language)

					_insert_css(se_epub, "glossary.css")

				case "halftitlepage":
					subtitle = se_epub.get_subtitle()

					src_path ="halftitlepage.xhtml"

					if subtitle:
						src_path = "halftitlepage-subtitle.xhtml"

					dest_path = se_epub.content_path / "text/halftitlepage.xhtml"

					_copy_file(src_path, dest_path, args.force)

					_replace_languague(dest_path, se_epub.language)

					with open(dest_path, "r+", encoding="utf-8") as file:
						xhtml = file.read()

						xhtml = xhtml.replace(">TITLE<", f">{se_epub.get_title()}<")

						if subtitle:
							xhtml = xhtml.replace(">SUBTITLE<", f">{subtitle}<")

						file.seek(0)
						file.write(xhtml)
						file.truncate()

				case "ignore":
					dest_path = se_epub.path / "se-lint-ignore.xml"

					_copy_file("se-lint-ignore.xml", dest_path, args.force)


		except se.SeException as ex:
			se.print_error(ex)
			return_code = ex.code
			return return_code

	return return_code
