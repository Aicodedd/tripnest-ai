"""Indian cities used as starting locations (static gazetteer, no external geocoding service).

Coordinates are approximate city centres from public knowledge. Tuple: (name, state, lat, lon, aliases).
"""

CITIES = [
    ("Delhi", "Delhi", 28.6139, 77.2090, ("new delhi", "nct")), ("Noida", "Uttar Pradesh", 28.5355, 77.3910, ()),
    ("Gurugram", "Haryana", 28.4595, 77.0266, ("gurgaon",)), ("Chandigarh", "Chandigarh", 30.7333, 76.7794, ()),
    ("Ludhiana", "Punjab", 30.9010, 75.8573, ()), ("Amritsar", "Punjab", 31.6340, 74.8723, ()),
    ("Jalandhar", "Punjab", 31.3260, 75.5762, ()), ("Shimla", "Himachal Pradesh", 31.1048, 77.1734, ()),
    ("Dehradun", "Uttarakhand", 30.3165, 78.0322, ()), ("Haridwar", "Uttarakhand", 29.9457, 78.1642, ()),
    ("Jammu", "Jammu and Kashmir", 32.7266, 74.8570, ()), ("Srinagar", "Jammu and Kashmir", 34.0837, 74.7973, ()),
    ("Leh", "Ladakh", 34.1526, 77.5771, ()),
    ("Lucknow", "Uttar Pradesh", 26.8467, 80.9462, ()), ("Kanpur", "Uttar Pradesh", 26.4499, 80.3319, ()),
    ("Varanasi", "Uttar Pradesh", 25.3176, 82.9739, ("banaras", "benares")), ("Agra", "Uttar Pradesh", 27.1767, 78.0081, ()),
    ("Prayagraj", "Uttar Pradesh", 25.4358, 81.8463, ("allahabad",)),
    ("Jaipur", "Rajasthan", 26.9124, 75.7873, ()), ("Jodhpur", "Rajasthan", 26.2389, 73.0243, ()),
    ("Udaipur", "Rajasthan", 24.5854, 73.7125, ()), ("Kota", "Rajasthan", 25.2138, 75.8648, ()),
    ("Ahmedabad", "Gujarat", 23.0225, 72.5714, ()), ("Surat", "Gujarat", 21.1702, 72.8311, ()),
    ("Vadodara", "Gujarat", 22.3072, 73.1812, ("baroda",)), ("Rajkot", "Gujarat", 22.3039, 70.8022, ()),
    ("Daman", "Dadra and Nagar Haveli and Daman and Diu", 20.3974, 72.8328, ()),
    ("Silvassa", "Dadra and Nagar Haveli and Daman and Diu", 20.2766, 73.0169, ()),
    ("Mumbai", "Maharashtra", 19.0760, 72.8777, ("bombay",)), ("Pune", "Maharashtra", 18.5204, 73.8567, ("poona",)),
    ("Nagpur", "Maharashtra", 21.1458, 79.0882, ()), ("Nashik", "Maharashtra", 19.9975, 73.7898, ()),
    ("Kolhapur", "Maharashtra", 16.7050, 74.2433, ()),
    ("Chhatrapati Sambhajinagar", "Maharashtra", 19.8762, 75.3433, ("aurangabad", "sambhajinagar")),
    ("Panaji", "Goa", 15.4909, 73.8278, ("goa", "panjim")),
    ("Bhopal", "Madhya Pradesh", 23.2599, 77.4126, ()), ("Indore", "Madhya Pradesh", 22.7196, 75.8577, ()),
    ("Gwalior", "Madhya Pradesh", 26.2183, 78.1828, ()), ("Jabalpur", "Madhya Pradesh", 23.1815, 79.9864, ()),
    ("Raipur", "Chhattisgarh", 21.2514, 81.6296, ()),
    ("Patna", "Bihar", 25.5941, 85.1376, ()), ("Ranchi", "Jharkhand", 23.3441, 85.3096, ()),
    ("Jamshedpur", "Jharkhand", 22.8046, 86.2029, ()),
    ("Kolkata", "West Bengal", 22.5726, 88.3639, ("calcutta",)), ("Siliguri", "West Bengal", 26.7271, 88.3953, ()),
    ("Bhubaneswar", "Odisha", 20.2961, 85.8245, ()), ("Puri", "Odisha", 19.8135, 85.8312, ()),
    ("Guwahati", "Assam", 26.1445, 91.7362, ("gauhati",)), ("Dibrugarh", "Assam", 27.4728, 94.9120, ()),
    ("Jorhat", "Assam", 26.7509, 94.2037, ()), ("Shillong", "Meghalaya", 25.5788, 91.8933, ()),
    ("Imphal", "Manipur", 24.8170, 93.9368, ()), ("Aizawl", "Mizoram", 23.7271, 92.7176, ()),
    ("Kohima", "Nagaland", 25.6751, 94.1086, ()), ("Itanagar", "Arunachal Pradesh", 27.0844, 93.6053, ()),
    ("Agartala", "Tripura", 23.8315, 91.2868, ()), ("Gangtok", "Sikkim", 27.3389, 88.6065, ()),
    ("Hyderabad", "Telangana", 17.3850, 78.4867, ("secunderabad",)),
    ("Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185, ("vizag", "vishakhapatnam")),
    ("Vijayawada", "Andhra Pradesh", 16.5062, 80.6480, ()), ("Tirupati", "Andhra Pradesh", 13.6288, 79.4192, ()),
    ("Bengaluru", "Karnataka", 12.9716, 77.5946, ("bangalore",)), ("Mysuru", "Karnataka", 12.2958, 76.6394, ("mysore",)),
    ("Mangaluru", "Karnataka", 12.9141, 74.8560, ("mangalore",)), ("Hubballi", "Karnataka", 15.3647, 75.1240, ("hubli",)),
    ("Chennai", "Tamil Nadu", 13.0827, 80.2707, ("madras",)), ("Coimbatore", "Tamil Nadu", 11.0168, 76.9558, ("kovai",)),
    ("Madurai", "Tamil Nadu", 9.9252, 78.1198, ()), ("Tiruchirappalli", "Tamil Nadu", 10.7905, 78.7047, ("trichy",)),
    ("Salem", "Tamil Nadu", 11.6643, 78.1460, ()), ("Vellore", "Tamil Nadu", 12.9165, 79.1325, ()),
    ("Puducherry", "Puducherry", 11.9416, 79.8083, ("pondicherry", "pondy")),
    ("Kochi", "Kerala", 9.9312, 76.2673, ("cochin", "ernakulam")),
    ("Thiruvananthapuram", "Kerala", 8.5241, 76.9366, ("trivandrum",)), ("Kozhikode", "Kerala", 11.2588, 75.7804, ("calicut",)),
    ("Port Blair", "Andaman and Nicobar Islands", 11.6234, 92.7265, ()),
    ("Kavaratti", "Lakshadweep", 10.5667, 72.6417, ()),
]


def as_dict(c) -> dict:
    return {"name": c[0], "state": c[1], "lat": c[2], "lon": c[3]}


def search(q: str, limit: int = 8) -> list[dict]:
    q = q.strip().lower()
    scored = []
    for c in CITIES:
        names = [c[0].lower(), *c[4]]
        if any(n.startswith(q) for n in names):
            scored.append((0, c[0], c))
        elif any(q in n for n in names) or q in c[1].lower():
            scored.append((1, c[0], c))
    scored.sort(key=lambda x: (x[0], x[1]))
    return [as_dict(c) for _, _, c in scored[:limit]]


def resolve(text: str) -> dict | None:
    """Exact name or alias (ignoring case and any ', State' suffix); otherwise a unique prefix match."""
    q = text.split(",")[0].strip().lower()
    if not q:
        return None
    for c in CITIES:
        if q == c[0].lower() or q in c[4]:
            return as_dict(c)
    hits = [c for c in CITIES if any(n.startswith(q) for n in (c[0].lower(), *c[4]))]
    return as_dict(hits[0]) if len(hits) == 1 else None


def _km(lat1, lon1, lat2, lon2) -> float:
    import math
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def nearest(lat: float, lon: float) -> dict:
    """The closest listed city, how far it is, and whether the position is inside the area TripNest covers (India)."""
    c = min(CITIES, key=lambda c: _km(lat, lon, c[2], c[3]))
    km = _km(lat, lon, c[2], c[3])
    inside = 6 <= lat <= 37.5 and 68 <= lon <= 98 and km <= 700
    out = {**as_dict(c), "query_lat": lat, "query_lon": lon, "distance_km": round(km, 1), "covered": inside,
           "label": c[0] if km < 25 else f"near {c[0]}"}
    if not inside:
        out["message"] = "TripNest AI covers destinations in India. Choose an Indian city to see places around it."
    return out
