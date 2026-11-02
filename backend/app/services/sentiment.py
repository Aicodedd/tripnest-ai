"""Aspect-based sentiment analysis (lexicon + rules baseline). Ported from the CrowdWise prototype.

Splits a review into clauses, scores each clause with a polarity lexicon (handling negation and
intensifiers) and attaches the score to every tourism aspect mentioned in that clause.
This is a transparent baseline that runs offline; swap `analyze()` for a transformer ABSA model
when real review data and compute are available.
"""
from __future__ import annotations

import re

ASPECTS = {
    "cleanliness": {"clean", "dirty", "garbage", "trash", "litter", "toilet", "toilets", "washroom", "washrooms",
                    "restroom", "restrooms", "smell", "smelly", "hygiene", "hygienic", "filthy", "waste",
                    "dustbin", "dustbins", "unclean", "stink", "stinks", "neat", "tidy", "maintained"},
    "parking": {"parking", "parked", "vehicle", "vehicles", "traffic", "shuttle", "cab", "taxi"},
    "safety": {"safe", "unsafe", "slippery", "railing", "railings", "danger", "dangerous", "accident",
               "theft", "lighting", "security", "secure", "guard", "guards", "lifeguard", "fenced"},
    "accessibility": {"wheelchair", "accessible", "ramp", "ramps", "steps", "stairs", "elderly", "senior",
                      "seniors", "steep", "lift", "disabled", "stroller", "handicapped"},
    "staff": {"staff", "rude", "helpful", "behaviour", "behavior", "attendant", "attendants", "guide",
              "guides", "volunteer", "volunteers", "polite", "courteous", "friendly", "unhelpful", "pushy"},
    "food_facilities": {"food", "snacks", "canteen", "cafe", "stalls", "stall", "benches", "bench", "seating",
                        "shade", "water", "restaurant", "restaurants", "tea", "coffee", "drinks", "tasty",
                        "delicious", "facilities", "amenities"},
    "ticketing": {"ticket", "tickets", "queue", "queues", "line", "entry", "booking", "counter", "counters",
                  "wait", "waiting", "slot", "token", "online", "entrance"},
    "crowding": {"crowd", "crowded", "crowds", "rush", "packed", "overcrowded", "jam", "jammed", "congested",
                 "chaos", "chaotic", "busy"},
}
ASPECT_LABELS = {"cleanliness": "Cleanliness", "parking": "Parking", "safety": "Safety",
                 "accessibility": "Accessibility", "staff": "Staff behaviour",
                 "food_facilities": "Food & facilities", "ticketing": "Ticketing & queues",
                 "crowding": "Crowding"}

POS = set("""good great excellent amazing beautiful clean neat tidy well maintained friendly helpful polite
courteous smooth easy quick fast spacious safe secure peaceful quiet calm lovely wonderful awesome nice
fantastic perfect convenient accessible affordable cheap fresh tasty delicious enjoyable fun worth recommend
recommended stunning scenic comfortable organised organized hygienic efficient reasonable pleasant gorgeous
superb ample adequate brilliant serene hassle-free""".split())
NEG = set("""bad poor terrible awful horrible worst dirty filthy unclean smelly smell stink stinks garbage litter
trash waste rude unhelpful slow long crowded packed jam jammed chaos chaotic unsafe dangerous slippery steep
broken damaged expensive overpriced costly scam disappointing disappointed mess messy congested noisy cramped
inadequate insufficient uncomfortable unorganised unorganized mismanaged harassed pushy aggressive overcrowded
shabby neglected unhygienic difficult hard tough hectic worse avoid horrible""".split())
NEGATORS = {"not", "no", "never", "hardly", "cannot", "nothing", "without", "lack", "lacks", "lacking",
            "zero", "neither", "barely"}
INTENS = {"very": 1.5, "extremely": 2.0, "really": 1.3, "too": 1.5, "so": 1.3, "quite": 1.2, "super": 1.5,
          "totally": 1.5, "absolutely": 1.6}

_ASPECT_LOOKUP = {}
for _a, _ws in ASPECTS.items():
    for _w in _ws:
        _ASPECT_LOOKUP.setdefault(_w, []).append(_a)


def _tokens(text: str):
    t = text.lower().replace("n't", " not").replace("’", "'")
    return re.findall(r"[a-z][a-z\-']*", t)


def _clauses(text: str):
    parts = re.split(r"[.!?;\n]+|\bbut\b|\bhowever\b|\balthough\b", text, flags=re.I)
    return [p.strip() for p in parts if p and p.strip()]


