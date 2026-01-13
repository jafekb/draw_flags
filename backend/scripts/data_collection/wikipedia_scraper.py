"""
Wikipedia scraper for extracting flag data from structured lists and tables.
"""

import re
from typing import Dict, List, Optional
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup, Tag

from backend.common.flag_data import Flag
from backend.scripts.data_collection.base_scraper import BaseScraper


class WikipediaScraper(BaseScraper):
    """Scraper for Wikipedia flag lists and infoboxes."""

    WIKIPEDIA_BASE = "https://en.wikipedia.org"
    WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

    def __init__(self, rate_limit_seconds: float = 2.0):
        super().__init__(rate_limit_seconds)

    def collect(self) -> List[Flag]:
        """
        Main collection method - to be overridden by specific collectors.
        """
        return self.collected_flags

    def get_page_html(self, page_title: str) -> Optional[BeautifulSoup]:
        """
        Get the HTML content of a Wikipedia page.

        Args:
            page_title: Wikipedia page title

        Returns:
            BeautifulSoup object or None
        """
        encoded_title = quote(page_title.replace(" ", "_"))
        url = f"{self.WIKIPEDIA_BASE}/wiki/{encoded_title}"

        response = self._get_with_retry(url)
        if response:
            return self._parse_html(response)
        return None

    def extract_flag_from_infobox(
        self, soup: BeautifulSoup, page_title: str
    ) -> Optional[Dict[str, str]]:
        """
        Extract flag information from a Wikipedia infobox.

        Args:
            soup: BeautifulSoup object of the page
            page_title: Page title for constructing URLs

        Returns:
            Dictionary with flag information or None
        """
        # Find infobox
        infobox = soup.find("table", class_=re.compile(r"infobox"))
        if not infobox:
            return None

        # Look for flag image in infobox
        flag_row = None
        for row in infobox.find_all("tr"):
            # Check if row contains "flag" in the label
            header = row.find("th")
            if header and "flag" in header.get_text().lower():
                flag_row = row
                break

            # Check for image with "flag" in alt text or filename
            img = row.find("img")
            if img:
                alt = img.get("alt", "").lower()
                src = img.get("src", "").lower()
                if "flag" in alt or "flag" in src:
                    flag_row = row
                    break

        # If no specific flag row, look for first image in infobox (often the flag)
        # But only if it looks like a flag
        if not flag_row:
            for row in infobox.find_all("tr"):
                img = row.find("img")
                if img and self._image_looks_like_flag(img):
                    flag_row = row
                    break

        if not flag_row:
            return None

        img = flag_row.find("img")
        if not img:
            return None

        # Extract image URL
        src = img.get("src", "")
        if src.startswith("//"):
            src = "https:" + src

        # Convert thumbnail to full resolution
        src = self._convert_to_full_image_url(src)

        # Final validation: make sure this looks like a flag image
        if not self._url_looks_like_flag(src):
            return None

        return {
            "image_url": src,
            "page_title": page_title,
            "page_url": f"{self.WIKIPEDIA_BASE}/wiki/{quote(page_title.replace(' ', '_'))}",
        }

    def _image_looks_like_flag(self, img: Tag) -> bool:
        """
        Check if an image element looks like it could be a flag.

        Args:
            img: BeautifulSoup img tag

        Returns:
            True if the image appears to be a flag
        """
        src = img.get("src", "").lower()
        alt = img.get("alt", "").lower()

        # Check for flag-related keywords in filename or alt text
        flag_keywords = ["flag", "coat_of_arms", "emblem", "ensign"]
        if any(keyword in src or keyword in alt for keyword in flag_keywords):
            return True

        # Prefer SVG files (almost always flags/symbols)
        if src.endswith(".svg"):
            return True

        # Reject obvious non-flags
        non_flag_keywords = [
            "map",
            "location",
            "photo",
            "image",
            "view",
            "city",
            "landscape",
            "building",
            "palace",
            "dome",
            "church",
            "temple",
            "mosque",
        ]
        if any(keyword in src or keyword in alt for keyword in non_flag_keywords):
            return False

        return False

    def _url_looks_like_flag(self, url: str) -> bool:
        """
        Check if a URL looks like it points to a flag image.

        Args:
            url: Image URL

        Returns:
            True if the URL appears to be a flag
        """
        url_lower = url.lower()

        # Strong positive indicators
        flag_indicators = ["flag", "coat_of_arms", "emblem", "ensign", "banner"]
        if any(indicator in url_lower for indicator in flag_indicators):
            return True

        # SVG files are almost always flags/symbols (not photos)
        if url_lower.endswith(".svg"):
            return True

        # Reject JPG/JPEG files unless they have "flag" in the name
        # (Photos of landmarks are usually JPG, flags are usually SVG or PNG)
        if url_lower.endswith((".jpg", ".jpeg")) and "flag" not in url_lower:
            return False

        # Reject obvious non-flags in filename
        non_flag_keywords = [
            "map",
            "location",
            "photo",
            "city",
            "landscape",
            "view",
            "building",
            "palace",
            "dome",
            "church",
            "temple",
            "mosque",
            "cathedral",
            "skyline",
            "panorama",
            "mountain",
            "river",
        ]
        if any(keyword in url_lower for keyword in non_flag_keywords):
            return False

        return False

    def _convert_to_full_image_url(self, thumbnail_url: str) -> str:
        """
        Convert Wikipedia thumbnail URL to full-resolution image URL.

        Args:
            thumbnail_url: Thumbnail image URL

        Returns:
            Full resolution image URL
        """
        # Wikipedia thumbnails have /thumb/ in path and end with /XXXpx-filename
        # Full URLs are in /wikipedia/commons/X/XX/filename format

        if "/thumb/" not in thumbnail_url:
            return thumbnail_url

        # Remove the thumbnail size suffix (e.g., /250px-Flag_of_X.svg.png)
        parts = thumbnail_url.split("/thumb/")
        if len(parts) != 2:
            return thumbnail_url

        # The path after /thumb/ is like: /9/9a/Flag_of_X.svg/250px-Flag_of_X.svg.png
        # We want: /9/9a/Flag_of_X.svg
        thumb_path = parts[1]
        path_parts = thumb_path.split("/")
        if len(path_parts) >= 3:
            # Reconstruct without the last part (size prefix)
            full_path = "/".join(path_parts[:-1])
            return parts[0] + "/" + full_path

        return thumbnail_url

    def extract_flags_from_table(
        self,
        soup: BeautifulSoup,
        table_selector: Optional[str] = None,
        name_column: int = 0,
        flag_column: int = 1,
    ) -> List[Dict[str, str]]:
        """
        Extract flag information from a Wikipedia table.

        Args:
            soup: BeautifulSoup object
            table_selector: CSS selector for the table (None for first wikitable)
            name_column: Column index containing the name
            flag_column: Column index containing the flag image

        Returns:
            List of dictionaries with flag information
        """
        flags = []

        # Find table
        if table_selector:
            table = soup.select_one(table_selector)
        else:
            table = soup.find("table", class_="wikitable")

        if not table:
            return flags

        rows = table.find_all("tr")
        for row in rows[1:]:  # Skip header row
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(name_column, flag_column):
                continue

            # Extract name
            name_cell = cells[name_column]
            name_link = name_cell.find("a")
            if name_link and name_link.get("href"):
                name = name_link.get_text().strip()
                href = name_link.get("href")
                if href.startswith("/wiki/"):
                    page_title = unquote(href.split("/wiki/")[1])
                else:
                    continue
            else:
                name = name_cell.get_text().strip()
                page_title = name

            if not name:
                continue

            # Extract flag image
            flag_cell = cells[flag_column]
            img = flag_cell.find("img")
            if not img:
                continue

            src = img.get("src", "")
            if src.startswith("//"):
                src = "https:" + src

            src = self._convert_to_full_image_url(src)

            flags.append(
                {
                    "name": name,
                    "image_url": src,
                    "page_title": page_title,
                    "page_url": f"{self.WIKIPEDIA_BASE}/wiki/{quote(page_title.replace(' ', '_'))}",
                }
            )

        return flags

    def extract_flags_from_gallery(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract flag information from a Wikipedia gallery.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of dictionaries with flag information
        """
        flags = []

        # Find gallery elements
        galleries = soup.find_all("ul", class_="gallery")

        for gallery in galleries:
            items = gallery.find_all("li", class_="gallerybox")

            for item in items:
                # Extract image
                img = item.find("img")
                if not img:
                    continue

                src = img.get("src", "")
                if src.startswith("//"):
                    src = "https:" + src
                src = self._convert_to_full_image_url(src)

                # Extract caption/name
                caption_div = item.find("div", class_="gallerytext")
                if caption_div:
                    # Look for link in caption
                    link = caption_div.find("a")
                    if link and link.get("href", "").startswith("/wiki/"):
                        name = link.get_text().strip()
                        page_title = unquote(link.get("href").split("/wiki/")[1])
                    else:
                        name = caption_div.get_text().strip()
                        page_title = name
                else:
                    # Try to extract from alt text
                    name = img.get("alt", "").replace("Flag of ", "").strip()
                    page_title = name

                if not name:
                    continue

                flags.append(
                    {
                        "name": name,
                        "image_url": src,
                        "page_title": page_title,
                        "page_url": f"{self.WIKIPEDIA_BASE}/wiki/{quote(page_title.replace(' ', '_'))}",
                    }
                )

        return flags

    def get_category_pages(self, category: str, limit: int = 500) -> List[str]:
        """
        Get list of page titles in a Wikipedia category using the API.

        Args:
            category: Category name (without "Category:" prefix)
            limit: Maximum number of pages to retrieve

        Returns:
            List of page titles
        """
        pages = []
        continue_token = None

        while len(pages) < limit:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": f"Category:{category}",
                "cmlimit": min(500, limit - len(pages)),
                "format": "json",
            }

            if continue_token:
                params["cmcontinue"] = continue_token

            self._rate_limit()
            response = self.session.get(self.WIKIPEDIA_API, params=params)

            if response.status_code != 200:
                break

            data = response.json()

            if "query" in data and "categorymembers" in data["query"]:
                for member in data["query"]["categorymembers"]:
                    pages.append(member["title"])

            # Check for continuation
            if "continue" in data and "cmcontinue" in data["continue"]:
                continue_token = data["continue"]["cmcontinue"]
            else:
                break

        return pages[:limit]
