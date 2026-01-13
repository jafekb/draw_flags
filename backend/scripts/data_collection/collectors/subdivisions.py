"""
Collector for country subdivision flags (states, provinces, territories, etc.)
"""

from typing import List

from backend.common.flag_data import Flag
from backend.scripts.data_collection.wikipedia_scraper import WikipediaScraper


class SubdivisionFlagCollector(WikipediaScraper):
    """Collects flags from country subdivisions."""
    
    # Define subdivision sources with their Wikipedia pages and parsing config
    SUBDIVISION_SOURCES = [
        # United States
        {
            'page': 'Flags_of_the_U.S._states_and_territories',
            'country': 'United States',
            'subdivision_type': 'state/territory'
        },
        # Canada
        {
            'page': 'List_of_Canadian_flags',
            'country': 'Canada',
            'subdivision_type': 'province/territory'
        },
        # Australia
        {
            'page': 'List_of_Australian_flags',
            'country': 'Australia',
            'subdivision_type': 'state/territory'
        },
        # Germany
        {
            'page': 'Flags_of_German_states',
            'country': 'Germany',
            'subdivision_type': 'state'
        },
        # Russia
        {
            'page': 'Flags_of_the_federal_subjects_of_Russia',
            'country': 'Russia',
            'subdivision_type': 'federal subject'
        },
        # India
        {
            'page': 'List_of_Indian_flags',
            'country': 'India',
            'subdivision_type': 'state/territory'
        },
        # Mexico
        {
            'page': 'Flags_of_the_states_of_Mexico',
            'country': 'Mexico',
            'subdivision_type': 'state'
        },
        # Brazil
        {
            'page': 'Flags_of_Brazil',
            'country': 'Brazil',
            'subdivision_type': 'state'
        },
        # China
        {
            'page': 'Flags_of_China',
            'country': 'China',
            'subdivision_type': 'province/region'
        },
        # Japan
        {
            'page': 'List_of_Japanese_flags',
            'country': 'Japan',
            'subdivision_type': 'prefecture'
        },
        # Spain
        {
            'page': 'List_of_Spanish_flags',
            'country': 'Spain',
            'subdivision_type': 'autonomous community'
        },
        # Italy
        {
            'page': 'List_of_Italian_flags',
            'country': 'Italy',
            'subdivision_type': 'region'
        },
        # United Kingdom
        {
            'page': 'List_of_British_flags',
            'country': 'United Kingdom',
            'subdivision_type': 'constituent country/territory'
        },
        # France
        {
            'page': 'List_of_French_flags',
            'country': 'France',
            'subdivision_type': 'region'
        },
        # Argentina
        {
            'page': 'List_of_Argentine_flags',
            'country': 'Argentina',
            'subdivision_type': 'province'
        },
        # South Africa
        {
            'page': 'List_of_South_African_flags',
            'country': 'South Africa',
            'subdivision_type': 'province'
        },
        # Switzerland
        {
            'page': 'Flags_and_arms_of_cantons_of_Switzerland',
            'country': 'Switzerland',
            'subdivision_type': 'canton'
        },
        # Netherlands
        {
            'page': 'List_of_flags_of_the_Netherlands',
            'country': 'Netherlands',
            'subdivision_type': 'province'
        },
        # Belgium
        {
            'page': 'List_of_Belgian_flags',
            'country': 'Belgium',
            'subdivision_type': 'region/community'
        },
        # Austria
        {
            'page': 'List_of_Austrian_flags',
            'country': 'Austria',
            'subdivision_type': 'state'
        },
        # Poland
        {
            'page': 'List_of_Polish_flags',
            'country': 'Poland',
            'subdivision_type': 'voivodeship'
        },
        # Indonesia
        {
            'page': 'List_of_Indonesian_flags',
            'country': 'Indonesia',
            'subdivision_type': 'province'
        },
        # Malaysia
        {
            'page': 'List_of_Malaysian_flags',
            'country': 'Malaysia',
            'subdivision_type': 'state'
        },
        # Pakistan
        {
            'page': 'List_of_Pakistani_flags',
            'country': 'Pakistan',
            'subdivision_type': 'province/territory'
        },
        # Nigeria
        {
            'page': 'List_of_Nigerian_flags',
            'country': 'Nigeria',
            'subdivision_type': 'state'
        },
        # Ukraine
        {
            'page': 'List_of_flags_of_Ukraine',
            'country': 'Ukraine',
            'subdivision_type': 'oblast/region'
        },
    ]
    
    def collect(self) -> List[Flag]:
        """
        Collect subdivision flags from multiple countries.
        
        Returns:
            List of Flag objects
        """
        print("Starting subdivision flag collection...")
        
        for source in self.SUBDIVISION_SOURCES:
            print(f"\nCollecting flags for {source['country']} subdivisions...")
            self._collect_from_page(
                source['page'],
                source['country'],
                source['subdivision_type']
            )
        
        self.print_stats()
        return self.collected_flags
    
    def _collect_from_page(self, page_title: str, country: str, subdivision_type: str):
        """
        Collect flags from a specific Wikipedia page.
        
        Args:
            page_title: Wikipedia page title
            country: Country name
            subdivision_type: Type of subdivision
        """
        soup = self.get_page_html(page_title)
        if not soup:
            print(f"  Failed to load page: {page_title}")
            return
        
        # Try to extract from tables
        flag_data_list = self.extract_flags_from_table(soup)
        
        # If no table found or table empty, try gallery
        if not flag_data_list:
            flag_data_list = self.extract_flags_from_gallery(soup)
        
        # Create Flag objects
        for flag_data in flag_data_list:
            flag = self.create_flag(
                name=flag_data['name'],
                wikipedia_page=flag_data['page_title'],
                wikipedia_url=flag_data['page_url'],
                wikipedia_image_url=flag_data['image_url'],
                verification_method='table'
            )
            
            if flag:
                self.collected_flags.append(flag)
        
        print(f"  Collected {len(flag_data_list)} flags from {page_title}")

