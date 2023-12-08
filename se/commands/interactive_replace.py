"""
This module implements the `se interactive-replace` command.
"""

import argparse
import curses
from pathlib import Path
import os
from math import floor
from typing import Tuple

import regex

import se


TAB_SIZE = 8


def _get_text_dimensions(text: str) -> Tuple[int, int]:
	"""
	Get the number of rows and columns to fit the given text.

	Returns (height, width)
	"""

	text_height = 0
	text_width = 0

	for line in text.split("\n"):
		text_height = text_height + 1

		line_length = 0
		for char in line:
			if char == "\t":
				line_length = line_length + TAB_SIZE
			else:
				line_length = line_length + 1

		if line_length > text_width:
			text_width = line_length

	return (text_height + 1, text_width + 1)

def _print_ui(screen, filepath: Path) -> None:
	"""
	Print the header and footer bars to the screen
	"""

	# Wipe the current screen, in case we resized
	screen.clear()

	screen_height, screen_width = screen.getmaxyx()

	header_bar = str(filepath)

	# If the filepath is longer than the screen, use the filename instead
	if len(str(filepath)) > screen_width:
		header_bar = str(filepath.name)

	# Fill blank space in the header bar
	fill_space = max(floor((screen_width - len(header_bar)) / 2), 0)

	if fill_space:
		header_bar = f"{' ': <{fill_space}}{header_bar}{' ': <{fill_space}}"

	if len(header_bar) < screen_width:
		header_bar = header_bar + " "

	# Create the footer bar
	# Be very careful with generating a footer of correct width, because unlike
	# the header, a footer that is too long will cause curses to crash
	footer_bar = "(y)es (n)o (a)ccept remaining (r)eject remaining (c)enter on match (q)uit"

	if len(footer_bar) >= screen_width:
		footer_bar = "y/n; a/r; c; q"

	if len(footer_bar) >= screen_width:
		footer_bar = ""

	fill_space = max(screen_width - len(footer_bar) - 1, 0)

	if fill_space:
		footer_bar = f"{footer_bar}{' ': <{fill_space}}"

	# Print the header and footer
	screen.attron(curses.A_REVERSE)
	screen.addstr(0, 0, header_bar)

	# Make accelerators bold
	footer_index = 0
	for char in footer_bar:
		if char == "(":
			screen.attron(curses.A_BOLD)

		# If the previous char was ), turn off bold
		if footer_index > 0 and footer_bar[footer_index - 1] == ")":
			screen.attroff(curses.A_BOLD)

		screen.addstr(screen_height - 1, footer_index, char)
		footer_index = footer_index + 1
	# The bottom right corner has to be set with insch() for some reason
	screen.insch(screen_height - 1, screen_width - 1, " ")
	screen.attroff(curses.A_REVERSE)

	screen.refresh()

def _get_center_of_match(text: str, match_start: int, match_end: int, screen_height: int, screen_width: int) -> Tuple[int, int]:
	"""
	Given the text, the start and end of the match, and the screen dimensions, return
	a tuple representing the pad x and y that will result in the pad's
	view being centered on the match.
	"""

	# Now we want to try to center the highlighted section on the screen
	# First, get the row/col dimensions of the highlighted region
	index = 0
	highlight_start_x = 0
	highlight_start_y = 0
	highlight_end_x = 0
	highlight_end_y = 0
	for char in text:
		if index < match_start:
			if char == "\n":
				highlight_start_y = highlight_start_y + 1
				highlight_end_y = highlight_end_y + 1
				highlight_start_x = 0
				highlight_end_x = 0
			elif char == "\t":
				highlight_start_x = highlight_start_x + TAB_SIZE
				highlight_end_x = highlight_end_x + TAB_SIZE
			else:
				highlight_start_x = highlight_start_x + 1
				highlight_end_x = highlight_end_x + 1

			index = index + 1

		elif index < match_end:
			if char == "\n":
				highlight_end_y = highlight_end_y + 1
				highlight_end_x = 0
			elif char == "\t":
				highlight_end_x = highlight_end_x + TAB_SIZE
			else:
				highlight_end_x = highlight_end_x + 1

			index = index + 1

		else:
			break

	pad_y = max(highlight_start_y - floor((highlight_start_y - highlight_end_y) / 2) - floor(screen_height / 2), 0)
	pad_x = max(highlight_start_x - floor((highlight_start_x - highlight_end_x) / 2) - floor(screen_width / 2), 0)

	return (pad_y, pad_x)

