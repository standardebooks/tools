#!/usr/bin/env python3
"""
Run Calibre's ebook conversion with deterministic UUIDs and CSS ordering.
"""

import random
import sys
import uuid
from collections.abc import Callable, Iterator
from typing import Any

from calibre.ebooks.conversion.cli import main as calibre_main
from calibre.ebooks.oeb.base import Manifest
from calibre.ebooks.oeb.transforms.flatcss import CSSFlattener


_original_flatten_node: Callable[..., Any] = CSSFlattener.flatten_node
_uuid_hex = ""


def _uuid4() -> uuid.UUID:
	"""
	Return the deterministic UUID selected for the current ebook.
	"""

	return uuid.UUID(hex=_uuid_hex)

def _manifest_iter(self: Manifest) -> Iterator[Any]:
	"""
	Iterate over manifest items in deterministic path order.
	"""

	return iter(sorted(self.items, key=lambda item: item.href))

def _manifest_values(self: Manifest) -> list[Any]:
	"""
	Return manifest items in deterministic path order.
	"""

	return sorted(self.items, key=lambda item: item.href)

def _flatten_node(self: CSSFlattener, *args: Any, **kwargs: Any) -> Any:
	"""
	Flatten an XHTML node and normalize its generated CSS class order.
	"""

	result = _original_flatten_node(self, *args, **kwargs)
	node = args[0]
	if node.get("class"):
		node.set("class", " ".join(sorted(node.get("class").split())))

	return result

def main() -> int:
	"""
	Configure Calibre for deterministic output and run its conversion command.
	"""

	global _uuid_hex

	random.seed(0)
	_uuid_hex = sys.argv.pop(1)[:32]
	uuid.uuid4 = _uuid4
	Manifest.__iter__ = _manifest_iter
	Manifest.values = _manifest_values
	CSSFlattener.flatten_node = _flatten_node

	return calibre_main()

if __name__ == "__main__":
	sys.exit(main())
