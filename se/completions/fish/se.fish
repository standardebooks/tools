function __fish_se_no_subcommand --description "Test if se has yet to be given the subcommand"
	for i in (commandline -opc)
		if contains -- $i british2american build build-ids build-images build-manifest build-spine build-title build-toc clean compare-versions create-draft css-select dec2roman extract-ebook find-mismatched-dashes find-mismatched-diacritics find-unusual-characters help hyphenate interactive-replace lint make-url-safe modernize-spelling prepare-release recompose-epub renumber-endnotes roman2dec semanticate shift-endnotes shift-illustrations split-file titlecase typogrify unicode-names version word-count xpath
			return 1
		end
	end
	return 0
end

complete -c se -n "__fish_se_no_subcommand" -s h -l help -x -d "show a help message and exit"
complete -c se -n "__fish_se_no_subcommand" -s p -l plain -x -d "print plain text output, without tables or formatting"
complete -c se -n "__fish_se_no_subcommand" -s v -l version -x -d "print version number and exit"

complete -c se -n "__fish_se_no_subcommand" -a british2american -d "Try to convert British quote style to American quote style."
complete -c se -A -n "__fish_seen_subcommand_from british2american" -s f -l force -d "force conversion of quote style"
complete -c se -A -n "__fish_seen_subcommand_from british2american" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from british2american" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a build -d "Build an ebook from a Standard Ebook source directory."
complete -c se -A -n "__fish_seen_subcommand_from build" -s b -l kobo -d "also build a .kepub.epub file for Kobo"
complete -c se -A -n "__fish_seen_subcommand_from build" -s c -l check -d "use epubcheck to validate the compatible .epub file; if Ace is installed, also validate using Ace; if --kindle is also specified and epubcheck or Ace fail, don’t create a Kindle file"
complete -c se -A -n "__fish_seen_subcommand_from build" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from build" -s k -l kindle -d "also build an .azw3 file for Kindle."
complete -c se -A -n "__fish_seen_subcommand_from build" -s o -l output-dir -d "a directory to place output files in; will be created if it doesn’t exist"
complete -c se -A -n "__fish_seen_subcommand_from build" -s p -l proof -d "insert additional CSS rules that are helpful for proofreading; output filenames will end in .proof"
complete -c se -A -n "__fish_seen_subcommand_from build" -s v -l verbose -d "increase output verbosity"
complete -c se -A -n "__fish_seen_subcommand_from build" -s y -l check-only -d "run tests used by --check but don’t output any ebook files and exit after checking"

complete -c se -n "__fish_se_no_subcommand" -a build-ids -d "Change ID attributes for non-sectioning content to their expected values across the entire ebook. IDs must be globally unique and correctly referenced, and the ebook spine must be complete."
complete -c se -A -n "__fish_seen_subcommand_from build-images" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from build-images" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a build-images -d "Build ebook cover and titlepage images in a Standard Ebook source directory."
complete -c se -A -n "__fish_seen_subcommand_from build-images" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from build-images" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a clean -d "Prettify and canonicalize individual XHTML or SVG files."
complete -c se -A -n "__fish_seen_subcommand_from clean" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from clean" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a compare-versions -d "Render and compare XHTML files in an ebook repository."
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s i -l include-se-files -d "include commonly-excluded S.E. files like imprint, titlepage, and colophon"
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s n -l no-images -d "don’t create images of diffs"
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a create-draft -d "Create a skeleton of a new Standard Ebook."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s a -l author -d "the author of the ebook"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s e -l email -d "use this email address as the main committer for the local Git repository"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s i -l illustrator -d "the illustrator of the ebook"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s p -l pg-id -d "the Project Gutenberg ID number of the ebook to download"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s o -l offline -d "create draft without network access"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s r -l translator -d "the translator of the ebook"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s t -l title -d "the title of the ebook"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s w -l white-label -d "create a generic epub skeleton without S.E. branding"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a css-select -d "Print the results of a CSS selector evaluated against a set of XHTML files."
complete -c se -A -n "__fish_seen_subcommand_from css-select" -s f -l only-files -x -d "only output filenames of files that contain matches, not the matches themselves"
complete -c se -A -n "__fish_seen_subcommand_from css-select" -s h -l help -x -d "show this help message and exit"

complete -c se -n "__fish_se_no_subcommand" -a dec2roman -d "Convert a decimal number to a Roman numeral."
complete -c se -A -n "__fish_seen_subcommand_from dec2roman" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from dec2roman" -s n -l no-newline -d "don’t end output with a newline"

complete -c se -n "__fish_se_no_subcommand" -a extract-ebook -d "Extract an EPUB, MOBI, or AZW3 ebook."
complete -c se -A -n "__fish_seen_subcommand_from extract-ebook" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from extract-ebook" -s o -l output-dir -d "a target directory to extract into"
complete -c se -A -n "__fish_seen_subcommand_from extract-ebook" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a find-mismatched-dashes -d "Find words with mismatched dashes in a set of XHTML files."
complete -c se -A -n "__fish_seen_subcommand_from find-mismatched-dashes" -s h -l help -x -d "show this help message and exit"

