"""Collect one real photograph per destination from Wikipedia / Wikimedia Commons and store it in app/data/images.json.

Run (from backend/):  python -m scripts.fetch_images [slug ...]
Only destinations not already in the file are fetched (pass slugs to redo specific ones). Review the printed titles:
a search can match the wrong article, in which case add an entry to QUERY and rerun for that slug.
The JSON holds only URLs, credit, licence and source page; no image files are stored in the project.
"""
from __future__ import annotations

import json
import re
import sys
import time

from app.data import catalog
from app.data.catalog_extra import EXTRA_DESTINATIONS
from app.services import photos
from app.services.seed import IMAGES_FILE

# slug -> Wikipedia search text, where "<name> <state>" finds the wrong article or no photo
QUERY = {
    "kevadia": "Statue of Unity", "aurangabad": "Ellora Caves", "mahabalipuram": "Shore Temple Mahabalipuram",
    "sohra": "Nohkalikai Falls", "andaman": "Radhanagar Beach", "agatti": "Agatti Island", "kutch": "Dhordo",
    "rameswaram": "Ramanathaswamy Temple", "puri": "Jagannath Temple Puri", "alappuzha": "Alappuzha backwaters",
    "badami": "Badami cave temples", "tarkarli": "Tarkarli beach", "spiti": "Spiti Valley", "ziro": "Ziro Valley",
    "majuli": "Majuli island", "thekkady": "Periyar National Park", "jagdalpur": "Chitrakote Falls", "agartala": "Ujjayanta Palace",
    "imphal": "Loktak Lake", "aizawl": "Aizawl city", "kohima": "Kohima War Cemetery", "delhi": "Red Fort", "mumbai": "Gateway of India",
    "hyderabad": "Charminar", "agra": "Taj Mahal", "kolkata": "Victoria Memorial Kolkata", "jaipur": "Hawa Mahal",
    "udaipur": "City Palace Udaipur", "madurai": "Meenakshi Temple", "thanjavur": "Brihadisvara Temple Thanjavur",
    "amritsar": "Golden Temple", "varanasi": "Varanasi ghats", "goa": "Goa beach", "tawang": "Tawang Monastery",
    "visakhapatnam": "Visakhapatnam beach", "kaziranga": "Kaziranga National Park", "bodh-gaya": "Mahabodhi Temple",
    "kanyakumari": "Vivekananda Rock Memorial", "mysuru": "Mysore Palace", "khajuraho": "Khajuraho Group of Monuments",
    "chandigarh": "Rock Garden of Chandigarh", "daman": "Moti Daman Fort", "gulmarg": "Gulmarg", "leh": "Leh Palace",
    "srinagar": "Dal Lake", "gangtok": "Gangtok", "darjeeling": "Darjeeling", "kodaikanal": "Kodaikanal Lake",
    "ooty": "Ooty Lake", "coorg": "Abbey Falls", "hampi": "Virupaksha Temple Hampi", "puducherry": "Puducherry promenade",
    "kochi": "Chinese fishing nets Fort Kochi", "kurukshetra": "Brahma Sarovar Kurukshetra", "jaisalmer": "Jaisalmer Fort",
    "lansdowne": "Lansdowne Uttarakhand", "pachmarhi": "Pachmarhi", "orchha": "Orchha", "pushkar": "Pushkar Lake",
    "mount-abu": "Nakki Lake", "bundi": "Taragarh Fort Bundi", "dharamshala": "McLeod Ganj", "kasol": "Kasol",
    "auli": "Auli Uttarakhand", "mussoorie": "Mussoorie", "wayanad": "Wayanad", "vagamon": "Vagamon",
    "varkala": "Varkala Beach", "gokarna": "Gokarna Karnataka", "chikmagalur": "Mullayanagiri", "valparai": "Valparai",
    "yercaud": "Yercaud", "lonavala": "Bhushi Dam", "mahabaleshwar": "Mahabaleshwar", "panchgani": "Panchgani",
    "alibag": "Alibag", "matheran": "Matheran",
}


def main() -> None:
    states = {s[0]: s[1] for s in catalog.STATES}
    rows = [(d[0], d[1], states[d[2]]) for d in [*catalog.DESTINATIONS, *EXTRA_DESTINATIONS]]
    data = json.loads(IMAGES_FILE.read_text()) if IMAGES_FILE.exists() else {}
    only = set(sys.argv[1:])
    for slug, name, state in rows:
        if (only and slug not in only) or (not only and slug in data):
            continue
        q = QUERY.get(slug) or f"{re.sub(r' *[(].*', '', name)} {state}"
        r = photos.lookup(q, size=900)
        if r.get("available"):
            data[slug] = {k: r.get(k) for k in ("url", "title", "credit", "licence", "source_page")} | {"query": q}
            print(f"{slug:<16} ok   {r['title'][:40]:<40} {str(r.get('licence'))[:14]:<14} <- {q}")
        else:
            print(f"{slug:<16} NONE {r.get('reason')} <- {q}")
        time.sleep(0.4)
    IMAGES_FILE.write_text(json.dumps(data, indent=1, sort_keys=True))
    print(f"{len(data)} of {len(rows)} destinations have a photo")


if __name__ == "__main__":
    main()
