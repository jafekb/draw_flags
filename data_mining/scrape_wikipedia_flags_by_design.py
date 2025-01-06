#!/usr/bin/python
"""
https://commons.wikimedia.org/wiki/Gallery_of_flags_by_design

This makes finding the chromedriver way easier:
python -m pip install chromedriver-binary==126.0.6478.126
"""
import time

from selenium import webdriver
import chromedriver_binary  # Adds chromedriver binary to path

driver = webdriver.Chrome()
driver.get("https://commons.wikimedia.org/wiki/Gallery_of_flags_by_design")

time.sleep(5)