def _clause_score(tokens):
    score = 0.0
    for i, tok in enumerate(tokens):
        val = 1.0 if tok in POS else -1.0 if tok in NEG else 0.0
        if not val:
            continue
        if i > 0 and tokens[i - 1] in INTENS:
            val *= INTENS[tokens[i - 1]]
        if any(t in NEGATORS for t in tokens[max(0, i - 3):i]):
            val = -val * 0.8
        score += val
    # absence of a facility: "no parking", "lack of toilets" -> negative
    if score == 0:
        for i, tok in enumerate(tokens):
            if tok in _ASPECT_LOOKUP and any(t in NEGATORS for t in tokens[max(0, i - 2):i]):
                score = -1.0
                break
    return score


def analyze(text: str, rating: float | None = None) -> dict:
    """Return overall label + per-aspect sentiment for a piece of free text."""
    aspects: dict[str, float] = {}
    total, n = 0.0, 0
    for clause in _clauses(text):
        toks = _tokens(clause)
        s = _clause_score(toks)
        if s:
            total += 1 if s > 0 else -1
            n += 1
        hit = {a for t in toks for a in _ASPECT_LOOKUP.get(t, [])}
        for a in hit:
            if s:
                aspects[a] = aspects.get(a, 0) + (1 if s > 0 else -1)
    overall = total / n if n else 0.0
    if rating is not None and abs(overall) < 0.2:
        overall = (rating - 3) / 2.0
    label = "positive" if overall > 0.2 else "negative" if overall < -0.2 else "neutral"
    return {
        "label": label, "score": round(overall, 2),
        "aspects": [{"aspect": a, "label": ASPECT_LABELS[a],
                     "sentiment": "positive" if v > 0 else "negative" if v < 0 else "neutral"}
                    for a, v in aspects.items()],
    }


# ------------------------------------------------------------------ demonstration reviews
# Sentences used to generate clearly labelled DEMO reviews (source="demo"); they are not real visitor reviews.
_POS_S = {
    "cleanliness": ["The place was clean and well maintained.", "Toilets were neat and tidy."],
    "parking": ["Parking was easy and there was plenty of space."],
    "safety": ["Felt very safe with proper railings and guards."],
    "accessibility": ["Ramps made it accessible for my elderly parents."],
    "staff": ["The staff were friendly and helpful.", "Guides were polite and courteous."],
    "food_facilities": ["Great food stalls and plenty of benches."],
    "ticketing": ["Ticket counter was quick and the queue moved fast."],
    "crowding": ["Surprisingly peaceful, not crowded at all.", "Quiet and calm when we visited early."],
}
_NEG_S = {
    "cleanliness": ["The toilets were dirty and smelly.", "Garbage and litter in places, poor hygiene."],
    "parking": ["Parking was a nightmare, terrible traffic jam."],
    "safety": ["Some steps were slippery and felt unsafe."],
    "accessibility": ["Too many steep steps, not accessible for elderly visitors."],
    "staff": ["Some attendants were rude and unhelpful."],
    "food_facilities": ["Overpriced food and very little seating or shade."],
    "ticketing": ["Ticket queue was very long and slow."],
    "crowding": ["Extremely crowded and chaotic on the weekend.", "Overcrowded around midday."],
}


def demo_reviews(key: str, popularity: float, n: int = 6, seed: int = 11):
    """Deterministic demo reviews for one destination: busier places get more crowding/queue complaints."""
    import random
    import zlib
    rnd = random.Random(zlib.crc32(f"{seed}|{key}".encode()))
    weak = {"crowding": min(0.8, 0.25 * popularity), "ticketing": min(0.7, 0.2 * popularity),
            "parking": 0.3, "cleanliness": 0.3, "food_facilities": 0.2, "staff": 0.15,
            "safety": 0.15, "accessibility": 0.2}
    out = []
    for _ in range(n):
        aspects = rnd.sample(list(_POS_S), rnd.choice([1, 2, 2, 3]))
        sents, neg = [], 0
        for a in aspects:
            is_neg = rnd.random() < weak[a]
            neg += is_neg
            sents.append(rnd.choice((_NEG_S if is_neg else _POS_S)[a]))
        rating = max(1, min(5, round(4.5 - 1.3 * neg + rnd.uniform(-0.5, 0.5))))
        out.append((" ".join(sents), rating))
    return out
