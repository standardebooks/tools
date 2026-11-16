#!/usr/bin/env python3
"""
Defines functions for interacting with headless browser sessions.
"""

import atexit
from contextlib import ExitStack
import ctypes
from enum import Enum
from hashlib import file_digest, sha256
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from typing import cast

import installed_browsers
from selenium import __version__ as selenium_version, webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.remote.webdriver import WebDriver

import se

# Storing temp directories in this list keeps them existant across function calls; when the script ends, they'll be automatically cleaned up.
_TEMP_DIRECTORY_STACK = ExitStack()
atexit.register(_TEMP_DIRECTORY_STACK.close)

class BrowserType(Enum):
	"""
	One of the supported browser types.
	"""

	FIREFOX = 1
	CHROME = 2
	SAFARI = 3

	@staticmethod
	def from_string(value: str|None) -> "BrowserType | None":
		"""
		Return the BrowserType for the given browser name string, or `None` if it can't be determined or is an unsupported browser.
		"""

		if not value:
			return None

		value = value.lower()

		if "firefox" in value:
			return BrowserType.FIREFOX

		if "chrome" in value or "chromium" in value:
			return BrowserType.CHROME

		# Disable Safari for now, see below for rationale.
		#if "safari" in value:
		#	return BrowserType.SAFARI

		return None

	@staticmethod
	def flatpak_application_id(browser_type: "BrowserType") -> str:
		"""
		Return the Flatpak application ID for the given browser type.
		"""

		if browser_type == BrowserType.FIREFOX:
			return "org.mozilla.firefox"

		return "org.chromium.Chromium"

class InstallationType(Enum):
	"""
	One of the supported browser installation types.
	"""

	NATIVE = 1
	SNAP = 2
	FLATPAK = 3

