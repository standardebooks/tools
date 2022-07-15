"""
This module implements the `se build-ids` command.
"""

import argparse
from typing import List, Tuple

import regex
from rich.console import Console

import se
import se.easy_xml
import se.formatting
from se.se_epub import SeEpub
from se.se_epub_lint import files_not_in_spine

def build_ids(plain_output: bool) -> int:
	"""
	Entry point for `se build-ids`
	"""

	parser = argparse.ArgumentParser(description="Change ID attributes for non-sectioning content to their expected values across the entire ebook. IDs must be globally unique and correctly referenced, and the ebook spine must be complete.")
	parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME, force_terminal=se.is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel

	for directory in args.directories:
		try:
			if args.verbose:
				console.print(se.prep_output(f"Processing [path][link=file://{directory}]{directory}[/][/] ...", plain_output))

			se_epub = SeEpub(directory)

			# First, check for spine sanity: no point in proceeding if it’s not correct
			missing_spine_files = files_not_in_spine(se_epub)
			if missing_spine_files:
				missing_spine_file_list = ", ".join([file.name for file in missing_spine_files])
				raise se.InvalidSeEbookException(f"Additional files not in spine: {missing_spine_file_list}")

			replacements: List[Tuple[se.easy_xml.EasyXmlElement, str]] = []
			id_counter = 0

			# Get a list of IDs that need to be replaced across the ebook
			for filename in se_epub.spine_file_paths:
				dom = se_epub.get_dom(filename)

				# First, get a list of all eligible elements with an ID.
				# We want to wipe their IDs so that we don't accidentally introduce duplicates.
				for node in dom.xpath("//*[@id and not(re:test(@epub:type, 'noteref')) and not(re:test(local-name(), '(section|article|nav|figure|dt|tr)'))]"):
					old_id = node.get_attr("id")
					new_id = f"se-replacement-id-{id_counter}"
					node.set_attr("id", new_id)

					# Match references in other files
					for other_file in se_epub.spine_file_paths:
						other_file_dom = se_epub.get_dom(other_file)
						write_to_disk = False
						for other_node in other_file_dom.xpath(f"/html/body//a[re:test(@href, '#{old_id}$')]"):
							other_node.set_attr("href", regex.sub(fr"#{old_id}$", f"#{new_id}", other_node.get_attr("href")))
							write_to_disk = True

						# If we changed this file, make sure to write it to disk
						if write_to_disk:
							with open(other_file, "w", encoding="utf-8") as file:
								file.write(other_file_dom.to_string())

					id_counter = id_counter + 1

				# Now, get a list of what we expect all eligible IDs to be.
				replacements = replacements + se.formatting.find_unexpected_ids(dom)

				# Write our wiped file, we'll update it later
				with open(filename, "w", encoding="utf-8") as file:
					file.write(dom.to_string())

			# Now, actually perform the replacements
			# Make sure to include the glossary search key map, if present
			files = se_epub.spine_file_paths
			if se_epub.glossary_search_key_map_path:
				files.append(se_epub.glossary_search_key_map_path)

			for filename in files:
				with open(filename, "r+", encoding="utf-8") as file:
					file_contents = file.read()

					for node, new_id in replacements:
						file_contents = regex.sub(fr"( id=\"|#){node.get_attr('id')}\"",  fr'\1{new_id}"', file_contents)

					file.seek(0)
					file.write(file_contents)
					file.truncate()

		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

	return 0
