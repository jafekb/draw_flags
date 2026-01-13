"""
Collector for national flags - scrapes from Wikipedia.
"""

from typing import List

from backend.common.flag_data import Flag
from backend.scripts.data_collection.wikipedia_scraper import WikipediaScraper


class NationalFlagCollector(WikipediaScraper):
    """Collects national flags from Wikipedia."""

    # Wikipedia pages containing national flags
    NATIONAL_FLAG_SOURCES = [
        "Gallery_of_sovereign_state_flags",
        "Flags_of_sovereign_states",
    ]

    # List of UN member states and widely recognized countries
    # This ensures we get all major countries even if gallery/list parsing has issues
    COUNTRY_PAGES = [
        # UN Member States (193 countries)
        "Afghanistan",
        "Albania",
        "Algeria",
        "Andorra",
        "Angola",
        "Antigua_and_Barbuda",
        "Argentina",
        "Armenia",
        "Australia",
        "Austria",
        "Azerbaijan",
        "Bahamas",
        "Bahrain",
        "Bangladesh",
        "Barbados",
        "Belarus",
        "Belgium",
        "Belize",
        "Benin",
        "Bhutan",
        "Bolivia",
        "Bosnia_and_Herzegovina",
        "Botswana",
        "Brazil",
        "Brunei",
        "Bulgaria",
        "Burkina_Faso",
        "Burundi",
        "Cabo_Verde",
        "Cambodia",
        "Cameroon",
        "Canada",
        "Central_African_Republic",
        "Chad",
        "Chile",
        "China",
        "Colombia",
        "Comoros",
        "Democratic_Republic_of_the_Congo",
        "Republic_of_the_Congo",
        "Costa_Rica",
        "Croatia",
        "Cuba",
        "Cyprus",
        "Czech_Republic",
        "Denmark",
        "Djibouti",
        "Dominica",
        "Dominican_Republic",
        "Ecuador",
        "Egypt",
        "El_Salvador",
        "Equatorial_Guinea",
        "Eritrea",
        "Estonia",
        "Eswatini",
        "Ethiopia",
        "Fiji",
        "Finland",
        "France",
        "Gabon",
        "Gambia",
        "Georgia_(country)",
        "Germany",
        "Ghana",
        "Greece",
        "Grenada",
        "Guatemala",
        "Guinea",
        "Guinea-Bissau",
        "Guyana",
        "Haiti",
        "Honduras",
        "Hungary",
        "Iceland",
        "India",
        "Indonesia",
        "Iran",
        "Iraq",
        "Republic_of_Ireland",
        "Israel",
        "Italy",
        "Ivory_Coast",
        "Jamaica",
        "Japan",
        "Jordan",
        "Kazakhstan",
        "Kenya",
        "Kiribati",
        "North_Korea",
        "South_Korea",
        "Kuwait",
        "Kyrgyzstan",
        "Laos",
        "Latvia",
        "Lebanon",
        "Lesotho",
        "Liberia",
        "Libya",
        "Liechtenstein",
        "Lithuania",
        "Luxembourg",
        "Madagascar",
        "Malawi",
        "Malaysia",
        "Maldives",
        "Mali",
        "Malta",
        "Marshall_Islands",
        "Mauritania",
        "Mauritius",
        "Mexico",
        "Federated_States_of_Micronesia",
        "Moldova",
        "Monaco",
        "Mongolia",
        "Montenegro",
        "Morocco",
        "Mozambique",
        "Myanmar",
        "Namibia",
        "Nauru",
        "Nepal",
        "Netherlands",
        "New_Zealand",
        "Nicaragua",
        "Niger",
        "Nigeria",
        "North_Macedonia",
        "Norway",
        "Oman",
        "Pakistan",
        "Palau",
        "Panama",
        "Papua_New_Guinea",
        "Paraguay",
        "Peru",
        "Philippines",
        "Poland",
        "Portugal",
        "Qatar",
        "Romania",
        "Russia",
        "Rwanda",
        "Saint_Kitts_and_Nevis",
        "Saint_Lucia",
        "Saint_Vincent_and_the_Grenadines",
        "Samoa",
        "San_Marino",
        "Sao_Tome_and_Principe",
        "Saudi_Arabia",
        "Senegal",
        "Serbia",
        "Seychelles",
        "Sierra_Leone",
        "Singapore",
        "Slovakia",
        "Slovenia",
        "Solomon_Islands",
        "Somalia",
        "South_Africa",
        "South_Sudan",
        "Spain",
        "Sri_Lanka",
        "Sudan",
        "Suriname",
        "Sweden",
        "Switzerland",
        "Syria",
        "Tajikistan",
        "Tanzania",
        "Thailand",
        "Timor-Leste",
        "Togo",
        "Tonga",
        "Trinidad_and_Tobago",
        "Tunisia",
        "Turkey",
        "Turkmenistan",
        "Tuvalu",
        "Uganda",
        "Ukraine",
        "United_Arab_Emirates",
        "United_Kingdom",
        "United_States",
        "Uruguay",
        "Uzbekistan",
        "Vanuatu",
        "Vatican_City",
        "Venezuela",
        "Vietnam",
        "Yemen",
        "Zambia",
        "Zimbabwe",
        # Additional widely recognized entities
        "Taiwan",  # Republic of China
        "Kosovo",
        "Palestine",
    ]

    def collect(self) -> List[Flag]:
        """
        Collect national flags from Wikipedia.

        Returns:
            List of Flag objects
        """
        print("Starting national flag collection from Wikipedia...")

        # Track which countries we attempted and which failed
        self.attempted_countries = []
        self.failed_countries = []

        # Method 1: Collect from gallery/list pages
        for page in self.NATIONAL_FLAG_SOURCES:
            print(f"\nCollecting from page: {page}")
            self._collect_from_list_page(page)

        # Method 2: Collect from individual country pages
        # This ensures we get all countries even if gallery parsing has issues
        print("\nCollecting from individual country pages...")
        print(f"  Processing {len(self.COUNTRY_PAGES)} countries...")

        collected_names = {flag.name.lower() for flag in self.collected_flags}
        new_count = 0

        for i, country in enumerate(self.COUNTRY_PAGES):
            # Track that we attempted this country
            self.attempted_countries.append(country)

            # Check if we already have this country
            country_name = country.replace("_", " ")
            if country_name.lower() in collected_names:
                continue

            # Collect from country page
            if self._collect_from_country_page(country):
                new_count += 1
                collected_names.add(country_name.lower())
            else:
                # Track failed country
                self.failed_countries.append(country)

            # Progress update every 50 countries
            if (i + 1) % 50 == 0:
                print(
                    f"  Progress: {i + 1}/{len(self.COUNTRY_PAGES)} countries checked, {new_count} new flags added"
                )

        print(f"  Collected {new_count} additional flags from country pages")

        if self.failed_countries:
            print(f"  Failed to collect: {len(self.failed_countries)} countries")
            print(f"  Failed countries: {', '.join(self.failed_countries[:10])}")
            if len(self.failed_countries) > 10:
                print(f"  ... and {len(self.failed_countries) - 10} more")

        self.print_stats()
        return self.collected_flags

    def _collect_from_list_page(self, page_title: str):
        """
        Collect flags from a Wikipedia list or gallery page.

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
                verification_method="table",
            )

            if flag:
                self.collected_flags.append(flag)

        print(f"  Collected {len(flag_data_list)} flags")

    def _collect_from_country_page(self, page_title: str) -> bool:
        """
        Collect flag from a country's Wikipedia page.

        Args:
            page_title: Wikipedia page title (country name)

        Returns:
            True if flag was collected
        """
        soup = self.get_page_html(page_title)
        if not soup:
            return False

        # Extract flag from infobox
        flag_data = self.extract_flag_from_infobox(soup, page_title)

        if flag_data:
            # Clean up name
            name = page_title.replace("_", " ")

            flag = self.create_flag(
                name=name,
                wikipedia_page=page_title,
                wikipedia_url=flag_data["page_url"],
                wikipedia_image_url=flag_data["image_url"],
                verification_method="table",
            )

            if flag:
                self.collected_flags.append(flag)
                return True

        return False