def _print_screen(screen, filepath: Path, text: str, start_matching_at: int, regex_search: str, regex_flags: int):
	"""
	Print the complete UI to the screen.

	Returns a tuple of (pad, line_numbers_pad, pad_y, pad_x, match_start, match_end)
	if there are more replacements to be made. If not, returns a tuple of
	(None, None, 0, 0, 0, 0)
	"""

	# Get the dimensions of the complete text, and the terminal screen
	text_height, text_width = _get_text_dimensions(text)
	screen_height, screen_width = screen.getmaxyx()
	line_numbers_height = text_height
	line_numbers_width = len(str(text_height))

	# Create the line numbers pad
	line_numbers_pad = curses.newpad(line_numbers_height, line_numbers_width)
	# Reset the cursor
	line_numbers_pad.addstr(0, 0, "")
	line_numbers_pad.attron(curses.A_REVERSE)
	line_numbers_pad.attron(curses.A_DIM)
	# Add the line numbers
	for i in range(line_numbers_height - 1):
		line_numbers_pad.addstr(i, 0, f"{i + 1}".rjust(line_numbers_width))

	# Create a new pad
	pad = curses.newpad(text_height, text_width)

	pad.keypad(True)

	# Reset the cursor
	pad.addstr(0, 0, "")

	# Do we have a regex match in the text?
	# We only consider text after the last completed match
	match = regex.search(fr"{regex_search}", text[start_matching_at:], flags=regex_flags)

	if not match:
		return (None, None, 0, 0, 0, 0)

	match_start = start_matching_at + match.start()
	match_end = start_matching_at + match.end()

	# Print the text preceding the match
	pad.addstr(text[:match_start])
	# Print the match itself, in reversed color
	if curses.has_colors():
		pad.addstr(text[match_start:match_end], curses.color_pair(1) | curses.A_BOLD)
	else:
		pad.attron(curses.A_REVERSE)
		pad.addstr(text[match_start:match_end])
		pad.attroff(curses.A_REVERSE)
	# Print the text after the match
	pad.addstr(text[match_end:len(text)])

	pad_y, pad_x = _get_center_of_match(text, match_start, match_end, screen_height, screen_width)

	# Print the header and footer
	_print_ui(screen, filepath)

	# Output to the screen
	pad.refresh(pad_y, pad_x, 1, line_numbers_width, screen_height - 2, screen_width - 1)

	line_numbers_pad.refresh(pad_y, 0, 1, 0, screen_height - 2, line_numbers_width)

	return (pad, line_numbers_pad, pad_y, pad_x, match_start, match_end)

def _init_screen(screen):
	# Initialize curses

	# Only initialize the screen if it's not already initialized
	if screen is not None:
		return screen

	screen = curses.initscr()
	curses.start_color()
	if curses.has_colors():
		curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)

	# Disable the blinking cursor
	try:
		curses.curs_set(False)
	# Because some terminals do not support the invisible cursor, proceeed
	# if curs_set fails to change the visibility
	except Exception:
		pass

	return screen

