# 2.3.5

## se build

- When simplifying CSS, don't add classes to elements that are not targeted by a selector

- Improve RMSDK compatibility for new titlepages

## se build-toc

- Added check on valid roman numerals in headings. Thanks to David Grigg

## se clean

-  Alpha-order CSS declarations

## se find-mismatched-diacritics

- Exclude link in colophon which may confuse results

## se lint

- Improve m-056

- Improve t-042

- Exclude valedictions from t-057

- Allow trailing `j` in s-026

## se modernize-spelling

- Various additions and fixes

## se semanticate

- Add check for Roman numerals ending in `j`

## se typogrify

- Use nbsp after ellipses that open dialog

- Fix broken regex

- Remove duplicate regex

- Prevent check for `B.C.` from matching `A. B. C.`

- Improve matching two-em-dashes at the end of dialog

- Replace `M‘foo` with `McFoo`

# 2.3.4

## se create-draft

- Add `id` attributes to `<nav>` elements in ToC

# 2.3.3

## General

- Downgrade Pillow so that it's compatible with the SE server

# 2.3.2

## General

- Remove accessibilityFeature=longDescription from content.opf template

- Gracefully fail when file can't be opened in various cases

- Remove deprecated pyopenssl. Thanks to Robin Whittleton

- Add support for se:image.style.realistic

- Change the LoI to be a top-level `<nav>` element

- Update shell completions for `se xpath` command

## se build

- Also simplify `[xml|lang]` selectors to classes

- Change 'noteref' to 'endnote' in Kobo builds to enable popup endnotes

- Use the Nu Validator (v.Nu) to check epubs for XHTML5 compatibility when using the `--check` option

- Remove now-unused exception filter for Ace output

- Ignore v.Nu warning about possibly invalid datetime value

## se build-toc

- Update to use data-parent attributes instead of nested `<section>`s. Thanks to David Grigg

- Update landmarks to IDPF a11y best practices

## se build-manifest

- Adjust accessibility metadata if we have images in the manifest

## se build-title

- Add a `z3998:roman` semantic to the `<title>` element if the title looks to be an entirely Roman numeral

## se clean

- Don't lowercase `currentColor` values

## se create-draft

- Update titlepage with `h1` and author/contributor information

- Remove display: flex from imprint because it doesn't play nice with page breaks in Webkit

## se lint

- Add s-096, heading in half title without fulltitle semantic

- Improve t-036

- Improve t-008

- Improve t-017

- Improve t-057

- Improve s-041

- Improve t-065

- Improve s-020

- Improve c-020

- Improve s-085

- Add t-058, illegal character

- Add `yi` to s-082 check

- t-063: Add `in extremis` and `par excellence`

- Add m-028, m-029, m-038, m-039, checks for image accessibility metadata

- Add s-097, `a` element without `href` attribute

- Add f-016, cover.jpg larger than 1.5MB

- Update x-017 to include all ID attributes across whole ebook

- Remove s-029 as it's a duplicate of s-050, and replace with s-029, section with nonexistent parent

- Don't check landmarks in m-044

- Remove m-043 and m-044 as they're obviated by updates in `se build-toc`

## se modernize-spelling

- Add `free-will` problem spelling check. Thanks to Robin Whittleton

- Various additions

- Improve removal of period after `percent`

## se prepare-release

- Exclude `<title>` elements that also have attributes from the word count

## se recompose-epub

- Print detailed exceptions

- Sort CSS namespaces so recompositions are deterministic

- Don't add a space before base64 images, in order to pass nu validation

- Un-self-close non-void elements in HTML5 output to satisfy the Nu HTML5 validator

- Replace `xml|lang` in CSS and remove CSS namespaces from HTML5 output

- Update to recompose using data-parent attribute instead of nested `<section>`s

# 2.3.1

## General

- Roll back incompatible GitPython version

## se lint

- Remove t-058, since CJK ditto mark isn't appropriate for the Latin alphabet

# 2.3.0

## General

- Template backmatter references to U.S. should be initialisms. Thanks to Robin Whittleton

## se british2american

- Improve guess function

## se build

- Confirm java is really installed on Mac OSX. Thanks to Vince Rice

## se build-toc

- Gracefully fail on invalid spine

## se create-draft

- Handle titles with em dashes

## se extract-ebook

- Don't allow the `--output-dir` option when more than one ebook is specified

## se find-mismatched-dashes

- Pretty print some exceptions

## se find-mismatched-diacritics

- Pretty print some exceptions

## se find-unusual-characters

- Add this new command. Thanks to Robin Whittleton

## se interactive-replace

- Don't rstrip file contents to prevent crash when a file ends in multiple newlines

## se lint

- Improve t-063

- Improve s-023

- Improve m-064

- Improve t-042

- Improve s-045 when times are capitalized in titles

- Add t-068, `<cite>` without leading em dash

- Add m-026, illegal mobile Wikipedia URL

- Add m-027, se:short-story found but no Shorts subject in metadata

- Correct broken m-027 error code

## se modernize-spelling

- Various additions and improvements

## se titlecase

- Improve titlecasing by checking some exceptions

- Add corner case exception for capitalized times

## se typogrify

- Add rsquo to bare `tis`

- Improve typogrification of `'twas` and `'twon't`

# 2.2.0

## General

- Remove Pylint warnings on C extensions and runtime class errors. Thanks to Robin Whittleton

- Update some `import`, `with`, and `items` syntax. Thanks to Robin Whittleton

- Remove python-version to pin test runner to OS version. Thanks to Robin Whittleton

- Fix error flagged by mypy in lint. Thanks to Robin Whittleton

- Allow xpath to return a single string

## se build

- Restore unconditional creation of compatible epub. Thanks to Vince Rice

- Remove `.gitignore` from white-label epub builds

- Capture warnings from epubcheck even if there are no errors

- Use quiet_remove instead of try/catch

## se build-manifest

- Improve output on invalid XHTML

- Fix incorrect path separator when run on Windows

## se build-spine

- Improve output on invalid XHTML

## se build-title