class Browser:
	"""
	A supported browser and its Selenium webdriver.
	"""

	def __init__(self):
		"""
		Initialize a browser wrapper for the user's default browser.
		"""

		self.type: BrowserType
		self.installation_type: InstallationType
		self.executable_path: Path
		self.version = ""
		self._driver: WebDriver | None = None

		try:
			for installed_browser in list(installed_browsers.browsers()):
				browser_type = BrowserType.from_string(installed_browser["name"])
				if browser_type:
					installed_browser_location = str(installed_browser["location"])
					self.type = browser_type
					self.installation_type = InstallationType.NATIVE
					self.executable_path = Path(installed_browser_location)
					self.version = installed_browser.get("version", "")

					# `installed_browsers.browsers()` doesn't identify browsers installed via Flatpak, but in case it does on some platforms, check that here.
					if "org.mozilla.firefox" in installed_browser_location or "org.chromium.Chromium" in installed_browser_location:
						self.installation_type = InstallationType.FLATPAK
					elif (browser_type == BrowserType.FIREFOX and Path("/snap/bin/geckodriver").is_file()) or (browser_type == BrowserType.CHROME and Path("/snap/bin/chromium.chromedriver").is_file()):
						self.installation_type = InstallationType.SNAP

					return

			# installed_browsers 0.1.5 fails to return machine-wide browser installations on Windows when no browser is registered for the current user.
			if os.name == 'nt':
				import winreg # pylint: disable=import-error,import-outside-toplevel

				for browser_type, executable_name in ((BrowserType.FIREFOX, 'firefox.exe'), (BrowserType.CHROME, 'chrome.exe')):
					for registry_hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
						try:
							with winreg.OpenKey(registry_hive, 'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\' + executable_name) as registry_key:
								executable_path = Path(winreg.QueryValue(registry_key, None))
								if executable_path.is_file():
									self.type = browser_type
									self.installation_type = InstallationType.NATIVE
									self.executable_path = executable_path
									return
						except FileNotFoundError:
							pass

			# `installed_browsers.browsers()` doesn't identify browsers installed via Flatpak. Try to identify them here.
			for browser_type in (BrowserType.FIREFOX, BrowserType.CHROME):
				for flatpak_export_directory in (
					Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "flatpak" / "exports" / "bin",
					Path("/var/lib/flatpak/exports/bin")
				):
					executable_path = flatpak_export_directory / BrowserType.flatpak_application_id(browser_type)
					if executable_path.is_file():
						self.type = browser_type
						self.installation_type = InstallationType.FLATPAK
						self.executable_path = executable_path
						return

		except Exception as ex:
			raise se.MissingDependencyException(f"Couldn’t find web browser. Message: {ex}")

		raise se.MissingDependencyException("Couldn’t find [command]chrome[/], [command]chromium[/], or [command]firefox[/].")

	def get_rendering_fingerprint(self) -> str | None:
		"""
		Fingerprint a native macOS or Linux browser and its fonts without starting a webdriver.
		"""

		if not (sys.platform.startswith("linux") or sys.platform == "darwin") or self.installation_type != InstallationType.NATIVE or not self.version:
			return None

		try:
			executable = Path(shutil.which(str(self.executable_path)) or self.executable_path).resolve(strict=True)
			# Generic launcher directories do not identify a complete browser installation.
			if executable.parent in (Path("/bin"), Path("/usr/bin"), Path("/usr/local/bin")):
				return None
			paths: set[Path] = set()
			installation = executable.parent
			if sys.platform == "darwin":
				# Include frameworks, resources, and policies throughout the browser's app bundle.
				for directory in (executable, *executable.parents):
					if directory.suffix == ".app":
						installation = directory
						break
				else:
					raise ValueError("Browser executable is not inside an app bundle.")

				# Core Text enumerates available font files, including fonts outside standard directories.
				core_text = ctypes.CDLL("/System/Library/Frameworks/CoreText.framework/CoreText")
				foundation = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
				core_text.CTFontManagerCopyAvailableFontURLs.argtypes = []
				core_text.CTFontManagerCopyAvailableFontURLs.restype = ctypes.c_void_p
				foundation.CFArrayGetCount.argtypes = [ctypes.c_void_p]
				foundation.CFArrayGetCount.restype = ctypes.c_long
				foundation.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
				foundation.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
				foundation.CFURLGetFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_void_p, ctypes.c_long]
				foundation.CFURLGetFileSystemRepresentation.restype = ctypes.c_bool
				foundation.CFRelease.argtypes = [ctypes.c_void_p]
				foundation.CFRelease.restype = None
				font_urls = cast(int | None, core_text.CTFontManagerCopyAvailableFontURLs())
				if not font_urls:
					raise ValueError("Core Text returned no font URL array.")
				try:
					count = cast(int, foundation.CFArrayGetCount(font_urls))
					if count <= 0:
						raise ValueError("Core Text returned no available fonts.")
					buffer = ctypes.create_string_buffer(os.pathconf("/", "PC_PATH_MAX") + 1)
					for index in range(count):
						url = cast(int | None, foundation.CFArrayGetValueAtIndex(font_urls, index))
						if not url or not foundation.CFURLGetFileSystemRepresentation(url, True, buffer, len(buffer)):
							raise ValueError("Could not resolve a Core Text font URL.")
						paths.add(Path(os.fsdecode(buffer.value)))
				finally:
					foundation.CFRelease(font_urls)

				packages = subprocess.run(["sw_vers"], check=True, capture_output=True)
				font_config = subprocess.run(["defaults", "export", "NSGlobalDomain", "-"], check=True, capture_output=True, text=True)
				for directory in (Path("/Library/Preferences"), Path.home() / "Library/Preferences", Path("/Library/Managed Preferences"), Path.home() / "Library/Managed Preferences"):
					for name in ("org.mozilla.firefox.plist", "com.google.Chrome.plist", "org.chromium.Chromium.plist"):
						if (directory / name).is_file():
							paths.add(directory / name)
			else:
				fonts = subprocess.run(["fc-list", "--format=%{file}\n"], check=True, capture_output=True, text=True)
				font_config = subprocess.run(["fc-conflist"], check=True, capture_output=True, text=True)
				paths.update(Path(path) for path in fonts.stdout.splitlines() if path)
				paths.update(Path(line.partition(":")[0].lstrip("+- ")) for line in font_config.stdout.splitlines() if line)
				for command in (
					["dpkg-query", "--show", "--showformat=${Package}=${Version}\n"],
					["rpm", "--query", "--all", "--queryformat=%{NAME}=%{VERSION}-%{RELEASE}.%{ARCH}\n"],
					["pacman", "--query"],
					["apk", "info", "--verbose"],
				):
					if shutil.which(command[0]):
						packages = subprocess.run(command, check=True, capture_output=True)
						break
				else:
					raise ValueError("No supported package database is available.")
				for directory in (Path("/etc/firefox"), Path("/etc/chromium"), Path("/etc/opt/chrome")):
					paths.update(path for path in directory.rglob("*") if path.is_file())
			paths.update(path for path in installation.rglob("*") if path.is_file())
			paths.add(Path(__file__))

			# Include settings that can change font selection, scaling, or browser rendering.
			environment = {name: value for name, value in os.environ.items() if name.startswith(("FONTCONFIG_", "LC_", "XDG_", "GDK_", "GTK_", "QT_", "MOZ_")) and name not in ("XDG_CACHE_HOME", "XDG_RUNTIME_DIR")}
			environment.update({name: os.environ.get(name, "") for name in ("HOME", "LANG", "FREETYPE_PROPERTIES")})
			digest = sha256(repr((self.type.name, self.version, str(executable), platform.platform(), sys.version, selenium_version, tuple(sorted(environment.items())))).encode("utf-8"))
			digest.update(b"\n".join(sorted(packages.stdout.splitlines())))
			digest.update(font_config.stdout.encode("utf-8"))
			for path in sorted(paths):
				digest.update(str(path).encode("utf-8") + b"\0")
				with path.open("rb") as file:
					digest.update(file_digest(file, "sha256").digest())
			return digest.hexdigest()
		except (OSError, ValueError, AttributeError, subprocess.CalledProcessError):
			# Unsupported installations and unavailable fingerprint inputs retain live measurement.
			return None

	@property
	def driver(self) -> WebDriver:
		"""
		Return the Selenium webdriver, initializing it if necessary.
		"""

		if self._driver is None:
			try:
				if self.type == BrowserType.CHROME:
					self._driver = self._initialize_selenium_chrome_webdriver()

				elif self.type == BrowserType.FIREFOX:
					self._driver = self._initialize_selenium_firefox_webdriver()

				# 2026-07-17: Safari doesn't have a headless mode, which means windows pop up over the CLI, and it also fails when stitching screenshots together in `compare-versions`, so for now, disable Safari support and require either Firefox or Chrome.
				# See <https://github.com/standardebooks/tools/pull/992> and <https://github.com/standardebooks/tools/pull/994>.
				#elif self.type == BrowserType.SAFARI:
				#	self._driver = self._initialize_selenium_safari_webdriver()

				else:
					raise se.MissingDependencyException("Couldn’t find [command]chrome[/], [command]chromium[/], or [command]firefox[/].")

			except Exception as ex:
				raise se.MissingDependencyException(f"Couldn’t start web browser. Message: {ex}")

		return self._driver

	def get_temporary_directory(self) -> Path | None:
		"""
		Return a temporary directory accessible to a sandboxed browser, or `None` if the browser doesn't require one.
		"""
		# Flatpak exposes this application-specific runtime directory at the same path inside and outside its sandbox.
		if self.installation_type == InstallationType.FLATPAK:
			runtime_directory = os.environ.get("XDG_RUNTIME_DIR", "/run/user/" + str(os.getuid()))
			flatpak_temporary_directory = Path(runtime_directory) / "app" / BrowserType.flatpak_application_id(self.type) / "tmp"
			flatpak_temporary_directory.mkdir(parents=True, exist_ok=True)
			return flatpak_temporary_directory

		if self.installation_type == InstallationType.SNAP and self.type == BrowserType.FIREFOX:
			firefox_snap_common_directory = Path.home() / "snap" / "firefox" / "common"
			if firefox_snap_common_directory.is_dir():
				return firefox_snap_common_directory

		if self.installation_type == InstallationType.SNAP and self.type == BrowserType.CHROME:
			chromium_snap_common_directory = Path.home() / "snap" / "chromium" / "common"
			if chromium_snap_common_directory.is_dir():
				return chromium_snap_common_directory

		return None

	def _initialize_selenium_chrome_webdriver(self) -> WebDriver:
		"""
		Initialize a Selenium Chrome-compatible driver and return it for use in other applications.
		"""

		options = ChromeOptions()

		# We have to use the headless option, otherwise it will pop up a browser window.
		options.add_argument("--headless=new")
		options.add_argument("--disable-dev-shm-usage")
		options.add_argument("--no-sandbox")
		if self.installation_type == InstallationType.FLATPAK and self.executable_path:
			options.binary_location = str(self.executable_path)
		else:
			options.add_argument("--remote-debugging-pipe")

		chrome_profile_directory = _TEMP_DIRECTORY_STACK.enter_context(tempfile.TemporaryDirectory(prefix="se-selenium-chrome-", dir=self.get_temporary_directory()))
		options.add_argument("--user-data-dir=" + chrome_profile_directory)

		# Disable history and caches so repeated screenshots do not inherit session state.
		options.add_argument("--incognito")
		options.add_argument("--disable-application-cache")
		options.add_argument("--disk-cache-size=0")
		options.add_argument("--media-cache-size=0")
		options.add_argument("--force-device-scale-factor=2")
		chrome_prefs: dict[str, int] = {
			"profile.default_content_setting_values.cookies": 2
		}
		options.add_experimental_option("prefs", chrome_prefs) # type: ignore This is an error in Selenium's type stub.

		# The Chromium Snap's chromedriver must run in the same Snap sandbox as Chromium. Specifying it also prevents Selenium Manager from treating the Snap launcher as the Chromium executable.
		if self.installation_type == InstallationType.SNAP:
			return webdriver.Chrome(options=options, service=ChromeService(executable_path="/snap/bin/chromium.chromedriver")) # type: ignore This is an error in Selenium's type stub.

		return webdriver.Chrome(options=options) # type: ignore This is an error in Selenium's type stub.

	def _initialize_selenium_firefox_webdriver(self) -> WebDriver:
		"""
		Initialize a Selenium Firefox driver and return it for use in other applications.
		"""

		# We have to use the headless option, otherwise it will pop up a Firefox window.
		options = FirefoxOptions()
		options.add_argument("-headless")
		# Force a wide viewport, otherwise Firefox may crash.
		options.add_argument("--width=1400")
		options.add_argument("--height=1000")
		if self.installation_type == InstallationType.FLATPAK and self.executable_path:
			options.binary_location = str(self.executable_path)

		# Disable the history, because otherwise links to (for example to end notes) may appear as "visited" in visits to other pages, and thus cause a fake diff.
		profile = FirefoxProfile()
		profile.set_preference("places.history.enabled", False) # type: ignore This is an error in Selenium's type stub.
		profile.set_preference("browser.cache.disk.enable", False) # type: ignore This is an error in Selenium's type stub.
		profile.set_preference("browser.cache.memory.enable", False) # type: ignore This is an error in Selenium's type stub.
		profile.set_preference("browser.cache.offline.enable", False) # type: ignore This is an error in Selenium's type stub.
		profile.set_preference("browser.http.use-cache", False) # type: ignore This is an error in Selenium's type stub.
		profile.set_preference("layout.css.devPixelsPerPx", "2.0") # type: ignore This is an error in Selenium's type stub.

		options.profile = profile

		# The Firefox Snap's geckodriver must run in the same Snap sandbox as Firefox. Specifying it also prevents Selenium Manager from treating the Snap launcher as the Firefox executable.
		if self.installation_type == InstallationType.SNAP:
			return webdriver.Firefox(options=options, service=FirefoxService(executable_path="/snap/bin/geckodriver")) # type: ignore This is an error in Selenium's type stub.

		if self.installation_type == InstallationType.FLATPAK:
			# Geckodriver must create profiles in a directory that the Flatpak Firefox process can access.
			flatpak_temporary_directory = self.get_temporary_directory()
			if flatpak_temporary_directory:
				service_environment = os.environ.copy()
				service_environment["TMPDIR"] = str(flatpak_temporary_directory)
				service = FirefoxService(service_args=["--profile-root", str(flatpak_temporary_directory)], env=service_environment)
				return webdriver.Firefox(options=options, service=service) # type: ignore This is an error in Selenium's type stub.

		return webdriver.Firefox(options=options) # type: ignore This is an error in Selenium's type stub.

	def _initialize_selenium_safari_webdriver(self) -> WebDriver:
		"""
		Initialize a Selenium Safari-compatible driver and return it for use in other applications.
		"""

		options = SafariOptions()

		return webdriver.Safari(options=options) # type: ignore This is an error in Selenium's type stub.
