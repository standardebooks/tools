function __fish_se_no_subcommand --description "Test if se has yet to be given the subcommand"
	for i in (commandline -opc)
		if contains -- $i add-file british2american build build-ids build-images build-loi build-manifest build-spine build-svg-titles build-title build-toc clean compare-versions create-draft css-select dec2roman extract-ebook find-mismatched-dashes find-mismatched-diacritics find-unusual-characters help hyphenate interactive-replace lint make-url-safe modernize-spelling prepare-release recompose-epub renumber-endnotes roman2dec semanticate shift-endnotes shift-illustrations split-file titlecase typogrify unicode-names word-count xpath
			return 1
		end
	end
	return 0
end

complete -c se -n "__fish_se_no_subcommand" -s h -l help -x -d "Show this help message and exit."
complete -c se -n "__fish_se_no_subcommand" -s p -l plain -x -d "Print plain text output, without tables, colors, or other formatting. For tabular output but without colors, set the NO_COLOR environmental variable to a non-empty value instead of this option."
complete -c se -n "__fish_se_no_subcommand" -s v -l version -x -d "Print version number and exit."

complete -c se -n "__fish_se_no_subcommand" -a add-file -d "Add a Standard Ebooks template file and any accompanying CSS."
complete -c se -A -n "__fish_seen_subcommand_from add-file" -s f -l force -x -d "Overwrite any existing files."
complete -c se -A -n "__fish_seen_subcommand_from add-file" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from add-file" -a "dedication dramatis-personae endnotes epigraph glossary halftitlepage ignore" -d "The type of file to add."

complete -c se -n "__fish_se_no_subcommand" -a british2american -d "Try to convert British quote style to American quote style. Quotes must already be typogrified using se typogrify. This script isn’t perfect; proofreading is required, especially near closing quotes near to em-dashes."
complete -c se -A -n "__fish_seen_subcommand_from british2american" -s f -l force -x -d "Force conversion of quote style."
complete -c se -A -n "__fish_seen_subcommand_from british2american" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from british2american" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a build -d "Build compatible .epub and advanced .epub ebooks from a Standard Ebook source directory. Output is placed in the current directory, or the target directory with --output-dir."
complete -c se -A -n "__fish_seen_subcommand_from build" -s b -l kobo -x -d "Also build a .kepub.epub file for Kobo."
complete -c se -A -n "__fish_seen_subcommand_from build" -s c -l check -x -d "Use epubcheck to validate the compatible .epub file, and the Nu Validator (v.Nu) to validate XHTML5; if Ace is installed, also validate using Ace; if --kindle is also specified and epubcheck, v.Nu, or Ace fail, don’t create a Kindle file."
complete -c se -A -n "__fish_seen_subcommand_from build" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from build" -s k -l kindle -x -d "Also build an .azw3 file for Kindle."
complete -c se -A -n "__fish_seen_subcommand_from build" -s o -l output-dir -d "A directory to place output files in; will be created if it doesn’t exist."
complete -c se -A -n "__fish_seen_subcommand_from build" -s p -l proof -x -d "Insert additional CSS rules that are helpful for proofreading; output filenames will end in .proof."
complete -c se -A -n "__fish_seen_subcommand_from build" -s v -l verbose -x -d "Increase output verbosity."
complete -c se -A -n "__fish_seen_subcommand_from build" -s y -l check-only -x -d "Run tests used by --check, but don’t output any ebook files, and exit after checking."

complete -c se -n "__fish_se_no_subcommand" -a build-ids -d "Change id attributes for non-sectioning content to their expected values across the entire ebook. IDs must be globally unique and correctly referenced, and the ebook spine must be complete."
complete -c se -A -n "__fish_seen_subcommand_from build-ids" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from build-ids" -s n -l no-endnotes -x -d "Exclude endnotes."
complete -c se -A -n "__fish_seen_subcommand_from build-ids" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a build-images -d "Generate ebook cover and titlepages for Standard Ebooks ebooks, and then build ebook covers and titlepages, placing the output in DIRECTORY/src/epub/images/."
complete -c se -A -n "__fish_seen_subcommand_from build-images" -s g -l no-generate -x -d "Don’t generate new source cover/titlepage SVGs, only build existing ones."
complete -c se -A -n "__fish_seen_subcommand_from build-images" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from build-images" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a build-loi -d "Update the LoI file based on all <figure> elements that contain an <img>."
complete -c se -A -n "__fish_seen_subcommand_from build-loi" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from build-loi" -s s -l stdout -x -d "Print to stdout instead of writing to the LoI file."

complete -c se -n "__fish_se_no_subcommand" -a build-manifest -d "Generate the <manifest> element for the given Standard Ebooks source directory and write it to the ebook’s metadata file."
complete -c se -A -n "__fish_seen_subcommand_from build-manifest" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from build-manifest" -s s -l stdout -x -d "Print to stdout instead of writing to the metadata file."

