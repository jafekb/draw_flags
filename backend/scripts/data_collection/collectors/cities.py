"""
Collector for city and municipal flags.
"""

from typing import List

from backend.common.flag_data import Flag
from backend.scripts.data_collection.wikipedia_scraper import WikipediaScraper


class CityFlagCollector(WikipediaScraper):
    """Collects flags from major cities and municipalities."""
    
    # Wikipedia pages containing city flags
    CITY_FLAG_SOURCES = [
        'Flags_of_cities_of_the_United_States',
        'List_of_city_flags_in_Europe',
    ]
    
    # Major world cities to collect directly
    MAJOR_CITIES = [
        # United States (state capitals and major cities)
        'Montgomery,_Alabama', 'Juneau,_Alaska', 'Phoenix,_Arizona', 'Little_Rock,_Arkansas',
        'Sacramento,_California', 'Denver,_Colorado', 'Hartford,_Connecticut', 'Dover,_Delaware',
        'Tallahassee,_Florida', 'Atlanta', 'Honolulu', 'Boise,_Idaho',
        'Springfield,_Illinois', 'Indianapolis', 'Des_Moines,_Iowa', 'Topeka,_Kansas',
        'Frankfort,_Kentucky', 'Baton_Rouge,_Louisiana', 'Augusta,_Maine', 'Annapolis,_Maryland',
        'Boston', 'Lansing,_Michigan', 'Saint_Paul,_Minnesota', 'Jackson,_Mississippi',
        'Jefferson_City,_Missouri', 'Helena,_Montana', 'Lincoln,_Nebraska', 'Carson_City,_Nevada',
        'Concord,_New_Hampshire', 'Trenton,_New_Jersey', 'Santa_Fe,_New_Mexico', 'Albany,_New_York',
        'Raleigh,_North_Carolina', 'Bismarck,_North_Dakota', 'Columbus,_Ohio', 'Oklahoma_City',
        'Salem,_Oregon', 'Harrisburg,_Pennsylvania', 'Providence,_Rhode_Island', 'Columbia,_South_Carolina',
        'Pierre,_South_Dakota', 'Nashville,_Tennessee', 'Austin,_Texas', 'Salt_Lake_City',
        'Montpelier,_Vermont', 'Richmond,_Virginia', 'Olympia,_Washington', 'Charleston,_West_Virginia',
        'Madison,_Wisconsin', 'Cheyenne,_Wyoming',
        # Additional major US cities
        'New_York_City', 'Los_Angeles', 'Chicago', 'Houston', 'Philadelphia',
        'San_Antonio', 'San_Diego', 'Dallas', 'San_Jose,_California', 'Seattle',
        'Miami', 'Las_Vegas', 'Portland,_Oregon', 'San_Francisco', 'Detroit',
        
        # European capitals and major cities
        'London', 'Paris', 'Berlin', 'Madrid', 'Rome',
        'Amsterdam', 'Brussels', 'Vienna', 'Warsaw', 'Budapest',
        'Prague', 'Copenhagen', 'Stockholm', 'Helsinki', 'Oslo',
        'Dublin', 'Athens', 'Lisbon', 'Bucharest', 'Sofia',
        'Belgrade', 'Zagreb', 'Ljubljana', 'Bratislava', 'Vilnius',
        'Riga', 'Tallinn', 'Luxembourg_City', 'Monaco', 'Vaduz',
        'Reykjavik', 'Bern', 'Zurich', 'Geneva', 'Barcelona',
        'Munich', 'Hamburg', 'Cologne', 'Frankfurt', 'Stuttgart',
        'Milan', 'Naples', 'Turin', 'Florence', 'Venice',
        'Marseille', 'Lyon', 'Toulouse', 'Nice', 'Manchester',
        'Birmingham', 'Glasgow', 'Edinburgh', 'Liverpool', 'Leeds',
        
        # Asian major cities
        'Tokyo', 'Beijing', 'Shanghai', 'Hong_Kong', 'Singapore',
        'Seoul', 'Bangkok', 'Jakarta', 'Manila', 'Kuala_Lumpur',
        'Delhi', 'Mumbai', 'Kolkata', 'Chennai', 'Bangalore',
        'Hyderabad,_India', 'Karachi', 'Lahore', 'Islamabad', 'Dhaka',
        'Hanoi', 'Ho_Chi_Minh_City', 'Yangon', 'Phnom_Penh', 'Vientiane',
        'Taipei', 'Osaka', 'Yokohama', 'Kyoto', 'Nagoya',
        'Tehran', 'Baghdad', 'Riyadh', 'Jeddah', 'Dubai',
        'Abu_Dhabi', 'Kuwait_City', 'Doha', 'Muscat', 'Sana\'a',
        'Amman', 'Damascus', 'Beirut', 'Jerusalem', 'Tel_Aviv',
        'Ankara', 'Istanbul', 'Tbilisi', 'Yerevan', 'Baku',
        
        # African major cities
        'Cairo', 'Lagos', 'Kinshasa', 'Johannesburg', 'Nairobi',
        'Casablanca', 'Algiers', 'Addis_Ababa', 'Accra', 'Dakar',
        'Abidjan', 'Dar_es_Salaam', 'Khartoum', 'Luanda', 'Maputo',
        'Cape_Town', 'Pretoria', 'Durban', 'Tunis', 'Rabat',
        
        # Oceanian major cities
        'Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide',
        'Auckland', 'Wellington', 'Christchurch', 'Canberra',
        
        # South American major cities
        'São_Paulo', 'Rio_de_Janeiro', 'Brasília', 'Buenos_Aires', 'Lima',
        'Bogotá', 'Santiago,_Chile', 'Caracas', 'Quito', 'La_Paz',
        'Montevideo', 'Asunción', 'Paramaribo', 'Georgetown,_Guyana',
        
        # Central American and Caribbean major cities
        'Mexico_City', 'Guadalajara', 'Monterrey', 'Guatemala_City', 'San_Salvador',
        'Tegucigalpa', 'Managua', 'San_José,_Costa_Rica', 'Panama_City',
        'Havana', 'Santo_Domingo', 'Port-au-Prince', 'Kingston,_Jamaica', 'San_Juan,_Puerto_Rico',
    ]
    
    def collect(self) -> List[Flag]:
        """
        Collect city flags.
        
        Returns:
            List of Flag objects
        """
        print("Starting city flag collection...")
        
        # Collect from list pages
        for page in self.CITY_FLAG_SOURCES:
            print(f"\nCollecting from page: {page}")
            self._collect_from_list_page(page)
        
        # Collect from major city pages
        print("\nCollecting from major city pages...")
        collected = 0
        for city in self.MAJOR_CITIES:
            if self._collect_from_city_page(city):
                collected += 1
            
            # Progress update every 50 cities
            if collected % 50 == 0 and collected > 0:
                print(f"  Progress: {collected}/{len(self.MAJOR_CITIES)} cities processed")
        
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
        
        # Try tables
        flag_data_list = self.extract_flags_from_table(soup)
        
        # Try gallery
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
        
        print(f"  Collected {len(flag_data_list)} flags")
    
    def _collect_from_city_page(self, page_title: str) -> bool:
        """
        Collect flag from a city's Wikipedia page.
        
        Args:
            page_title: Wikipedia page title
            
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
            name = page_title.replace('_', ' ')
            
            flag = self.create_flag(
                name=name,
                wikipedia_page=page_title,
                wikipedia_url=flag_data['page_url'],
                wikipedia_image_url=flag_data['image_url'],
                verification_method='table'
            )
            
            if flag:
                self.collected_flags.append(flag)
                return True
        
        return False

