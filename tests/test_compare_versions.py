"""
Test that browser screenshots include the full page.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

from PIL import Image
import pytest

from se.browser import Browser, BrowserType
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