complete -c se -n "__fish_se_no_subcommand" -a build-spine -d "Generate the <spine> element for the given Standard Ebooks source directory and write it to the ebook’s metadata file."
complete -c se -A -n "__fish_seen_subcommand_from build-spine" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from build-spine" -s s -l stdout -x -d "Print to stdout instead of writing to the metadata file."

complete -c se -n "__fish_se_no_subcommand" -a build-svg-titles -d "Update or add SVG <title> elements based on the alt attributes from the <img> elements."
complete -c se -A -n "__fish_seen_subcommand_from build-svg-titles" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from build-svg-titles" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a build-title -d "Generate the title of an XHTML file based on its headings and update the file’s <title> element."
complete -c se -A -n "__fish_seen_subcommand_from build-title" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from build-title" -s n -l no-newline -x -d "With --stdout, don’t end output with a newline."
complete -c se -A -n "__fish_seen_subcommand_from build-title" -s s -l stdout -x -d "Print to stdout instead of writing to the file."

complete -c se -n "__fish_se_no_subcommand" -a build-toc -d "Generate the table of contents for the ebook’s source directory and update the ToC file."
complete -c se -A -n "__fish_seen_subcommand_from build-toc" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from build-toc" -s s -l stdout -x -d "Print to stdout instead of writing to the ToC file."

complete -c se -n "__fish_se_no_subcommand" -a clean -d "Prettify and canonicalize individual XHTML, SVG, or CSS files, or all XHTML, SVG, or CSS files in a source directory."
complete -c se -A -n "__fish_seen_subcommand_from clean" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from clean" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a compare-versions -d "Use Firefox to render and compare XHTML files in an ebook repository. Run on a dirty repository to visually compare the repository’s dirty state with its clean state. If a file renders differently, place screenshots of the new, original, and diff (if available) renderings in the current working directory. A file called diff.html is created to allow for side-by-side comparisons of original and new files."
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s i -l include-se-files -x -d "Include commonly-excluded Standard Ebooks files like imprint, titlepage, and colophon."
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s n -l no-images -x -d "Don’t create images of diffs."
complete -c se -A -n "__fish_seen_subcommand_from compare-versions" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a create-draft -d "Create a skeleton of a new Standard Ebook in the current directory."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s a -l author -d "An author of the ebook."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s e -l email -d "Use this email address as the main committer for the local Git repository."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s f -l fp-id -d "The Faded Page ID number of the ebook to download."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s o -l offline -x -d "Create draft without network access."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s p -l pg-id -d "The Project Gutenberg ID number of the ebook to download."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s r -l translator -d "A translator of the ebook."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s t -l title -d "The title of the ebook."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s v -l verbose -x -d "Increase output verbosity."
complete -c se -A -n "__fish_seen_subcommand_from create-draft" -s w -l white-label -x -d "Create a generic epub skeleton without Standard Ebooks branding."

complete -c se -n "__fish_se_no_subcommand" -a css-select -d "Print the results of a CSS selector evaluated against a set of XHTML files."
complete -c se -A -n "__fish_seen_subcommand_from css-select" -s f -l only-filenames -x -d "Only output filenames of files that contain matches, not the matches themselves."
complete -c se -A -n "__fish_seen_subcommand_from css-select" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from css-select" -s q -l quiet -x -d "Don’t output anything, only a return code if matches exist in any files."

complete -c se -n "__fish_se_no_subcommand" -a dec2roman -d "Convert a decimal number to a Roman numeral."
complete -c se -A -n "__fish_seen_subcommand_from dec2roman" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from dec2roman" -s n -l no-newline -x -d "Don’t end output with a newline."

complete -c se -n "__fish_se_no_subcommand" -a extract-ebook -d "Extract an .epub, .mobi, or .azw3 ebook into ./FILENAME.extracted/ or a target directory."
complete -c se -A -n "__fish_seen_subcommand_from extract-ebook" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from extract-ebook" -s o -l output-dir -d "A target directory to extract into."
complete -c se -A -n "__fish_seen_subcommand_from extract-ebook" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a find-mismatched-dashes -d "Find words with mismatched dashes in a set of XHTML files. For example, extra-physical in one file and extraphysical in another."
complete -c se -A -n "__fish_seen_subcommand_from find-mismatched-dashes" -s h -l help -x -d "Show this help message and exit."

complete -c se -n "__fish_se_no_subcommand" -a find-mismatched-diacritics -d "Find words with mismatched diacritics in a set of XHTML files. For example, cafe in one file and café in another."
complete -c se -A -n "__fish_seen_subcommand_from find-mismatched-diacritics" -s h -l help -x -d "Show this help message and exit."

