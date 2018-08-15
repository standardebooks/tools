# About

A collection of tools Standard Ebooks uses to produce its ebooks, including basic setup of ebooks, text processing, and build tools.

# Installation

## Ubuntu 18.04 (Bionic) users

```shell
# Install some pre-flight dependencies
# lxml requires the following packages for its pip build process: python3-dev libxml2-dev libxslt1-dev zlib1g-dev
sudo apt install -y python3-pip python3-dev libxml2-dev libxslt1-dev zlib1g-dev libxml2-utils librsvg2-bin libssl-dev libimage-exiftool-perl imagemagick epubcheck default-jre inkscape calibre curl git

# Clone the tools repo
git clone https://github.com/standardebooks/tools.git

# Install required fonts
mkdir -p ~/.local/share/fonts/
curl -s -o ~/.local/share/fonts/LeagueSpartan-Bold.otf "https://raw.githubusercontent.com/theleagueof/league-spartan/master/LeagueSpartan-Bold.otf"
curl -s -o ~/.local/share/fonts/OFLGoudyStM.otf "https://raw.githubusercontent.com/theleagueof/sorts-mill-goudy/master/OFLGoudyStM.otf"
curl -s -o ~/.local/share/fonts/OFLGoudyStM-Italic.otf "https://raw.githubusercontent.com/theleagueof/sorts-mill-goudy/master/OFLGoudyStM-Italic.otf"

# Refresh the local font cache
sudo fc-cache -fv

# Install python dependencies
pip3 install -r ./tools/requirements.txt
```

## macOS users

These instructions were tested on macOS 10.12 and 10.13. Your mileage may vary. Corrections and fixes to these steps are welcomed, as the SE maintainers don’t have access to Macs.

1. Install the [Homebrew package manager](https://brew.sh). Or, if you already have it installed, make sure it’s up to date:

    ```shell
    brew update
    ```

2. Install dependencies:

	```shell
	# Install some pre-flight dependencies
	brew install python epubcheck imagemagick libmagic librsvg exiftool git

	# Clone the tools repo
	git clone https://github.com/standardebooks/tools.git

	# Install required applications
	brew cask install java calibre xquartz inkscape

	# Install required fonts
	curl -s -o ~/Library/Fonts/LeagueSpartan-Bold.otf "https://raw.githubusercontent.com/theleagueof/league-spartan/master/LeagueSpartan-Bold.otf"
	curl -s -o ~/Library/Fonts/OFLGoudyStM.otf "https://raw.githubusercontent.com/theleagueof/sorts-mill-goudy/master/OFLGoudyStM.otf"
	curl -s -o ~/Library/Fonts/OFLGoudyStM-Italic.otf "https://raw.githubusercontent.com/theleagueof/sorts-mill-goudy/master/OFLGoudyStM-Italic.otf"

	# Install python dependencies
	pip3 install -r ./tools/requirements.txt
	```

# TODO

Help and pull requests are welcomed!

- Move some legacy scripts like `hyphenate` into appropriate libraries/scripts.

- Some tool functionality should be moved into the SeEpub class. Suggestions on how to better organize SE code into packages/classes are welcome.

# Tool descriptions

-	### `british2american`

	Try to convert British quote style to American quote style in DIRECTORY/src/epub/text/.

	Quotes must already be typogrified using the ```typogrify``` tool.

	This script isn’t perfect; proofreading is required, especially near closing quotes near to em-dashes.

-	### `build`

	Build an ebook from a Standard Ebook source directory.

-	### `build-images`

	Build ebook cover and titlepage images in a Standard Ebook source directory and place the output in DIRECTORY/src/epub/images/.

-	### `clean`

	Prettify and canonicalize individual XHTML or SVG files, or all XHTML and SVG files in a source directory.  Note that this only prettifies the source code; it doesn’t perform typography changes.

-	### `compare-versions`

	Use Firefox to render and compare XHTML files in an ebook repository. Run on a dirty repository to visually compare the repository’s dirty state with its clean state.

-	### `create-draft`

	Create a skeleton of a new Standard Ebook.

-	### `dec2roman`

	Convert a decimal number to a Roman numeral.

-	### `extract-ebook`

	Extract an EPUB, MOBI, or AZW3 ebook into ./FILENAME.extracted/ or a target directory.

-	### `find-mismatched-diacritics`

	Find words with mismatched diacritics in Standard Ebook source directories.  For example, ```cafe``` in one file and ```café``` in another.

-	### `hyphenate`

	Insert soft hyphens at syllable breaks in an XHTML file.

-	### `interactive-sr`

	A macro for calling Vim to interactively search and replace a regex on a list of files.

-	### `lint`

	Check for various Standard Ebooks style errors.

-	### `make-url-safe`

	Make a string URL-safe.

-	### `modernize-spelling`

	Modernize spelling of some archaic words, and replace words that may be archaically compounded with a dash to a more modern spelling.  For example, replace ```ash-tray``` with ```ashtray```.

-	### `prepare-release`

	Calculate work word count, insert release date if not yet set, and update modified date and revision number.

-	### `print-manifest-and-spine`

	Create a ```<manifest>``` and ```<spine>``` tag for content.opf based on the passed Standard Ebooks source directory and print to standard output.

-	### `reading-ease`

	Calculate the Flesch reading ease for a Standard Ebooks source directory.

-	### `recompose-epub`

	Recompose a Standard Ebooks source directory into a single HTML5 file, and print to standard output.

-	### `reorder-endnotes`

	Increment the specified endnote and all following endnotes by 1.

-	### `roman2dec`

	Convert a Roman numeral to a decimal number.

-	### `semanticate`

	Apply some scriptable semantics rules from the Standard Ebooks semantics manual to a Standard Ebook source directory.

-	### `split-file`

	Split an XHTML file into many files at all instances of `<!--se:split-->`, and include a header template for each file.

-	### `titlecase`

	Convert a string to titlecase.

-	### `typogrify`

	Apply some scriptable typography rules from the Standard Ebooks typography manual to a Standard Ebook source directory.

-	### `unicode-names`

	Display Unicode code points, descriptions, and links to more details for each character in a string.  Useful for differentiating between different flavors of spaces, dashes, and invisible characters like word joiners.

-	### `word-count`

	Count the number of words in an HTML file and optionally categorize by length.


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
