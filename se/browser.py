#!/usr/bin/env python3
"""
Defines functions for interacting with headless browser sessions.
"""

import os
import shutil
from pathlib import Path
import importlib_resources

from selenium import webdriver
from selenium.common.exceptions import WebDriverException


import se

def initialize_selenium_firefox_webdriver() -> webdriver.firefox.webdriver.WebDriver:
	"""
	Initialize a Selenium Firefox driver and return it for use in other applications.

	INPUTS
	None.

	RETURNS
	A Selenium webdriver for Firefox.
	"""

	if not shutil.which("firefox") and not Path("/Applications/Firefox.app/Contents/MacOS/firefox").exists():
		raise se.MissingDependencyException("Couldn’t locate [bash]firefox[/]. Is it installed?")

	# Initialize the selenium driver to take screenshots

	# We have to use the headless option, otherwise it will pop up a Firefox window
	options = webdriver.FirefoxOptions()
	options.headless = True

	# Disable the history, because otherwise links to (for example to end notes) may appear as "visited" in visits to other pages, and thus cause a fake diff
	profile = webdriver.FirefoxProfile()
	profile.set_preference("places.history.enabled", False)
	profile.set_preference("browser.cache.disk.enable", False)
	profile.set_preference("browser.cache.memory.enable", False)
	profile.set_preference("browser.cache.offline.enable", False)
	profile.set_preference("browser.http.use-cache", False)
	profile.set_preference("layout.css.devPixelsPerPx", "2.0")

	try:
		with importlib_resources.path("se.data.geckodriver", "geckodriver") as geckodriver_path:
			driver = webdriver.Firefox(firefox_profile=profile, options=options, service_log_path=os.devnull, executable_path=geckodriver_path)
	except WebDriverException as ex:
		raise se.MissingDependencyException("Selenium Firefox web driver is not installed. To install it on Linux, download the appropriate zip file from [url][link=https://github.com/mozilla/geckodriver/releases/latest]https://github.com/mozilla/geckodriver/releases/latest[/][/] and place the [bash]geckodriver[/] executable in your [path]$PATH[/] (for example, in [path]~/.local/bin/[/] or [path]/usr/local/bin/[/]). To install it on macOS, run [bash]brew install geckodriver[/].") from ex

	return driver
