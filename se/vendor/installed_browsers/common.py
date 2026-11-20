from typing import TypedDict


class OS:
    LINUX = "linux"
    WINDOWS = "win32"
    MAC = "darwin"
    WIN32 = "32bit"
    WIN64 = "64bit"


class Browser(TypedDict):
    name: str
    description: str
    version: str
    location: str


class Version(TypedDict):
    version: str
