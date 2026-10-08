import re
from typing import NamedTuple, Optional


class ResolvedAirport(NamedTuple):
    iata_code: str
    display_name: str


class LocationResolutionError(Exception):
    """Raised when a location string cannot be resolved to a known IATA airport code."""

    def __init__(self, location: str, message: Optional[str] = None):
        self.location = location
        self.message = message or f"Unable to resolve airport for location: '{location}'. Please select a major city or state."
        super().__init__(self.message)


# Primary Indian city-to-airport mapping
CITY_AIRPORTS = {
    # Major Metros & Primary Hubs
    "kolkata": ResolvedAirport("CCU", "Kolkata"),
    "calcutta": ResolvedAirport("CCU", "Kolkata"),
    "delhi": ResolvedAirport("DEL", "Delhi"),
    "new delhi": ResolvedAirport("DEL", "New Delhi"),
    "mumbai": ResolvedAirport("BOM", "Mumbai"),
    "bombay": ResolvedAirport("BOM", "Mumbai"),
    "bengaluru": ResolvedAirport("BLR", "Bengaluru"),
    "bangalore": ResolvedAirport("BLR", "Bengaluru"),
    "chennai": ResolvedAirport("MAA", "Chennai"),
    "madras": ResolvedAirport("MAA", "Chennai"),
    "hyderabad": ResolvedAirport("HYD", "Hyderabad"),
    "goa": ResolvedAirport("GOI", "Goa"),
    "panaji": ResolvedAirport("GOI", "Panaji"),
    "vasco da gama": ResolvedAirport("GOI", "Vasco da Gama"),
    "dabolim": ResolvedAirport("GOI", "Goa (Dabolim)"),
    "mopa": ResolvedAirport("GOX", "Goa (Manohar)"),
    "jaipur": ResolvedAirport("JAI", "Jaipur"),
    "ahmedabad": ResolvedAirport("AMD", "Ahmedabad"),
    "pune": ResolvedAirport("PNQ", "Pune"),
    # South India
    "kochi": ResolvedAirport("COK", "Kochi"),
    "cochin": ResolvedAirport("COK", "Kochi"),
    "thiruvananthapuram": ResolvedAirport("TRV", "Thiruvananthapuram"),
    "trivandrum": ResolvedAirport("TRV", "Thiruvananthapuram"),
    "kozhikode": ResolvedAirport("CCJ", "Kozhikode"),
    "calicut": ResolvedAirport("CCJ", "Kozhikode"),
    "kannur": ResolvedAirport("CNN", "Kannur"),
    "mangaluru": ResolvedAirport("IXE", "Mangaluru"),
    "mangalore": ResolvedAirport("IXE", "Mangaluru"),
    "coimbatore": ResolvedAirport("CJB", "Coimbatore"),
    "madurai": ResolvedAirport("IXM", "Madurai"),
    "tiruchirappalli": ResolvedAirport("TRZ", "Tiruchirappalli"),
    "trichy": ResolvedAirport("TRZ", "Tiruchirappalli"),
    "visakhapatnam": ResolvedAirport("VTZ", "Visakhapatnam"),
    "vizag": ResolvedAirport("VTZ", "Visakhapatnam"),
    "vijayawada": ResolvedAirport("VGA", "Vijayawada"),
    "tirupati": ResolvedAirport("TIR", "Tirupati"),
    "hubballi": ResolvedAirport("HBX", "Hubballi"),
    "hubli": ResolvedAirport("HBX", "Hubballi"),
    "belagavi": ResolvedAirport("IXG", "Belagavi"),
    "belgaum": ResolvedAirport("IXG", "Belagavi"),
    "puducherry": ResolvedAirport("PNY", "Puducherry"),
    "pondicherry": ResolvedAirport("PNY", "Puducherry"),
    # East & North-East India
    "guwahati": ResolvedAirport("GAU", "Guwahati"),
    "bagdogra": ResolvedAirport("IXB", "Bagdogra"),
    "darjeeling": ResolvedAirport("IXB", "Darjeeling (Bagdogra)"),
    "siliguri": ResolvedAirport("IXB", "Siliguri (Bagdogra)"),
    "kalimpong": ResolvedAirport("IXB", "Kalimpong (Bagdogra)"),
    "gangtok": ResolvedAirport("IXB", "Gangtok (Bagdogra)"),
    "bhubaneswar": ResolvedAirport("BBI", "Bhubaneswar"),
    "patna": ResolvedAirport("PAT", "Patna"),
    "gaya": ResolvedAirport("GAY", "Gaya"),
    "ranchi": ResolvedAirport("IXR", "Ranchi"),
    "raipur": ResolvedAirport("RPR", "Raipur"),
    "agartala": ResolvedAirport("IXA", "Agartala"),
    "imphal": ResolvedAirport("IMF", "Imphal"),
    "dimapur": ResolvedAirport("DMU", "Dimapur"),
    "aizawl": ResolvedAirport("AJL", "Aizawl"),
    "shillong": ResolvedAirport("SHL", "Shillong"),
    "dibrugarh": ResolvedAirport("DIB", "Dibrugarh"),
    "silchar": ResolvedAirport("IXS", "Silchar"),
    "jorhat": ResolvedAirport("JRH", "Jorhat"),
    "tezpur": ResolvedAirport("TEZ", "Tezpur"),
    "itanagar": ResolvedAirport("HGI", "Itanagar (Hollongi)"),
    "naharlagun": ResolvedAirport("HGI", "Naharlagun (Hollongi)"),
    "pasighat": ResolvedAirport("IXT", "Pasighat"),
    "jharsuguda": ResolvedAirport("JRG", "Jharsuguda"),
    "rourkela": ResolvedAirport("RRK", "Rourkela"),
    # North & West India
    "lucknow": ResolvedAirport("LKO", "Lucknow"),
    "varanasi": ResolvedAirport("VNS", "Varanasi"),
    "benares": ResolvedAirport("VNS", "Varanasi"),
    "prayagraj": ResolvedAirport("IXD", "Prayagraj"),
    "allahabad": ResolvedAirport("IXD", "Prayagraj"),
    "ayodhya": ResolvedAirport("AYJ", "Ayodhya"),
    "agra": ResolvedAirport("AGR", "Agra"),
    "kanpur": ResolvedAirport("KNU", "Kanpur"),
    "gorakhpur": ResolvedAirport("GOP", "Gorakhpur"),
    "bareilly": ResolvedAirport("BEK", "Bareilly"),
    "amritsar": ResolvedAirport("ATQ", "Amritsar"),
    "chandigarh": ResolvedAirport("IXC", "Chandigarh"),
    "bathinda": ResolvedAirport("BUP", "Bathinda"),
    "srinagar": ResolvedAirport("SXR", "Srinagar"),
    "jammu": ResolvedAirport("IXJ", "Jammu"),
    "leh": ResolvedAirport("IXL", "Leh"),
    "dehradun": ResolvedAirport("DED", "Dehradun"),
    "haridwar": ResolvedAirport("DED", "Haridwar (Dehradun)"),
    "rishikesh": ResolvedAirport("DED", "Rishikesh (Dehradun)"),
    "dharamsala": ResolvedAirport("DHM", "Dharamsala"),
    "dharamshala": ResolvedAirport("DHM", "Dharamsala"),
    "kullu": ResolvedAirport("KUU", "Kullu"),
    "manali": ResolvedAirport("KUU", "Manali (Kullu)"),
    "shimla": ResolvedAirport("SLV", "Shimla"),
    "udaipur": ResolvedAirport("UDR", "Udaipur"),
    "jodhpur": ResolvedAirport("JDH", "Jodhpur"),
    "jaisalmer": ResolvedAirport("JSA", "Jaisalmer"),
    "bikaner": ResolvedAirport("BKB", "Bikaner"),
    "surat": ResolvedAirport("STV", "Surat"),
    "vadodara": ResolvedAirport("BDQ", "Vadodara"),
    "rajkot": ResolvedAirport("RAJ", "Rajkot"),
    "bhuj": ResolvedAirport("BHJ", "Bhuj"),
    "indore": ResolvedAirport("IDR", "Indore"),
    "bhopal": ResolvedAirport("BHO", "Bhopal"),
    "gwalior": ResolvedAirport("GWL", "Gwalior"),
    "jabalpur": ResolvedAirport("JLR", "Jabalpur"),
    "khajuraho": ResolvedAirport("HJR", "Khajuraho"),
    "nagpur": ResolvedAirport("NAG", "Nagpur"),
    "aurangabad": ResolvedAirport("IXU", "Aurangabad"),
    "nashik": ResolvedAirport("ISK", "Nashik"),
    "kolhapur": ResolvedAirport("KLH", "Kolhapur"),
    "shirdi": ResolvedAirport("SAG", "Shirdi"),
    "diu": ResolvedAirport("DIU", "Diu"),
    # Island UTs
    "port blair": ResolvedAirport("IXZ", "Port Blair"),
    "sri vijaya puram": ResolvedAirport("IXZ", "Port Blair"),
    "sri vijaya puram (port blair)": ResolvedAirport("IXZ", "Port Blair"),
    "agatti": ResolvedAirport("AGX", "Agatti"),
    "lakshadweep": ResolvedAirport("AGX", "Agatti (Lakshadweep)"),
}

