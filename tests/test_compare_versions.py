"""
Test that browser screenshots include the full page.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

from PIL import Image
import pytest

from se.browser import Browser, BrowserType
import se.commands.compare_versions as compare_versions_module
from se.commands.compare_versions import _screenshot_html_element # pyright: ignore[reportPrivateUsage] Test the internal screenshot helper directly.


@pytest.mark.parametrize("height", [5, 6])
def test_firefox_screenshot_includes_every_viewport(tmp_path: Path, height: int) -> None:
	"""
	Capture content above the final viewport, including an overlapping final tile.
	"""

	browser = Mock(spec=Browser)
	browser.type = BrowserType.FIREFOX
	positions = [min(position, height - 2) for position in range(0, height, 2)]
	browser.driver.execute_script.side_effect = [
		{"width": 4, "height": height, "viewportWidth": 4, "viewportHeight": 2},
		*positions,
	]
	viewports: list[bytes] = []
	for position in positions:
		viewport = Image.new("RGB", (4, 2))
		for row in range(2):
			viewport.paste((position + row + 1, 0, 0), (0, row, 4, row + 1))
		buffer = BytesIO()
		viewport.save(buffer, format="PNG")
		viewports.append(buffer.getvalue())
	browser.driver.get_screenshot_as_png.side_effect = viewports
	output = tmp_path / "screenshot.png"

	_screenshot_html_element(browser, tmp_path / "chapter.xhtml", output)

	with Image.open(output) as screenshot:
		assert screenshot.size == (4, height)
		for row in range(height):
			assert screenshot.getpixel((0, row)) == (row + 1, 0, 0)


@pytest.mark.parametrize("scenario, expected", [
	("chapter", {"chapter-1.xhtml"}),
	("multiple", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("css", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("font", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("image", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("added", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("deleted", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("renamed", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("untracked", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("script", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("embedded", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("resource", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("css-url", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("invalid", {"chapter-1.xhtml", "chapter-2.xhtml"}),
	("ignored", set[str]()),
])
@pytest.mark.parametrize("include_se_files", [False, True])
def test_comparison_selects_only_independent_changed_pages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str, expected: set[str], include_se_files: bool) -> None:
	"""
	Skip unaffected pages while preserving full comparisons for shared or uncertain dependencies.
	"""

	target = tmp_path / "book"
	target.mkdir()
	xhtml = '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0"><head><title>Test</title></head><body><section epub:type="chapter">Text.</section></body></html>'
	for name in ("chapter-1.xhtml", "chapter-2.xhtml"):
		(target / name).write_text(xhtml, encoding="utf-8")
	(target / "imprint.xhtml").write_text(xhtml.replace('epub:type="chapter"', 'epub:type="imprint"'), encoding="utf-8")
	changes = "M\0chapter-1.xhtml\0"
	if scenario == "multiple":
		changes += "M\0chapter-2.xhtml\0"
	elif scenario in ("css", "font", "image"):
		changes += f"M\0shared.{ {'css': 'css', 'font': 'woff2', 'image': 'png'}[scenario]}\0"
	elif scenario == "added":
		changes = "A\0chapter-1.xhtml\0"
	elif scenario == "deleted":
		changes = "D\0old.xhtml\0"
	elif scenario == "renamed":
		changes = "D\0old.xhtml\0A\0chapter-1.xhtml\0"
	elif scenario in ("script", "embedded", "resource"):
		markup = {"script": "<script/>", "embedded": '<iframe src="chapter-1.xhtml"/>', "resource": '<img src="chapter-1%2exhtml"/>'}[scenario]
		(target / "chapter-2.xhtml").write_text(xhtml.replace("Text.", markup), encoding="utf-8")
	elif scenario == "css-url":
		(target / "shared.css").write_text('body{background:url("chapter-1.xhtml")}', encoding="utf-8")
	elif scenario == "invalid":
		(target / "chapter-2.xhtml").write_text("<html>", encoding="utf-8")
	elif scenario == "ignored":
		changes = "M\0imprint.xhtml\0"
		if include_se_files:
			expected = {"imprint.xhtml"}
	if include_se_files and scenario not in ("chapter", "multiple", "ignored"):
		expected = expected | {"imprint.xhtml"}

	git_command = Mock()
	git_command.status.return_value = "Changes to be committed."
	git_command.diff.return_value = changes
	git_command.ls_files.return_value = "untracked.css\0" if scenario == "untracked" else ""
	monkeypatch.setattr(compare_versions_module.cmd, "Git", Mock(return_value=git_command))
	browser = Mock(spec=Browser)
	browser.get_temporary_directory.return_value = None
	monkeypatch.setattr(compare_versions_module, "Browser", Mock(return_value=browser))
	captured: list[str] = []

	def screenshot(_browser: Browser, filename: Path, output_path: Path) -> None:
		"""
		Record each capture and supply an identical image without starting a browser.
		"""

		captured.append(filename.name)
		Image.new("RGB", (4, 4), "white").save(output_path)

	monkeypatch.setattr(compare_versions_module, "_screenshot_html_element", screenshot)
	arguments = ["se compare-versions", "--no-images", str(target)]
	if include_se_files:
		arguments.append("--include-se-files")
	monkeypatch.setattr("sys.argv", arguments)
	assert compare_versions_module.compare_versions(plain_output=True) == 0
	assert set(captured) == expected
	assert len(captured) == len(expected) * 2
	git_command.diff.assert_called_once_with("HEAD", "--name-status", "--no-renames", "-z")
