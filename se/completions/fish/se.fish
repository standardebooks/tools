function __fish_se_no_subcommand --description "Test if se has yet to be given the subcommand"
	for i in (commandline -opc)
		if contains -- $i british2american build build-images clean compare-versions create-draft dec2roman extract-ebook find-mismatched-diacritics help hyphenate interactive-sr lint make-url-safe modernize-spelling prepare-release print-manifest print-spine print-toc recompose-epub renumber-endnotes reorder-endnotes roman2dec semanticate split-file titlecase typogrify unicode-names version word-count
			return 1
		end
	end
	return 0
end

complete -c se -n "__fish_se_no_subcommand" -s h -l help -x -d "Print usage"

complete -c se -n "__fish_se_no_subcommand" -a british2american -d "Try to convert British quote style to American quote style."
complete -c se -A -n "__fish_seen_subcommand_from british2american" -s f -l force -d "force conversion of quote style"
complete -c se -A -n "__fish_seen_subcommand_from british2american" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from british2american" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a build -d "Build an ebook from a Standard Ebook source directory."
complete -c se -A -n "__fish_seen_subcommand_from build" -s b -l kobo -d "also build a .kepub.epub file for Kobo"
complete -c se -A -n "__fish_seen_subcommand_from build" -s c -l check -d "use epubcheck to validate the compatible .epub file; if --kindle is also specified and epubcheck fails, don’t create a Kindle file"
complete -c se -A -n "__fish_seen_subcommand_from build" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from build" -s k -l kindle -d "also build an .azw3 file for Kindle."
complete -c se -A -n "__fish_seen_subcommand_from build" -s o -l output-dir -d "a directory to place output files in; will be created if it doesn’t exist"
complete -c se -A -n "__fish_seen_subcommand_from build" -s p -l proof -d "insert additional CSS rules that are helpful for proofreading; output filenames will end in .proof"
complete -c se -A -n "__fish_seen_subcommand_from build" -s t -l covers -d "output the cover and a cover thumbnail; can only be used when there is a single build target"
complete -c se -A -n "__fish_seen_subcommand_from build" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a build-images -d "Build ebook cover and titlepage images in a Standard Ebook source directory."
complete -c se -A -n "__fish_seen_subcommand_from build-images" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from build-images" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a clean -d "Prettify and canonicalize individual XHTML or SVG files."
complete -c se -A -n "__fish_seen_subcommand_from clean" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from clean" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a compare-versions -d "Render and compare XHTML files in an ebook repository."
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s i -l include-common -d "include commonly-excluded SE files like imprint, titlepage, and colophon"
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s n -l no-images -d "don’t create images of diffs"
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a create-draft -d "Create a skeleton of a new Standard Ebook."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s a -l author -d "the author of the ebook"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s e -l email -d "use this email address as the main committer for the local Git repository"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s i -l illustrator -d "the illustrator of the ebook"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s p -l pg-url -d "the URL of the Project Gutenberg ebook to download"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s o -l offline -d "create draft without network access"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s r -l translator -d "the translator of the ebook"
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s t -l title -d "the title of the ebook"

complete -c se -n "__fish_se_no_subcommand" -a dec2roman -d "Convert a decimal number to a Roman numeral."
complete -c se -A -n "__fish_seen_subcommand_from dec2roman" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from dec2roman" -s n -l no-newline -d "don’t end output with a newline"

complete -c se -n "__fish_se_no_subcommand" -a extract-ebook -d "Extract an EPUB, MOBI, or AZW3 ebook."
complete -c se -A -n "__fish_seen_subcommand_from extract-ebook" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from extract-ebook" -s o -l output-dir -d "a target directory to extract into"
complete -c se -A -n "__fish_seen_subcommand_from extract-ebook" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a find-mismatched-diacritics -d "Find words with mismatched diacritics in Standard Ebook source directories."
complete -c se -A -n "__fish_seen_subcommand_from find-mismatched-diacritics" -s h -l help -x -d "show this help message and exit"

complete -c se -n "__fish_se_no_subcommand" -f -a help -d "List available SE commands"

complete -c se -n "__fish_se_no_subcommand" -a hyphenate -d "Insert soft hyphens at syllable breaks in an XHTML file."
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s i -l ignore-h-tags -d "don’t add soft hyphens to text in <h1-6> tags"
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s l -l language -d "specify the language for the XHTML files; if unspecified, defaults to the `xml:lang` or `lang` attribute of the root <html> element"
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a interactive-sr -d "Use Vim to perform an interactive search and replace on a list of files."
complete -c se -A -n "__fish_seen_subcommand_from interactive-sr" -s h -l help -x -d "show this help message and exit"