- Improve output when `<br/>` and `&` are present

## se build-toc

- Handle `<br/>` in titles

## se clean

- Fix error when checking single XHTML files. Thanks to Robin Whittleton

- Polite failure if file doesn't exist

## se create-draft

- Improve output of `--white-label` option

- Fix missing translator block in new productions. Thanks to Robin Whittleton

- Move `<link>` to correct location in white label OPF file

- Parse single/double quote encoding. Thanks to Mike Colagrosso

- Save body text even if it can't be parsed. Thanks to Vince Rice

- Linkify error message

- Handle titles and contributors containing XML entities

## se find-mismatched-dashes

- Strip tags before processing, but keep `alt` and `title` attributes

## se find-mismatched-diacritics

- Lowercase matches so that uppercased entries don't cause duplicate output

- Strip tags before processing, but keep `alt` and `title` attributes

## se interactive-replace

- Don't overwrite file if the file is not dirty

- Fix curs_set issue in interactive-replace. Thanks to Weijia Cheng

## se lint

- Improve t-042

- Add t-063, Latin phrase set without italics

- Don't emit m-020 if SE subject has not yet been filled out

- Add s-091, `<span>` not followed by `<br/>` in poetry

- Improve t-063

- Make s-086 also check for Loc. Cit.

- Improve s-091

- Tweak message for s-086

- Add s-092, anonymous contributor with name semantic

- Add t-064, title not correctly titlecased

- Add f-017, png file without transparency

- Fix broken t-064 message

- Add t-065: Header ending in a period

- Allow empty `<col/>` and `<colgroup/>`

- Make separate messages for t-042 typos. Thanks to Vince Rice

- Add t-066, regnal ordinal preceded by 'the'

- Fix broken hyperlink in m-070 error message

- Convert some tests to xpath instead of regex

- Improve s-064

- Fix t-031

- Don't include legal cases in t-064

- Improve t-008

- Improve s-039

- Add s-093, nested `<abbr>` element

- Don't duplicate entries in t-017

- Add m-071 and m-072, DP links with incorrect text

- Merge m-026, m-027, m-028, m-029, m-037, m-038, m-039, m-040 into single m-037 message

- m-041 only check colophon and imprint

- Fix bug in m-037

- Only emit m-071, m-072, m-041 if there are fewer than 2 sources

- Add Ukranian to the set of scripts that need a Latn suffix. Thanks to Robin Whittleton

- Add s-094, endnote out of sequence

- Stop extremely long filenames from breaking lint output. Thanks to Robin Whittleton

- Add t-067, plural grapheme formed without apostrophe

- Merge multiple s-094 messsages into one entry

- Add `--allow` option to allow passing through specific errors that are ignored in `se-lint-ignore.xml`.

- Add s-095, `<hgroup>` with `<h#>` that is out of order

## se modernize-spelling

- Various additions

- Fix `per cent.,` -> `percent,`

## se renumber-endnotes

- Added safety check before running. thanks to David Grigg

- Improved endnote check. Thanks to David Grigg

- Add `--brute-force` option

## se semanticate

- Reduce false positives when adding semantics to 'in.'

- Various additions

- Don't add abbr semantics to `SOS`

- Rework checks for eoc on abbreviations. Thanks to Vince Rice

- Handle AD/BC terminating periods. Thanks to Vince Rice

## se titlecase

- Various titlecasing improvements

## se typogrify

- Fix common transcription error of :- -> :—

- Escape user input before passing to regex when hyphenating

- Improved typogrification of fractions

## se unicode-names

- Gracefully handle unrecognized character

# 2.1.0

## General

- Allow non-SE ebook folders to be parsed and operated on. A non-SE ebook does not have a `./src/` folder and does not have an SE-style `<dc:identifier>`.

- Fixes for all commands to work with the manual 1.6.1 rules for semantics vs classes

## se build

- Add the `--check-only` option to only run epubcheck/ace without outputting any ebook files

## se create-draft

- Add the `-w`, `--white-label` option to create an epub skeleton without SE branding

## se find-mismatched-dashes

- Create this command. Scans an ebook for cases of the same compound word with and without dashes. Output is like `se find-mismatched-diacritics`.

## se find-mismatched-diacritics

- Revamp output format to use Rich and to linkify words to M-W

## se lint

- Improve t-042

- Add t-061, summary-style bridgehead without ending punctuation

- Improve t-060

- Strip elements before glossary search key map linting. Thanks to Robin Whittleton

- Don't crash when throwing f-002

- Use self.content_path instead of hard-coded path

- Add t-062, uppercased a.m./p.m.

## se modernize-spelling

- Various additions

- Fix a broken regex. Thanks to David Grigg

## se renumber-endnotes

- Fix an error with endnote IDs. Thanks to David Grigg

## se typogrify

- Fix a common error case for incorrectly curled left quote

# 2.0.1

## General

- Fix broken `se --version` command

- Restore the `quiet_remove()` function until the SE server is running a version of Python that can handle the alternative

# 2.0.0

## Breaking changes

- `se reorder-endnotes` has been renamed to `se shift-endnotes` to better differentiate it from `se renumber-endnotes`

- `se print-manifest`, `se print-spine`, and `se print-toc` have been renamed to `se build-manifest`, `se build-spine`, and `se build-toc`. The `-i,--in-place` option has been removed and the tool now writes to disk by default. The `-s,--stdout` option has been added to print to stdout instead of writing to disk

- The `se create-draft` `-p`,`--pg-url` option has been replaced with `-p`,`--pg-id`, which takes the Project Gutenberg book ID number instead of a whole URL

- The `se interactive-sr` command has been replaced with the `se interactive-replace` command, a totally independent TUI utility that removes the Vim dependency

- The `se build` `-t`,`--covers` option has been removed

## General

- Add a new `-p`,`--plain` option to the base `se` command to enable plain-text output for all subcommands. For example: `se --plain lint .`

- Replace all XHTML-processing regexes in all tools with dom operations

- Most checks that perform actions based on a filename now check the dom and perform checks based on the semantics in the file instead

