"""
Test internal SE programming functions
"""

# pylint: disable=protected-access
# pyright: reportPrivateUsage=false

import builtins
from pathlib import Path

from PIL import Image, ImageDraw
from pytest import MonkeyPatch
import regex

import se.se_epub_build
from se.se_epub_build import __convert_image, __convert_mathml_to_png
from se.se_epub_generate_toc import add_landmark, TocItem
import se.easy_xml
import se.images
from se.se_epub_lint import SourceFile


XML_COMMENT_PATTERN = regex.compile(r"<!--.+?-->", flags=regex.DOTALL)

def test_add_landmark_empty_title():
	"""
	Verify we can find a landmark title when title element is present but empty.
	"""
	dom = se.easy_xml.EasyXmlTree('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US"><head><title></title></head><body><section epub:type="foo"><h1></h1></section></body></html>')
	landmarks: list[TocItem] = []
	add_landmark(dom, "file", landmarks)

	assert landmarks[0].title == "Foo"

def test_add_landmark_no_title():
	"""
	Verify we can find a landmark title when title element is not present.
	"""
	dom = se.easy_xml.EasyXmlTree('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US"><body><section epub:type="foo"><h1></h1></section></body></html>')
	landmarks: list[TocItem] = []
	add_landmark(dom, "file", landmarks)

	assert landmarks[0].title == "Foo"

def test_add_landmark_with_title():
	"""
	Verify we can find a landmark title when title element is present.
	"""
	dom = se.easy_xml.EasyXmlTree('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US"><head><title>Bar</title></head><body><section epub:type="foo"><h1></h1></section></body></html>')
	landmarks: list[TocItem] = []
	add_landmark(dom, "file", landmarks)

	assert landmarks[0].title == "Bar"

def test_inner_text():
	"""
	Verify that inner_text strips leading and trailing whitespace from the root
	element, retains interior whitespace, excludes all tags and attributes, and
	returns both named and numeric entities as their corresponding characters.
	"""
	dom = se.easy_xml.EasyXmlTree('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-US"><body><p epub:type="foo"> a <i>&lt;</i>b <span epub:type="bar">\t&#913; </span>c<br/>\nd </p>e</body></html>')
	p = next(iter(dom.xpath("//p")))

	assert p.inner_text() == "a <b \tΑ c\nd"

def test_optimize_png(tmp_path: Path):
	"""
	Verify the oxipng binding optimizes a PNG file in place without changing the image.
	"""
	image_path = tmp_path / "test.png"
	image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
	draw = ImageDraw.Draw(image)
	draw.rectangle((4, 4, 18, 18), fill=(255, 0, 0, 255))
	draw.ellipse((12, 12, 28, 28), fill=(0, 0, 255, 255))
	image.save(image_path, compress_level=0)
	original_size = image_path.stat().st_size

	with Image.open(image_path) as original_image:
		original_image.load()
		original_pixels = original_image.convert("RGBA").tobytes()

	se.images.optimize_png(image_path)

	with Image.open(image_path) as optimized_image:
		optimized_image.load()

		assert optimized_image.format == "PNG"
		assert optimized_image.size == (32, 32)
		assert optimized_image.convert("RGBA").tobytes() == original_pixels

	assert image_path.stat().st_size < original_size

