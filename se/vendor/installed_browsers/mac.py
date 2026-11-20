import os
import plistlib
import subprocess
from pathlib import Path
from typing import Iterator, Optional

from .common import Browser, Version

# tuple of possible browsers
POSSIBLE_BROWSERS = (
    ("chrome", "com.google.Chrome", "KSVersion"),
    ("chrome-canary", "com.google.Chrome.canary", "KSVersion"),
    ("chromium", "org.chromium.Chromium", "CFBundleShortVersionString"),
    ("firefox", "org.mozilla.firefox", "CFBundleShortVersionString"),
    ("firefox-developer", "org.mozilla.firefoxdeveloperedition", "CFBundleShortVersionString"),
    ("firefox-nightly", "org.mozilla.nightly", "CFBundleShortVersionString"),
    ("safari", "com.apple.Safari", "CFBundleShortVersionString"),
    ("opera", "com.operasoftware.Opera", "CFBundleVersion"),
    ("opera-beta", "com.operasoftware.OperaNext", "CFBundleVersion"),
    ("opera-developer", "com.operasoftware.OperaDeveloper", "CFBundleVersion"),
    ("msedge", "com.microsoft.edgemac", "CFBundleVersion"),
    ("msedge-beta", "com.microsoft.edgemac.Beta", "CFBundleVersion"),
    ("msedge-dev", "com.microsoft.edgemac.Dev", "CFBundleVersion"),
    ("msedge-canary", "com.microsoft.edgemac.Canary", "CFBundleVersion"),
    ("brave", "com.brave.Browser", "CFBundleVersion"),
    ("brave-beta", "com.brave.Browser.beta", "CFBundleVersion"),
    ("brave-nightly", "com.brave.Browser.nightly", "CFBundleVersion"),
    ("vivaldi-stable", "com.vivaldi.Vivaldi", "CFBundleVersion"),
    ("vivaldi-snapshot", "com.vivaldi.Vivaldi.snapshot", "CFBundleVersion"),
    ("min", "com.electron.min", "CFBundleVersion"),
    ("kosmik", "paris.lithium.kosmik", "CFBundleShortVersionString"),
    ("pale-moon", "org.mozilla.pale*", "CFBundleShortVersionString"),
    ("arc", "company.thebrowser.Browser", "CFBundleShortVersionString"),
    ("shift", "com.shift.browser", "CFBundleShortVersionString"),
    ("duckduckgo", "com.duckduckgo.mobile.ios", "CFBundleShortVersionString")
)


# get all installed browsers
def browsers() -> Iterator[Browser]:
    for browser, bundle_id, version_string in POSSIBLE_BROWSERS:
        paths = subprocess.getoutput(f'mdfind "kMDItemCFBundleIdentifier == {bundle_id}"').splitlines()
        for path in paths:
            with open(os.path.join(path, "Contents/Info.plist"), "rb") as f:
                plist = plistlib.load(f)
                executable_name = plist.get("CFBundleExecutable")
                executable = os.path.join(path, "Contents/MacOS", executable_name)
                description = plist.get("CFBundleDisplayName") or plist.get("CFBundleName", browser)
                version = plist[version_string]
                yield Browser(
                    name=browser,
                    description=description,
                    version=version,
                    location=executable if browser != "safari" else path
                )


