import os
import pathlib
import platform
from typing import Iterator, Optional

from .common import Browser, OS, Version

try:
    # noinspection PyUnresolvedReferences
    import winreg
except ImportError:     # pragma: no cover
    import_error = "Operating system is not Windows, winreg is not imported."

try:
    # noinspection PyUnresolvedReferences
    import win32api
except ImportError:     # pragma: no cover
    import_error = "Operating system is not Windows, win32api is not imported."

# dictionary of possible browsers
POSSIBLE_BROWSERS = {
    "Google Chrome": "chrome",
    "Google Chrome Canary": "chrome-canary",
    "Chromium": "chromium",
    "Mozilla Firefox": "firefox",
    "Firefox Developer Edition": "firefox-developer",
    "Firefox Nightly": "firefox-nightly",
    "Opera Stable": "opera-stable",
    "Opera beta": "opera-beta",
    "Opera developer": "opera-developer",
    "Microsoft Edge": "msedge",
    "Microsoft Edge Beta": "msedge-beta",
    "Microsoft Edge Dev": "msedge-dev",
    "Microsoft Edge Canary": "msedge-canary",
    "Internet Explorer": "msie",
    "Brave": "brave",
    "Brave Beta": "brave-beta",
    "Brave Nightly": "brave-nightly",
    "Vivaldi": "vivaldi",
    "Min": "min",
    "Pale Moon": "pale-moon",
    "Shift Browser": "shift",
    "DuckDuckGo": "duckduckgo"
}

# dictionary of default browsers
DEFAULT_BROWSER_DETAILS = {
    "ChromeHTML": "Google Chrome",
    "ChromeSSHTM": "Google Chrome Canary",
    "ChromiumHTM": "Chromium",
    "OperaStable": "Opera Stable",
    "Operabeta": "Opera beta",
    "Operadeveloper": "Opera developer",
    "MSEdgeHTM": "Microsoft Edge",
    "MSEdgeBHTML": "Microsoft Edge Beta",
    "MSEdgeDHTML": "Microsoft Edge Dev",
    "MSEdgeSSHTM": "Microsoft Edge Canary",
    "IE.HTTP": "Internet Explorer",
    "BraveHTML": "Brave",
    "BraveBHTML": "Brave Beta",
    "BraveSSHTM": "Brave Nightly",
    "VivaldiHTM": "Vivaldi",
    "Min": "Min",
    "PaleMoonURL": "Pale Moon",
    "ShiftHTM": "Shift",
    "duckduckgo": "DuckDuckGo"
}

# dictionary of possible browser names
POSSIBLE_BROWSER_NAMES = dict(
    (value, key) for key, value in POSSIBLE_BROWSERS.items()
)

# constant declaration
DASH = "-"
DOT = "."
EXECUTABLE = "exe"
FIREFOX = "firefox"
DUCKDUCKGO = "duckduckgo"
DUCK_INSTALL = "AppX"
DESKTOP_BROWSER = "DesktopBrowser"


# get all installed browsers
def browsers() -> Iterator[Browser]:
    match platform.architecture()[0]:
        case OS.WIN32:    # pragma: no cover
            yield from _get_unique_browsers(winreg.KEY_WOW64_32KEY)
        case OS.WIN64:
            yield from _get_unique_browsers(winreg.KEY_WOW64_64KEY)


# get default browser
def what_is_the_default_browser() -> Optional[str]:
    description = "No browser is set to default."
    registry_path = r'Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
        default_browser = winreg.QueryValueEx(key, "ProgId")[0]
        if default_browser:
            if DASH in default_browser:
                return _setup_firefox_versions(default_browser)
            elif DOT in default_browser:
                default_browser = default_browser.split(".", 1)[0]
            elif DUCK_INSTALL in default_browser:
                return _search_for_default_duckduckgo(default_browser)
            description = DEFAULT_BROWSER_DETAILS.get(default_browser, "unknown")
            for browser in (browser_record for browser_record in POSSIBLE_BROWSERS
                            if description == browser_record):
                # registry is not updated when a default browser is deleted from system
                # default browser should be checked if it is really installed
                if not do_i_have_installed(POSSIBLE_BROWSERS[browser]):
                    description = "No browser is set to default."
    return description