- Don't include contributor name twice in SE identifier string if they are both a translator and illustrator

-  Remove the `quiet_remove` function now that `Path.unlink()` accepts the `missing_ok` parameter

## se build

- The `--check` flag now invokes Ace to check accessibility. Ace is only invoked if it's present in `$PATH`, otherwise it is not invoked and the build process will continue uninterrupted

- If epubcheck/Ace fails, the build files are kept on disk and are hyperlinked in the output

- Replace ditto mark (U+3003) with ldquo

- Don't crash if the colophon is missing

- Allow building without a cover image, or with a jpg/png cover image

- Alpha sort simplified class names so builds are deterministic

- Remove obsolete replacement of `<abbr>` with `<span>`

- Improve MathML replacement so many more basic MathML expressions get converted to plain text instead of an image

- Print epubcheck/Ace output in a lint-style table instead of using raw output

- Replace Unicode ratio character U+2236 with colon

- Add more ARIA roles to include, and improve xpath to include them

- Add alt text to mathml nodes that were converted to PNG

- Restructure work directory format during the build process and don't zip an epub until epubcheck/ace pass

- Save debug epub into a fixed location to prevent multiple runs from taking up disk space

- Use a temp file to capture epubcheck's stdout in case it's too long

- Remove outdated Google Play Books compatibility fix

- Pretty-print some more obscure errors instead of crashing

- Don't add more than one `role` attribute when adding ARIA roles

- Add first ARIA-valid `epub:type` to the role attribute

- Don't add ARIA roles to `<article>`

- Remove the `-t`,`--covers` option

## se build-manifest

- Don't add glossary property for the ToC

- Don't fail if no manifest exists

## se build-spine

- Don't fail if no spine exists

## se build-title

- Add the `n`,`--no-newline` option

## se build-toc

- Don't duplicate `*matter` semantic in landmarks

- Add support for `hidden` attribute on headings

## se clean

- Trim white space within `<p>` in content.opf long description

- Don't remove spaces after `:` in CSS media queries

- When formatting CSS, don't add spaces after colons in strings

## se create-draft

- Add LCCN entry for David Widger automatically

- Don't allow unidecode to convert rsquo to straight quote

- Don't try to find Wikipedia URL for a book if it's a generic compilation

- Update colophon template

- Update Uncopyright template

- Replace `-p`,`--pg-url` with `-p`,`--pg-id`

- Use correct `se:image.color-depth` semantic instead of `se:color-depth`

- Titlecase the book title

- Update metadata template to use variable for production notes

## se lint

- Allow ex units for font size in c-023

- Correct URL references to URI in `id.loc.gov` errors. Thanks to Vince Rice

- Add t-058, quote used instead of ditto mark in table

- Add t-059, period at end of `<cite>` element before endnote backlink

- Add `together` to list of ignored classes

- Emit lint error instead of crashing in some cases

- Output f-002 only once, with sub items

- Check for half title page at any sectioning level

- Merge m-036, m-052, and m-062 into m-036, variable not replaced with value

- Add m-055, description does not end with a period

- Improve t-059

- Add s-035, endnote containing only `<cite>`

- Don't crash if there is no cover

- Merge m-011 into m-005

- Ignore some common known names in t-007

- Add s-084, poem has incorrect semantics

- Add t-060, old style Bible citation

- Add s-085, h# element found at unexpected depth

- Remove accidental duplicate message s-050

- Allow any value for the scope attribute in s-055

- Don't throw s-025 if the titlepage has any heading content

- Add s-086, Op. Cit. in endnote

- Improve t-060

- Improve t-017

- Remove s-031; replace s-032 with generic 'invalid epub:type value' check that checks against set vocabularies

- Remove incorrect entry in SE vocabulary definition and update epub vocabulary definitions

- Add s-031, duplicate value in `epub:type` attribute

- Expand on t-017 error message

- Fix error in t-017

- Improve m-007

- Improve c-015

- Add m-011, Subtitle in metadata but no full title element

- Add s-087, subtitle in metadata but no subtitle in half title page

- Add s-088, subtitle in half title page but no subtitle in metadata

- Add m-062, `<dc:title>` missing matching file-as

- Add m-068, `<dc:title>` missing matching title-type

- Add s-089, MathML without `alttext` attribute

- Add m-069, `comprised of` in metadata

- Improve t-042

- Improve message for s-018

- Don't throw m-055 if the short description is not yet filled

- Don't throw m-016 if the long description is not yet filled out

- Update m-022 to check for any empty element, not just production notes

- Add m-070, lint check for glossary entries missing from the text. Thanks to Robin Whittleton

- Add s-090, invalid language tag

## se modernize-spelling

- Various additions

## se recompose-epub

- Improve fix for positioning figures/images with `positon: absolute;` during recomposition

- Remove `data-css` classes from output

## se renumber-endnotes

- Don't print traceback if the target is not an SE directory

- Properly process endnotes within endnotes.xhtml itself. Thanks to David Grigg

- Actually follow spine order

## se semanticate

- Various additions

## se shift-endnotes

- Correctly handle endnotes within endnotes

- Add `-a`,`--amount` flag to shift endnotes by any amount

- Fix incorrect increment calculation

## se split-file

- Add NUMBER parameter to template

## se typogrify

- Remove shy hyphens

## se xpath

- Add `-f`,`--only-filenames` option

- Smarter check when adding Roman semantics

- Escape `[` to prevent Rich from parsing those characters as styling commands

# 1.9.3

## se build

- Add compatibility code to allow Kindle to display pages whose only content is an aboslutely positioned image

- Replace vh/vw units with percent for compatible epub

## se lint

- Add c-023, font size set without em units

- Add c-024, line-height set with units

- Add c-025, illegal percent unit on height property

## se print-toc

- Fixed a crash when ToC level could not be determined. Thanks to David Grigg

## se recompose-epub

-  recompose-epub: Add `position: relative;` to sections with child figures that have position: absolute, so that they will position correctly after recomposition

## se typogrify

