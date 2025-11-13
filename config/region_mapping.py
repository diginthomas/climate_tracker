"""
Mapping of BC Regional Districts to High-Level Regions
This mapping groups the 27 regional districts into 5 high-level regions.
"""

REGIONAL_DISTRICT_TO_REGION = {
    # Northern BC (7 districts)
    "Regional District of Bulkley-Nechako": "Northern BC",
    "Cariboo Regional District": "Northern BC",
    "Regional District of Fraser-Fort George": "Northern BC",
    "Regional District of Kitimat-Stikine": "Northern BC",
    "Peace River Regional District": "Northern BC",
    "North Coast Regional District": "Northern BC",
    "Stikine Region (Unincorporated)": "Northern BC",
    
    # Thompson-Okanagan (4 districts)
    "Regional District of Central Okanagan": "Thompson-Okanagan",
    "Regional District of Okanagan-Similkameen": "Thompson-Okanagan",
    "Regional District of North Okanagan": "Thompson-Okanagan",
    "Thompson-Nicola Regional District": "Thompson-Okanagan",
    
    # Lower Mainland (3 districts)
    "Metro Vancouver Regional District": "Lower Mainland",
    "Fraser Valley Regional District": "Lower Mainland",
    "Squamish-Lillooet Regional District": "Lower Mainland",
    
    # Vancouver Island & Coast (10 districts)
    "Capital Regional District": "Vancouver Island & Coast",
    "Comox Valley Regional District": "Vancouver Island & Coast",
    "Cowichan Valley Regional District": "Vancouver Island & Coast",
    "Regional District of Nanaimo": "Vancouver Island & Coast",
    "Regional District of Alberni-Clayoquot": "Vancouver Island & Coast",
    "Regional District of Mount Waddington": "Vancouver Island & Coast",
    "Strathcona Regional District": "Vancouver Island & Coast",
    "Central Coast Regional District": "Vancouver Island & Coast",
    "qathet Regional District": "Vancouver Island & Coast",
    "Sunshine Coast Regional District": "Vancouver Island & Coast",
    
    # Kootenay/Columbia (4 districts)
    "Regional District of Central Kootenay": "Kootenay/Columbia",
    "Regional District of East Kootenay": "Kootenay/Columbia",
    "Regional District of Kootenay Boundary": "Kootenay/Columbia",
    "Columbia Shuswap Regional District": "Kootenay/Columbia",
}

# High-level region colors (matching frontend)
REGION_COLORS = {
    "Northern BC": "#3498db",
    "Thompson-Okanagan": "#e74c3c",
    "Lower Mainland": "#2ecc71",
    "Vancouver Island & Coast": "#f39c12",
    "Kootenay/Columbia": "#9b59b6",
}

# High-level region centers (for map centering)
REGION_CENTERS = {
    "Northern BC": {"lat": 57.0, "lng": -125.0},
    "Thompson-Okanagan": {"lat": 50.5, "lng": -119.0},
    "Lower Mainland": {"lat": 49.2, "lng": -123.0},
    "Vancouver Island & Coast": {"lat": 49.6, "lng": -125.0},
    "Kootenay/Columbia": {"lat": 49.5, "lng": -116.0},
}

# Cities for each region (for backward compatibility)
REGION_CITIES = {
    "Northern BC": ["Prince George", "Fort St. John", "Terrace"],
    "Thompson-Okanagan": ["Kamloops", "Kelowna", "Vernon"],
    "Lower Mainland": ["Vancouver", "Surrey", "Burnaby"],
    "Vancouver Island & Coast": ["Victoria", "Nanaimo", "Courtenay"],
    "Kootenay/Columbia": ["Cranbrook", "Nelson", "Castlegar"],
}



REGION_ID = {
    "Northern BC":"100",
    "Thompson-Okanagan":"101",
    "Lower Mainland":"102",
    "Vancouver Island & Coast":"103",
    "Kootenay/Columbia":"104"
}