# check if the given browser is installed
def do_i_have_installed(name):
    for browser in (browser_record for browser_record in POSSIBLE_BROWSER_NAMES
                    if name == browser_record):
        browser_name = POSSIBLE_BROWSER_NAMES[browser]

        if name == DUCKDUCKGO:
            return _get_duckduckgo_from_registry()

        match platform.architecture()[0]:
            case OS.WIN32:  # pragma: no cover
                is_browser_installed = _get_browser_from_registry(
                    winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_32KEY, browser_name)
            case OS.WIN64:
                is_browser_installed = _get_browser_from_registry(
                    winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_64KEY, browser_name)
        if not is_browser_installed:
            is_browser_installed = _get_browser_from_registry(
                winreg.HKEY_CURRENT_USER, winreg.KEY_READ, browser_name)
        return is_browser_installed
    return False


# get details of a browser
def get_details_of(name) -> Optional[Browser | str]:
    for browser in (browser_record for browser_record in POSSIBLE_BROWSER_NAMES
                    if name == browser_record):
        browser_name = POSSIBLE_BROWSER_NAMES[browser]

        if name == DUCKDUCKGO:
            yield _get_duckduckgo_details_from_registry()
            # return

        yield _get_browser_details_from_registry(winreg.HKEY_CURRENT_USER, winreg.KEY_READ, browser_name)
        match platform.architecture()[0]:   # pragma: no cover
            case OS.WIN32:
                yield _get_browser_details_from_registry(
                    winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_32KEY, browser_name)
            case OS.WIN64:
                yield _get_browser_details_from_registry(
                    winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_64KEY, browser_name)
    return "Browser is not installed."


# retrieve browser version
def get_version_of(name) -> Optional[Version | str]:
    for browser in (browser_record for browser_record in POSSIBLE_BROWSER_NAMES
                    if name == browser_record):
        browser_name = POSSIBLE_BROWSER_NAMES[browser]

        if name == DUCKDUCKGO:
            yield _get_duckduckgo_version_from_registry()

        yield _get_browser_version_from_registry(winreg.HKEY_CURRENT_USER, winreg.KEY_READ, browser_name)
        match platform.architecture()[0]:
            case OS.WIN32:  # pragma: no cover
                yield _get_browser_version_from_registry(
                    winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_32KEY, browser_name)
            case OS.WIN64:
                yield _get_browser_version_from_registry(
                    winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_64KEY, browser_name)
    return "Browser is not installed."


# get browsers from registry
def _get_browsers_from_registry(tree: int, access: int) -> Iterator[Browser]:
    try:
        with winreg.OpenKey(tree, r"Software\Clients\StartMenuInternet", access=access) as hkey:
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(hkey, i)
                    i += 1
                except OSError:
                    break
                try:
                    description = winreg.QueryValue(hkey, subkey)
                    if not description or not isinstance(description, str):  # pragma: no cover
                        description = subkey
                except OSError:  # pragma: no cover
                    description = subkey
                try:
                    cmd = winreg.QueryValue(hkey, rf"{subkey}\shell\open\command")
                    cmd = cmd.strip('"')
                    os.stat(cmd)
                except (OSError, AttributeError, TypeError, ValueError):  # pragma: no cover
                    continue
                yield Browser(
                    name=POSSIBLE_BROWSERS.get(description, "unknown"),
                    description=description,
                    version=_create_browser_version(cmd),
                    location=cmd
                )
    except FileNotFoundError:  # pragma: no cover
        pass


# get a single browser from registry
def _get_browser_from_registry(tree: int, access: int, name: str):
    try:
        with winreg.OpenKey(tree, r"Software\Clients\StartMenuInternet", access=access) as hkey:
            browser_found = False
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(hkey, i)
                    i += 1
                except OSError:  # pragma: no cover
                    break
                try:
                    description = winreg.QueryValue(hkey, subkey)
                    if not description or not isinstance(description, str):  # pragma: no cover
                        description = subkey
                except OSError:  # pragma: no cover
                    description = subkey
                if description == name:
                    browser_found = True
                    break
            return browser_found
    except FileNotFoundError:   # pragma: no cover
        pass


