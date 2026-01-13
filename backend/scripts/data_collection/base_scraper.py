"""
Base scraper class with common functionality for all flag data collectors.
"""

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from backend.common.flag_data import Flag


class BaseScraper(ABC):
    """Base class for all scrapers with rate limiting and error handling."""

    def __init__(self, rate_limit_seconds: float = 2.0):
        """
        Initialize the base scraper.

        Args:
            rate_limit_seconds: Minimum seconds between requests (default 2.0)
        """
        self.rate_limit_seconds = rate_limit_seconds
        self._last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "DrawFlags/1.0 (https://github.com/jafekb/draw_flags/; jafek91@gmail.com)"
            }
        )
        self.collected_flags: List[Flag] = []
        self.errors: List[Dict[str, str]] = []

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_time = time.time()

    def _get_with_retry(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """
        Make a GET request with retry logic.

        Args:
            url: URL to request
            max_retries: Maximum number of retry attempts

        Returns:
            Response object or None if all retries failed
        """
        self._rate_limit()

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    self.errors.append({"url": url, "error": str(e), "type": "request_failed"})
                    print(f"Failed to fetch {url} after {max_retries} attempts: {e}")
                    return None
                time.sleep(2**attempt)  # Exponential backoff

        return None

    def _parse_html(self, response: requests.Response) -> Optional[BeautifulSoup]:
        """
        Parse HTML response into BeautifulSoup object.

        Args:
            response: Response object with HTML content

        Returns:
            BeautifulSoup object or None if parsing failed
        """
        try:
            return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            self.errors.append({"url": response.url, "error": str(e), "type": "parse_failed"})
            print(f"Failed to parse HTML from {response.url}: {e}")
            return None

    def _resolve_image_url(self, base_url: str, image_url: str) -> str:
        """
        Resolve relative image URLs to absolute URLs.

        Args:
            base_url: Base URL of the page
            image_url: Image URL (may be relative or absolute)

        Returns:
            Absolute image URL
        """
        if image_url.startswith("http"):
            return image_url
        return urljoin(base_url, image_url)

    def _is_valid_flag_image_url(self, url: str) -> bool:
        """
        Check if URL looks like a valid flag image.

        Args:
            url: Image URL to validate

        Returns:
            True if URL appears valid
        """
        if not url:
            return False

        # Check for valid image extensions
        valid_extensions = (
            ".svg",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".SVG",
            ".PNG",
            ".JPG",
            ".JPEG",
            ".GIF",
        )
        parsed = urlparse(url)
        path = parsed.path.lower()

        return any(path.endswith(ext.lower()) for ext in valid_extensions)

    def create_flag(
        self,
        name: str,
        wikipedia_page: str,
        wikipedia_url: str,
        wikipedia_image_url: str,
        category: str,
        entity_type: str,
        country: Optional[str] = None,
        adoption_year: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Flag]:
        """
        Create a Flag object with validation.

        Args:
            name: Name of the flag/location
            wikipedia_page: Wikipedia page title
            wikipedia_url: Full Wikipedia URL
            wikipedia_image_url: URL to flag image
            category: Flag category (national, subdivision, city, organization, historical, fotw)
            entity_type: Entity type (country, state, province, territory, city, organization, historical)
            country: Parent country (for subdivisions/cities)
            adoption_year: Year flag was adopted
            tags: List of searchable tags

        Returns:
            Flag object or None if validation failed
        """
        try:
            # Basic validation
            if not name or not wikipedia_image_url:
                self.errors.append(
                    {"name": name, "error": "Missing required fields", "type": "validation_failed"}
                )
                return None

            if not self._is_valid_flag_image_url(wikipedia_image_url):
                self.errors.append(
                    {
                        "name": name,
                        "url": wikipedia_image_url,
                        "error": "Invalid image URL",
                        "type": "validation_failed",
                    }
                )
                return None

            # Generate basic tags if not provided
            if tags is None:
                tags = self._generate_basic_tags(name, category, entity_type, country)

            flag = Flag(
                name=name,
                wikipedia_page=wikipedia_page,
                wikipedia_url=wikipedia_url,
                wikipedia_image_url=wikipedia_image_url,
                category=category,
                entity_type=entity_type,
                country=country,
                adoption_year=adoption_year,
                tags=tags,
            )

            return flag

        except Exception as e:
            self.errors.append({"name": name, "error": str(e), "type": "creation_failed"})
            print(f"Failed to create flag for {name}: {e}")
            return None
    
    def _generate_basic_tags(
        self, name: str, category: str, entity_type: str, country: Optional[str]
    ) -> List[str]:
        """Generate basic tags for a flag."""
        tags = [category]
        if entity_type != category:
            tags.append(entity_type)
        
        if country:
            tags.append(country.lower())
        
        # Parse name for keywords - keep multi-word names together
        name_clean = name.lower().replace("flag of ", "").replace("the ", "")
        
        # Split by comma to separate location from country/region
        parts = [p.strip() for p in name_clean.split(',')]
        
        # Add the main location name (before first comma) as a complete tag
        if parts:
            location_name = parts[0].strip()
            if location_name and location_name not in ['flag', 'the']:
                tags.append(location_name)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags

    @abstractmethod
    def collect(self) -> List[Flag]:
        """
        Collect flags from the data source.
        Must be implemented by subclasses.

        Returns:
            List of collected Flag objects
        """

    def save_progress(self, output_file: Path):
        """
        Save collected flags to a JSON file.

        Args:
            output_file: Path to save the flags
        """
        if not self.collected_flags:
            print(f"No flags collected yet for {self.__class__.__name__}")
            return

        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Save as simple list for now
        import json

        data = [flag.model_dump() for flag in self.collected_flags]
        with output_file.open("w") as f:
            json.dump(data, f, indent=2)

        print(f"Saved {len(self.collected_flags)} flags to {output_file}")

    def print_stats(self):
        """Print collection statistics."""
        print(f"\n{self.__class__.__name__} Statistics:")
        print(f"  Flags collected: {len(self.collected_flags)}")
        print(f"  Errors encountered: {len(self.errors)}")

        if self.errors:
            error_types = {}
            for error in self.errors:
                error_type = error.get("type", "unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1

            print("  Error breakdown:")
            for error_type, count in error_types.items():
                print(f"    {error_type}: {count}")