def test_cache_directory_uses_xdg_cache_home(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify the Standard Ebooks cache directory honors XDG_CACHE_HOME on any platform.
	"""

	monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

	assert se.get_cache_directory() == tmp_path / "se"

def test_cache_directory_uses_localappdata_on_windows(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify the Standard Ebooks cache directory honors LOCALAPPDATA on Windows when XDG_CACHE_HOME is unset.
	"""

	monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
	monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
	monkeypatch.setattr(se.sys, "platform", "win32")

	assert se.get_cache_directory() == tmp_path / "se"

def test_cache_directory_uses_dot_cache_on_non_windows(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify the Standard Ebooks cache directory defaults to ~/.cache/se on non-Windows platforms.
	"""

	monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
	monkeypatch.setattr(se.sys, "platform", "linux")
	monkeypatch.setattr(se.Path, "home", lambda: tmp_path)

	assert se.get_cache_directory() == tmp_path / ".cache" / "se"

def test_cache_directory_uses_library_caches_on_macos(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify the Standard Ebooks cache directory defaults to ~/Library/Caches/se on macOS.
	"""

	monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
	monkeypatch.setattr(se.sys, "platform", "darwin")
	monkeypatch.setattr(se.Path, "home", lambda: tmp_path)

	assert se.get_cache_directory() == tmp_path / "Library" / "Caches" / "se"

def test_config_directory_uses_xdg_config_home(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify the Standard Ebooks config directory honors XDG_CONFIG_HOME on any platform.
	"""

	monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

	assert se.get_config_directory() == tmp_path / "se"

def test_config_directory_uses_appdata_on_windows(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify the Standard Ebooks config directory honors APPDATA on Windows when XDG_CONFIG_HOME is unset.
	"""

	monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
	monkeypatch.setenv("APPDATA", str(tmp_path))
	monkeypatch.setattr(se.sys, "platform", "win32")

	assert se.get_config_directory() == tmp_path / "se"

def test_config_directory_uses_dot_config_on_non_windows(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify the Standard Ebooks config directory defaults to ~/.config/se on non-Windows platforms.
	"""

	monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
	monkeypatch.setattr(se.sys, "platform", "linux")
	monkeypatch.setattr(se.Path, "home", lambda: tmp_path)

	assert se.get_config_directory() == tmp_path / ".config" / "se"

def test_config_directory_uses_library_application_support_on_macos(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify the Standard Ebooks config directory defaults to ~/Library/Application Support/se on macOS.
	"""

	monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
	monkeypatch.setattr(se.sys, "platform", "darwin")
	monkeypatch.setattr(se.Path, "home", lambda: tmp_path)

	assert se.get_config_directory() == tmp_path / "Library" / "Application Support" / "se"

def test_config_value_uses_default_when_file_does_not_exist(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify config values fall back to defaults when no local configuration file exists.
	"""

	config_directory = tmp_path / "config"
	monkeypatch.setattr(se, "get_config_directory", lambda: config_directory)
	se._get_config_dom.cache_clear()

	assert se.get_config_value("/configuration/build/@max-cache-size") == "50MB"
	assert not config_directory.exists()

def test_config_value_uses_configuration_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify config values are read from the local configuration file when present.
	"""

	config_directory = tmp_path / "config"
	config_directory.mkdir()
	(config_directory / "configuration.xml").write_text("""<?xml version="1.0" encoding="utf-8"?>
<configuration>
	<build max-cache-size="100MB"/>
</configuration>
	""", encoding="utf-8")
	monkeypatch.setattr(se, "get_config_directory", lambda: config_directory)
	se._get_config_dom.cache_clear()

	assert se.get_config_value("/configuration/build/@max-cache-size") == "100MB"

def test_config_value_caches_configuration_dom(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify the parsed configuration DOM is reused between config value lookups.
	"""

	config_directory = tmp_path / "config"
	config_directory.mkdir()
	config_file_path = config_directory / "configuration.xml"
	config_file_path.write_text("""<?xml version="1.0" encoding="utf-8"?>
<configuration>
	<build max-cache-size="100MB"/>
</configuration>
	""", encoding="utf-8")
	monkeypatch.setattr(se, "get_config_directory", lambda: config_directory)
	se._get_config_dom.cache_clear()

	assert se.get_config_value("/configuration/build/@max-cache-size") == "100MB"

	config_file_path.write_text("""<?xml version="1.0" encoding="utf-8"?>
<configuration>
	<build max-cache-size="200MB"/>
</configuration>
""", encoding="utf-8")

	assert se.get_config_value("/configuration/build/@max-cache-size") == "100MB"

def test_config_value_uses_default_when_key_is_missing(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify config values fall back to defaults when the requested key is missing.
	"""

	config_directory = tmp_path / "config"
	config_directory.mkdir()
	(config_directory / "configuration.xml").write_text("""<?xml version="1.0" encoding="utf-8"?>
<configuration>
	<build/>
</configuration>
	""", encoding="utf-8")
	monkeypatch.setattr(se, "get_config_directory", lambda: config_directory)
	se._get_config_dom.cache_clear()

	assert se.get_config_value("/configuration/build/@max-cache-size") == "50MB"

def test_config_value_supports_empty_values(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify config values can be empty strings.
	"""

	config_directory = tmp_path / "config"
	config_directory.mkdir()
	(config_directory / "configuration.xml").write_text("""<?xml version="1.0" encoding="utf-8"?>
<configuration>
	<create-draft default-email=""/>
</configuration>
	""", encoding="utf-8")
	monkeypatch.setattr(se, "get_config_directory", lambda: config_directory)
	se._get_config_dom.cache_clear()

	assert se.get_config_value("/configuration/create-draft/@default-email") == ""

def test_config_value_uses_default_when_file_is_not_readable(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify config values fall back to defaults when the local configuration file is not readable.
	"""

	def unreadable_open(_file: object, *args: object, **kwargs: object) -> object:
		"""
		Raise an OSError to simulate an unreadable configuration file.
		"""

		del args
		del kwargs
		raise OSError

	monkeypatch.setattr(se, "get_config_directory", lambda: tmp_path)
	se._get_config_dom.cache_clear()
	monkeypatch.setattr(builtins, "open", unreadable_open)

	assert se.get_config_value("/configuration/build/@max-cache-size") == "50MB"

def test_svg_png_cache_key_changes_with_render_inputs(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify SVG-to-PNG cache keys change when render inputs change.
	"""

	epub_root_directory = tmp_path / "epub-root"
	image_directory = epub_root_directory / "epub" / "images"
	cache_directory = tmp_path / "cache"
	image_directory.mkdir(parents=True)
	cache_directory.mkdir()
	svg_path = image_directory / "illustration.svg"
	png_path = image_directory / "illustration.png"
	svg_path.write_text("<svg/>", encoding="utf-8")

	def fake_svg2png(**_kwargs: object) -> int:
		"""
		Write fake SVG conversion output.
		"""

		return png_path.write_bytes(b"png")

	def fake_optimize_png(_filename: Path) -> None:
		"""
		Skip PNG optimization in cache key tests.
		"""

	monkeypatch.setattr(se.se_epub_build.cairosvg, "__version__", "1")
	monkeypatch.setattr(se.se_epub_build, "svg2png", fake_svg2png)
	monkeypatch.setattr(se.images, "optimize_png", fake_optimize_png)
	key = __convert_image(svg_path, png_path, 1, cache_directory)

	assert __convert_image(svg_path, png_path, 1, cache_directory) == key
	assert __convert_image(svg_path, image_directory / "other-path.png", 2, cache_directory) != key
	svg_path.write_text("<svg><path/></svg>", encoding="utf-8")
	assert __convert_image(svg_path, png_path, 1, cache_directory) != key
	monkeypatch.setattr(se.se_epub_build.cairosvg, "__version__", "2")
	assert __convert_image(svg_path, png_path, 1, cache_directory) != key

def test_copy_template_svg_png_for_known_logo(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify known SVGs can use template PNGs instead of local cache entries.
	"""

	svg_contents = b"<svg>logo</svg>"
	svg_sha256 = se.se_epub_build.sha256(svg_contents).hexdigest()
	svg_path = tmp_path / "logo.svg"
	png_path = tmp_path / "logo.png"
	svg_path.write_bytes(svg_contents)
	monkeypatch.setattr(se.se_epub_build, "SE_LOGO_SVG_SHA256", svg_sha256)

	assert __convert_image(svg_path, png_path, 1, tmp_path / "cache") is None

	assert png_path.read_bytes() == (Path("se") / "data" / "templates" / "logo.png").read_bytes()

def test_mathml_png_cache_avoids_rendering(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	"""
	Verify MathML-to-PNG cache hits avoid rendering the MathML fragment.
	"""

	driver = object()
	mathml_fragment = "<math xmlns=\"http://www.w3.org/1998/Math/MathML\"><mi>x</mi></math>"
	cache_directory = tmp_path / "cache"
	cache_directory.mkdir()
	output_path = tmp_path / "mathml.png"
	output_path_2x = tmp_path / "mathml-2x.png"
	render_calls: list[str] = []

	def fake_render_mathml_to_png(_driver: object, mathml: str, output_filename: Path, output_filename_2x: Path) -> None:
		"""
		Write fake MathML render outputs.
		"""

		render_calls.append(mathml)
		output_filename.write_bytes(b"1x")
		output_filename_2x.write_bytes(b"2x")

	monkeypatch.setattr(se.images, "render_mathml_to_png", fake_render_mathml_to_png)

	cache_paths, reused_driver = __convert_mathml_to_png(mathml_fragment, output_path, output_path_2x, cache_directory, driver)
	output_path.unlink()
	output_path_2x.unlink()
	cached_paths, cached_driver = __convert_mathml_to_png(mathml_fragment, output_path, output_path_2x, cache_directory, driver)

	assert cache_paths == cached_paths
	assert reused_driver is driver
	assert cached_driver is driver
	assert render_calls == [mathml_fragment]
	assert output_path.read_bytes() == b"1x"
	assert output_path_2x.read_bytes() == b"2x"

def test_line_numbers_no_comments():
	"""
	Verify line number offset calculations without comments.
	"""
	contents = """\
<p>L1</p>
<p>L2</p>
<p>L3</p>"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # type: ignore # pylint: disable=protected-access
	assert bounds == [(0, 1), (10, 2), (20, 3)]

def test_line_numbers_leading_comments():
	"""
	Verify line number offset calculations with leading comments.
	"""
	contents = """\
<!-- C1 --><p>L1</p>
<!-- C2 --><p>L2</p>
<!-- C3 --><p>L3</p>"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # type: ignore # pylint: disable=protected-access
	assert bounds == [(0, 1), (10, 2), (20, 3)]

def test_line_numbers_trailing_comments():
	"""
	Verify line number offset calculations with trailing comments.
	"""
	contents = """\
<p>L1</p><!-- C1 -->
<p>L2</p><!-- C2 -->
<p>L3</p><!-- C3 -->"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # type: ignore # pylint: disable=protected-access
	assert bounds == [(0, 1), (10, 2), (20, 3)]

def test_line_numbers_inline_comments():
	"""
	Verify line number offset calculations with inline comments.
	"""
	contents = """\
<p>L1<!-- C1 --></p>
<p><!-- C2 -->L2</p>
<p>L3</p>"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # type: ignore # pylint: disable=protected-access
	assert bounds == [(0, 1), (10, 2), (20, 3)]

def test_line_numbers_line_comments():
	"""
	Verify line number offset calculations with full line comments.
	"""
	contents = """\
<p>L1</p>
<!--L2-->
<p>L3</p>
<!--L4-->
<p>L5</p>"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # type: ignore # pylint: disable=protected-access
	assert bounds == [(0, 1), (10, 2), (11, 3), (21, 4), (22, 5)]

def test_line_numbers_multiline_comments():
	"""
	Verify line number offset calculations with multiline comments.
	"""
	contents = """\
<!--   L1
   L2 -->
<p>L3</p>
<!--   L4
       L5
	  L6-->
<p>L7</p>
<!--   L8
    L9-->
<p>LA</p>
<!--   LB
    LC-->"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # type: ignore # pylint: disable=protected-access
	assert bounds == [(0, 1), (1, 3), (11, 4), (12, 7), (22, 8), (23, 10), (33, 11)]
