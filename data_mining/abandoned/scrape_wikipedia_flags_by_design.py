#!/usr/bin/python
"""
https://commons.wikimedia.org/wiki/Gallery_of_flags_by_design

This makes finding the chromedriver way easier:
python -m pip install chromedriver-binary==126.0.6478.126
"""
import time

from selenium import webdriver
import chromedriver_binary  # Adds chromedriver binary to path
from selenium.webdriver.common.by import By


driver = webdriver.Chrome()
# TODO(bjafek) this one doesn't load fully unless you scroll down, how?
# driver.get("https://commons.wikimedia.org/wiki/Gallery_of_flags_by_design")
driver.get("https://en.wikipedia.org/wiki/List_of_flags_by_design")

# Find all elements with the given class and style attributes
gallery_boxes = driver.find_elements(
    By.XPATH,
    "//li[@class='gallerybox' and contains(@style, 'width: 185px')]",
)

# Print the number of elements found
print(f"Number of gallery boxes found: {len(gallery_boxes)}")

time.sleep(2)

# Iterate through the found elements
for box in gallery_boxes:
    # Perform actions on each element, e.g.,
    print(box.text)  # Print the text content of the element
    # box.click()  # Click on the element
    # time.sleep(2)

# Close the browser
driver.quit()