# State and Union Territory primary commercial airport mapping
STATE_AIRPORTS = {
    "west bengal": ResolvedAirport("CCU", "Kolkata"),
    "delhi (nct)": ResolvedAirport("DEL", "Delhi"),
    "delhi": ResolvedAirport("DEL", "Delhi"),
    "maharashtra": ResolvedAirport("BOM", "Mumbai"),
    "karnataka": ResolvedAirport("BLR", "Bengaluru"),
    "tamil nadu": ResolvedAirport("MAA", "Chennai"),
    "telangana": ResolvedAirport("HYD", "Hyderabad"),
    "gujarat": ResolvedAirport("AMD", "Ahmedabad"),
    "goa": ResolvedAirport("GOI", "Goa"),
    "rajasthan": ResolvedAirport("JAI", "Jaipur"),
    "kerala": ResolvedAirport("COK", "Kochi"),
    "uttar pradesh": ResolvedAirport("LKO", "Lucknow"),
    "bihar": ResolvedAirport("PAT", "Patna"),
    "assam": ResolvedAirport("GAU", "Guwahati"),
    "odisha": ResolvedAirport("BBI", "Bhubaneswar"),
    "punjab": ResolvedAirport("ATQ", "Amritsar"),
    "madhya pradesh": ResolvedAirport("IDR", "Indore"),
    "andhra pradesh": ResolvedAirport("VTZ", "Visakhapatnam"),
    "haryana": ResolvedAirport("DEL", "Delhi"),
    "chandigarh": ResolvedAirport("IXC", "Chandigarh"),
    "jammu and kashmir": ResolvedAirport("SXR", "Srinagar"),
    "ladakh": ResolvedAirport("IXL", "Leh"),
    "uttarakhand": ResolvedAirport("DED", "Dehradun"),
    "jharkhand": ResolvedAirport("IXR", "Ranchi"),
    "chhattisgarh": ResolvedAirport("RPR", "Raipur"),
    "himachal pradesh": ResolvedAirport("DHM", "Dharamsala"),
    "andaman and nicobar islands": ResolvedAirport("IXZ", "Port Blair"),
    "tripura": ResolvedAirport("IXA", "Agartala"),
    "manipur": ResolvedAirport("IMF", "Imphal"),
    "nagaland": ResolvedAirport("DMU", "Dimapur"),
    "mizoram": ResolvedAirport("AJL", "Aizawl"),
    "meghalaya": ResolvedAirport("SHL", "Shillong"),
    "puducherry": ResolvedAirport("PNY", "Puducherry"),
    "arunachal pradesh": ResolvedAirport("HGI", "Itanagar"),
    "dadra and nagar haveli and daman and diu": ResolvedAirport("DIU", "Diu"),
    "lakshadweep": ResolvedAirport("AGX", "Agatti"),
    "sikkim": ResolvedAirport("IXB", "Bagdogra"),
}

