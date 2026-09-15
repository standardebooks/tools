"""
This module implements the `se build` command.
"""

import argparse
import os
import shutil
from pathlib import Path
from hashlib import sha256

from rich import box
from rich.console import Console, RenderableType
from rich.table import Table
from rich.text import Text
from rich.style import Style
import regex

import se
from se.se_epub import SeEpub
from se.se_help_formatter import SeHelpFormatter
from se.formatting import make_url_safe

def _highlight_checker_message(text: str, filename: Path | None) -> Text:
	"""Apply semantic colors to checker diagnostics without interpreting external text as markup."""
	output = Text(text)
	for match in regex.finditer(r"(?P<xml><(?:[^>\"']|\"[^\"]*\"|'[^']*')+>)|(?P<url>https?://[^\s<>\"’”]+)|[\"“‘'](?P<quoted>[^\"”’'\n]+)[\"”’']", output.plain):
		start, end = match.span()
		if match.group("xml"):
			for span in se.highlight_xml(match.group()).spans:
				output.stylize(span.style, start + span.start, start + span.end)
		elif match.group("url"):
			url = match.group().rstrip(".,;)")
			output.stylize("url", start, start + len(url))
			output.stylize(Style(link=url), start, start + len(url))
		else:
			start, end = match.span("quoted")
			value = match.group("quoted")
			context = output.plain[:match.start()]
			style = "val"
			if regex.search(r"\b(?:attribute|attributes)\s+$", context, regex.IGNORECASE):
				style = "attr"
			elif regex.search(r"\b(?:element|elements|tag)\s+$", context, regex.IGNORECASE):
				style = "xhtml"
			elif regex.search(r"\.(?:xhtml|html|opf|ncx|css|svg|png|jpe?g|epub|woff2?|ttf|otf)(?:#.*)?$", value, regex.IGNORECASE):
				style = "path"
				if filename:
					path, _, fragment = value.partition("#")
					url = (filename.parent / path).resolve().as_uri()
					output.stylize(Style(link=f"{url}#{fragment}" if fragment else url), start, end)
			output.stylize(style, start, end)

	# Highlight attribute assignments separately so fragments inside diagnostic quotes retain XML syntax colors.
	for match in regex.finditer(r"(?<![\w:.-])(?P<attribute>[\p{L}_:][\w:.-]*)\s*=\s*(?P<value>\"[^\"]*\"|'[^']*')", output.plain):
		output.stylize("attr", *match.span("attribute"))
		output.stylize("val", *match.span("value"))

	return output

