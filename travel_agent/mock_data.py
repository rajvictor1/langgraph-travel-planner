"""Small, transparent inventory. Prices are illustrative, not live quotes."""

FLIGHTS = [
    {"id": "F101", "origin": "Delhi", "destination": "Goa", "stops": 0, "layover_hours": 0, "class": "economy", "price": 8200, "airline": "IndiGo"},
    {"id": "F102", "origin": "Delhi", "destination": "Goa", "stops": 1, "layover_hours": 2.5, "class": "economy", "price": 6400, "airline": "Air India"},
    {"id": "F103", "origin": "Jaipur", "destination": "Goa", "stops": 1, "layover_hours": 3, "class": "economy", "price": 5600, "airline": "Air India Express"},
    {"id": "F104", "origin": "Delhi", "destination": "Goa", "stops": 0, "layover_hours": 0, "class": "business", "price": 23500, "airline": "Vistara"},
    {"id": "F201", "origin": "Mumbai", "destination": "Goa", "stops": 0, "layover_hours": 0, "class": "economy", "price": 4200, "airline": "IndiGo"},
    {"id": "F301", "origin": "Bengaluru", "destination": "Goa", "stops": 0, "layover_hours": 0, "class": "economy", "price": 4700, "airline": "Akasa Air"},
]

STAYS = [
    {"id": "S101", "destination": "Goa", "style": "luxury", "name": "Coastal Grand", "nightly": 12500, "rating": 4.8},
    {"id": "S102", "destination": "Goa", "style": "hotel", "name": "Casa Verde", "nightly": 5400, "rating": 4.5},
    {"id": "S103", "destination": "Goa", "style": "hostel", "name": "Nomad House", "nightly": 1600, "rating": 4.3},
    {"id": "S104", "destination": "Goa", "style": "airbnb", "name": "Palm Courtyard", "nightly": 3900, "rating": 4.6},
    {"id": "S105", "destination": "Goa", "style": "room_share", "name": "Beach Share", "nightly": 1100, "rating": 4.1},
]

ACTIVITIES = [
    {"id": "A101", "destination": "Goa", "tags": ["beach", "relaxation"], "name": "South Goa beach day", "price": 600},
    {"id": "A102", "destination": "Goa", "tags": ["food", "culture"], "name": "Panaji food walk", "price": 1800},
    {"id": "A103", "destination": "Goa", "tags": ["adventure", "water sports"], "name": "Water-sports session", "price": 3200},
    {"id": "A104", "destination": "Goa", "tags": ["history", "culture"], "name": "Old Goa heritage walk", "price": 900},
    {"id": "A105", "destination": "Goa", "tags": ["nightlife"], "name": "Evening music experience", "price": 2200},
]

