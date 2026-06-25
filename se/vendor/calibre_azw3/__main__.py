"""
Run the vendored calibre EPUB-to-AZW3 converter.
"""

from __future__ import annotations

import sys
from pathlib import Path

from se.vendor.calibre_azw3 import convert_epub_to_azw3


def main() -> int:
	"""
	Parse worker arguments and convert the requested EPUB file.
	"""

	if len(sys.argv) not in {4, 5}:
		raise ValueError("Expected input path, output path, deterministic ID, and optional cover path.")

	convert_epub_to_azw3(
		Path(sys.argv[1]),
		Path(sys.argv[2]),
		Path(sys.argv[4]) if len(sys.argv) == 5 else None,
		sys.argv[3],
	)

	return 0

if __name__ == "__main__":
	sys.exit(main())