complete -c se -n "__fish_se_no_subcommand" -a lint -d "Check for various Standard Ebooks style errors."
complete -c se -A -n "__fish_seen_subcommand_from lint" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from lint" -s n -l no-colors -d "don’t use color or hyperlinks in output"
complete -c se -A -n "__fish_seen_subcommand_from lint" -s p -l plain -d "print plain text output, without tables or colors"
complete -c se -A -n "__fish_seen_subcommand_from lint" -s s -l skip-lint-ignore -d "ignore rules in se-lint-ignore.xml file"
complete -c se -A -n "__fish_seen_subcommand_from lint" -s v -l verbose -d "increase output verbosity"
complete -c se -A -n "__fish_seen_subcommand_from lint" -s w -l wrap -d "force lines to wrap at this number of columns instead of auto-wrapping"

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

complete -c se -n "__fish_se_no_subcommand" -a print-spine -d "Print the <manifest> element for the given Standard Ebooks source directory to standard output, for use in that directory’s content.opf."
complete -c se -A -n "__fish_seen_subcommand_from print-manifest" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from print-manifest" -s i -l in-place -d "overwrite the <manifest> element in content.opf instead of printing to stdout"

complete -c se -n "__fish_se_no_subcommand" -a print-spine -d "Print the <spine> element for the given Standard Ebooks source directory to standard output, for use in that directory’s content.opf."
complete -c se -A -n "__fish_seen_subcommand_from print-spine" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from print-spine" -s i -l in-place -d "overwrite the <spine> element in content.opf instead of printing to stdout"

complete -c se -n "__fish_se_no_subcommand" -a print-title -d "Print the expected value for an XHTML file’s <title> element."
complete -c se -A -n "__fish_seen_subcommand_from print-toc" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from print-toc" -s i -l in-place -d "replace the file’s <title> element instead of printing to stdout"

complete -c se -n "__fish_se_no_subcommand" -a print-toc -d "Build a table of contents for an SE source directory and print to stdout."
complete -c se -A -n "__fish_seen_subcommand_from print-toc" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from print-toc" -s i -l in-place -d "overwrite the existing toc.xhtml file instead of printing to stdout."

complete -c se -n "__fish_se_no_subcommand" -a recompose-epub -d "Recompose a Standard Ebooks source directory into a single HTML5 file, and print to standard output"
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s o -l output -d "a file to write output to instead of printing to standard output"
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s x -l xhtml -d "output XHTML instead of HTML5"

complete -c se -n "__fish_se_no_subcommand" -a renumber-endnotes -d "Renumber all endnotes and noterefs sequentially from the beginning."
complete -c se -A -n "__fish_seen_subcommand_from renumber-endnotes" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from renumber-endnotes" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a reorder-endnotes -d "Increment the specified endnote and all following endnotes by 1."
complete -c se -A -n "__fish_seen_subcommand_from reorder-endnotes" -s d -l decrement -d "decrement the target endnote number and all following endnotes"
complete -c se -A -n "__fish_seen_subcommand_from reorder-endnotes" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from reorder-endnotes" -s i -l increment -d "increment the target endnote number and all following endnotes"

complete -c se -n "__fish_se_no_subcommand" -a roman2dec -d "Convert a Roman numeral to a decimal number."
complete -c se -A -n "__fish_seen_subcommand_from roman2dec" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from roman2dec" -s n -l no-newline -d "don’t end output with a newline"

complete -c se -n "__fish_se_no_subcommand" -a semanticate -d "Apply some scriptable semantics rules from the Standard Ebooks semantics manual."
complete -c se -A -n "__fish_seen_subcommand_from semanticate" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from semanticate" -s v -l verbose -d "increase output verbosity"

complete -c se -n "__fish_se_no_subcommand" -a split-file -d "Split an XHTML file into many files."
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s f -l filename-format -d "a format string for the output files; `%n` is replaced with the current chapter number; defaults to `chapter-%n.xhtml`"
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s h -l help -x -d "show this help message and exit"
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s s -l start-at -d "start numbering chapters at this number, instead of at 1"
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s t -l template-file -d "a file containing an XHTML template to use for each chapter; the string `NUMBER` is replaced by the chapter number, and the string `TEXT` is replaced by the chapter body"

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
complete -c se -A -n "__fish_seen_subcommand_from word-count" -s x -l exclude-se-files -d "exclude some non-bodymatter files common to SE ebooks, like the ToC and colophon"
complete -c se -A -n "__fish_seen_subcommand_from word-count" -s h -l help -x -d "show this help message and exit"