# Direct IATA code set for validation
KNOWN_IATA_CODES = {v.iata_code for v in list(CITY_AIRPORTS.values()) + list(STATE_AIRPORTS.values())}


def clean_location_string(raw: str) -> str:
    """Normalize input strings for airport lookup."""
    s = raw.strip().lower()
    # Strip common suffixes like ', india'
    s = re.sub(r",\s*india$", "", s)
    return s.strip()


def resolve_location_to_airport(location: str, city_hint: Optional[str] = None) -> ResolvedAirport:
    """
    Resolve a user input (city, state, or IATA code) to an IATA airport code and display name.

    Priority:
    1. City hint if provided
    2. Exact city name match (e.g. "Goa", "Delhi", "Kolkata")
    3. Exact state name match (e.g. "West Bengal", "Goa")
    4. Known 3-letter IATA code (e.g. 'CCU', 'DEL')
    5. Substring matches
    """
    loc_clean = clean_location_string(location)
    raw_upper = location.strip().upper()

    # 1. City hint priority
    if city_hint:
        hint_clean = clean_location_string(city_hint)
        if hint_clean in CITY_AIRPORTS:
            return CITY_AIRPORTS[hint_clean]

    # 2. Direct city name
    if loc_clean in CITY_AIRPORTS:
        return CITY_AIRPORTS[loc_clean]

    # 3. State name
    if loc_clean in STATE_AIRPORTS:
        return STATE_AIRPORTS[loc_clean]

    # 4. Known 3-letter IATA code
    if len(raw_upper) == 3 and raw_upper.isalpha():
        for resolved in list(CITY_AIRPORTS.values()) + list(STATE_AIRPORTS.values()):
            if resolved.iata_code == raw_upper:
                return resolved
        if location.strip().isupper():
            return ResolvedAirport(raw_upper, raw_upper)

    # 5. Check for substring matches (e.g. "Kolkata, West Bengal" -> "kolkata")
    for city_key, airport in CITY_AIRPORTS.items():
        if city_key in loc_clean:
            return airport

    for state_key, airport in STATE_AIRPORTS.items():
        if state_key in loc_clean:
            return airport

    raise LocationResolutionError(location)

