"""
Convert EPUB files to AZW3 using the vendored calibre conversion source.
"""

from __future__ import annotations

import sys
from pathlib import Path
from threading import Lock


_conversion_lock = Lock()
_is_runtime_configured = False


def _configure_runtime() -> None:
	"""
	Configure module and resource paths for the vendored calibre source.
	"""

	global _is_runtime_configured

	if _is_runtime_configured:
		return

	vendor_root = Path(__file__).parent
	upstream_root = vendor_root / "upstream"
	sys.path.insert(0, str(upstream_root))
	setattr(sys, "extensions_location", str(upstream_root / "calibre_extensions"))
	setattr(sys, "resources_location", str(vendor_root / "resources"))
	_is_runtime_configured = True

def convert_epub_to_azw3(input_path: Path, output_path: Path, cover_path: Path | None, deterministic_id: str) -> None:
	"""
	Convert an EPUB file to AZW3 using the vendored calibre conversion pipeline.
	"""

	with _conversion_lock:
		_configure_runtime()

		from calibre.ebooks.conversion.plumber import Plumber
		from calibre.utils.logging import DevNull
		from calibre.utils.standardebooks import reset_deterministic_id, set_deterministic_id

		token = set_deterministic_id(deterministic_id)
		try:
			plumber = Plumber(str(input_path), str(output_path), DevNull())
			recommendations: list[tuple[str, object, int]] = [
				("pretty_print", True, 3),
				("no_inline_toc", True, 3),
				("max_toc_links", 0, 3),
				("prefer_metadata_cover", True, 3),
			]

			if cover_path is not None:
				recommendations.append(("cover", str(cover_path), 3))

			plumber.merge_ui_recommendations(recommendations)
			plumber.run()
		except Exception as ex:
			raise ex
		finally:
			reset_deterministic_id(token)