# get browser details from registry
def _get_browser_details_from_registry(tree: int, access: int, name: str) -> Optional[Browser | str]:
    try:
        with winreg.OpenKey(tree, r"Software\Clients\StartMenuInternet", access=access) as hkey:
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(hkey, i)
                    i += 1
                except OSError:  # pragma: no cover
                    break
                try:
                    description = winreg.QueryValue(hkey, subkey)
                    if not description or not isinstance(description, str):  # pragma: no cover
                        description = subkey
                except OSError:  # pragma: no cover
                    description = subkey
                if description == name:
                    try:
                        cmd = winreg.QueryValue(hkey, rf"{subkey}\shell\open\command")
                        cmd = cmd.strip('"')
                        os.stat(cmd)
                    except (OSError, AttributeError, TypeError, ValueError):  # pragma: no cover
                        continue
                    yield Browser(
                        name=POSSIBLE_BROWSERS.get(description, "unknown"),
                        description=description,
                        version=_create_browser_version(cmd),
                        location=cmd
                    )
    except FileNotFoundError:   # pragma: no cover
        pass


# get browser version from registry
def _get_browser_version_from_registry(tree: int, access: int, name: str) -> Optional[Version | str]:
    try:
        with winreg.OpenKey(tree, r"Software\Clients\StartMenuInternet", access=access) as hkey:
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(hkey, i)
                    i += 1
                except OSError:     # pragma: no cover
                    break
                try:
                    description = winreg.QueryValue(hkey, subkey)
                    if not description or not isinstance(description, str):  # pragma: no cover
                        description = subkey
                except OSError:  # pragma: no cover
                    description = subkey
                if description == name:
                    try:
                        cmd = winreg.QueryValue(hkey, rf"{subkey}\shell\open\command")
                        cmd = cmd.strip('"')
                        os.stat(cmd)
                    except (OSError, AttributeError, TypeError, ValueError):  # pragma: no cover
                        continue
                    yield Version(
                        version=_create_browser_version(cmd),
                    )
    except FileNotFoundError:   # pragma: no cover
        pass


# determine browser version
def _create_browser_version(path: str) -> str:
    info = win32api.GetFileVersionInfo(path, "\\")
    ms = info["FileVersionMS"]
    ls = info["FileVersionLS"]
    return ".".join(map(str, (win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), win32api.LOWORD(ls))))


# determine firefox version
def _setup_firefox_versions(browser_id: str) -> str:
    registry_path = str(pathlib.Path(r'Software\Classes', browser_id, "DefaultIcon"))
    # firefox version can be installed in both local machine and current user registries
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as key:
            firefox_path = winreg.QueryValue(key, "")
            path_split = firefox_path.split("\\", 15)
            for description in (name for name in path_split
                                if FIREFOX in name.lower()
                                and EXECUTABLE not in name.lower()):
                return description
    except FileNotFoundError:  # pragma: no cover
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
                firefox_path = winreg.QueryValue(key, "")
                path_split = firefox_path.split("\\", 15)
                for description in (name for name in path_split
                                    if FIREFOX in name.lower()
                                    and EXECUTABLE not in name.lower()):
                    return description
        except FileNotFoundError:  # pragma: no cover
            pass


# get only unique browsers
def _get_unique_browsers(winreg_key) -> Iterator[Browser]:
    # get browsers from local machine
    browsers_local_machine = _get_browsers_from_registry(winreg.HKEY_LOCAL_MACHINE,
                                                         winreg.KEY_READ | winreg_key)

    # get browsers from current user
    browsers_current_user = _get_browsers_from_registry(winreg.HKEY_CURRENT_USER, winreg.KEY_READ)

    # get browsers available in both places
    duplicates = []
    for browser_current_user in browsers_current_user:  # pragma: no cover
        yield browser_current_user

        for browser_local_machine in _get_browsers_from_registry(winreg.HKEY_LOCAL_MACHINE,
                                                                 winreg.KEY_READ | winreg_key):
            if browser_current_user == browser_local_machine:
                duplicates.append(browser_local_machine)
                continue

    # filter for unique browsers
    for browser_local_machine in browsers_local_machine:    # pragma: no cover
        for duplicate in duplicates:
            if duplicate == browser_local_machine:
                browser_local_machine.clear()
                break
            elif browser_local_machine not in duplicates:
                yield browser_local_machine
                break

    # get duckduckgo and filter for unique occurrence
    for duckduckgo in _search_for_duckduckgo():
        if duckduckgo not in duplicates:
            duplicates.append(duckduckgo)
            yield duckduckgo


# search for duckduckgo browser
def _search_for_default_duckduckgo(browser_id: str) -> str:
    registry_path = fr'Software\Classes\{browser_id}\Application'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as hkey:
        default_browser = winreg.QueryValueEx(hkey, "ApplicationName")[0]
    return DEFAULT_BROWSER_DETAILS.get(default_browser.lower(), "unknown")