- Add word joiners after em dashes within `<cite>` elements

# 1.9.2

## General

-  Improve url-safe string generation when string contains accents. Thanks to Robin Whittleton

## se build

- Unwrap double-nested Kobo spans to prevent unexpected styling in local.css

## se create-draft

- Ensure NACOAF prefix is http. Thanks to Vince Rice

- Add `unlocked` accesibility feature to `content.opf` template

## se lint

- Add `sa` and `he` to s-082

- Add lint check for `id.loc.gov` URLs that start with https. Thanks to Robin Whittleton

- Add m-067, non-SE link in long description

- Improve s-045

- Add t-057, <p> beginning with lowercase letter

- Improve t-012

## se modernize-spelling

- Various additions

## se print-spine

- Add dramatis-personae and halftitlepage to exluded files. Thanks to Asher Smith

## se reorder-endnotes

-  reorder-endnotes: Improve reordering for endnotes within the endnotes file

## se semanticate

- Add SOS and TV

## se xpath

- Don't crash when printing string output

# 1.9.1

## General

- Update the toolset to use `halftitlepage.xhtml` instead of `halftitle.xhtml` throughout

- Add support for new `se:role` metadata property

## se build

- Use posix path for XSLT transform. Thanks to ConcaveTrillion

- Convert combining vertical line above to acute accent during build

- Remove outdated Calibre workaround for Kindle

- Remove outdated Play Books compatibility tweak

- Update `epubcheck` to 4.2.5

- Remove outdated `epubcheck` workaround

## se create-draft

-  Remove unnecessary prefilling of cover and titlepage. Thanks to Robin Whittleton

## se modernize-spelling

- Various additions

## se print-toc

- Add exception msg on file open/parse error. Thanks to Vince Rice

- Fix Unicode file open issues. Thanks to ConcaveTrillion

## se lint

- Update t-011 to exlude quotations in letter signatures

- Add c-022, illegal rem unit

- Add more detail to lint error message for invalid XML

- Add filename to lint error message for invalid XML

- Add s-082, non-Latin-script language tag missing script suffix

- Add t-055, lone acute accent

- Add t-056, ordinal character used instead of degree character

- Merge t-045 and s-081 in favor of s-081

- Add f-015, filename doesn't match id attribute

- Add t-045, element with z3998:persona semantic that is set in italics

- Add s-083, persona <td> with child <p> element

## se recompose-epub

- Don't pretty-print output if the size of the string would crash lxml

## se titlecase

- Lowercase `mm` if used as a measurement

## se typogrify

- Don't ignore colophon, loi, or half title

- Fix broken regex

- Typogrify all metadata, not just the descriptions

# 1.8.5

## General

- New command: `se xpath` to run an XHTML-namespaced xpath selector on a directory or individual files

## se build

- Replace no-break hyphens in Kobo builds

## se create-draft

- Update chapter template and split-file command to use roman numerals instead of arabic numerals. Thanks to maticstric

- Improve LCSH subject heading fetching to find results more often. Thanks to maticstric


## se lint

- Add x-018, unused ID attribute

- Replace internal CSS cache with general file cache

- Add t-050, possessive `'s` outside of persona element

- Add t-051, dialog in `<p>` without closing double quote, but next `<p>` doesn't have opening double qoute

- Add t-052, stage direction without ending punctuation

- Add t-053, stage direction starting in lowercase

- Improve t-042

- Add t-054, epigraphs entirely in non-English but set in Roman and not italics

- Add m-065, incorrect word count in metadata

- Allow nested at-rules when checking CSS. Thanks to maticstric

## se modernize-spelling

- Various additions

## se semanticate

- Don't add Roman semantics to obscured names starting with I, V, or X. Thanks to Weijia Cheng

- Improve check for Imperial measurements

## se titlecase

- Lowercase `o’`

# 1.8.4

## General

- Update core.css to use `break-*` instead of `page-break-*`

- Add fixed margins to blockquotes in core.css

## se find-mismatched-diacritics

- Remove regex compilation as it's built in to the regex library now

- In output, differentiate words with tab and not comma

- Add some exceptions for common edge cases

## se semanticate

- Don't add Roman semantics around `i`

## se build

- Add `and all` to CSS media queries during build to placate RMSDK

- Force unicode encoding when converting MathML to PNG

## se create-draft

- Add `<abbr class="name">` around abbreviated names in colophon

## se lint

- Add c-019, signature semantics without small caps; this replaces c-006

- Improve m-007 by checking for bad archive.org links

- Add s-079, element with no children and only white space

- Improve c-015

- Add s-080, <td> in drama containing both inline text and a block-level element

- Add c-020, multiple `<article>` or `<section>` in file but without `break-*` CSS

- Add c-021, nested italics without `font-style: normal;`

- s-081, `<figure>`, `<table>`, or `<blockquote>` followed by `<p>` that does not have `continued` class

## se modernize-spelling

- Various additions

## se print-spine

- Fix prologue being added to spine twice. Thanks to Vince Rice

## se print-toc

- Fix endnotes being included in the ToC. Thanks to David Grigg

## se titlecase

- Improve check for Roman numerals in titles

## se typogrify

- Add `nbsp` after some titles

- Remove unused regexes

- Convert hyphen before closing double quote to em dash

- Fix incorrectly curled quote following inline closing tag

## se recompose-epub

- Strip CDATA from HTML5 output

- Don't print duplicate lang attributes on `<html>` when outputting HTML5

# v1.8.3

## se build

- Remove multiple ARIA roles added during build, as epub doesn't support them

- Include filename in exception

# v1.8.2

## General

- Add the ability to apply a stylesheet to an EasyXml DOM tree. Applied styles can be accessed on an EaxyXmlElement by getting the `data-css-<attr>` property.

- Use EasyXhtmlTree instead of raw lxml for various operations across the codebase

- Remove se.XHTML_NAMESPACES constant in favor of more targeted namespace applications in the EasyXmlTree classes

- Update core.css to remove text indent from centered `<p>` elements in `<header>`

