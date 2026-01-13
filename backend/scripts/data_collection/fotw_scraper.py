"""
FOTW (Flags of the World) website scraper.
"""

import re
from typing import List, Optional
from urllib.parse import urljoin

from backend.common.flag_data import Flag
from backend.scripts.data_collection.base_scraper import BaseScraper


class FOTWScraper(BaseScraper):
    """Scraper for the Flags of the World (FOTW) website."""

    FOTW_BASE = "https://www.crwflags.com/fotw/flags/"

    def __init__(self, rate_limit_seconds: float = 2.0):
        super().__init__(rate_limit_seconds)

    def collect(self) -> List[Flag]:
        """
        Collect flags from FOTW.
        This is a basic implementation - can be extended.

        Returns:
            List of Flag objects
        """
        print("Starting FOTW flag collection...")

        # For now, we'll focus on collecting from specific FOTW categories
        # The full FOTW site has 89,000+ pages which would take too long
        # We'll collect a representative sample

        categories = [
            "mil.html",  # Military flags
            "nav.html",  # Naval ensigns
            "pol.html",  # Political flags
            "spo.html",  # Sports flags
        ]

        for category in categories:
            print(f"\nCollecting from FOTW category: {category}")
            self._collect_from_category(category)

        self.print_stats()
        return self.collected_flags

    def _collect_from_category(self, category_page: str):
        """
        Collect flags from a FOTW category page.

        Args:
            category_page: Category page filename
        """
        url = urljoin(self.FOTW_BASE, category_page)
        response = self._get_with_retry(url)

        if not response:
            return

        soup = self._parse_html(response)
        if not soup:
            return

        # FOTW pages have a specific structure
        # Look for links to flag pages
        links = soup.find_all("a", href=True)

        count = 0
        for link in links:
            href = link.get("href")
            if not href or not href.endswith(".html"):
                continue

            # Skip navigation links
            if href in ["index.html", "../index.html", "flags.html"]:
                continue

            # Get flag page
            flag_url = urljoin(url, href)
            flag = self._extract_flag_from_page(flag_url)

            if flag:
                self.collected_flags.append(flag)
                count += 1

            # Limit to avoid overwhelming FOTW servers
            if count >= 100:
                break

        print(f"  Collected {count} flags from {category_page}")

    def _extract_flag_from_page(self, url: str) -> Optional[Flag]:
        """
        Extract flag information from a FOTW flag page.

        Args:
            url: URL of the flag page

        Returns:
            Flag object or None
        """
        response = self._get_with_retry(url)
        if not response:
            return None

        soup = self._parse_html(response)
        if not soup:
            return None

        # Extract name from title or heading
        title = soup.find("title")
        if title:
            name = title.get_text().strip()
            # Clean up common FOTW title patterns
            name = re.sub(r"\s*\[.*?\]", "", name)  # Remove [country codes]
            name = re.sub(r"\s*\(FOTW\)", "", name)
            name = name.strip()
        else:
            # Fallback to URL
            name = url.split("/")[-1].replace(".html", "").replace("_", " ")

        # Look for flag images
        images = soup.find_all("img")
        flag_image = None

        for img in images:
            src = img.get("src", "")
            alt = img.get("alt", "").lower()

            # Look for images that are likely flags
            if "flag" in alt or "/flags/" in src:
                # Convert relative URL to absolute
                flag_image = urljoin(url, src)
                break

        if not flag_image:
            return None

        # For FOTW, we'll use the FOTW page as the "wikipedia_url" equivalent
        flag = self.create_flag(
            name=name,
            wikipedia_page=name,
            wikipedia_url=url,
            wikipedia_image_url=flag_image,
            verification_method="check_options",
        )

        return flag
