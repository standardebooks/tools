#About this repository

This repository contains various tools Standard Ebooks uses to produce its ebooks.

##british2american

Try to convert British quote style to American quote style in DIRECTORY/src/epub/text/.

Quotes must already be "typogrified"--i.e. curly.

This script isn't perfect; proofreading is required, especially near closing quotes near to em-dashes.

##build

Build an ebook from a Standard Ebooks ebook source directory and place the output in DIRECTORY/dist/.

##build-cover

Build an ebook cover a Standard Ebooks ebook source directory and place the output in DIRECTORY/src/epub/images/.

##clean

Prettify source files in a Standard Ebooks ebook source directory, including canonicalizing XML and minifying SVGs. Note that this only prettifies the source code; it doesn't perform typography changes.

##create-draft

Create a skeleton of a new Standard Ebooks ebook.

##endnotes2kindle

Convert epub-friendly endnotes to Kindle-friendly popup endnotes.  Generally only used by the `build` script and not called independently.

##modernize-hyphenation

Replace words that may be archaically compounded with a dash to a more modern spelling.  For example, replace "ash-tray" with "ashtray".

##pre-commit

A useful script to put in .git/hooks that will automatically update content.opf and colophon.xhtml with word count and timestamp information.

##split-file

Split an XHTML file into many files at all instances of <!--se:split-->, and include a header template for each file.

##view-modified

Check all author directories in the current or specified directory to see if there are changes that need to be committed.

##dec2roman

Convert a decimal number to a Roman numeral.

##roman2dec

Convert a Roman numeral to a decimal number.

##titlecase

Convert a string to titlecase.

##unicode-names

Display Unicode code points, descriptions, and links to more details for each character in a string.  Useful for differentiating between different flavors of spaces, dashes, and invisible characters like word joiners.

##update-asin

Change the ASIN of a mobi file.

##wordcount

Get a word count of an XHTML file.

#What a Standard Ebooks source directory looks like

Many of these tools act on Standard Ebooks source directories.  Such directories have a consistent minimal structure:

	.
	|-dist/
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
	
./dist/ contains built ebook files ready for distribution.

./images/ contains source images for the cover and titlepages, as well as ebook-specific source images.  Source images should be in their maximum available resolution, then compressed and placed in ./src/epub/images/ for distribution.

./src/epub/ contains the actual epub files.
	
#Setting up your build environment

1.	Download and install Calibre: http://calibre-ebook.com/download

	**Important:** Don't use the version of Calibre included with your system's package manager.  That's almost always an out-of-date version that will cause problems.  Install it by downloading it directly from the Calibre website.
	
2.	Download and install epubcheck: https://github.com/IDPF/epubcheck/releases
	
	Currently you have to place it in /opt/epubcheck/.

3.	Install other dependencies.  On Ubuntu 15.04, you can do:
		
		sudo apt-add-repository ppa:svg-cleaner-team/svgcleaner
		sudo apt-get install xsltproc libxml2-utils xmlstarlet libxml-xpath-perl svgcleaner recode html-xml-utils
		pip install roman titlecase beautifulsoup4
		
That should be it!