- Update core.css to add media to @media rules for RMSDK compatibility. Thanks to Robin Whittleton

- Update se.css to use `text-align: initial;`

## se build

- Fix dark mode in iOS13+ iBooks and drop dark mode hack for older Apple Books. Thanks to Robin Whittleton

- Move prefers-color-scheme image inversion to `core.css`. Thanks to Robin Whittleton

- Convert `vh` units to `em` for compatible epub build

- Output correct manifest when writing Kobo files

- Disable quote-align insertion code

- Simplify `text-align: initial;` to `text-align: left;`

## se clean

- Alphabetize classes, except 'eoc' always goes last

## se create-draft

- Fix extra whitespace in content.opf when translator/illustrators not present

- Prompt the user if the title appears to contain a subtitle

## se lint

- Fix m-045 not working with ampersands

- Fix s-021 not working with ampersands

- Fix t-002 not working with word joiners

- Make sure s-021 reaches headers within `<header>` elements

- Add c-001, don't use some pseudoclasses on `*`

- Add t-048, chapter opening text in all caps

- Add c-010, `<footer>` without correct style

- Add c-011, centered element that still has text-indent applied

- Cache CSS rules for performance

- Add c-012, element without header and without correct `margin-top`

- Correctly remove color from CSS output if requested via option

- add c-013, element with `margin` or `padding` not in increments of `.5em`

- Add t-049, two em dash used for whole word elision

- Add s-076, `lang` attr used instead of `xml:lang`

- Improve t-049 check

- Add c-014, `<table>` without explicit margins

- Make sure CLI output expands to fill available space

- Improve x-017

- Fix links in error messages for f-003, f-004, f-005, and f-006

- Add c-015, element after or containing salutation does not have `text-indent: 0`

- Add s-077, `<header>` with preceding sibling

- Add s-078, `<footer>` with following sibling

- Add c-016, `text-align: left;` found instead of `text-align: initial;`

- Add c-017, element with postscript semantic but missing `margin-top: 1em;`

- Add c-018, element with postscript semantic but missing `text-indent: 0;`

- Improve t-042, possible typo

## se modernize-spelling

- Remove space before `'ll`

- Various additions

## se semanticate

- Improve lowercase i check

## se titlecase

- Lowercase `du`

# v1.8.1

## se build

- Fix incorrect application of `<span class="quote-align">` to `&hellip;`

- Don't remove `datetime` attributes from `<time>`

## se create-draft

- Fix broken HTML in colophon if translator is specified

- Fix colophon author formula if author is anonymous

- Remove white space from transcriber names when fetching from PG

## se lint

- Improve t-042 by checking for consecutive periods

- Improve t-042 by checking for `,.`

- Improve t-042 by checking for miscurled `&lsquo;`

- Add m-063, cover image has not been built

- Add m-064, ebook linked in long description but not italicized

## se modernize-spelling

- Various additions

## se typogrify

- Add word joiners before and after hair spaces preceding `&hellip;`

- Auto-fix commonly miscurled quotation marks around `'n'`

# v1.8.0

## General

- Fix broken GitHub test/build framework. Thanks to Dave Halliday

## se build

- Fix missing generated epub-type-x classes. Thanks to Robin Whittleton

## se create-draft

- Accept multiple authors, translators, and illustrators

- Remove unused metadata blocks

- Try to guess at contributor sorting

## se hyphenate

- Switch from unmaintained PyHyphen to pyphen. Thanks to Robin Whittleton

## se lint

- Improve checks for missing metadata leftover from `se create-draft`

- Add m-062, missing data in imprint

- Add s-075, `<body>` with illegal direct child

## se modernize-spelling

- Various additions

## se print-toc

- Remove BeautifulSoup dependency, using lxml and xpath instead. Thanks to David Grigg

## se recompose-epub

- Add filenames to error messages

## se semanticate

- Add `pp.` as an abbreviation. Thanks to Robin Whittleton

## se typogrify

- Don't insert nbsp or word joiners in `<title>` elements

## se unicode-names

- Use unicode.org for hyperlinks for more details

# v1.7.1

## General

- Ensure Python 3.9 compatibility with latest Pillow. Thanks to Robin Whittleton

## se build

- Align quotation marks over ellipses, and align nested quotations

- Don't align quotes in Kobo builds, as it messes up spacing

## se lint

- Add t-046, incorrect rough breathing mark

- Update m-041 to check all variations of HathiTrust

- Add m-061, HT/IA metadata link must be preceded by `the`

## se modernize-spelling

- Various additions

## se recompose-epub

- Apply `epub:type` of `<body>` to all direct children

## se renumber-endnotes

- Use with/open file open pattern

# v1.7.0

## se recompose-epub

- Add --extra-css-file option to include additional CSS when recomposing

- Don't destroy external links when recomposing

- Improve formatting of CSS in `<style>` elements, and escape with CDATA

# v1.6.3

## General

- In core.css, Indent `<p>` elements following `<ul>`, `<ol>`, and `<table>` by default

## se build

- Generate and use 2x MathML images. Thanks to Vince Rice

- Expand canvas if either generated MathML dimensions are odd. Thanks to Vince Rice

## se lint

- t-032: Ignore abbrevations that contain `<sup>`, like `r<sup>o</sup>`

- t-032: Ignore abbrevations ending in numbers, like stage direction

- Add new Google Books URL structure to checks

- Add m-060, alternate style for new Google Books URLs

- t-042: check for dialog starting in lowercase letters

- Add s-074, `<hgroup>` element containing sequential `<h#>` children at the same heading level

## se modernize-spelling

- Various additions and modifications

## se print-title

- Catch and pretty print invalid XHTML exceptions

## se print-toc

- Correctly print first child of title when there are multiple hgroup children. Thanks to David Grigg

## se recompose-epub

- Include all images as inline data

- Bug fixes and improvements

## se semanticate

- Reduce false positives when adding semantics to measurements

## se titlecase

- Use word boundaries instead of spaces when uppercasing initialisms

- Add `Des` and `De La` to lowercased exceptions