def build(plain_output: bool) -> int:
	"""
	Entry point for `se build`.
	"""

	parser = argparse.ArgumentParser(description="Build compatible [path].epub[/] and advanced [path].epub[/] ebooks from a Standard Ebook source directory. Output is placed in the current directory, or the target directory with [flag]--output-dir[/].", prog="[command]se[/] [subcommand]build[/]", formatter_class=SeHelpFormatter)
	parser.add_argument("-b", "--kobo", dest="build_kobo", action="store_true", help="Also build a [path].kepub.epub[/] file for Kobo.")
	parser.add_argument("-c", "--check", action="store_true", help="Use epubcheck to validate the compatible [path].epub[/] file, and the Nu Validator (v.Nu) to validate XHTML5; if Ace is installed, also validate using Ace; if [flag]--kindle[/] is also specified and epubcheck, v.Nu, or Ace fail, don’t create a Kindle file.")
	parser.add_argument("-k", "--kindle", dest="build_kindle", action="store_true", help="Also build an [path].azw3[/] file for Kindle.")
	parser.add_argument("-n", "--no-cache", action="store_true", help="Don’t use cached generated images; always rebuild them.")
	parser.add_argument("-o", "--output-dir", metavar="[path]DIRECTORY[/]", type=str, default="", help="A directory to place output files in; will be created if it doesn’t exist.")
	parser.add_argument("-p", "--proof", dest="proof", action="store_true", help="Insert additional CSS rules that are helpful for proofreading; output filenames will end in .proof.")
	parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity.")
	parser.add_argument("-y", "--check-only", action="store_true", help="Run tests used by [flag]--check[/], but don’t output any ebook files, and exit after checking.")
	parser.add_argument("directories", metavar="[path]DIRECTORY[/]", nargs="+", help="A Standard Ebooks source directory.")
	args = parser.parse_args()

	called_from_parallel = se.is_called_from_parallel(False)
	force_terminal = se.should_output_color()
	first_output = True
	return_code = 0

	build_cache_root_directory = se.get_cache_directory() / "build"
	build_cache_directory = build_cache_root_directory / "ebooks"

	# Rich needs to know the terminal width in order to format tables.
	# If we're called from Parallel, there is no width because Parallel is not a terminal. Thus we must export `$COLUMNS` before invoking Parallel, and then get that value here.
	console = Console(width=int(os.environ["COLUMNS"]) if called_from_parallel and "COLUMNS" in os.environ else None, highlight=False, theme=se.RICH_THEME, force_terminal=force_terminal) # Syntax highlighting will do weird things when printing paths; `force_terminal` prints colors when called from GNU Parallel.

	if args.check_only and (args.check or args.build_kindle or args.build_kobo or args.proof or args.output_dir):
		se.print_error("The [flag]--check-only[/] option can’t be combined with any other flags except for [flag]--verbose[/].", plain_output=plain_output)
		return se.InvalidArgumentsException.code

	try:
		max_cache_size = se.parse_size_string(se.get_config_value("/configuration/build/@max-cache-size"))
		if max_cache_size <= 0:
			max_cache_size = None

	except se.InvalidArgumentsException as ex:
		se.print_error(f"Invalid value for maximum cache size in [link=file://{se.get_config_file()}]configuration file[/].", plain_output=plain_output)
		return ex.code

	if args.verbose and not called_from_parallel:
		console.print(f"Using [path][link={build_cache_directory}]{build_cache_directory}[/][/] to cache files.")

	for directory in args.directories:
		directory = Path(directory).resolve()
		messages = []
		exception = None
		table_data: list[list[RenderableType]] = []
		has_output = False

		try:
			se_epub = SeEpub(directory)

			if se_epub.identifier is None:
				raise se.InvalidSeEbookException("Couldn’t determine ebook identifier.")

			if args.no_cache:
				ebook_cache_directory = None
			else:
				identifier = regex.sub(r"^https://standardebooks\.org/ebooks/", "", se_epub.identifier)
				ebook_cache_directory = build_cache_directory / f"{sha256(se_epub.identifier.encode('utf-8')).hexdigest()}-{make_url_safe(identifier)}"

				try:
					ebook_cache_directory.mkdir(parents=True, exist_ok=True)

					if not os.access(ebook_cache_directory, os.W_OK):
						raise se.SeException()

				except Exception:
					# If we failed to write the cache directory, notify the user in verbose mode and continue anyway without the cache.
					if args.verbose:
						console.print(f"Couldn’t write to [path][link={ebook_cache_directory}]{ebook_cache_directory}[/][/]; continuing without cache.")

					ebook_cache_directory = None

			# Now build the ebook!
			se_epub.build(args.check, args.check_only, args.build_kobo, args.build_kindle, Path(args.output_dir), args.proof, ebook_cache_directory)

			# If our cache directory is empty after building, then delete it.
			if ebook_cache_directory:
				try:
					if ebook_cache_directory.is_dir() and not any(ebook_cache_directory.iterdir()):
						ebook_cache_directory.unlink()
				except Exception:
					pass

		except se.BuildFailedException as ex:
			exception = ex
			messages = ex.messages
			return_code = ex.code
		except se.SeException as ex:
			se.print_error(ex)
			return_code = ex.code

		# Print a separator newline if more than one table is printed.
		if not first_output and (args.verbose or messages or exception):
			console.print("")
		elif first_output:
			first_output = False

		# Print the table header.
		if ((len(args.directories) > 1 or called_from_parallel) and (messages or exception)) or args.verbose:
			has_output = True
			if plain_output:
				console.print(directory)
			else:
				console.print(f"[reverse][path][link=file://{directory}]{directory}[/][/][/reverse]")

		if exception:
			has_output = True
			se.print_error(exception, plain_output=plain_output)

		# Print the tables.
		if messages:
			has_output = True
			return_code = se.BuildFailedException.code

			if plain_output:
				for message in messages:
					message_filename = ""
					if message.filename:
						message_filename = message.filename.name

					console.print(f"{message.source}: {message.code} {message_filename}{message.location if message.location else ''} {message.text}", markup=False)
			else:
				for message in messages:
					# Add hyperlinks around message filenames.
					message_filename = Text()
					if message.filename:
						message_filename.append(message.filename.name, style="path")
						message_filename.stylize(Style(link=f"{message.filename.resolve().as_uri()}{message.link_location or ''}"))
						message_filename.append(message.location or "")

					table_data.append([Text(message.source, style="command"), Text(message.code, style="text"), message_filename, _highlight_checker_message(message.text, message.filename)])

					if message.submessages:
						for submessage in message.submessages:
							# Keep excerpts dim while retaining semantic XML syntax colors.
							submessage_object = se.highlight_xml(submessage)
							submessage_object.stylize_before("dim")

							table_data.append([" ", " ", Text("→", justify="right"), submessage_object])

				table = Table(show_header=True, header_style="bold", show_lines=True, expand=True)
				table.add_column("Source", width=9, no_wrap=True)
				table.add_column("Code", no_wrap=True)
				table.add_column("File", no_wrap=True)
				table.add_column("Message", ratio=10)

				for row in table_data:
					table.add_row(row[0], row[1], row[2], row[3])

				console.print(table)

		if args.verbose and not messages and not exception:
			if plain_output:
				console.print("OK")
			else:
				table = Table(show_header=False, box=box.SQUARE)
				table.add_column("", style="white on green4 bold")
				table.add_row("OK")
				console.print(table)

		# Print a newline if we're called from Parallel and we just printed something, to better visually separate output blocks.
		if called_from_parallel and has_output:
			console.print("")

		if max_cache_size is not None:
			# Check if we have to prune the cache before continuing to the next ebook.
			# We prune if `max_cache_size` is set, *and* if there is more than one cached ebook.
			if build_cache_directory.is_dir():
				ebook_cache_directories = [path for path in build_cache_directory.iterdir() if path.is_dir()]

				while len(ebook_cache_directories) > 1 and se.get_directory_size(build_cache_directory) > max_cache_size:
					try:
						oldest_cache_directory = min(ebook_cache_directories, key=lambda path: path.stat().st_mtime)
					except OSError:
						continue

					shutil.rmtree(oldest_cache_directory, ignore_errors=True)
					ebook_cache_directories.remove(oldest_cache_directory)

	return return_code
