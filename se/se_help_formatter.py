"""
This module implements Standard Ebooks command-line help formatting.
"""

import argparse
import io
import re
import sys
from collections.abc import Iterable
from typing import NoReturn

from rich.console import Console
from rich.style import Style
from rich.text import Text

import se

class SeHelpFormatter(argparse.HelpFormatter):
	"""
	Format `argparse` auto-generated help text using the Standard Ebooks command-line help style.
	"""

	def __init__(self, prog: str) -> None:
		"""
		Initialize the formatter with indentation that matches the shell script help layout.
		"""

		super().__init__(prog)
		self._help_parts: list[Text] = []
		self._current_section_heading: str | None = None
		self._last_rendered_section_heading: str | None = None

	def _wrap_text(self, text: Text, indent: str = "\t") -> list[Text]:
		"""
		Return text wrapped at the requested indentation level.
		"""

		console = Console(width=max(self._width - len(indent.expandtabs()), 11), file=io.StringIO())
		indent_text = Text(indent)
		lines: list[Text] = []

		for line in text.split("\n") or [Text()]:
			if not line.plain:
				lines.append(Text("\n"))
				continue

			for wrapped_line in line.wrap(console, console.width, overflow="fold", tab_size=8):
				wrapped_line.rstrip()
				lines.append(indent_text + wrapped_line + Text("\n"))

		return lines

	def _append_wrapped_text(self, text: Text, indent: str = "\t") -> None:
		"""
		Append wrapped text at the requested indentation level.
		"""

		self._help_parts.extend(self._wrap_text(text, indent))

	def _parse_markup(self, text: str) -> Text:
		"""
		Parse help text containing Standard Ebooks Rich-style formatting tags.
		"""

		return Text.from_markup(text)

	def format_error(self, message: str) -> str:
		"""
		Format parameter names in an `argparse` error message.
		"""

		formatted_message = re.sub(r"\b([A-Z][A-Z0-9_-]*)\b", r"[parameter]<\1>[/]", message)
		formatted_message = formatted_message[0].upper() + formatted_message[1:]

		if formatted_message[-1] not in ".!?":
			formatted_message = f"{formatted_message}."

		return formatted_message

	def _append_usage_chunks(self, chunks: Iterable[Text], indent: str = "\t") -> None:
		"""
		Append usage chunks, wrapping complete chunks where possible.
		"""

		width = max(self._width - len(indent.expandtabs()), 11)
		indent_text = Text(indent)
		line = Text()

		for chunk in chunks:
			separator_width = 1 if line.plain else 0

			if line.plain and line.cell_len + separator_width + chunk.cell_len <= width:
				line.append(" ", style="default")
				line.append(chunk)
				continue

			if line.plain:
				line.rstrip()
				self._help_parts.append(indent_text + line + Text("\n"))
				line = Text()

			if chunk.cell_len <= width:
				line = chunk.copy()
			else:
				for wrapped_line in self._wrap_text(chunk, indent):
					self._help_parts.append(wrapped_line)

		if line.plain:
			line.rstrip()
			self._help_parts.append(indent_text + line + Text("\n"))

	def _format_metavar(self, action: argparse.Action) -> Text:
		"""
		Return an angle-bracketed metavar for an action.
		"""

		metavar_string = str(action.metavar if action.metavar else action.dest.upper())

		if metavar_string.startswith("<") and metavar_string.endswith(">"):
			metavar_string = metavar_string[1:-1]

		metavar = self._parse_markup(metavar_string)
		if not metavar.spans:
			return Text(f"<{metavar_string}>", style="parameter")

		parameter_style = se.RICH_THEME.styles["parameter"]
		path_style = se.RICH_THEME.styles["path"]
		underlined_parameter_style = Style.combine([parameter_style, Style(underline=path_style.underline)])

		for span in list(metavar.spans):
			if span.style == "path":
				metavar.stylize(underlined_parameter_style, span.start, span.end)
			else:
				metavar.stylize(parameter_style, span.start, span.end)

		return Text("<", style="parameter") + metavar + Text(">", style="parameter")

	def _format_args_for_action(self, action: argparse.Action) -> Text:
		"""
		Format an action's variables for usage and options output.
		"""

		if action.nargs == 0:
			return Text()

		metavar = self._format_metavar(action)

		if action.nargs == "+":
			return metavar.copy() + Text(" [", style="default") + metavar.copy() + Text(" ", style="default") + Text("...", style="parameter") + Text("]", style="default")

		if action.nargs == "*":
			return Text("[", style="default") + metavar.copy() + Text(" ", style="default") + Text("...", style="parameter") + Text("]", style="default")

		if action.nargs == "?":
			return Text("[", style="default") + metavar.copy() + Text("]", style="default")

		if isinstance(action.nargs, int):
			return Text(" ", style="default").join(metavar.copy() for _ in range(action.nargs))

		return metavar

	def _format_option_invocation(self, action: argparse.Action) -> Text:
		"""
		Format an action's option strings and variables.
		"""

		invocation = Text()

		for index, option_string in enumerate(action.option_strings):
			if index > 0:
				invocation.append(",", style="default")

			invocation.append(option_string, style="bright_blue")

		args = self._format_args_for_action(action)

		if args.plain:
			invocation.append(" ", style="default")
			invocation.append(args)

		return invocation

	def _format_help_text(self, action: argparse.Action) -> str:
		"""
		Format an action's help text.
		"""

		if action.help is None:
			return ""

		help_text = action.help

		if help_text == "show this help message and exit":
			help_text = "Show this help message and exit."

		def replace_help_placeholder(match: re.Match[str]) -> str:
			return str(getattr(action, match[1]))

		return re.sub(r"%\(([^)]+)\)s", replace_help_placeholder, help_text)

	def add_usage(self, usage: str | None, actions: Iterable[argparse.Action], groups: Iterable[object], prefix: str | None = None) -> None:
		"""
		Render the USAGE section.
		"""

		if usage is argparse.SUPPRESS:
			return

		prog = self._parse_markup(self._prog)
		if not prog.spans:
			prog.stylize("green")

		chunks: list[Text] = [prog]

		for action in actions:
			if action.help is argparse.SUPPRESS:
				continue

			if action.option_strings:
				chunk = self._format_option_invocation(action)

				if not action.required:
					chunk = Text("[", style="default") + chunk + Text("]", style="default")

				chunks.append(chunk)
			else:
				chunks.append(self._format_args_for_action(action))

		self._help_parts.append(Text("USAGE\n", style="bold green"))
		self._help_parts.append(Text("\n"))
		self._append_usage_chunks(chunks)
		self._help_parts.append(Text("\n"))

	def add_text(self, text: object | None) -> None:
		"""
		Render the DESCRIPTION section.
		"""

		if text is argparse.SUPPRESS or text is None:
			return

		self._help_parts.append(Text("DESCRIPTION\n", style="bold green"))
		self._help_parts.append(Text("\n"))
		self._append_wrapped_text(self._parse_markup(str(text)))
		self._help_parts.append(Text("\n"))

	def start_section(self, heading: str | None) -> None:
		"""
		Store the current section heading.
		"""

		self._current_section_heading = heading.upper() if heading else None

	def end_section(self) -> None:
		"""
		Clear the current section heading.
		"""

		self._current_section_heading = None

	def add_arguments(self, actions: Iterable[argparse.Action]) -> None:
		"""
		Render the OPTIONS section.
		"""

		action_list = [action for action in actions if action.help is not argparse.SUPPRESS]

		if not action_list:
			return

		if self._last_rendered_section_heading == "POSITIONAL ARGUMENTS":
			self._help_parts.append(Text("\n"))

		if self._current_section_heading:
			self._help_parts.append(Text(f"{self._current_section_heading}\n", style="bold green"))
			self._help_parts.append(Text("\n"))

		for index, action in enumerate(action_list):
			if action.option_strings:
				self._append_wrapped_text(self._format_option_invocation(action))
			else:
				self._append_wrapped_text(self._format_args_for_action(action))

			help_text = self._format_help_text(action)
			if help_text:
				self._help_parts.append(Text("\n"))
				self._append_wrapped_text(self._parse_markup(help_text), "\t\t")

			if index < len(action_list) - 1:
				self._help_parts.append(Text("\n\n"))

		self._last_rendered_section_heading = self._current_section_heading

	def format_help(self) -> str:
		"""
		Return the formatted help text.
		"""

		text = Text().join(self._help_parts)
		if not se.should_output_color():
			return text.plain

		output = io.StringIO()
		console = Console(file=output, force_terminal=True, color_system="truecolor", theme=se.RICH_THEME, width=self._width)
		console.print(text, end="")

		return output.getvalue()

def _format_error(self: argparse.ArgumentParser, message: str) -> NoReturn:
	"""
	Print a usage message and exit with a formatted error.
	"""

	self.print_usage(sys.stderr)
	se.print_error(SeHelpFormatter(self.prog).format_error(message))
	self.exit(2)

argparse.ArgumentParser.error = _format_error