# v1.6.2

## se build

- Fix issue where adding quote spans interrupts alt attributes and title tags

# v1.6.1

## General

- Remove almost all BS4 dependencies

- Change default indentation of `<p>` following `<blockquote>` to be 1em instead of 0; add `continued` class to `core.css` for such `<p>`s that are semantic continuations of the `<blockquote>`'s preceding `<p>`

- Rename some EasyXml functions

## se build

- In the compatible build, add `<span>`s around punctuation followed by quotation marks to move them closer together typographically

- Add compatibility CSS to remove hanging indents from iOS in compatible epub build

- Add `continued` class to `core.css` and make `blockquote + p` indented by default

## se create-draft

- Include IA URL as a `<dc:source>` element in the generated template `content.opf`. Thanks to maticstric

## se generate-toc

- Fix exception message. Thanks to Vince Rice

## se modernize-spelling

- Various additions. Thanks to Robin Whittleton

## se lint

- Add x-017, duplicate ID value on non-sectioning element

- Downgrade s-039 to a warning and tweak message

- Require block-level child in LoI `<li>` elements

- Perform most checks using the file's semantics and not the filename

- Add f-014, se.css doesn't match template

- Only check top-level elements in m-030-35

- Update s-066 to include Act and Scene and improve check to reduce false positives

- Add s-073, header element requires both label and ordinal semantic children

- Add some mathml to exceptions in s-010

- Fix m-043 message. Thanks to Vince Rice

- Add `continued` class to checks

- Add m-059, source in colophon but missing in metadata

- Add t-045, p preceded by blockquote and starting in lowercase letter but missing `continued` class

## se semanticate

- Fix Roman semantics added to lowercase `i`

# v1.6.0

## General

- Support for new <hgroup> header scheme in tools and templates

- CSS for SE boilerplate files like titlepages, colophons, and the Uncopyright page are now in a new CSS file named `se.css`, and those files no longer include `local.css`.

- Corpus-wide switch to using `epub:type="z3998:signature"` instead of `class="signature"`.

- `core.css` now defaults to lowercase numbers and hanging punctuation.

- Fix to pipx install documentation. Thanks to Robin Whittleton

- Add various functions to the EasyXmlTree and EasyXmlNode classes

- `<title>` elements now have the same value as their ToC entries

## se build

- Remove BS4 dependency

- The raw, non-compatible epub file is now named `*_advanced.epub`, instead of having an `.epub3` file extension

- Add workaround for glossary bug in epubcheck 4.2.4

## se create-draft

- Add support for new `se.css` file and update various template files

## se hyphenate

- Remove BS4 dependency

## se modernize-spelling

- Various additions

## se print-manifest

- Add support for the epub glossary spec

## se lint

- Change s-049 to match `<header>` elements with only `<h#>` children

- Add s-065, `fulltitle` semantic on element that is not an `<h1>`

- Add t-008, repeated punctuation

- Improve t-017

- Add f-013, glossary search key map must have exact filename

- Add s-024, header elements that are entirely non-English should not have italics

- Add s-066 and s-067, header elements with incorrect label semantics

- Add s-068, header missing ordinal semantic

- Improve s-066

- Add t-044, comma required after leading `Or` in subtitle

- Add s-069, `<body>` without direct child `<section>` or `<article>`

- Add s-070, heading element without semantic inflection

- Improve t-020

- Update m-045 to use the output of the `generate_title()` function

- Add s-071, sectioning element with more than one heading element

- Replace various filename-based checks with semantics-based checks

- Add s-072, element with a single `<span>` child

- Remove various now-obsolete checks

- Check for CSS required for `z3998:signature` semantic

## se print-title

- Compatibility with new `<hgroup>` standards

- Remove word joiners and no-break spaces from titles

- Emit a warning if we can't guess the title based on the file contents

## se print-toc

- Compatibility with new `<hgroup>` standards. Thanks to David Grigg

- After adding the bodymatter item in the landmarks, don't output any more frontmatter-like landmark entries

## se semanticate

- Wrap lowercase Roman numerals in semantics

## se typogrify

- Improve rehydration of `&amp;`

- Don't collapse spaces between ellipses and em-dash

- Typogrify the half title if present

# v1.5.9

## General

- Bump to epubcheck 4.2.4

- Pin versions of testing framework libraries so that tests don't fail unexpectedly when new library versions are released. Thanks to Dave Halliday

- Various testing framework updates. Thanks to Dave Halliday

## se build

- Fix extra spaces before 4-dot ellipses and nested quotations in Kobo. Thanks to Robin Whittleton

- Temporarily disable 2x MathML PNG generation due to iBooks srcset bug

- Only add white stroke outline to logo SVG if the logo matches the SE logo

- Don't fail when CSS media queries are present

- Remove Readium compatibility CSS as the Readium reader is no longer maintained

- Don't add -epub-hyphens since it is now required in the base CSS

- Instead of checking for word length when checking if a word is too long for the hyphenator library, catch the exception instead, as some Unicode strings report as shorter than they really are when checked with `len()`

## se compare-versions

- Don't print double newlines in output

## se create-draft

- Remove leading white space from title lines when generating the title/cover SVG

## se lint

- Fix x-009 to check for only leading `0`s, not `-0` anywhere in the value

- Add x-011, illegal underscore in id attribute

- Remove t-007 and t-008 as they are now handled by typogrify

- Add `<footer>` to allowed block level children in s-007

- Improve m-045 check

- Fix unhandled exception when filename not present in lint output. Thanks to Michael Glanznig

- Improve t-017

- Fix typo in s-052 message

- Fix incorrect MathML rendering in some cases

- Catch abbr classes with no periods in s-045. Thanks to Vince Rice

- Allow initialisms with numbers in t-030. Thanks to Vince Rice

- Add several initialism exceptions. Thanks to Vince Rice and Robin Whittleton

- Add some self-closing MathML tags to list of allowed empty elements

- Add s-043, se:short-story/se:novella semantic on element that is not `<article>`

- Add s-061, title and following header content not in `<header>`