complete -c se -n "__fish_se_no_subcommand" -a find-unusual-characters -d "Find characters outside a nominal expected range in a set of XHTML files. This can be useful to find transcription mistakes and mojibake."
complete -c se -A -n "__fish_seen_subcommand_from find-unusual-characters" -s h -l help -x -d "Show this help message and exit."

complete -c se -n "__fish_se_no_subcommand" -a help -d "List available Standard Ebooks commands."

complete -c se -n "__fish_se_no_subcommand" -a hyphenate -d "Insert soft hyphens at syllable breaks in XHTML files."
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s i -l ignore-h-tags -x -d "Don’t add soft hyphens to text in <h1-6> tags."
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s l -l language -d "Specify the language for the XHTML files; if unspecified, defaults to the xml:lang or lang attribute of the root <html> element."
complete -c se -A -n "__fish_seen_subcommand_from hyphenate" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a interactive-replace -d "Perform an interactive search and replace on a list of files using Python-flavored regex. The view is scrolled using the arrow keys, with alt to scroll by page in any direction. Basic Emacs (default) or Vim style navigation is available. The following actions are possible: (y) Accept replacement. (n) Reject replacement. (a) Accept all remaining replacements in this file. (r) Reject all remaining replacements in this file. (c) Center on match. (q) Save this file and quit."
complete -c se -A -n "__fish_seen_subcommand_from interactive-replace" -s d -l dot-all -x -d "Make . match newlines; equivalent to regex.DOTALL."
complete -c se -A -n "__fish_seen_subcommand_from interactive-replace" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from interactive-replace" -s i -l ignore-case -x -d "Ignore case when matching; equivalent to regex.IGNORECASE."
complete -c se -A -n "__fish_seen_subcommand_from interactive-replace" -s m -l multiline -x -d "Make ^ and \$ consider each line; equivalent to regex.MULTILINE."
complete -c se -A -n "__fish_seen_subcommand_from interactive-replace" -s v -l vim -x -d "Use basic Vim-like navigation shortcuts."

complete -c se -n "__fish_se_no_subcommand" -a lint -d "Check for various Standard Ebooks style errors."
complete -c se -A -n "__fish_seen_subcommand_from lint" -s a -l allow -d "If an se-lint-ignore.xml file is present, allow these specific codes to be raised by lint."
complete -c se -A -n "__fish_seen_subcommand_from lint" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from lint" -s s -l skip-lint-ignore -x -d "Ignore all rules in the se-lint-ignore.xml file."
complete -c se -A -n "__fish_seen_subcommand_from lint" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a make-url-safe -d "Make a string URL-safe."
complete -c se -A -n "__fish_seen_subcommand_from make-url-safe" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from make-url-safe" -s n -l no-newline -x -d "Don’t end output with a newline."

complete -c se -n "__fish_se_no_subcommand" -a modernize-spelling -d "Modernize spelling of some archaic words, and replace words that may be archaically compounded with a dash to a more modern spelling. For example, replace ash-tray with ashtray."
complete -c se -A -n "__fish_seen_subcommand_from modernize-spelling" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from modernize-spelling" -s n -l no-hyphens -x -d "Don’t modernize hyphenation."
complete -c se -A -n "__fish_seen_subcommand_from modernize-spelling" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a prepare-release -d "Calculate work word count, insert release date if not yet set, and update modified date and revision number."
complete -c se -A -n "__fish_seen_subcommand_from prepare-release" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from prepare-release" -s r -l no-revision -x -d "Don’t increment the revision number."
complete -c se -A -n "__fish_seen_subcommand_from prepare-release" -s v -l verbose -x -d "Increase output verbosity."
complete -c se -A -n "__fish_seen_subcommand_from prepare-release" -s w -l no-word-count -x -d "Don’t calculate word count."

complete -c se -n "__fish_se_no_subcommand" -a recompose-epub -d "Recompose a Standard Ebooks source directory into a single (X?)HTML5 file, and print to standard output."
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s e -l extra-css-file -d "The path to an additional CSS file to include after any CSS files in the epub."
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s i -l image-files -x -d "Leave image src attributes as relative URLs instead of inlining as data: URIs."
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s o -l output -d "A file to write output to instead of printing to standard output."
complete -c se -A -n "__fish_seen_subcommand_from recompose-epub" -s x -l xhtml -x -d "Output XHTML instead of HTML5."

complete -c se -n "__fish_se_no_subcommand" -a renumber-endnotes -d "Renumber all endnotes and noterefs sequentially from the beginning, taking care to match noterefs and endnotes if possible."
complete -c se -A -n "__fish_seen_subcommand_from renumber-endnotes" -s b -l brute-force -x -d "Renumber without checking that noterefs and endnotes match; may result in endnotes with empty backlinks or noterefs without matching endnotes."
complete -c se -A -n "__fish_seen_subcommand_from renumber-endnotes" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from renumber-endnotes" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a roman2dec -d "Convert a Roman numeral to a decimal number."
complete -c se -A -n "__fish_seen_subcommand_from roman2dec" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from roman2dec" -s n -l no-newline -x -d "Don’t end output with a newline."

