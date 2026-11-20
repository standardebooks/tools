from typing import TypedDict

class OS:
	LINUX: str
	WINDOWS: str
	MAC: str
	WIN32: str
	WIN64: str

class Browser(TypedDict):
	name: str
	description: str
	version: str
	location: str

class Version(TypedDict):
	version: str
