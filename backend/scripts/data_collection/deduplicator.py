"""
Deduplication logic for merging flags from multiple sources.
"""

from difflib import SequenceMatcher
from typing import Dict, List, Tuple

from backend.common.flag_data import Flag


class FlagDeduplicator:
    """Deduplicates flags based on name and image URL similarity."""

    def __init__(self, name_similarity_threshold: float = 0.85):
        """
        Initialize deduplicator.

        Args:
            name_similarity_threshold: Minimum similarity score to consider names matching
        """
        self.name_similarity_threshold = name_similarity_threshold
        self.duplicates_found = 0
        self.duplicates_removed = 0

    def deduplicate(self, flags: List[Flag]) -> List[Flag]:
        """
        Remove duplicate flags from the list.

        Args:
            flags: List of Flag objects

        Returns:
            Deduplicated list of Flag objects
        """
        if not flags:
            return []

        print(f"Starting deduplication of {len(flags)} flags...")

        # Create index of flags by normalized name and image URL
        unique_flags: Dict[Tuple[str, str], Flag] = {}

        for flag in flags:
            # Normalize name and image URL for comparison
            norm_name = self._normalize_name(flag.name)
            norm_image = self._normalize_image_url(flag.wikipedia_image_url)

            key = (norm_name, norm_image)

            # Check for exact duplicates
            if key in unique_flags:
                self.duplicates_found += 1
                self.duplicates_removed += 1
                continue

            # Check for near-duplicates by name similarity
            is_duplicate = False
            for existing_key in unique_flags:
                existing_norm_name, existing_norm_image = existing_key

                # If images are the same, it's likely a duplicate
                if norm_image == existing_norm_image:
                    self.duplicates_found += 1
                    self.duplicates_removed += 1
                    is_duplicate = True
                    break

                # Check name similarity
                similarity = self._name_similarity(norm_name, existing_norm_name)
                if similarity >= self.name_similarity_threshold:
                    # Also check if images are similar
                    if self._images_likely_same(norm_image, existing_norm_image):
                        self.duplicates_found += 1
                        self.duplicates_removed += 1
                        is_duplicate = True
                        break

            if not is_duplicate:
                unique_flags[key] = flag

        result = list(unique_flags.values())

        print("Deduplication complete:")
        print(f"  Original count: {len(flags)}")
        print(f"  Duplicates found: {self.duplicates_found}")
        print(f"  Duplicates removed: {self.duplicates_removed}")
        print(f"  Final count: {len(result)}")

        return result

    def _normalize_name(self, name: str) -> str:
        """
        Normalize a flag name for comparison.

        Args:
            name: Flag name

        Returns:
            Normalized name
        """
        # Convert to lowercase
        name = name.lower()

        # Remove common prefixes/suffixes
        prefixes = ["flag of ", "flag of the ", "the "]
        for prefix in prefixes:
            name = name.removeprefix(prefix)

        # Remove special characters
        name = "".join(c for c in name if c.isalnum() or c.isspace())

        # Remove extra whitespace
        name = " ".join(name.split())

        return name

    def _normalize_image_url(self, url: str) -> str:
        """
        Normalize an image URL for comparison.

        Args:
            url: Image URL

        Returns:
            Normalized URL
        """
        # Extract filename from URL
        url = url.lower()

        # Remove URL parameters
        if "?" in url:
            url = url.split("?")[0]

        # Extract the actual filename (last part of path)
        parts = url.split("/")
        filename = parts[-1] if parts else url

        # Remove common variations
        filename = filename.replace("%20", " ")
        filename = filename.replace("_", " ")

        return filename

    def _name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two names.

        Args:
            name1: First name
            name2: Second name

        Returns:
            Similarity score between 0 and 1
        """
        return SequenceMatcher(None, name1, name2).ratio()

    def _images_likely_same(self, image1: str, image2: str) -> bool:
        """
        Check if two image URLs likely refer to the same image.

        Args:
            image1: First image URL
            image2: Second image URL

        Returns:
            True if images are likely the same
        """
        # Extract core filenames
        file1 = image1.split("/")[-1].split(".")[0]
        file2 = image2.split("/")[-1].split(".")[0]

        # Check if one contains the other (handles version suffixes, etc.)
        if file1 in file2 or file2 in file1:
            return True

        # Check similarity
        similarity = SequenceMatcher(None, file1, file2).ratio()
        return similarity > 0.9
