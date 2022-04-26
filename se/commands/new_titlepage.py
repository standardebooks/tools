"""
This module implements the `se convert-sectioning` command.
"""

import argparse
from pathlib import Path
import regex
import se
import se.easy_xml
import se.formatting
from se.se_epub import SeEpub


def new_titlepage(plain_output: bool) -> int: # pylint: disable=unused-argument
	"""
	Entry point for `se convert-sectioning`
	"""

	parser = argparse.ArgumentParser(description="Generate the <spine> element for the given Standard Ebooks source directory and write it to the ebook’s metadata file.")
	parser.add_argument("directories", metavar="DIRECTORY", nargs="+", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	for directory in args.directories:
		try:
			se_epub = SeEpub(directory)

			title = se_epub.metadata_dom.xpath("/package/metadata/dc:title[@id=\"title\"]/text()", True)

			with open(Path(directory) / "src/epub/text/titlepage.xhtml", "r+", encoding="utf-8") as file:
				xhtml = file.read()

				if "<h1" in xhtml:
					continue

				new_title = ""

				alt = regex.findall(r"alt=\"[^\"]+?\"", xhtml)[0].replace('alt="', "").replace('"', '')

				xhtml = regex.sub(r"alt=\"[^\"]+?\"", "alt=\"\"", xhtml)

				last_line = regex.findall(r" Illustrated by .+?$", alt)

				if last_line:
					illustrator = regex.sub(r"\.$", "", last_line[0].replace('  Illustrated by ', ''))
					new_title = new_title + f"<p>Illustrated by<br/><b>{illustrator}</b>.</p>"
					alt = alt.replace(last_line[0], "")


				last_line = regex.findall(r" Translated by .+?$", alt)

				if last_line:
					translator = regex.sub(r"\.$", "", last_line[0].replace('  Translated by ', ''))
					new_title = f"<p>Translated by<br/><b epub:type=\"z3998:translator\">{translator}</b>.</p>" + new_title
					alt = alt.replace(last_line[0], "")



				last_line = regex.findall(fr"{title}, by .+?$", alt)

				if last_line:
					author = regex.sub(r"\.$", "", last_line[0].replace(title + ', by ', ''))
					new_title = f"<p>By<br/><b epub:type=\"z3998:author\">{author}</b>.</p>" + new_title
					alt = alt.replace(last_line[0], "")


				#new_title = new_title.replace(".</b>", "</b>")

				new_title = f"<h1 epub:type=\"title\">{title}</h1>" + new_title


				xhtml = xhtml.replace('epub:type="titlepage">', f'epub:type="titlepage">{new_title}')

				file.seek(0)
				file.write(se.formatting.format_xhtml(xhtml))
				file.truncate()


		except se.SeException as ex:
			se.print_error(ex)
			return ex.code

	return 0
