"""
Collector for historical flags.
"""

from typing import List

from backend.common.flag_data import Flag
from backend.scripts.data_collection.wikipedia_scraper import WikipediaScraper


class HistoricalFlagCollector(WikipediaScraper):
    """Collects historical flags from various sources."""

    # Wikipedia pages with historical flags
    HISTORICAL_SOURCES = [
        "Gallery_of_sovereign_state_flags",
        "Timeline_of_national_flags",
        "List_of_former_sovereign_states",
        "List_of_proposed_state_mergers",
    ]

    # Former countries and entities
    FORMER_COUNTRIES = [
        # Soviet Union and related
        "Soviet_Union",
        "Russian_Soviet_Federative_Socialist_Republic",
        "Ukrainian_Soviet_Socialist_Republic",
        "Byelorussian_Soviet_Socialist_Republic",
        "Uzbek_Soviet_Socialist_Republic",
        "Kazakh_Soviet_Socialist_Republic",
        "Georgian_Soviet_Socialist_Republic",
        "Azerbaijan_Soviet_Socialist_Republic",
        "Lithuanian_Soviet_Socialist_Republic",
        "Moldavian_Soviet_Socialist_Republic",
        "Latvian_Soviet_Socialist_Republic",
        "Kirghiz_Soviet_Socialist_Republic",
        "Tajik_Soviet_Socialist_Republic",
        "Armenian_Soviet_Socialist_Republic",
        "Turkmen_Soviet_Socialist_Republic",
        "Estonian_Soviet_Socialist_Republic",
        # Yugoslavia and successor states
        "Socialist_Federal_Republic_of_Yugoslavia",
        "Kingdom_of_Yugoslavia",
        "Serbia_and_Montenegro",
        # Germany
        "East_Germany",
        "West_Germany",
        "Nazi_Germany",
        "Weimar_Republic",
        "German_Empire",
        # European former states
        "Czechoslovakia",
        "Austria-Hungary",
        "Ottoman_Empire",
        # Asian former states
        "Republic_of_China_(1912–1949)",
        "Empire_of_Japan",
        "Manchukuo",
        "South_Vietnam",
        "North_Vietnam",
        "Democratic_Kampuchea",
        "South_Yemen",
        "North_Yemen",
        # African former states
        "Rhodesia",
        "South_West_Africa",
        "Tanganyika",
        "Zanzibar",
        # American former states
        "Confederate_States_of_America",
        "Republic_of_Texas",
        "California_Republic",
        # Middle Eastern former states
        "United_Arab_Republic",
        "Kingdom_of_Iraq",
        "Kingdom_of_Egypt",
        # Colonial flags
        "British_Raj",
        "French_Algeria",
        "Portuguese_Angola",
        "Portuguese_Mozambique",
        "Belgian_Congo",
        "French_Indochina",
    ]

    def collect(self) -> List[Flag]:
        """
        Collect historical flags.

        Returns:
            List of Flag objects
        """
        print("Starting historical flag collection...")

        # Collect from list pages
        for page in self.HISTORICAL_SOURCES:
            print(f"\nCollecting from page: {page}")
            self._collect_from_page(page)

        # Collect from specific former country pages
        print("\nCollecting from former country pages...")
        for country in self.FORMER_COUNTRIES:
            self._collect_from_country_page(country)

        self.print_stats()
        return self.collected_flags

    def _collect_from_page(self, page_title: str):
        """
        Collect flags from a list page.

        Args:
            page_title: Wikipedia page title
        """
        soup = self.get_page_html(page_title)
        if not soup:
            return

        # Try tables
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
                category="historical",
                entity_type="historical",
                country=None,
            )

            if flag:
                self.collected_flags.append(flag)

        print(f"  Collected {len(flag_data_list)} flags")

    def _collect_from_country_page(self, page_title: str):
        """
        Collect flag from a former country's Wikipedia page.

        Args:
            page_title: Wikipedia page title
        """
        soup = self.get_page_html(page_title)
        if not soup:
            return

        # Extract flag from infobox
        flag_data = self.extract_flag_from_infobox(soup, page_title)

        if flag_data:
            # Clean up name
            name = page_title.replace("_", " ")
            # Add "(historical)" to distinguish from current countries
            if "historical" not in name.lower() and "former" not in name.lower():
                name = f"{name} (historical)"

            flag = self.create_flag(
                name=name,
                wikipedia_page=page_title,
                wikipedia_url=flag_data["page_url"],
                wikipedia_image_url=flag_data["image_url"],
                category="historical",
                entity_type="historical",
                country=None,
            )

            if flag:
                self.collected_flags.append(flag)
                print(f"  Collected flag for: {name}")
