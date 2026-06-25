"""
Store deterministic conversion state for the Standard Ebooks calibre subset.
"""

from contextvars import ContextVar, Token
from hashlib import sha256
from uuid import UUID


_deterministic_id: ContextVar[str] = ContextVar("standardebooks_deterministic_id")


def set_deterministic_id(value: str) -> Token[str]:
	"""
	Set the deterministic identifier for the current conversion context.
	"""

	return _deterministic_id.set(value)

def reset_deterministic_id(token: Token[str]) -> None:
	"""
	Restore the deterministic identifier from before the current conversion.
	"""

	_deterministic_id.reset(token)

def deterministic_uuid() -> UUID:
	"""
	Return the deterministic UUID for the current conversion.
	"""

	return UUID(hex=_deterministic_id.get()[:32])

def deterministic_asin() -> str:
	"""
	Return the ASIN for the current conversion.
	"""

	return _deterministic_id.get()

def deterministic_mobi_uid() -> int:
	"""
	Return the deterministic MOBI UID derived from the ASIN.
	"""

	return int(deterministic_asin()[:8], 16)

def deterministic_bytes(namespace: str, data: bytes, length: int) -> bytes:
	"""
	Return deterministic bytes derived from the conversion identifier and input data.
	"""

	result = bytearray()
	counter = 0
	while len(result) < length:
		digest = sha256()
		digest.update(deterministic_asin().encode("ascii"))
		digest.update(namespace.encode("utf-8"))
		digest.update(counter.to_bytes(4, "big"))
		digest.update(data)
		result.extend(digest.digest())
		counter += 1

	return bytes(result[:length])