- Allow `<p>` in s-058

- Add t-007, possessive s inside italics that are for a name

- Don't check MathML attributes for underscores

- Add s-063, z3998:persona semantic on an element that's not a `<b>` or `<td>`

- Add s-064, check that endnote citations are wrapped in `<cite>`

## se modernize-spelling

- Various additions. Thanks to matistric

## se print-manifest

- Add support for epub dictionaries and glossaries

## se print-toc

- Remove word joiners and nbsp from generated ToC

## se semanticate

- Add `2D`/`3D`/`4D` as recognized abbreviations. Thanks to Vince Rice

- Don't add z3998:roman semantic to `x-ray`

## se typogrify

- Add a no break space before ampersands

- Remove word joiners and nbsps from alt attributs

- Don't add an nbsp before `St.` if it is within an `<abbr class="name">` element

- Convert horizontal bar to em dash

# v1.5.6 - v1.5.8

Released in error; no changes.

# v1.5.5

## General

- Restrict pytest version to work around new pytest bug. Thanks to Dave Halliday

- Update core.css to use `break-*` properties instead of `page-break-*`, and to avoid page breaks inside and after `<header>` by default

## se build

- Convert `break-*` properties to `page-break-*` during build, not the other way around; and use correct value of `break-*: page` where appropriate

## se lint

- Add c-007, `hyphens` CSS property without matching `-epub-hyphens` property

- Merge s-007, s-053, and s-061 into one check, now s-007

## se semanticate

- Improve checks for eoc classes when adding `<abbr>` elements. Thanks to Vince Rice

# v1.5.4

## se build

- Don't pretty-print files when doing a Kobo build, as it will screw up whitespace when rendered

## se clean

- Remove leading and trailing whitespace from attribute values

- Improve cleaning of inline whitespace. Thanks to Dave Halliday

- Preserve doctype in XML files

## se create-draft

- Fix crash when creating a draft of an ebook with a very short title

## se lint

- Ignore noterefs when checking for s-035

- Link filename in s-022 error message

- Add m-058, se:subject implied by other se:subject

- Fix s-056 to match endnotes that have the backlink in an element that is not the last p child of the endnote

- Add s-061 and s-062, checks for glossary rules

- Allow `<abbr>` in s-058

- Fix crash in f-001 caused by not using PosixPath

## se modernize-spelling

- Several additions. Thanks to maticstric

## se print-spine

- Place prologue in front of bodymatter

## se print-title

- Ignore italics when generating title. Thanks to Robin Whittleton

## se print-toc

- Fix bug where dc:subject was used instead of se:subject when deciding if a work was fiction or nonfiction

## se semanticate

- Add semantics for Gov., and Col. Thanks to maticstric

- Add periods and hair space to PhD

- Remove initialism class from MS. Thanks to Mike Bennett

## se typogrify

- Don't include nbsp or word joiners in the ToC

# v1.5.3

## se build

- Add support for building titlepage/imprint/colophon files with color depth semantics on images

- Format Kobo output before writing kepub files

## se create-draft

- Add color depth semantics to titlepage/imprint/colophon templates

# v1.5.2

## General

- Remove 'adventure' from tags listed as non-fiction, when deciding on the fiction type for a work

- Use xpath instead of regex to get spine items

## se build

- Fix several MathML related bugs

## se lint

- Improve s-043 to select blockquotes with inline elements and not just text nodes

# v1.5.1

## se build

- Use pathlib instead of regex when composing PNG output paths

- Output hi-DPI MathML PNGs using `<img srcset>`. Thanks to Robin Whittleton

- Include translator name in output filenames

## se create-draft

- When creating the title/cover page images, check if the first line is a word of less than 3 letters, instead of checking against a set of short words.

## se lint

- Add s-055, `<th>` element not in `<thead>` ancestor

- Add s-056, last `<p>` child of endnote missing backlink

- Add s-057, backlink notereef fragment identifier doesn't match endnote number

- Add m-056, author name present in long description but first instance isn't hyperlinked

- Add s-058, stage direction sematnics only allowed in `<i>` elements

- Add s-059 internal link beginning with ../text/

- Add s-060, italics on name that requires quotes

- Add m-057, xml:lang illegal in long description. Thanks to Robin Whittleton

- Improve s-046

- Improve t-002

- Fix bad filename in s-027

## se modernize-spelling

- Various additions.

## se word-count

- Improve removal of PG headers/footers

# v1.5.0

## General

- The Rich console library is now used for output. This allows us much more detailed and nicely-formatted table output in lint, as well as nicer colors, and hyperlinks in output. If your terminal supports it, all filenames (including filenames in error messages) are now hyperlinked, so that you can ctrl + click on them to open them directly instead of having to hunt for them in your editor or filesystem.

## se build-images

- Catch exception when trying to parse SVGs

## se clean

- Remove space before `<br/>` and non-tag content

- Add t-043, dialog tag missing punctuation

- Add x-016, language tag starting in uppercase letter

- Add m-054, SE URL with trailing slash

- Improve check for malformed URLs

## se create-draft

- When creating title/cover page images, if the first line is a single short word like "the", "of", "or", etc., then move the next word up to the first line

## se create-draft

- Remove `<!CDATA` tag from long description in the content.opf template, now that se clean correctly escapes the long-description

- Create a new draft with cover/titlepage images already built, so that drafts can be built with `se build` without errors from the get-go

## se lint

- Add m-052, check if alternate-title is missing in metadata

- Ignore all dotfiles in an ebook repo, and only issue f-001 if a dotfile is in the repo *and* tracked by Git

- Don't throw f-008 for files not tracked by Git

- Add t-041, illegal space before punctuation

- Improve t-036, check for missing opening/closing double quotes

- Add m-053, se:subject elements must be in alpha order

- Add t-042, possible typo

- Improve some slow regexes

- Remove -w option, replaced with a better incantation of GNU Parallel in the README

- Improve t-003, check for unclosed double quotes

- Improve t-010, time set with . instead of :

- Merge s-047, s-048, s-049, and s-50 into one message

