# About 
This repository contains various tools Standard Ebooks uses to produce its ebooks.

## Build Tools 
### `british2american`
Try to convert British quote style to American quote style in DIRECTORY/src/epub/text/.

Quotes must already be "typogrified"--i.e. curly.

This script isn't perfect; proofreading is required, especially near closing quotes near to em-dashes.

### `build`

Build an ebook from a Standard Ebook source directory.

### `build-cover`

Build an ebook cover a Standard Ebook source directory and place the output in DIRECTORY/src/epub/images/.

### `build-kobo`

Convert files in a Standard Ebooks source directory to be Kobo-compatible.

### `clean`

Prettify source files in a Standard Ebook source directory, including canonicalizing XML and minifying SVGs. Note that this only prettifies the source code; it doesn't perform typography changes.

### `create-draft`

Create a skeleton of a new Standard Ebook.

### `dec2roman`

Convert a decimal number to a Roman numeral.

### `endnotes2kindle`

Convert epub-friendly endnotes to Kindle-friendly popup endnotes.

### `find-mismatched-diacritics`

Find words with mismatched diacritics in Standard Ebook source directories.  For example, 'cafe' in one file and 'café' in another.

### `find-unused-selectors`

Find unused local.css CSS selectors in Standard Ebook source directories.

### `hyphenate`

Insert soft hyphens at syllable breaks in an XHTML file.

### `interactive-sr`

A macro for calling Vim to interactively search and replace a regex on a list of files.

### `make-url-safe`

Convert all arguments to URL-safe strings.

### `modernize-spelling`

Modernize spelling of some archaic words, and replace words that may be archaically compounded with a dash to a more modern spelling.  For example, replace "ash-tray" with "ashtray".

### `ordinal`

Print the ordinal for one or more integers.

### `prepare-release`

Calculate the ebook's word count, and update content.opf and colophon.xhtml with release and modified timestamps.

### `print-manifest-and-spine`

Create a ```<manifest>``` and ```<spine>``` tag for content.opf based on the passed Standard Ebooks source directory and print to standard output.

### `reading-ease`

Calculate the Flesch reading ease for a Standard Ebooks source directory.

### `reorder-endnotes`

Increment the specified endnote and all following endnotes by 1.

### `roman2dec`

Convert a Roman numeral to a decimal number.

### `semanticate`

Apply some scriptable semantics rules from the Standard Ebooks semantics manual to a Standard Ebook source directory.

### `simplify-tags`
Simplify some HTML and CSS to be more compatible with crappier reading systems (ADE I'm looking at you...)

### `split-file`

Split an XHTML file into many files at all instances of `<!--se:split-->`, and include a header template for each file.

### `titlecase`

Convert a string to titlecase.

### `toc2kindle`

Flatten ToC to be at most 2 levels deep for Kindle compatibility.  Generally only used by the `build` script and not called independently.

### `typogrify`

Apply some scriptable typography rules from the Standard Ebooks typography manual to a Standard Ebook source directory.

### `unicode-names`

Display Unicode code points, descriptions, and links to more details for each character in a string.  Useful for differentiating between different flavors of spaces, dashes, and invisible characters like word joiners.

### `update-asin`

Change the ASIN of a mobi/azw3 file.

### `word-count`

Count the number of words in an HTML file and optionally categorize by length.

### `view-modified`

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

./images/ contains source images for the cover and titlepages, as well as ebook-specific source images.  Source images should be in their maximum available resolution, then compressed and placed in ./src/epub/images/ for distribution.

./src/epub/ contains the actual epub files.

# Setting up your build environment

1.	Install dependencies.  On Ubuntu 16.04, you can do:

		sudo apt-add-repository ppa:svg-cleaner-team/svgcleaner
		sudo apt-get install xsltproc libxml2-utils xmlstarlet libxml-xpath-perl svgcleaner recode html-xml-utils python3-cssselect python3-regex python3-pip librsvg2-bin libimage-exiftool-perl python3-lxml zip epubcheck calibre
		sudo pip3 install pyhyphen roman titlecase beautifulsoup4
		sudo python3 -c "exec(\"from hyphen import dictools\\ndictools.install('en_GB')\\ndictools.install('en_US')\")"

2.	If you plan on editing cover or titlepage images, make sure the League Spartan and Sorts Mill Goudy fonts are installed on your system: [https://github.com/theleagueof/league-spartan](https://github.com/theleagueof/league-spartan), [https://github.com/theleagueof/sorts-mill-goudy](https://github.com/theleagueof/sorts-mill-goudy)

That should be it!
