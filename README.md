# About

A collection of tools Standard Ebooks uses to produce its ebooks, including basic setup of ebooks, text processing, and build tools.

Installing this toolset using `pipx` makes the `se` command line executable available. Its various commands are described below, or you can use `se help` to list them.

# Installation

The toolset requires Python >= 3.8 and <= 3.12.

To install the toolset locally for development and debugging, see [Installation for toolset developers](#installation-for-toolset-developers).

Optionally, install [Ace](https://daisy.github.io/ace/) and the `se build --check` command will automatically run it as part of the checking process.

## Ubuntu 24.04 (Noble) users

```shell
# Install some pre-flight dependencies.
sudo apt install -y calibre default-jre git python3-dev python3-pip python3-venv pipx

# Install the toolset.
pipx install standardebooks
```

## Ubuntu 20.04 (Trusty) users

```shell
# Install some pre-flight dependencies.
sudo apt install -y calibre default-jre git python3-dev python3-pip python3-venv

# Install `pipx`.
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install the toolset.
pipx install --python=3.12 --fetch-missing-python standardebooks
```

### Optional: Install shell completions

```shell
# Install ZSH completions.
sudo ln -s $(pipx environment --value PIPX_LOCAL_VENVS)/standardebooks/lib/python3.*/site-packages/se/completions/zsh/_se /usr/share/zsh/vendor-completions/_se && hash -rf && compinit

# Install Bash completions.
sudo ln -s $(pipx environment --value PIPX_LOCAL_VENVS)/standardebooks/lib/python3.*/site-packages/se/completions/bash/se /usr/share/bash-completion/completions/se

# Install Fish completions.
ln -s $(pipx environment --value PIPX_LOCAL_VENVS)/standardebooks/lib/python3.*/site-packages/se/completions/fish/se.fish $HOME/.config/fish/completions/
```

## Fedora 41 users

```shell
# Install some pre-flight dependencies.
sudo dnf install pipx python3.12 python3.12-devel gcc libxslt-devel calibre git java-21-openjdk-headless

# Ensure `$PATH` environment variable is correctly set up for `pipx`.
pipx ensurepath

# Install the toolset.
pipx install --python=3.12 standardebooks
pipx inject standardebooks setuptools
```

### Optional: Install shell completions

```shell
# Install ZSH completions.
sudo ln -s $(pipx environment --value PIPX_LOCAL_VENVS)/standardebooks/lib/python3.*/site-packages/se/completions/zsh/_se /usr/share/zsh/vendor-completions/_se && hash -rf && compinit

# Install Bash completions.
sudo ln -s $(pipx environment --value PIPX_LOCAL_VENVS)/standardebooks/lib/python3.*/site-packages/se/completions/bash/se /usr/share/bash-completion/completions/se

# Install Fish completions.
ln -s $(pipx environment --value PIPX_LOCAL_VENVS)/standardebooks/lib/python3.*/site-packages/se/completions/fish/se $HOME/.config/fish/completions/se.fish
```

## macOS users

1. Install the [Homebrew package manager](https://brew.sh). Or, if you already have it installed, make sure it’s up-to-date:

	```shell
	brew update
	```

2. Install dependencies:

	```shell
	# Install some pre-flight dependencies.
	brew install cairo calibre git openjdk pipx python@3.12
	pipx ensurepath
	sudo ln -sfn $(brew --prefix)/opt/openjdk/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk.jdk

	# Install the toolset.
	pipx install --python "$(brew --prefix)"/bin/python3.12 standardebooks

	# Optional: Bash users who have set up bash-completion via brew can install tab completion.
	ln -s $(pipx environment --value PIPX_LOCAL_VENVS)/standardebooks/lib/python3.*/site-packages/se/completions/bash/se $(brew --prefix)/etc/bash_completion.d/se

	# Optional: Fish users can install tab completion.
	ln -s $(pipx environment --value PIPX_LOCAL_VENVS)/standardebooks/lib/python3.*/site-packages/se/completions/fish/se $HOME/.config/fish/completions/se.fish
	```

## OpenBSD 6.6 Users

These instructions were tested on OpenBSD 6.6, but may also work on the 6.5 release as well.

1. Create a text file to feed into `pkg_add` called `~/standard-ebooks-packages`. It should contain the following:

	```shell
	py3-pip--
	py3-virtualenv--
	py3-gitdb--
	jdk--%11
	calibre--
	git--
	```

2. Install dependencies using `doas pkg_add -ivl ~/standard-ebooks-packages`. Follow linking instructions provided by `pkg_add` to save keystrokes, unless you want to have multiple python versions and pip versions. In my case, I ran `doas ln -sf /usr/local/bin/pip3.7 /usr/local/bin/pip`.

3. Add `~/.local/bin` to your path.

4. Run `pip install --user pipx`

5. If you’re using KSH from base and have already added `~/.local/bin`, you can skip `pipx ensurepath` because this step is for Bash users.

6. The rest of the process is similar to that used on other platforms:

	```shell
	# Install the toolset.
	pipx install standardebooks
	```

## Installation for toolset developers

If you want to work on the toolset source, it’s helpful to tell `pipx` to install the package in “editable” mode. This will allow you to edit the source of the package live and see changes immediately, without having to uninstall and re-install the package.

To do that, follow the general installation instructions above; but instead of doing `pipx install standardebooks`, do the following:

```shell
git clone https://github.com/standardebooks/tools.git
pipx install --editable ./tools
```

Now the `se` binary is in your path, and any edits you make to source files in the `tools/` directory are immediately reflected when executing the binary.

### Running commands on the entire corpus

As a developer, it’s often useful to run an `se` command like `se lint` or `se build` on the entire corpus for testing purposes. This can be very time-consuming in a regular invocation (like `se lint /path/to/ebook/repos/*`), because each argument is processed sequentially. Instead of waiting for a single invocation to process all of its arguments sequentially, use [GNU Parallel](https://www.gnu.org/software/parallel/) to start multiple invocations in parallel, with each one processing a single argument. For example:

```shell
# Slow: Each argument is processed in sequence.
se lint /path/to/ebook/repos/*

# Fast: Multiple invocations each process a single argument in parallel.
export COLUMNS; parallel --keep-order se lint ::: /path/to/ebook/repos/*
```

The toolset tries to detect when it’s being invoked from `parallel`, and it adjusts its output to accommodate.

We export `COLUMNS` because `se lint` needs to know the width of the terminal so that it can format its tabular output correctly. We pass the `--keep-order` flag to output results in the order we passed them in, which is useful if comparing the results of multiple runs.

### Linting with `pylint` and `mypy`

Before we can use `pylint` or `mypy` on the toolset source, we have to inject them (and additional typings) into the venv `pipx` created for the `standardebooks` package:

```shell
pipx inject standardebooks pylint==3.3.3 mypy==1.14.0 types-requests==2.32.0.20241016 types-setuptools==75.6.0.20241223 types-Pillow==10.2.0.20240822
```

Then make sure to call the `pylint` and `mypy` binaries that `pipx` installed in the `standardebooks` venv, *not* any other globally-installed binaries:

```shell
cd /path/to/tools/repo
$HOME/.local/pipx/venvs/standardebooks/bin/pylint tests/*.py se
```

### Testing with `pytest`

Instructions are found in the testing [README](tests/README.md).

### Code style

- In general, we follow a relaxed version of [PEP 8](https://www.python.org/dev/peps/pep-0008/). In particular, we use tabs instead of spaces, and there is no line length limit.

- Always use the `regex` module instead of the `re` module.

# Help wanted

We need volunteers to take the lead on the following goals:

- Add more test cases to the test framework.

- Writing installation instructions for Bash and ZSH completions for macOS.

- Currently, the toolset requires the whole Calibre package, which is very big, but it’s only used to convert epub to azw3. Can we inline Calibre’s azw3 conversion code into our `./vendor/` directory, to avoid having to install the entire Calibre package as a big dependency? If so, how do we keep it updated as Calibre evolves?

- Over the years, `./se/se_epub_build.py` has evolved to become very large and unwieldy. Is there a better, clearer way to organize this code?

# Tool descriptions

-	### `se add-file`

	Add an SE template file and any accompanying CSS.

-	### `se british2american`

	Try to convert British quote style to American quote style in `DIRECTORY/src/epub/text/`.

	Quotes must already be typogrified using the `se typogrify` tool.

	This script isn’t perfect; proofreading is required, especially near closing quotes near to em-dashes.

-	### `se build`

	Build an ebook from a Standard Ebook source directory.

-	### `se build-ids`

	Change ID attributes for non-sectioning content to their expected values across the entire ebook. IDs must be globally unique and correctly referenced, and the ebook spine must be complete.

-	### `se build-images`

	Build ebook cover and titlepage images in a Standard Ebook source directory and place the output in `DIRECTORY/src/epub/images/`.

-	### `se build-manifest`

	Generate the `<manifest>` element for the given Standard Ebooks source directory and write it to the ebook’s metadata file.

-	### `se build-spine`

	Generate the `<spine>` element for the given Standard Ebooks source directory and write it to the ebook’s metadata file.

-	### `se build-title`

	Generate the title of an XHTML file based on its headings and update the file’s `<title>` element.

-	### `se build-toc`

	Generate the table of contents for the ebook’s source directory and update the ToC file.

-	### `se clean`

	Prettify and canonicalize individual XHTML, SVG, or CSS files, or all XHTML, SVG, or CSS files in a source directory.

-	### `se compare-versions`

	Use Firefox to render and compare XHTML files in an ebook repository. Run on a dirty repository to visually compare the repository’s dirty state with its clean state. If a file renders differently, place screenshots of the new, original, and diff (if available) renderings in the current working directory. A file called diff.html is created to allow for side-by-side comparisons of original and new files.

-	### `se create-draft`

	Create a skeleton of a new Standard Ebook.

-	### `se css-select`

	Print the results of a CSS selector evaluated against a set of XHTML files.

-	### `se dec2roman`

	Convert a decimal number to a Roman numeral.

-	### `se extract-ebook`

	Extract an .epub, .mobi, or .azw3 ebook into `./FILENAME.extracted/` or a target directory.

-	### `se find-mismatched-dashes`

	Find words with mismatched dashes in a set of XHTML files. For example, `extra-physical` in one file and `extraphysical` in another.

-	### `se find-mismatched-diacritics`

	Find words with mismatched diacritics in a set of XHTML files. For example, `cafe` in one file and `café` in another.

-	### `se find-unusual-characters`

	Find characters outside a nominal expected range in a set of XHTML files. This can be useful to find transcription mistakes and mojibake.

-	### `se help`

	List available SE commands.

-	### `se hyphenate`

	Insert soft hyphens at syllable breaks in an XHTML file.

-	### `se interactive-replace`

	Perform an interactive search and replace on a list of files using Python-flavored regex. The view is scrolled using the arrow keys, with alt to scroll by page in any direction. Basic Emacs (default) or Vim style navigation is available. The following actions are possible: (y) Accept replacement. (n) Reject replacement. (a) Accept all remaining replacements in this file. (r) Reject all remaining replacements in this file. (c) Center on match. (q) Save this file and quit.

-	### `se lint`

	Check for various Standard Ebooks style errors.

-	### `se make-url-safe`

	Make a string URL-safe.

-	### `se modernize-spelling`

	Modernize spelling of some archaic words, and replace words that may be archaically compounded with a dash to a more modern spelling. For example, replace `ash-tray` with `ashtray`.

-	### `se prepare-release`

	Calculate work word count, insert release date if not yet set, and update modified date and revision number.

-	### `se recompose-epub`

	Recompose a Standard Ebooks source directory into a single HTML5 file, and print to standard output.

-	### `se renumber-endnotes`

	Renumber all endnotes and noterefs sequentially from the beginning.

-	### `se roman2dec`

	Convert a Roman numeral to a decimal number.

-	### `se semanticate`

	Apply some scriptable semantics rules from the Standard Ebooks semantics manual to a Standard Ebook source directory.

-	### `se shift-endnotes`

	Increment or decrement the specified endnote and all following endnotes by 1 or a specified amount.

-	### `se shift-illustrations`

	Increment or decrement the specified illustration and all following illustrations by 1 or a specified amount.

-	### `se split-file`

	Split an XHTML file into many files at all instances of `<!--se:split-->`, and include a header template for each file.

-	### `se titlecase`

	Convert a string to titlecase.

-	### `se typogrify`

	Apply some scriptable typography rules from the Standard Ebooks typography manual to a Standard Ebook source directory.

-	### `se unicode-names`

	Display Unicode code points, descriptions, and links to more details for each character in a string. Useful for differentiating between different flavors of spaces, dashes, and invisible characters like word joiners.

-	### `se word-count`

	Count the number of words in an HTML file and optionally categorize by length.

-	### `se xpath`

	Print the results of an xpath expression evaluated against a set of XHTML files. The default namespace is removed.

# What a Standard Ebooks source directory looks like

Many of these tools act on Standard Ebooks source directories. Such directories have a consistent minimal structure:

```
.
|__ images/
|   |__ cover.jpg
|   |__ cover.source.jpg
|   |__ cover.svg
|   |__ titlepage.svg
|
|__ src/
|   |__ META-INF/
|   |   |__ container.xml
|   |
|   |__ epub/
|   |   |__ css/
|   |   |   |__ core.css
|   |   |   |__ local.css
|   |   |   |__ se.css
|   |   |
|   |   |__ images/
|   |   |   |__ cover.svg
|   |   |   |__ logo.svg
|   |   |   |__ titlepage.svg
|   |   |
|   |   |__ text/
|   |   |   |__ colophon.xhtml
|   |   |   |__ imprint.xhtml
|   |   |   |__ titlepage.xhtml
|   |   |   |__ uncopyright.xhtml
|   |   |
|   |   |__ content.opf
|   |   |__ onix.xml
|   |   |__ toc.xhtml
|   |
|   |__ mimetype
|
|__ LICENSE.md
```

`./images/` contains source images for the cover and titlepages, as well as ebook-specific source images. Source images should be in their maximum available resolution, then compressed and placed in `./src/epub/images/` for distribution.

`./src/epub/` contains the actual epub files.