# get default browser
def what_is_the_default_browser() -> Optional[str]:
    PREFERENCES = (
        Path.home()
        / "Library"
        / "Preferences"
        / "com.apple.LaunchServices/com.apple.launchservices.secure.plist"
    )

    SUPPORTED_BROWSERS = {
        "": "No browser is set to default.",
        "com.google.chrome": "Google Chrome",
        "com.google.chrome.canary": "Google Chrome Canary",
        "org.chromium.chromium": "Chromium",
        "org.mozilla.firefox": "Firefox",
        "org.mozilla.firefoxdeveloperedition": "Firefox Developer Edition",
        "org.mozilla.nightly": "Firefox Nightly",
        "com.apple.safari": "Safari",
        "com.operasoftware.opera": "Opera",
        "com.operasoftware.operanext": "Opera Beta",
        "com.operasoftware.operadeveloper": "Opera Developer",
        "com.microsoft.edgemac": "Microsoft Edge",
        "com.microsoft.edgemac.beta": "Microsoft Edge Beta",
        "com.microsoft.edgemac.dev": "Microsoft Edge Dev",
        "com.microsoft.edgemac.canary": "Microsoft Edge Canary",
        "com.brave.browser": "Brave Browser",
        "com.brave.browser.beta": "Brave Browser Beta",
        "com.brave.browser.nightly": "Brave Browser Nightly",
        "com.vivaldi.vivaldi": "Vivaldi",
        "com.vivaldi.vivaldi.snapshot": "Vivaldi Snapshot",
        "com.electron.min": "Min",
        "paris.lithium.kosmik": "Kosmik",
        "org.mozilla.pale moon": "Pale Moon",
        "company.thebrowser.browser": "Arc",
        "com.shift.browser": "Shift Browser",
        "com.duckduckgo.mobile.ios": "DuckDuckGo"
    }

    with PREFERENCES.open("rb") as config_file:
        configuration = plistlib.load(config_file)

    default_browser = "No browser is set to default."
    for handler in configuration["LSHandlers"]:
        if handler.get("LSHandlerURLScheme") == "https":
            role = handler["LSHandlerRoleAll"]
            if role not in SUPPORTED_BROWSERS:
                default_browser = "Default browser is not supported."
                continue
            default_browser = SUPPORTED_BROWSERS[role]
            for name, bundle_id, version_string in (browser_record for browser_record in POSSIBLE_BROWSERS
                                                    if browser_record[1].lower() == role):
                # configuration plist is not updated when a default browser is deleted from system
                # default browser should be checked if it is really installed
                if not do_i_have_installed(name):
                    default_browser = "No browser is set to default."
    return default_browser


# check if the given browser is installed
def do_i_have_installed(name):
    for browser, bundle_id, version_string in (browser_record for browser_record in POSSIBLE_BROWSERS
                                               if browser_record[0] == name):
        paths = subprocess.getoutput(f'mdfind "kMDItemCFBundleIdentifier == {bundle_id}"').splitlines()
        for path in paths:
            with open(os.path.join(path, "Contents/Info.plist"), "rb") as f:
                plist = plistlib.load(f)
                executable_name = plist.get("CFBundleExecutable")
                if executable_name:
                    return True
    return False


# get details of a browser
def get_details_of(name) -> Optional[Browser]:
    for browser, bundle_id, version_string in (browser_record for browser_record in POSSIBLE_BROWSERS
                                               if browser_record[0] == name):
        paths = subprocess.getoutput(f'mdfind "kMDItemCFBundleIdentifier == {bundle_id}"').splitlines()
        for path in paths:
            with open(os.path.join(path, "Contents/Info.plist"), "rb") as f:
                plist = plistlib.load(f)
                executable_name = plist.get("CFBundleExecutable")
                executable = os.path.join(path, "Contents/MacOS", executable_name)
                description = plist.get("CFBundleDisplayName") or plist.get("CFBundleName", browser)
                version = plist[version_string]
                yield Browser(
                    name=browser,
                    description=description,
                    version=version,
                    location=executable if browser != "safari" else path
                )
    yield "Browser is not installed."


# retrieve browser version
def get_version_of(name) -> Optional[Version]:
    for browser, bundle_id, version_string in (browser_record for browser_record in POSSIBLE_BROWSERS
                                               if browser_record[0] == name):
        paths = subprocess.getoutput(f'mdfind "kMDItemCFBundleIdentifier == {bundle_id}"').splitlines()
        for path in paths:
            with open(os.path.join(path, "Contents/Info.plist"), "rb") as f:
                plist = plistlib.load(f)
                version = plist[version_string]
                yield Version(
                    version=version
                )
    yield "Browser is not installed."
