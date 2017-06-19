# About

A collection of tools Standard Ebooks uses to produce its ebooks, including basic setup of ebooks, text processing, and build tools.

# Warning for Mac users

This repository started out as all Bash scripts targeting Ubuntu 16.04, and over time the tools have been converted to Python scripts for better cross-platform compatibility.  However not all the tools are converted yet, notably `build` and `create-draft`.  There have been many reports of breakage when using these scripts in a Mac environment.  Until we finish converting these last few scripts to Python, we suggest starting up an Ubuntu 16.04 virtual machine to run the `build` script.

# Installation

Several dependencies must be installed before you can use these tools. On Ubuntu 16.04, you can install everything with:

	sudo apt install python3-pip xsltproc libxml2-utils xmlstarlet libxml-xpath-perl recode html-xml-utils python3-cssselect python3-regex python3-pip librsvg2-bin libimage-exiftool-perl python3-lxml zip epubcheck calibre
	sudo pip3 install pyhyphen roman titlecase beautifulsoup4 smartypants

	# Install hyphenation dictionaries for the pyhyphen library
	sudo python3 -c "exec(\"from hyphen import dictools\\ndictools.install('en_GB')\\ndictools.install('en_US')\")"

	# Install required fonts
	mkdir -p ~/.fonts/
	wget -O ~/.fonts/LeagueSpartan-Bold.otf "https://github.com/theleagueof/league-spartan/blob/master/LeagueSpartan-Bold.otf?raw=true"
	wget -O ~/.fonts/OFLGoudyStM.otf "https://github.com/theleagueof/sorts-mill-goudy/blob/master/OFLGoudyStM.otf?raw=true"
	wget -O ~/.fonts/OFLGoudyStM-Italic.otf "https://github.com/theleagueof/sorts-mill-goudy/blob/master/OFLGoudyStM-Italic.otf?raw=true"
	sudo fc-cache -fv

You can also install the dependencies locally via pip:

    pip3 install -r requirements.txt

# Tool descriptions

-	### `british2american`

	Try to convert British quote style to American quote style in DIRECTORY/src/epub/text/.

	Quotes must already be "typogrified"--i.e. curly.

	This script isn't perfect; proofreading is required, especially near closing quotes near to em-dashes.

-	### `build`

	Build an ebook from a Standard Ebook source directory.

-	### `build-cover`

	Build an ebook cover a Standard Ebook source directory and place the output in DIRECTORY/src/epub/images/.

-	### `build-kobo`

	Convert files in a Standard Ebooks source directory to be Kobo-compatible.

-	### `clean`

	Prettify source files in a Standard Ebook source directory, including canonicalizing XML and minifying SVGs. Note that this only prettifies the source code; it doesn't perform typography changes.

-	### `create-draft`

	Create a skeleton of a new Standard Ebook.

-	### `dec2roman`

	Convert a decimal number to a Roman numeral.

-	### `endnotes2kindle`

	Convert epub-friendly endnotes to Kindle-friendly popup endnotes.

-	### `find-mismatched-diacritics`

	Find words with mismatched diacritics in Standard Ebook source directories.  For example, 'cafe' in one file and 'café' in another.

-	### `find-unused-selectors`

	Find unused local.css CSS selectors in Standard Ebook source directories.

-	### `hyphenate`

	Insert soft hyphens at syllable breaks in an XHTML file.

-	### `interactive-sr`

	A macro for calling Vim to interactively search and replace a regex on a list of files.

-	### `make-url-safe`

	Make a string URL-safe.

-	### `modernize-spelling`

	Modernize spelling of some archaic words, and replace words that may be archaically compounded with a dash to a more modern spelling.  For example, replace "ash-tray" with "ashtray".

-	### `ordinal`

	Print the ordinal for one or more integers.

-	### `prepare-release`

	Calculate the ebook's word count, and update content.opf and colophon.xhtml with release and modified timestamps.

-	### `print-manifest-and-spine`

	Create a ```<manifest>``` and ```<spine>``` tag for content.opf based on the passed Standard Ebooks source directory and print to standard output.

-	### `reading-ease`

	Calculate the Flesch reading ease for a Standard Ebooks source directory.

-	### `reorder-endnotes`

	Increment the specified endnote and all following endnotes by 1.

-	### `roman2dec`

	Convert a Roman numeral to a decimal number.

-	### `semanticate`

	Apply some scriptable semantics rules from the Standard Ebooks semantics manual to a Standard Ebook source directory.

-	### `simplify-tags`

	Simplify some HTML and CSS to be more compatible with crappier reading systems (ADE I'm looking at you...)

-	### `split-file`

	Split an XHTML file into many files at all instances of `<!--se:split-->`, and include a header template for each file.

-	### `titlecase`

	Convert a string to titlecase.

-	### `toc2kindle`

	Flatten ToC to be at most 2 levels deep for Kindle compatibility.  Generally only used by the `build` script and not called independently.

-	### `typogrify`

	Apply some scriptable typography rules from the Standard Ebooks typography manual to a Standard Ebook source directory.

-	### `unicode-names`

	Display Unicode code points, descriptions, and links to more details for each character in a string.  Useful for differentiating between different flavors of spaces, dashes, and invisible characters like word joiners.

-	### `update-asin`

	Change the ASIN of a mobi/azw3 file.

-	### `word-count`

	Count the number of words in an HTML file and optionally categorize by length.

-	### `view-modified`

	Check all author directories in the current or specified directory to see if there are changes that need to be committed.

# What a Standard Ebooks source directory looks like

Many of these tools act on Standard Ebooks source directories.  Such directories have a consistent minimal structure:

	.
	|-images/
	|--cover.jpg
	|--cover.source.jpg
	|--cover.svg
	|--titlepage.svg
	|-src/
	|--epub/
	|---css/
	|----core.css
	|----local.css
	|---images/
	|----cover.svg
	|----titlepage.svg
	|---text/
	|---content.opf
	|---onix.xml
	|---toc.xhtml
	|--META-INF/
	|---container.xml
	|--mimetype

`./images/` contains source images for the cover and titlepages, as well as ebook-specific source images.  Source images should be in their maximum available resolution, then compressed and placed in `./src/epub/images/` for distribution.

`./src/epub/` contains the actual epub files.
