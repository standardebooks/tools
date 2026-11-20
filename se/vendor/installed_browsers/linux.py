import os
import re
import subprocess
from typing import Iterator, Optional

from xdg.DesktopEntry import DesktopEntry

from .common import Browser, Version

# tuple of possible browsers
# desktop entry name may be different for different architectures:
# for example "chromium_chromium.desktop" or "chromium-browser.desktop"
POSSIBLE_BROWSERS = (
    ("chrome", ("google-chrome",)),
    ("chromium", ("chromium", "chromium_chromium", "chromium-browser")),
    ("firefox", ("firefox", "firefox_firefox")),
    ("opera", ("opera",)),
    ("opera-beta", ("opera-beta",)),
    ("opera-developer", ("opera-developer",)),
    ("msedge", ("microsoft-edge",)),
    ("msedge-beta", ("microsoft-edge-beta",)),
    ("msedge-dev", ("microsoft-edge-dev",)),
    ("brave", ("brave-browser", "brave_brave")),
    ("brave-beta", ("brave-browser-beta",)),
    ("brave-nightly", ("brave-browser-nightly",)),
    ("vivaldi-stable", ("vivaldi-stable",)),
    ("vivaldi-snapshot", ("vivaldi-snapshot",)),
    ("min", ("min",))
)

# tuple of browser locations
# $XDG_DATA_HOME and $XDG_DATA_DIRS are not always set
BROWSER_LOCATIONS = (
    "~/.local/share/applications",
    "/usr/share/applications",
    "/var/lib/snapd/desktop/applications",
)

# set version pattern with dot separation
VERSION_PATTERN = re.compile(r"\b(\S+\.\S+)\b")


# get all installed browsers
def browsers() -> Iterator[Browser]:
    unique_browsers = set()
    for browser, desktop_entries in POSSIBLE_BROWSERS:
        for application_dir in BROWSER_LOCATIONS:
            for desktop_entry in desktop_entries:
                path = os.path.join(application_dir, f"{desktop_entry}.desktop")
                if not os.path.isfile(path):
                    continue
                if browser in unique_browsers:
                    continue    # pragma: no cover
                entry = DesktopEntry(path)
                executable_path = entry.getExec()
                if executable_path.lower().endswith(" %u"):
                    executable_path = executable_path[:-3].strip()
                version = subprocess.getoutput(f"{executable_path} --version 2>&1").strip()
                match = VERSION_PATTERN.search(version)
                if match:
                    version = match[0]
                yield Browser(
                    name=browser, description=entry.getName(), version=version, location=executable_path
                )
                unique_browsers.add(browser)


# get default browser
def what_is_the_default_browser() -> Optional[str]:
    cmd = "xdg-settings get default-web-browser".split()
    try:
        default_browser = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except subprocess.CalledProcessError:   # pragma: no cover
        default_browser = "No browser is set to default."
    if not default_browser:
        default_browser = "No browser is set to default."
    else:
        default_browser = _get_browser_description(default_browser)
    return default_browser


# check if the given browser is installed
def do_i_have_installed(name):
    for browser, desktop_names in (browser_record for browser_record in POSSIBLE_BROWSERS
                                   if browser_record[0] == name):
        for desktop_name in desktop_names:
            for application_dir in BROWSER_LOCATIONS:
                path = os.path.join(application_dir, f"{desktop_name}.desktop")
                if not os.path.isfile(path):
                    continue
                entry = DesktopEntry(path)
                if entry:
                    return True
    return False


# get details of a browser
def get_details_of(name) -> Optional[Browser]:
    for browser, desktop_names in (browser_record for browser_record in POSSIBLE_BROWSERS
                                   if browser_record[0] == name):
        for desktop_name in desktop_names:
            for application_dir in BROWSER_LOCATIONS:
                path = os.path.join(application_dir, f"{desktop_name}.desktop")
                if not os.path.isfile(path):
                    continue
                entry = DesktopEntry(path)
                executable_path = entry.getExec()
                if executable_path.lower().endswith(" %u"):
                    executable_path = executable_path[:-3].strip()
                version = subprocess.getoutput(f"{executable_path} --version 2>&1").strip()
                match = VERSION_PATTERN.search(version)
                if match:
                    version = match[0]
                yield Browser(
                    name=browser, description=entry.getName(), version=version, location=executable_path
                )
    yield "Browser is not installed."


# retrieve browser version
def get_version_of(name) -> Optional[Version]:
    for browser, desktop_names in (browser_record for browser_record in POSSIBLE_BROWSERS
                                   if browser_record[0] == name):
        for desktop_name in desktop_names:
            for application_dir in BROWSER_LOCATIONS:
                path = os.path.join(application_dir, f"{desktop_name}.desktop")
                if not os.path.isfile(path):
                    continue
                entry = DesktopEntry(path)
                executable_path = entry.getExec()
                if executable_path.lower().endswith(" %u"):
                    executable_path = executable_path[:-3].strip()
                version = subprocess.getoutput(f"{executable_path} --version 2>&1").strip()
                match = VERSION_PATTERN.search(version)
                if match:
                    version = match[0]
                yield Version(
                    version=version
                )
    yield "Browser is not installed."


# determine browser description
def _get_browser_description(desktop_name):
    for application_dir in BROWSER_LOCATIONS:
        path = os.path.join(application_dir, desktop_name)
        if os.path.isfile(path):
            entry = DesktopEntry(path)
            return entry.getName()
