# About

A collection of tools Standard Ebooks uses to produce its ebooks, including basic setup of ebooks, text processing, and build tools.

# Installation

## Step 1a: Ubuntu 16.04 users

```shell
# Install some pre-flight dependencies
# python3-dev libxml2-dev libxslt1-dev zlib1g-dev are required for building lxml via pip
sudo apt install -y python3-pip python3-dev libxml2-dev libxslt1-dev zlib1g-dev libxml2-utils librsvg2-bin libimage-exiftool-perl imagemagick epubcheck default-jre inkscape calibre curl git

# Install required fonts
mkdir -p ~/.fonts/
curl -s -o ~/.fonts/LeagueSpartan-Bold.otf "https://raw.githubusercontent.com/theleagueof/league-spartan/master/LeagueSpartan-Bold.otf"
curl -s -o ~/.fonts/OFLGoudyStM.otf  "https://raw.githubusercontent.com/theleagueof/sorts-mill-goudy/master/OFLGoudyStM.otf"
curl -s -o ~/.fonts/OFLGoudyStM-Italic.otf "https://raw.githubusercontent.com/theleagueof/sorts-mill-goudy/master/OFLGoudyStM-Italic.otf"

# Refresh the local font cache
sudo fc-cache -fv
```

## Step 1b: Mac OS users

These instructions were tested on Mac OS X 10.12. Your mileage may vary.

1. Install the [Homebrew package manager](https://brew.sh). Or, if you already have it installed, make sure it's up to date:

    ```shell
    brew update
    ```

2. Install dependencies:

	```shell
	# Install some pre-flight dependencies
	brew install python3 epubcheck imagemagick librsvg exiftool

	# Install required applications
	brew cask install java calibre xquartz inkscape

	# Install required fonts
	curl -s -o ~/Library/Fonts/LeagueSpartan-Bold.otf "https://github.com/theleagueof/league-spartan/blob/master/LeagueSpartan-Bold.otf?raw=true"
	curl -s -o ~/Library/Fonts/OFLGoudyStM.otf "https://github.com/theleagueof/sorts-mill-goudy/blob/master/OFLGoudyStM.otf?raw=true"
	curl -s -o ~/Library/Fonts/OFLGoudyStM-Italic.otf "https://github.com/theleagueof/sorts-mill-goudy/blob/master/OFLGoudyStM-Italic.otf?raw=true"
	```

## Step 2: All platforms

```shell
# Clone the tools repo
git clone https://github.com/standardebooks/tools.git

# Install python dependencies
pip3 install -r ./tools/requirements.txt

# Install hyphenation dictionaries for the pyhyphen library
python3 -c "exec(\"from hyphen import dictools\\ndictools.install('en_GB')\\ndictools.install('en_US')\")"
```

# TODO

Help and pull requests are welcomed!

- Move some legacy scripts like `build-kobo` and `endnotes2kindle` into appropriate libraries/scripts.

- Update scripts to use new library global variables like `XHTML_NAMESPACES`, instead of redefining them in each script.


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

	Prettify and canonicalize individual XHTML or SVG files, or all XHTML and SVG files in a source directory.  Note that this only prettifies the source code; it doesn't perform typography changes.

-	### `create-draft`

	Create a skeleton of a new Standard Ebook.

-	### `dec2roman`

	Convert a decimal number to a Roman numeral.

-	### `endnotes2kindle`

	Convert epub-friendly endnotes to Kindle-friendly popup endnotes.

-	### `extract-ebook`

	Extract an EPUB, MOBI, or AZW3 ebook into ./FILENAME.extracted/ or a target directory.

-	### `find-mismatched-diacritics`

	Find words with mismatched diacritics in Standard Ebook source directories.  For example, 'cafe' in one file and 'café' in another.

-	### `hyphenate`

	Insert soft hyphens at syllable breaks in an XHTML file.

-	### `interactive-sr`

	A macro for calling Vim to interactively search and replace a regex on a list of files.

-	### `lint`

	Check for various Standard Ebooks style errors.

-	### `make-url-safe`

	Make a string URL-safe.

-	### `modernize-spelling`

	Modernize spelling of some archaic words, and replace words that may be archaically compounded with a dash to a more modern spelling.  For example, replace "ash-tray" with "ashtray".

-	### `ordinal`

	Print the ordinal for one or more integers.

-	### `prepare-release`

	Calculate work word count, insert release date if not yet set, and update modified date and revision number.

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
	|----colophon.xhtml
	|----imprint.xhtml
	|----titlepage.xhtml
	|----uncopyright.xhtml
	|---content.opf
	|---onix.xml
	|---toc.xhtml
	|--META-INF/
	|---container.xml
	|--mimetype
	|-LICENSE.md

`./images/` contains source images for the cover and titlepages, as well as ebook-specific source images.  Source images should be in their maximum available resolution, then compressed and placed in `./src/epub/images/` for distribution.

`./src/epub/` contains the actual epub files.
