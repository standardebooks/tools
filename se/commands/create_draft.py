"""
This module implements the `se create_draft` command.
"""

import argparse

import regex

import se


def create_draft() -> int:
	"""
	Entry point for `se create-draft`

	The meat of this function is broken out into the create_draft.py module for readability
	and maintainability.
	"""

	# Use an alias because se.create_draft.create_draft() is the same name as this.create_draft()
	from se.executables_create_draft import create_draft as se_create_draft

	parser = argparse.ArgumentParser(description="Create a skeleton of a new Standard Ebook in the current directory.")
	parser.add_argument("-i", "--illustrator", dest="illustrator", help="the illustrator of the ebook")
	parser.add_argument("-r", "--translator", dest="translator", help="the translator of the ebook")
	parser.add_argument("-p", "--pg-url", dest="pg_url", help="the URL of the Project Gutenberg ebook to download")
	parser.add_argument("-e", "--email", dest="email", help="use this email address as the main committer for the local Git repository")
	parser.add_argument("-s", "--create-se-repo", dest="create_se_repo", action="store_true", help="initialize a new repository on the Standard Ebook server; Standard Ebooks admin powers required")
	parser.add_argument("-g", "--create-github-repo", dest="create_github_repo", action="store_true", help="initialize a new repository at the Standard Ebooks GitHub account; Standard Ebooks admin powers required; can only be used when --create-se-repo is specified")
	parser.add_argument("-o", "--offline", dest="offline", action="store_true", help="create draft without network access")
	parser.add_argument("-a", "--author", dest="author", required=True, help="the author of the ebook")
	parser.add_argument("-t", "--title", dest="title", required=True, help="the title of the ebook")
	args = parser.parse_args()

	if args.create_github_repo and not args.create_se_repo:
		se.print_error("--create-github-repo option specified, but --create-se-repo option not specified.")
		return se.InvalidInputException.code

	if args.pg_url and not regex.match("^https?://www.gutenberg.org/ebooks/[0-9]+$", args.pg_url):
		se.print_error("Project Gutenberg URL must look like: https://www.gutenberg.org/ebooks/<EBOOK-ID>")
		return se.InvalidInputException.code

	try:
		se_create_draft(args)
	except se.SeException as ex:
		se.print_error(ex)
		return ex.code

	return 0
