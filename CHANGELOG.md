v1.4.0
======

General
*******

- Fix various errors in shell completions. Thanks to Dave Halliday

- Regexes using the [a-z] character set have been replaced to use the [\p{Letter}] Unicode property, which will catch non-ASCII letters

- Add CHANGELOG.md file

- Update required package versions

se build
********

- Internally, cache CSSSelector instances to improve performance. Thanks to Dave Halliday

- Internally, throw exceptions instead of printing to the console

se build-images
***************

- Catch exception for invalid source directory. Thanks to Dave Halliday

se clean
********

- Remove external call to xmllint, instead use lxml to pretty-print with Python for a huge performance improvement. Thanks to Dave Halliday

- remove -s,--single-lines option, as that case is now handled by default in the new implementation

- Remove white space between opening/closing tags and text nodes

- Lowercase tag and attributes names in XHTML

se create-draft
***************

- Remove <!CDATA tag from long description in the content.opf template, now that se clean correctly escapes the long-description

- Create a new draft with cover/titlepage images already built, so that drafts can be built with `se build` without errors from the get-go

se lint
*******

- All checks have been converted to xpath expressions, from regular expressions

- Add detailed error matches for various checks

- Improve message for missing verse/poetry styling

- Check for duplicate selectors in CSS

- Check for illegal ID attributes in SVGs

- Replace f-008 with a more general check URLs for complete URL safety, not just for uppercase letters in URL

- Check for illegal `<style>` elements

- Replace x-015 with a more general check for illegal elements in <head>

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

se modernize-spelling
*********************

- Various additions to automated spelling replacements

- Fix error in subtile -> subtle change

- Remove proper names from word list used to calculate hyphen removals

- Fix maneuver modernization

- Add punctuation after some abbrevations even if not followed by white space

- Internally, remove some duplicate checks and merge some othes


se print-title
**************

- Remove endnotes from generated titles. Thanks to Robin Whittleton

- Fix bug where empty `<title>` elements would not get filled with the -i option

- Fix for correct titles for books with parts. Thanks to Robin Whittleton

se prepare-release
**************

- change -n option to -w for consistency with other options

se recompose-epub
*****************

- Add -x,--xhtml option to output XHTML5 instead of HTML5

se semanticate
**************

- Add <abbr> around `vs.`, `Bros.`, and £sd shorthand

- Improved handling of P.S.

- Add more semantic meaning on some existing additions

- Fix for `eoc` class being added twice

se titlecase
************

- Titlecase now correctly titlecases non-ASCII letters. This fix was also pushed upstream to the pypi titlecase package

- Tweak capitalization of `and` in some cases

- Titles consisting of *almost* all caps should now be correctly titlecased

se typogrify
************

- Curl quotation marks before `'uns`, `'ud`, `'cept`

- Typogrify `<dc:description>` and long-description in content.opf when invoked

- Improved handling of P.S.

- Don't use word joiners or nbsp in content.opf long-description

- Add hair space between consecutive single quotes
