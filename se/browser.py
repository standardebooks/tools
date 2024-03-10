#!/usr/bin/env python3
"""
Defines functions for interacting with headless browser sessions.
"""

import os
import platform
import shutil
from pathlib import Path

from selenium import webdriver

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

	possible_system_geckodriver = shutil.which("geckodriver")

	if platform.system() == "Linux":
		geckodriver_path = Path("se.data.geckodriver", "geckodriver-linux64")
	elif platform.system() == "Windows":
		geckodriver_path = Path("se.data.geckodriver", "geckodriver-win64.exe")
	elif platform.system() == "Darwin":
		if platform.machine() == "arm64":
			geckodriver_path = Path("se.data.geckodriver", "geckodriver-macos-aarch64")
		else:
			geckodriver_path = Path("se.data.geckodriver", "geckodriver-macos")
	elif possible_system_geckodriver is not None:
		geckodriver_path = Path(possible_system_geckodriver)
	else:
		raise se.MissingDependencyException("Selenium Firefox web driver is not installed. To install it on Linux or Windows, download the appropriate zip file from [url][link=https://github.com/mozilla/geckodriver/releases/latest]https://github.com/mozilla/geckodriver/releases/latest[/][/] and place the [bash]geckodriver[/] executable in your [path]$PATH[/] (for example, in [path]~/.local/bin/[/] or [path]/usr/local/bin/[/]). To install it on macOS, run [bash]brew install geckodriver[/].")

	return webdriver.Firefox(firefox_profile=profile, options=options, service_log_path=os.devnull, executable_path=geckodriver_path)
