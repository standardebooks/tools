import sys
from typing import Iterator, Optional
from .common import Browser, Version, OS

match sys.platform:
    case OS.LINUX:
        from . import linux
    case OS.MAC:
        from . import mac
    case OS.WINDOWS:
        from . import windows

__all__ = ["Browser",
           "browsers",
           "what_is_the_default_browser",
           "do_i_have_installed",
           "give_me_details_of",
           "get_version_of"]


# get all installed browsers
def browsers() -> Iterator[Browser]:
    """
    Iterates over installed browsers.\n
    Locally installed browser versions (portable) are not considered.

    :return: Iterator of dictionary of browser key and information.
    """
    match sys.platform:
        case OS.LINUX:
            yield from linux.browsers()
        case OS.MAC:
            yield from mac.browsers()
        case OS.WINDOWS:
            yield from windows.browsers()
        case _:
            yield Browser(
                name="exception", description="This operating system is not yet supported.", version="", location=""
            )


# get default browser
def what_is_the_default_browser():
    """
    Shows the default browser in system - if there is any.

    :return: Default browser description.
    """
    match sys.platform:
        case OS.LINUX:
            return linux.what_is_the_default_browser()
        case OS.MAC:
            return mac.what_is_the_default_browser()
        case OS.WINDOWS:
            return windows.what_is_the_default_browser()


# check if the given browser is installed
def do_i_have_installed(name: str):
    """
    Checks if the provided browser is installed in system.

    Parameters:
                Possible browser entries / parameters\n
                for Linux:\n
                chrome, chromium, firefox, opera, opera-beta, opera-developer, msedge, msedge-beta, msedge-dev
                brave, brave-beta, brave-nightly, vivaldi, vivaldi-snapshot, min\n
                for macOS:\n
                chrome, chrome-canary, chromium, firefox, firefox-developer, firefox-nightly,
                safari, opera, opera-beta, opera-developer, msedge, msedge-beta, msedge-dev, msedge-canary,
                brave, brave-beta, brave-nightly, vivaldi, vivaldi-snapshot, min, arc, kosmik, pale-moon\n
                for Windows:\n
                chrome, chrome-canary, chromium, firefox, firefox-developer, firefox-nightly,
                opera-stable, opera-beta, opera-developer, msedge, msedge-beta, msedge-dev, msedge-canary, msie,
                brave, brave-beta, brave-nightly, vivaldi, min, pale-moon
    :return: True or False depending on the browser is installed or not.
    """
    match sys.platform:
        case OS.LINUX:
            return linux.do_i_have_installed(name)
        case OS.MAC:
            return mac.do_i_have_installed(name)
        case OS.WINDOWS:
            return windows.do_i_have_installed(name)


# retrieve browser details
def give_me_details_of(name: str) -> Optional[Browser | str]:
    """
    Retrieve browser details if the provided browser is installed in system.\n
    Browser details are: name\n
                         description\n
                         version\n
                         location\n

    Parameters:
                Possible browser entries / parameters\n
                for Linux:\n
                chrome, chromium, firefox, opera, opera-beta, opera-developer, msedge, msedge-beta, msedge-dev
                brave, brave-beta, brave-nightly, vivaldi, vivaldi-snapshot, min\n
                for macOS:\n
                chrome, chrome-canary, chromium, firefox, firefox-developer, firefox-nightly,
                safari, opera, opera-beta, opera-developer, msedge, msedge-beta, msedge-dev, msedge-canary,
                brave, brave-beta, brave-nightly, vivaldi, vivaldi-snapshot, min, arc, kosmik, pale-moon\n
                for Windows:\n
                chrome, chrome-canary, chromium, firefox, firefox-developer, firefox-nightly,
                opera-stable, opera-beta, opera-developer, msedge, msedge-beta, msedge-dev, msedge-canary, msie,
                brave, brave-beta, brave-nightly, vivaldi, min, pale-moon
    :return: Dictionary containing browser name, description, desktop version and location.
    """
    match sys.platform:
        case OS.LINUX:
            for found in (entity for entity in linux.get_details_of(name) if entity is not None):
                return found
        case OS.MAC:
            for found in (entity for entity in mac.get_details_of(name) if entity is not None):
                return found
        case OS.WINDOWS:
            for found in windows.get_details_of(name):
                # if found:
                #     return found
                for details in found:
                   return details
            return "Browser is not installed."


# retrieve browser version
def get_version_of(name: str) -> Optional[Version | str]:
    """
    Retrieve browser version if the provided browser is installed in system.

    Parameters:
                Possible browser entries / parameters\n
                for Linux:\n
                chrome, chromium, firefox, opera, opera-beta, opera-developer, msedge, msedge-beta, msedge-dev
                brave, brave-beta, brave-nightly, vivaldi, vivaldi-snapshot, min\n
                for macOS:\n
                chrome, chrome-canary, chromium, firefox, firefox-developer, firefox-nightly,
                safari, opera, opera-beta, opera-developer, msedge, msedge-beta, msedge-dev, msedge-canary,
                brave, brave-beta, brave-nightly, vivaldi, vivaldi-snapshot, min, arc, kosmik, pale-moon\n
                for Windows:\n
                chrome, chrome-canary, chromium, firefox, firefox-developer, firefox-nightly,
                opera-stable, opera-beta, opera-developer, msedge, msedge-beta, msedge-dev, msedge-canary, msie,
                brave, brave-beta, brave-nightly, vivaldi, min, pale-moon, shift, duckduckgo
    :return: Browser description and version.
    """
    match sys.platform:
        case OS.LINUX:
            for found in (entity for entity in linux.get_version_of(name) if entity is not None):
                return found
        case OS.MAC:
            for found in (entity for entity in mac.get_version_of(name) if entity is not None):
                return found
        case OS.WINDOWS:
            for found in windows.get_version_of(name):
                for version in found:
                    return version
            return "Browser is not installed."
