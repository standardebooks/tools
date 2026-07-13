#!/usr/bin/env python3
"""
Defines functions for interacting with headless browser sessions.
"""

import atexit
from contextlib import ExitStack
from enum import Enum
import tempfile

import installed_browsers
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
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

		return None

def _initialize_selenium_chrome_webdriver() -> WebDriver:
	"""
	Initialize a Selenium Chrome-compatible driver and return it for use in other applications.
	"""

	options = ChromeOptions()

	# We have to use the headless option, otherwise it will pop up a browser window.
	options.add_argument("--headless=new")
	options.add_argument("--disable-dev-shm-usage")
	options.add_argument("--no-sandbox")
	options.add_argument("--remote-debugging-pipe")

	chrome_profile_directory = _TEMP_DIRECTORY_STACK.enter_context(tempfile.TemporaryDirectory(prefix="se-selenium-chrome-"))
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

	return webdriver.Chrome(options=options) # type: ignore This is an error in Selenium's type stub.

def _initialize_selenium_firefox_webdriver() -> WebDriver:
	"""
	Initialize a Selenium Firefox driver and return it for use in other applications.
	"""

	# We have to use the headless option, otherwise it will pop up a Firefox window.
	options = FirefoxOptions()
	options.add_argument("-headless")
	# Force a wide viewport, otherwise Firefox may crash.
	options.add_argument("--width=1400")
	options.add_argument("--height=1000")

	# Disable the history, because otherwise links to (for example to end notes) may appear as "visited" in visits to other pages, and thus cause a fake diff.
	profile = FirefoxProfile()
	profile.set_preference("places.history.enabled", False) # type: ignore This is an error in Selenium's type stub.
	profile.set_preference("browser.cache.disk.enable", False) # type: ignore This is an error in Selenium's type stub.
	profile.set_preference("browser.cache.memory.enable", False) # type: ignore This is an error in Selenium's type stub.
	profile.set_preference("browser.cache.offline.enable", False) # type: ignore This is an error in Selenium's type stub.
	profile.set_preference("browser.http.use-cache", False) # type: ignore This is an error in Selenium's type stub.
	profile.set_preference("layout.css.devPixelsPerPx", "2.0") # type: ignore This is an error in Selenium's type stub.

	options.profile = profile

	return webdriver.Firefox(options=options) # type: ignore This is an error in Selenium's type stub.

def initialize_selenium_webdriver() -> WebDriver:
	"""
	Initialize a Selenium driver for the user's default browser and return it for use in other applications.

	RETURNS
	A Selenium webdriver for Chrome or Firefox.
	"""

	try:
		for browser in installed_browsers.browsers():
			browser_type = BrowserType.from_string(browser["name"])

			if browser_type == BrowserType.CHROME:
				return _initialize_selenium_chrome_webdriver()

			if browser_type == BrowserType.FIREFOX:
				return _initialize_selenium_firefox_webdriver()

	except Exception as ex:
		raise se.MissingDependencyException(f"Couldn’t start web browser. Message: {ex}")

	raise se.MissingDependencyException("Couldn’t start [command]chrome[/] or [command]firefox[/].")