complete -c se -n "__fish_se_no_subcommand" -a find-mismatched-diacritics -d "Find words with mismatched diacritics in a set of XHTML files."
complete -c se -A -n "__fish_seen_subcommand_from find-mismatched-diacritics" -s h -l help -x -d "show this help message and exit"

complete -c se -n "__fish_se_no_subcommand" -a find-unusual-characters -d "Find characters outside a nominal expected range in a set of XHTML files."
complete -c se -A -n "__fish_seen_subcommand_from find-unusual-characters" -s h -l help -x -d "show this help message and exit"

complete -c se -n "__fish_se_no_subcommand" -f -a help -d "List available S.E. commands"

complete -c se -n "__fish_se_no_subcommand" -a hyphenate -d "Insert soft hyphens at syllable breaks in an XHTML file."
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s i -l ignore-h-tags -d "don’t add soft hyphens to text in <h1-6> tags"
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s l -l language -d "specify the language for the XHTML files; if unspecified, defaults to the `xml:lang` or `lang` attribute of the root <html> element"
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a interactive-replace -d "Perform an interactive search and replace on a list of files using Python-flavored regex. The view is scrolled using the arrow keys, with alt to scroll by page in any direction. Basic Emacs (default) or Vim style navigation is available. The following actions are possible: (y) Accept replacement. (n) Reject replacement. (a) Accept all remaining replacements in this file. (r) Reject all remaining replacements in this file. (c) Center on match. (q) Save this file and quit."
complete -c se -A -n "__fish_seen_subcommand_from interactive-replace" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from interactive-replace" -s i -l ignore-case -x -d "ignore case when matching; equivalent to regex.IGNORECASE"
complete -c se -A -n "__fish_seen_subcommand_from interactive-replace" -s m -l multiline -x -d "make `^` and `\$` consider each line; equivalent to regex.MULTILINE"
complete -c se -A -n "__fish_seen_subcommand_from interactive-replace" -s d -l dot-all -x -d "make `.` match newlines; equivalent to regex.DOTALL"
complete -c se -A -n "__fish_seen_subcommand_from interactive-replace" -s v -l vim -x -d "use basic Vim-like navigation shortcuts"

complete -c se -n "__fish_se_no_subcommand" -a lint -d "Check for various Standard Ebooks style errors."
complete -c se -A -n "__fish_seen_subcommand_from lint" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from lint" -s a -l allow -d "if an se-lint-ignore.xml file is present, allow these specific codes to be raised by lint"
complete -c se -A -n "__fish_seen_subcommand_from lint" -s s -l skip-lint-ignore -d "ignore all rules in the se-lint-ignore.xml file"
complete -c se -A -n "__fish_seen_subcommand_from lint" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a make-url-safe -d "Make a string URL-safe."
complete -c se -A -n "__fish_seen_subcommand_from make-url-safe" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from make-url-safe" -s n -l no-newline -d "don’t end output with a newline"

complete -c se -n "__fish_se_no_subcommand" -a modernize-spelling -d "Modernize spelling of some archaic words, and replace words that may be archaically compounded with a dash to a more modern spelling."
complete -c se -A -n "__fish_seen_subcommand_from modernize-spelling" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from modernize-spelling" -s n -l no-hyphens -d "don’t modernize hyphenation"
complete -c se -A -n "__fish_seen_subcommand_from modernize-spelling" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a prepare-release -d "Calculate work word count, insert release date if not yet set, and update modified date and revision number."
complete -c se -A -n "__fish_seen_subcommand_from prepare-release" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from prepare-release" -s r -l no-revision -d "don’t increment the revision number"
complete -c se -A -n "__fish_seen_subcommand_from prepare-release" -s w -l no-word-count -d "don’t calculate word count"
complete -c se -A -n "__fish_seen_subcommand_from prepare-release" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a build-manifest -d "Generate the <manifest> element for the given Standard Ebooks source directory and write it to the ebook’s metadata file."
complete -c se -A -n "__fish_seen_subcommand_from build-manifest" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from build-manifest" -s s -l stdout -d "print to stdout instead of writing to the metadata file"

complete -c se -n "__fish_se_no_subcommand" -a build-spine -d "Generate the <spine> element for the given Standard Ebooks source directory and write it to the ebook’s metadata file."
complete -c se -A -n "__fish_seen_subcommand_from build-spine" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from build-spine" -s s -l stdout -d "print to stdout instead of writing to the metadata file"

complete -c se -n "__fish_se_no_subcommand" -a build-title -d "Generate the title of an XHTML file based on its headings and update the file’s <title> element."
complete -c se -A -n "__fish_seen_subcommand_from build-title" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from build-title" -s n -l no-newline -d "with --stdout, don’t end output with a newline"
complete -c se -A -n "__fish_seen_subcommand_from build-title" -s s -l stdout -d "print to stdout intead of writing to the file"

complete -c se -n "__fish_se_no_subcommand" -a build-toc -d "Generate the table of contents for the ebook’s source directory and update the ToC file."
complete -c se -A -n "__fish_seen_subcommand_from build-toc" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from build-toc" -s s -l stdout -d "print to stdout intead of writing to the ToC file"

