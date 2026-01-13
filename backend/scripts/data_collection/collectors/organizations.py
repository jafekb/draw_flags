"""
Collector for international organization flags.
"""

from typing import List

from backend.common.flag_data import Flag
from backend.scripts.data_collection.wikipedia_scraper import WikipediaScraper


class OrganizationFlagCollector(WikipediaScraper):
    """Collects flags from international organizations."""

    # Wikipedia pages containing organization flags
    ORGANIZATION_SOURCES = [
        "Flags_of_international_organizations",
        "List_of_flags_of_the_United_Nations",
        "List_of_flags_of_the_European_Union",
        "Flags_of_NATO",
        "Flags_of_the_Olympic_Movement",
    ]

    # Specific organizations to collect
    SPECIFIC_ORGANIZATIONS = [
        # Major UN organizations
        "United_Nations",
        "UNESCO",
        "UNICEF",
        "World_Health_Organization",
        "International_Monetary_Fund",
        "World_Bank",
        "International_Labour_Organization",
        "Food_and_Agriculture_Organization",
        "World_Trade_Organization",
        # Regional organizations
        "European_Union",
        "African_Union",
        "ASEAN",
        "Arab_League",
        "Organization_of_American_States",
        "Commonwealth_of_Nations",
        "Caribbean_Community",
        "Pacific_Islands_Forum",
        "South_Asian_Association_for_Regional_Cooperation",
        "Eurasian_Economic_Union",
        # Military alliances
        "NATO",
        "Collective_Security_Treaty_Organization",
        # Economic organizations
        "European_Free_Trade_Association",
        "Organization_of_the_Petroleum_Exporting_Countries",
        "World_Customs_Organization",
        "Asia-Pacific_Economic_Cooperation",
        "G20",
        "BRICS",
        # Sports organizations
        "International_Olympic_Committee",
        "FIFA",
        "Union_of_European_Football_Associations",
        "International_Cricket_Council",
        "International_Basketball_Federation",
        # Humanitarian organizations
        "International_Committee_of_the_Red_Cross",
        "International_Red_Cross_and_Red_Crescent_Movement",
        # Other important organizations
        "Organisation_for_Economic_Co-operation_and_Development",
        "Council_of_Europe",
        "Organization_for_Security_and_Co-operation_in_Europe",
        "International_Criminal_Court",
        "Interpol",
        "World_Intellectual_Property_Organization",
    ]

    def collect(self) -> List[Flag]:
        """
        Collect organization flags from Wikipedia.

        Returns:
            List of Flag objects
        """
        print("Starting organization flag collection...")

        # Collect from list pages
        for page in self.ORGANIZATION_SOURCES:
            print(f"\nCollecting from page: {page}")
            self._collect_from_list_page(page)

        # Collect from specific organization pages
        print("\nCollecting from specific organization pages...")
        for org in self.SPECIFIC_ORGANIZATIONS:
            self._collect_from_organization_page(org)

        self.print_stats()
        return self.collected_flags

    def _collect_from_list_page(self, page_title: str):
        """
        Collect flags from a list page.

        Args:
            page_title: Wikipedia page title
        """
        soup = self.get_page_html(page_title)
        if not soup:
            return

        # Try tables first
        flag_data_list = self.extract_flags_from_table(soup)

        # Try gallery
        if not flag_data_list:
            flag_data_list = self.extract_flags_from_gallery(soup)

        # Create Flag objects
        for flag_data in flag_data_list:
            flag = self.create_flag(
                name=flag_data["name"],
                wikipedia_page=flag_data["page_title"],
                wikipedia_url=flag_data["page_url"],
                wikipedia_image_url=flag_data["image_url"],
                category="organization",
                entity_type="organization",
                country=None,
            )

            if flag:
                self.collected_flags.append(flag)

        print(f"  Collected {len(flag_data_list)} flags")

    def _collect_from_organization_page(self, page_title: str):
        """
        Collect flag from an organization's main Wikipedia page.

        Args:
            page_title: Wikipedia page title
        """
        soup = self.get_page_html(page_title)
        if not soup:
            return

        # Extract flag from infobox
        flag_data = self.extract_flag_from_infobox(soup, page_title)

        if flag_data:
            # Clean up name (remove underscores)
            name = page_title.replace("_", " ")

            flag = self.create_flag(
                name=name,
                wikipedia_page=page_title,
                wikipedia_url=flag_data["page_url"],
                wikipedia_image_url=flag_data["image_url"],
                category="organization",
                entity_type="organization",
                country=None,
            )

            if flag:
                self.collected_flags.append(flag)
                print(f"  Collected flag for: {name}")
