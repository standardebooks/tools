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