def _search_for_duckduckgo() -> Iterator[Browser]:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes") as hkey:
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(hkey, i)
                    i += 1
                except OSError:  # pragma: no cover
                    break
                try:
                    description = winreg.QueryValue(hkey, subkey)
                    if not description or not isinstance(description, str):  # pragma: no cover
                        description = subkey
                    if description.startswith(DUCK_INSTALL):
                        registry_path = fr'Software\Classes\{description}\Application'
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
                            browser = winreg.QueryValueEx(key, "AppUserModelID")[0]
                            if DESKTOP_BROWSER in browser:
                                description = winreg.QueryValueEx(key, "ApplicationName")[0]
                                try:
                                    cmd = winreg.QueryValue(hkey, rf"{subkey}\shell\open\command")
                                    cmd = cmd.strip('"')
                                    os.stat(cmd)
                                except (OSError, AttributeError, TypeError, ValueError):  # pragma: no cover
                                    continue
                                yield Browser(
                                    name=POSSIBLE_BROWSERS.get(description, "unknown"),
                                    description=description,
                                    version=_create_browser_version(cmd),
                                    location=cmd
                                )
                except OSError:  # pragma: no cover
                    description = subkey
    except FileNotFoundError:  # pragma: no cover
         pass


# get duckduckgo from registry
def _get_duckduckgo_from_registry():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes") as hkey:
            browser_found = False
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(hkey, i)
                    i += 1
                except OSError:  # pragma: no cover
                    break
                try:
                    description = winreg.QueryValue(hkey, subkey)
                    if not description or not isinstance(description, str):  # pragma: no cover
                        description = subkey
                    if description.startswith(DUCK_INSTALL):
                        registry_path = fr'Software\Classes\{description}\Application'
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
                            browser = winreg.QueryValueEx(key, "AppUserModelID")[0]
                            if DESKTOP_BROWSER in browser:
                                browser_found = True
                                break
                except FileNotFoundError:  # pragma: no cover
                    pass
            return browser_found
    except FileNotFoundError:  # pragma: no cover
         pass


# get duckduckgo details from registry
def _get_duckduckgo_details_from_registry() -> Optional[Browser | str]:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes") as hkey:
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(hkey, i)
                    i += 1
                except OSError:  # pragma: no cover
                    break
                try:
                    description = winreg.QueryValue(hkey, subkey)
                    if not description or not isinstance(description, str):  # pragma: no cover
                        description = subkey
                    if description.startswith(DUCK_INSTALL):
                        registry_path = fr'Software\Classes\{description}\Application'
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
                            browser = winreg.QueryValueEx(key, "AppUserModelID")[0]
                            if DESKTOP_BROWSER in browser:
                                description = winreg.QueryValueEx(key, "ApplicationName")[0]
                                try:
                                    cmd = winreg.QueryValue(hkey, rf"{subkey}\shell\open\command")
                                    cmd = cmd.strip('"')
                                    os.stat(cmd)
                                except (OSError, AttributeError, TypeError, ValueError):  # pragma: no cover
                                    continue
                                yield Browser(
                                    name=POSSIBLE_BROWSERS.get(description, "unknown"),
                                    description=description,
                                    version=_create_browser_version(cmd),
                                    location=cmd
                                )

                except OSError:  # pragma: no cover
                    description = subkey
    except FileNotFoundError:  # pragma: no cover
         pass


# get duckduckgo version from registry
def _get_duckduckgo_version_from_registry() -> Optional[Version | str]:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes") as hkey:
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(hkey, i)
                    i += 1
                except OSError:  # pragma: no cover
                    break
                try:
                    description = winreg.QueryValue(hkey, subkey)
                    if not description or not isinstance(description, str):  # pragma: no cover
                        description = subkey
                    if description.startswith(DUCK_INSTALL):
                        registry_path = fr'Software\Classes\{description}\Application'
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
                            browser = winreg.QueryValueEx(key, "AppUserModelID")[0]
                            if DESKTOP_BROWSER in browser:
                                try:
                                    cmd = winreg.QueryValue(hkey, rf"{subkey}\shell\open\command")
                                    cmd = cmd.strip('"')
                                    os.stat(cmd)
                                except (OSError, AttributeError, TypeError, ValueError):  # pragma: no cover
                                    continue
                                yield Version(
                                    version=_create_browser_version(cmd)
                                )

                except OSError:  # pragma: no cover
                    description = subkey
    except FileNotFoundError:  # pragma: no cover
         pass