def interactive_replace(plain_output: bool) -> int: # pylint: disable=unused-argument
	"""
	Entry point for `se interactive-replace`
	"""

	parser = argparse.ArgumentParser(description="Perform an interactive search and replace on a list of files using Python-flavored regex. The view is scrolled using the arrow keys, with alt to scroll by page in any direction. Basic Emacs (default) or Vim style navigation is available. The following actions are possible: (y) Accept replacement. (n) Reject replacement. (a) Accept all remaining replacements in this file. (r) Reject all remaining replacements in this file. (c) Center on match. (q) Save this file and quit.")
	parser.add_argument("-i", "--ignore-case", action="store_true", help="ignore case when matching; equivalent to regex.IGNORECASE")
	parser.add_argument("-m", "--multiline", action="store_true", help="make `^` and `$` consider each line; equivalent to regex.MULTILINE")
	parser.add_argument("-d", "--dot-all", action="store_true", help="make `.` match newlines; equivalent to regex.DOTALL")
	parser.add_argument("-v", "--vim", action="store_true", help="use basic Vim-like navigation shortcuts")
	parser.add_argument("regex", metavar="REGEX", help="a regex of the type accepted by Python’s `regex` library.")
	parser.add_argument("replace", metavar="REPLACE", help="a replacement regex of the type accepted by Python’s `regex` library.")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="a file or directory on which to perform the search and replace")
	args = parser.parse_args()

	# By default, the esc key has a delay before its delivered to curses.
	# Set the delay to 0
	os.environ.setdefault("ESCDELAY", "0")

	# Save errors for later, because we can only print them after curses is
	# deinitialized
	errors = []
	return_code = 0
	screen = None

	nav_down = b"^N"
	nav_up = b"^P"
	nav_right = b"^F"
	nav_left = b"^B"

	if args.vim:
		nav_down = b"j"
		nav_up = b"k"
		nav_right = b"l"
		nav_left = b"h"

	regex_flags = 0
	if args.ignore_case:
		regex_flags = regex_flags | regex.IGNORECASE

	if args.multiline:
		regex_flags = regex_flags | regex.MULTILINE

	if args.dot_all:
		regex_flags = regex_flags | regex.DOTALL

	try:
		for filepath in se.get_target_filenames(args.targets, ".xhtml"):
			try:
				with open(filepath, "r", encoding="utf-8") as file:
					xhtml = file.read()
			except Exception:
				errors.append(f"Couldn’t open file: {filepath}")
				return_code = se.InvalidFileException.code
				continue

			original_xhtml = xhtml
			is_file_dirty = False

			# Only init the screen if we actually have matches

			# Do we have a regex match in the text?
			# We only consider text after the last completed match
			if regex.search(fr"{args.regex}", original_xhtml, flags=regex_flags):
				screen = _init_screen(screen)
			else:
				continue

			screen_height, screen_width = screen.getmaxyx()

			# In curses terminology, a "pad" is a window that is larger than the viewport.
			# Pads can be scrolled around.
			# Create and output our initial pad
			try:
				pad, line_numbers_pad, pad_y, pad_x, match_start, match_end = _print_screen(screen, filepath, xhtml, 0, args.regex, regex_flags)
			except curses.error as ex:
				# Curses has a hard upper limit on the width of a pad, around 32k. If a line is too long,
				# curses will crash with this error message. This happens in ebooks with very very long lines,
				# like Proust. It's very rare for this to occur, so we just print an error instead of trying
				# to solve the general case; the solution would probably involve soft-wrapping very long lines before
				# sending to curses.
				if str(ex) == "curses function returned NULL":
					errors.append(f"File contains a line that is too long to process: {filepath}")
					return_code = se.InvalidInputException.code
					continue

				raise ex

			while pad:
				# Wait for input
				char = pad.getch()

				esc_pressed = False
				alt_pressed = False

				if char == 27: # ALT was pressed
					pad.nodelay(True)
					alt_pressed = True
					char = pad.getch() # Get the key pressed after ALT
					pad.nodelay(False)

				if alt_pressed and char == -1: # ESC
					esc_pressed = True

				# We have input!

				pad_height, pad_width = pad.getmaxyx()
				_, line_numbers_width = line_numbers_pad.getmaxyx()

				# Accept all remaining replacements and continue to the next file
				if curses.keyname(char) in (b"a", b"A"):
					xhtml = xhtml[:match_start] + regex.sub(fr"{args.regex}", fr"{args.replace}", xhtml[match_start:], flags=regex_flags)

					# Can't check is_file_dirty, we have to compare file contents
					if xhtml != original_xhtml:
						with open(filepath, "w", encoding="utf-8") as file:
							file.write(xhtml)

					break

				# Reject all remaining replacements and continue to the next file
				if curses.keyname(char) in (b"r", b"R") or esc_pressed:
					if is_file_dirty:
						with open(filepath, "w", encoding="utf-8") as file:
							file.write(xhtml)

					break

				# Save this file and quit immediately
				if curses.keyname(char) in (b"q", b"Q"):
					if is_file_dirty:
						with open(filepath, "w", encoding="utf-8") as file:
							file.write(xhtml)

					# Throw a blank exception so that we break out of the loop
					# and disinitialize curses in `finally`
					raise Exception # pylint: disable=broad-exception-raised

				if curses.keyname(char) in (b"y", b"Y"):
					# Do the replacement, but starting from the beginning of the match in case we
					# skipped replacements earlier
					new_xhtml = xhtml[:match_start] + regex.sub(fr"{args.regex}", fr"{args.replace}", xhtml[match_start:], 1, flags=regex_flags)

					# Our replacement has changed the XHTML string, so the
					# match_end doesn't point to the right place any more.
					# Update match_end to account for the change in string length
					# caused by the replacement before passing it to _print_screen()
					match_end = match_end + (len(new_xhtml) - len(xhtml))

					is_file_dirty = True

					# OK, now set our xhtml to the replaced version
					xhtml = new_xhtml

					pad, line_numbers_pad, pad_y, pad_x, match_start, match_end = _print_screen(screen, filepath, xhtml, match_end, args.regex, regex_flags)

				if curses.keyname(char) in (b"n", b"N"):
					# Skip this match
					pad, line_numbers_pad, pad_y, pad_x, match_start, match_end = _print_screen(screen, filepath, xhtml, match_end, args.regex, regex_flags)

				# Center on the match
				if curses.keyname(char) in (b"c", b"C"):
					pad_y, pad_x = _get_center_of_match(xhtml, match_start, match_end, screen_height, screen_width)

					pad.refresh(pad_y, pad_x, 1, line_numbers_width, screen_height - 2, screen_width - 1)
					line_numbers_pad.refresh(pad_y, 0, 1, 0, screen_height - 2, line_numbers_width)

				# The terminal has been resized, redraw the UI
				if curses.keyname(char) == b"KEY_RESIZE":
					screen_height, screen_width = screen.getmaxyx()
					# Note that we pass match_start instead of match_end to print screen, so that we don't
					# appear to increment the search when we resize!
					pad, line_numbers_pad, pad_y, pad_x, _, _ = _print_screen(screen, filepath, xhtml, match_start, args.regex, regex_flags)

				if curses.keyname(char) in (b"KEY_DOWN", nav_down):
					if pad_height - pad_y - screen_height >= 0:
						pad_y = pad_y + 1
						pad.refresh(pad_y, pad_x, 1, line_numbers_width, screen_height - 2, screen_width - 1)
						line_numbers_pad.refresh(pad_y, 0, 1, 0, screen_height - 2, line_numbers_width)

				if curses.keyname(char) in (b"KEY_UP", nav_up):
					if pad_y > 0:
						pad_y = pad_y - 1
						pad.refresh(pad_y, pad_x, 1, line_numbers_width, screen_height - 2, screen_width - 1)
						line_numbers_pad.refresh(pad_y, 0, 1, 0, screen_height - 2, line_numbers_width)

				# pgdown or alt + down, which has its own keycode
				if curses.keyname(char) in (b"KEY_NPAGE", b"kDN3") or (not args.vim and curses.keyname(char) == b"^V") or (args.vim and curses.keyname(char) == b"^F"):
					if pad_height - pad_y - screen_height > 0:
						pad_y = pad_y + screen_height
						if pad_y + screen_height > pad_height:
							pad_y = pad_height - screen_height + 1
						pad.refresh(pad_y, pad_x, 1, line_numbers_width, screen_height - 2, screen_width - 1)
						line_numbers_pad.refresh(pad_y, 0, 1, 0, screen_height - 2, line_numbers_width)

				# pgup or alt + up, which has its own keycode
				if curses.keyname(char) in (b"KEY_PPAGE", b"kUP3") or (not args.vim and alt_pressed and curses.keyname(char) == b"v") or (args.vim and curses.keyname(char) == b"^B"):
					if pad_y > 0:
						pad_y = max(pad_y - screen_height, 0)
						pad.refresh(pad_y, pad_x, 1, line_numbers_width, screen_height - 2, screen_width - 1)
						line_numbers_pad.refresh(pad_y, 0, 1, 0, screen_height - 2, line_numbers_width)

				if curses.keyname(char) in (b"KEY_RIGHT", nav_right):
					if pad_width - pad_x - screen_width + line_numbers_width > 1:
						pad_x = pad_x + 1
						pad.refresh(pad_y, pad_x, 1, line_numbers_width, screen_height - 2, screen_width - 1)

				if curses.keyname(char) in (b"KEY_LEFT", nav_left):
					if pad_x > 0:
						pad_x = pad_x - 1
						pad.refresh(pad_y, pad_x, 1, line_numbers_width, screen_height - 2, screen_width - 1)

				# alt + right, which as its own key code
				if curses.keyname(char) == b"kRIT3":
					if pad_width - pad_x - screen_width + line_numbers_width > 1:
						pad_x = pad_x + screen_width - line_numbers_width
						if pad_x + screen_width >= pad_width:
							pad_x = pad_width - screen_width + line_numbers_width - 1
						pad.refresh(pad_y, pad_x, 1, line_numbers_width, screen_height - 2, screen_width - 1)

				# alt + left, which as its own key code
				if curses.keyname(char) == b"kLFT3":
					if pad_x > 0:
						pad_x = max(pad_x - screen_width, 0)
						pad.refresh(pad_y, pad_x, 1, line_numbers_width, screen_height - 2, screen_width - 1)

			if is_file_dirty:
				with open(filepath, "w", encoding="utf-8") as file:
					file.write(xhtml)

	except Exception as ex:
		# We check for the `pattern` attr instead of catching
		# regex._regex_core.error because the regex error type is
		# private and pylint will complain
		if hasattr(ex, "pattern"):
			errors.append(f"Invalid regular expression: {ex}")
			return_code = se.InvalidInputException.code

		# We may get here if we pressed `q`
	finally:
		if screen is not None:
			curses.endwin()

	for error in errors:
		se.print_error(error)

	return return_code