complete -c se -n "__fish_se_no_subcommand" -a recompose-epub -d "Recompose a Standard Ebooks source directory into a single HTML5 file, and print to standard output"
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s o -l output -d "a file to write output to instead of printing to standard output"
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s x -l xhtml -d "output XHTML instead of HTML5"
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s e -l extra-css-file -d "the path to an additional CSS file to include after any CSS files in the epub"

complete -c se -n "__fish_se_no_subcommand" -a renumber-endnotes -d "Renumber all endnotes and noterefs sequentially from the beginning, taking care to match noterefs and endnotes if possible."
complete -c se -A -n "__fish_seen_subcommand_from renumber-endnotes" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from renumber-endnotes" -s b -l brute-force -d "renumber without checking that noterefs and endnotes match; may result in endnotes with empty backlinks or noterefs without matching endnotes"
complete -c se -A -n "__fish_seen_subcommand_from renumber-endnotes" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a roman2dec -d "Convert a Roman numeral to a decimal number."
complete -c se -A -n "__fish_seen_subcommand_from roman2dec" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from roman2dec" -s n -l no-newline -d "don’t end output with a newline"

complete -c se -n "__fish_se_no_subcommand" -a semanticate -d "Apply some scriptable semantics rules from the Standard Ebooks semantics manual."
complete -c se -A -n "__fish_seen_subcommand_from semanticate" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from semanticate" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a shift-endnotes -d "Increment the specified endnote and all following endnotes by 1 or a specified amount."
complete -c se -A -n "__fish_seen_subcommand_from shift-endnotes" -s d -l decrement -d "decrement the target endnote number and all following endnotes"
complete -c se -A -n "__fish_seen_subcommand_from shift-endnotes" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from shift-endnotes" -s i -l increment -d "increment the target endnote number and all following endnotes"

complete -c se -n "__fish_se_no_subcommand" -a shift-illustrations -d "Increment the specified illustration and all following illustrations by 1 or a specified amount."
complete -c se -A -n "__fish_seen_subcommand_from shift-illustrations" -s d -l decrement -d "decrement the target illustration number and all following illustrations"
complete -c se -A -n "__fish_seen_subcommand_from shift-illustrations" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from shift-illustrations" -s i -l increment -d "increment the target illustration number and all following illustrations"

complete -c se -n "__fish_se_no_subcommand" -a split-file -d "Split an XHTML file into many files."
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s f -l filename-format -d "a format string for the output files; `%n` is replaced with the current chapter number; defaults to `chapter-%n.xhtml`"
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s s -l start-at -d "start numbering chapters at this number, instead of at 1"
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s t -l template-file -d "a file containing an XHTML template to use for each chapter; the string `NUMBER` is replaced by the chapter number, the string `NUMERAL` is replaced by the chapter Roman numeral, and the string `TEXT` is replaced by the chapter body"

complete -c se -n "__fish_se_no_subcommand" -a titlecase -d "Convert a string to titlecase."
complete -c se -A -n "__fish_seen_subcommand_from titlecase" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from titlecase" -s n -l no-newline -d "don’t end output with a newline"

complete -c se -n "__fish_se_no_subcommand" -a typogrify -d "Apply some scriptable typography rules from the Standard Ebooks typography manual to a Standard Ebook source directory."
complete -c se -A -n "__fish_seen_subcommand_from typogrify" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from typogrify" -s n -l no-quotes -d "don’t convert to smart quotes before doing other adjustments"
complete -c se -A -n "__fish_seen_subcommand_from typogrify" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a unicode-names -d "Display Unicode code points, descriptions, and links to more details for each character in a string."
complete -c se -A -n "__fish_seen_subcommand_from unicode-names" -s h -l help -x -d "show this help message and exit"

complete -c se -n "__fish_se_no_subcommand" -a version -d "Print the version number and exit."

complete -c se -n "__fish_se_no_subcommand" -a word-count -d "Count the number of words in an HTML file and optionally categorize by length."
complete -c se -A -n "__fish_seen_subcommand_from word-count" -s c -l categorize -d "include length categorization in output"
complete -c se -A -n "__fish_seen_subcommand_from word-count" -s p -l ignore-pg-boilerplate -d "attempt to ignore Project Gutenberg boilerplate headers and footers before counting"
complete -c se -A -n "__fish_seen_subcommand_from word-count" -s x -l exclude-se-files -d "exclude some non-bodymatter files common to S.E. ebooks, like the ToC and colophon"
complete -c se -A -n "__fish_seen_subcommand_from word-count" -s h -l help -x -d "show this help message and exit"

complete -c se -n "__fish_se_no_subcommand" -a xpath -d "Print the results of an xpath expression evaluated against a set of XHTML files. The default namespace is removed."
complete -c se -A -n "__fish_seen_subcommand_from xpath" -s f -l only-files -x -d "only output filenames of files that contain matches, not the matches themselves"
complete -c se -A -n "__fish_seen_subcommand_from xpath" -s h -l help -x -d "show this help message and exit"