- Add s-048, se:name.* semantic used on block-level element

- Add s-046, check for <p> elements that have poetry structure but no poetry semantic on parent

- Add s-049, `<header>` with direct child text node

- Improve s-026, invalid Roman numeral

- Add s-050, `<span>` element exists only to apply epub:type

- Add z:3998:lyrics to all verse-type checks

- Add m-055, missing data in metadata

## se modernize-spelling

- Add various new modernizations

## se typogrify

- Improve replacement of two-em-dashes

- Don't change existing rsquo chars. This will help prevent typogrify from ruining hand-made changes on subsequent runs.

- Don't remove white space before an em dash, if the white space is preceded by `<br/>`

## se word-count

- Added -p, --ignore-pg-boilerplate flag to attempt to ignore PG headers, footers, and page numbers when calculating word count

## se unicode-names

- New tabular output format for easier reading

# v1.4.0

## General

- Fix various errors in shell completions. Thanks to Dave Halliday

- Regexes using the [a-z] character set have been replaced to use the [\p{Letter}] Unicode property, which will catch non-ASCII letters

- Add CHANGELOG.md file

- Update required package versions

## se build

- Internally, cache CSSSelector instances to improve performance. Thanks to Dave Halliday

- Internally, throw exceptions instead of printing to the console

## se build-images

- Catch exception for invalid source directory. Thanks to Dave Halliday

## se clean

- Remove external call to xmllint, instead use lxml to pretty-print with Python for a huge performance improvement. Thanks to Dave Halliday

- remove -s,--single-lines option, as that case is now handled by default in the new implementation

- Remove white space between opening/closing tags and text nodes

- Lowercase tag and attributes names in XHTML

## se create-draft

- Remove `<!CDATA` tag from long description in the content.opf template, now that se clean correctly escapes the long-description

- Create a new draft with cover/titlepage images already built, so that drafts can be built with `se build` without errors from the get-go

## se lint

- All checks have been converted to xpath expressions, from regular expressions

- Add detailed error matches for various checks

- Improve message for missing verse/poetry styling

- Check for duplicate selectors in CSS

- Check for illegal ID attributes in SVGs

- Replace f-008 with a more general check URLs for complete URL safety, not just for uppercase letters in URL

- Check for illegal `<style>` elements

- Replace x-015 with a more general check for illegal elements in `<head>`

- Improve check for incorrect filenames

- Check for lowercase letters after periods

- Improve check for miscurled quotation marks

- Improve check for correctly formatted measurements

- Improve check for period followed by lowercase letter

- Check for correct height/width on cover.jpg

- Check for `<abbr>` with `title` attribute

- Check for `<article>` without `id` attribute

- Check for `<img>` element without `alt` attribute

- Tweak s-006 error message and fix exception in rare corner cases

- Check for `<cite>` as direct child of `<blockquote>`

- Improve t-008 check by checking for white space, not absence of nbsp

- Check for initialisms without periods

- Internally, cache dom objects to improve lint performance

- Check for initialisms followed by periods

- Internally, cache CSSSelector instances to improve performance. Thanks to Dave Halliday

- Add m-010, invalid `refines` attribute

- Add m-050, non-typogrified character in `<dc:title>`

- Add m-051, check for missing metadata elements

- Consolidate several checks into single broader checks

- Add check for invalid Roman numerals

- Internally, convert all instances of BS4 to LXML for consistency and performance

- If invoked with multiple ebooks, and one throws an exception (like invald XHTML), print to console and continue linting the rest of the books instead of exiting

- Add s-053, newlines in colophon not preceded by `<br/>`

- Add more detail to t-017 message

- Add t-003, space after dash

- Add t-034, `<cite>` preceded by em dash

- Add t-035, `<cite>` element not preceded by space

- Don't complain about mismatched ToC if header elements have the `hidden` attribute

- Change c-006 to include general check for any missing style, thus obsoleting c-007

- Add s-016, incorrect `the` before Google Books link

- Add t-036, mismatched rdquo

- Add t-037, `”` preceded by space

- Add t-038, `“` before closing `</p>`

- Add t-039, initialism followed by `’s`

- Detect if we're being called from GNU Parallel, so that we can tweak output accordingly

- Add -w,--wrap option to force line wraps to a certain column; useful for lint is called from GNU Parallel

- Add s-043, `<blockquote>` must have block-level child

- Add s-044, poetry/verse must have a descendant `<p>` element

- Add s-045, check for `<abbr>` without semantic class

- Add t-040, illegal period at end of subtitle

- Improve s-038 check for asterisms to also check for other kinds of section breaks that should be `<hr/>`

## se modernize-spelling

- Various additions to automated spelling replacements

- Fix error in subtile -> subtle change

- Remove proper names from word list used to calculate hyphen removals

- Fix maneuver modernization

- Add punctuation after some abbrevations even if not followed by white space

- Internally, remove some duplicate checks and merge some othes


## se print-title

- Remove endnotes from generated titles. Thanks to Robin Whittleton

- Fix bug where empty `<title>` elements would not get filled with the -i option

- Fix for correct titles for books with parts. Thanks to Robin Whittleton

## se prepare-release

- change -n option to -w for consistency with other options

## se recompose-epub

- Add -x,--xhtml option to output XHTML5 instead of HTML5

## se semanticate

- Add `<abbr>` around `vs.`, `Bros.`, and £sd shorthand

- Improved handling of P.S.

- Add more semantic meaning on some existing additions

- Fix for `eoc` class being added twice

## se titlecase

- Titlecase now correctly titlecases non-ASCII letters. This fix was also pushed upstream to the pypi titlecase package

- Tweak capitalization of `and` in some cases

- Titles consisting of *almost* all caps should now be correctly titlecased

## se typogrify

- Curl quotation marks before `'uns`, `'ud`, `'cept`

- Typogrify `<dc:description>` and long-description in content.opf when invoked

- Improved handling of P.S.

- Don't use word joiners or nbsp in content.opf long-description

- Add hair space between consecutive single quotes