complete -c se -n "__fish_se_no_subcommand" -a semanticate -d "Automatically add semantics to Standard Ebooks source directories."
complete -c se -A -n "__fish_seen_subcommand_from semanticate" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from semanticate" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a shift-endnotes -d "Increment or decrement the specified endnote and all following endnotes by 1 or a specified amount."
complete -c se -A -n "__fish_seen_subcommand_from shift-endnotes" -s a -l amount -d "The amount to increment or decrement by; defaults to 1."
complete -c se -A -n "__fish_seen_subcommand_from shift-endnotes" -s d -l decrement -x -d "Decrement the target endnote number and all following endnotes."
complete -c se -A -n "__fish_seen_subcommand_from shift-endnotes" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from shift-endnotes" -s i -l increment -x -d "Increment the target endnote number and all following endnotes."

complete -c se -n "__fish_se_no_subcommand" -a shift-illustrations -d "Increment or decrement the specified illustration and all following illustrations by 1 or a specified amount."
complete -c se -A -n "__fish_seen_subcommand_from shift-illustrations" -s a -l amount -d "The amount to increment or decrement by; defaults to 1."
complete -c se -A -n "__fish_seen_subcommand_from shift-illustrations" -s d -l decrement -x -d "Decrement the target illustration number and all following illustrations."
complete -c se -A -n "__fish_seen_subcommand_from shift-illustrations" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from shift-illustrations" -s i -l increment -x -d "Increment the target illustration number and all following illustrations."

complete -c se -n "__fish_se_no_subcommand" -a split-file -d "Split an XHTML file into many files at all instances of <!--se:split-->, and include a header template for each file."
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s f -l filename-format -d "A format string for the output files; %%n is replaced with the current chapter number; defaults to chapter-%%n.xhtml."
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s s -l start-at -d "Start numbering chapters at this number, instead of at 1."
complete -c se -A -n "__fish_seen_subcommand_from split-file" -s t -l template-file -d "A file containing an XHTML template to use for each chapter; the string LANG is replaced by the guessed language, the string NUMBER is replaced by the chapter number, the string NUMERAL is replaced by the chapter Roman numeral, and the string TEXT is replaced by the chapter body."

complete -c se -n "__fish_se_no_subcommand" -a titlecase -d "Convert a string to titlecase."
complete -c se -A -n "__fish_seen_subcommand_from titlecase" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from titlecase" -s n -l no-newline -x -d "Don’t end output with a newline."

complete -c se -n "__fish_se_no_subcommand" -a typogrify -d "Apply some scriptable typography rules from the Standard Ebooks typography manual to XHTML files."
complete -c se -A -n "__fish_seen_subcommand_from typogrify" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from typogrify" -s n -l no-quotes -x -d "Don’t convert to smart quotes before doing other adjustments."
complete -c se -A -n "__fish_seen_subcommand_from typogrify" -s v -l verbose -x -d "Increase output verbosity."

complete -c se -n "__fish_se_no_subcommand" -a unicode-names -d "Display Unicode code points, descriptions, and links to more details for each character in a string. Useful for differentiating between different flavors of spaces, dashes, and invisible characters like word joiners."
complete -c se -A -n "__fish_seen_subcommand_from unicode-names" -s h -l help -x -d "Show this help message and exit."

complete -c se -n "__fish_se_no_subcommand" -a word-count -d "Count the number of words in an XHTML file and optionally categorize by length. If multiple files are specified, show the total word count for all."
complete -c se -A -n "__fish_seen_subcommand_from word-count" -s c -l categorize -x -d "Include length categorization in output."
complete -c se -A -n "__fish_seen_subcommand_from word-count" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from word-count" -s p -l ignore-pg-boilerplate -x -d "Attempt to ignore Project Gutenberg boilerplate headers and footers before counting."
complete -c se -A -n "__fish_seen_subcommand_from word-count" -s x -l exclude-se-files -x -d "Exclude some non-bodymatter files common to Standard Ebooks ebooks, like the ToC and colophon."

complete -c se -n "__fish_se_no_subcommand" -a xpath -d "Print the results of an xpath expression evaluated against a set of XHTML files. The default namespace is removed."
complete -c se -A -n "__fish_seen_subcommand_from xpath" -s f -l only-filenames -x -d "Only output filenames of files that contain matches, not the matches themselves."
complete -c se -A -n "__fish_seen_subcommand_from xpath" -s h -l help -x -d "Show this help message and exit."
complete -c se -A -n "__fish_seen_subcommand_from xpath" -s q -l quiet -x -d "Don’t output anything, only a return code if matches exist in any files."
