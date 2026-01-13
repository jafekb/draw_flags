"""
Collector for national flags - reuses existing data and adds missing countries.
"""

import json
from pathlib import Path
from typing import List

from backend.common.flag_data import Flag
from backend.scripts.data_collection.wikipedia_scraper import WikipediaScraper


class NationalFlagCollector(WikipediaScraper):
    """Collects national flags, starting with existing dataset."""
    
    EXISTING_FLAGS_FILE = Path("backend/data/national_flags/flags.json")
    
    def collect(self) -> List[Flag]:
        """
        Collect national flags, starting with existing dataset.
        
        Returns:
            List of Flag objects
        """
        print("Starting national flag collection...")
        
        # Load existing flags
        if self.EXISTING_FLAGS_FILE.exists():
            print(f"Loading existing flags from {self.EXISTING_FLAGS_FILE}")
            with self.EXISTING_FLAGS_FILE.open() as f:
                data = json.load(f)
                for flag_data in data['flags']:
                    flag = Flag(**flag_data)
                    self.collected_flags.append(flag)
            print(f"  Loaded {len(self.collected_flags)} existing national flags")
        
        # Optionally collect additional nations/territories from Wikipedia
        # We can add this if needed
        
        self.print_stats()
        return self.collected_flags

