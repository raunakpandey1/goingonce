"""Demo inventory for ACV + Copart, plus each car's Life Passport history.

Everything here is synthetic. A fixed random seed fills out a realistic-looking
marketplace, and a handful of hand-placed cars make the pitch story repeatable:
the Rochester Camry request always finds 3 good cars and catches 1 flood car
that was sold as salvage on Copart and now carries a clean title.
"""

from __future__ import annotations

import random
from functools import lru_cache

CURRENT_YEAR = 2026

CITIES: dict[str, tuple[str, float, float]] = {
    # city: (state, lat, lon)
    "Buffalo": ("NY", 42.886, -78.878),
    "Rochester": ("NY", 43.156, -77.608),
    "Syracuse": ("NY", 43.048, -76.147),
    "Albany": ("NY", 42.652, -73.756),
    "Binghamton": ("NY", 42.099, -75.918),
    "New York": ("NY", 40.713, -74.006),
    "Erie": ("PA", 42.129, -80.085),
    "Pittsburgh": ("PA", 40.440, -79.996),
    "Scranton": ("PA", 41.408, -75.662),
    "Harrisburg": ("PA", 40.273, -76.886),
    "Philadelphia": ("PA", 39.952, -75.165),
    "Cleveland": ("OH", 41.499, -81.694),
    "Akron": ("OH", 41.081, -81.519),
    "Columbus": ("OH", 39.961, -82.999),
    "Toledo": ("OH", 41.663, -83.555),
    "Detroit": ("MI", 42.331, -83.046),
}

# Rough "new car" anchor used to estimate today's market value.
MODEL_BASE: dict[tuple[str, str], int] = {
    ("Toyota", "Camry"): 26000,
    ("Toyota", "Corolla"): 22000,
    ("Toyota", "RAV4"): 31000,
    ("Toyota", "Tacoma"): 36000,
    ("Toyota", "Highlander"): 38000,
    ("Honda", "Civic"): 24000,
    ("Honda", "Accord"): 28000,
    ("Honda", "CR-V"): 30000,
    ("Ford", "F-150"): 42000,
    ("Ford", "Escape"): 27000,
    ("Ford", "Explorer"): 37000,
    ("Chevrolet", "Silverado 1500"): 41000,
    ("Chevrolet", "Equinox"): 27000,
    ("Chevrolet", "Malibu"): 23000,
    ("Ram", "1500"): 42000,
    ("Nissan", "Altima"): 25000,
    ("Nissan", "Rogue"): 28000,
    ("Hyundai", "Elantra"): 21000,
    ("Hyundai", "Tucson"): 27000,
    ("Jeep", "Grand Cherokee"): 39000,
    ("Jeep", "Wrangler"): 36000,
    ("Subaru", "Outback"): 30000,
    ("Tesla", "Model 3"): 38000,
}

TRIMS = ["LE", "SE", "XLE", "Sport", "EX", "LX", "SEL", "Limited", "Base", "Premium"]
DEALERS = [
    "Lakeshore Ford", "Elmwood Motors", "Niagara Auto Group", "Finger Lakes Toyota",
    "Keystone Honda", "Allegheny Chevrolet", "Buckeye Nissan", "Southtowns Auto",
    "Genesee Valley Motors", "Lehigh Auto Mall", "Cuyahoga Cars", "Mohawk Auto Sales",
]
INSURERS = ["State Farm", "GEICO", "Progressive", "Allstate", "Erie Insurance"]
COPART_DAMAGE = ["Front end", "Rear end", "Side", "Hail", "Flood", "Minor dents/scratches", "Mechanical"]
COLORS = ["White", "Black", "Silver", "Gray", "Blue", "Red"]
VIN_CHARS = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"


def market_value(make: str, model: str, year: int, mileage: int) -> int:
    """Estimated clean-title retail-ish value today (simple depreciation model)."""
    base = MODEL_BASE.get((make, model), 26000)
    age = max(CURRENT_YEAR - year, 0)
    value = base * (0.88 ** age)
    expected_miles = 12000 * max(age, 1)
    value -= (mileage - expected_miles) * 0.05
    return int(max(value, 1500) // 50 * 50)


def _vin(rng: random.Random) -> str:
    return "".join(rng.choice(VIN_CHARS) for _ in range(17))


def _car(**kw) -> dict:
    city = kw["city"]
    state, lat, lon = CITIES[city]
    car = {
        "id": kw["id"],
        "source": kw["source"],
        "vin": kw["vin"],
        "year": kw["year"],
        "make": kw["make"],
        "model": kw["model"],
        "trim": kw.get("trim", "LE"),
        "color": kw.get("color", "Silver"),
        "mileage": kw["mileage"],
        "price": kw["price"],
        "city": city,
        "state": state,
        "lat": lat,
        "lon": lon,
        "condition_grade": kw.get("condition_grade", 3.5),
        "title_status": kw.get("title_status", "clean"),
        "primary_damage": kw.get("primary_damage"),
        "seller": kw.get("seller", "Elmwood Motors"),
        "auction_ends": kw.get("auction_ends", "Today 2:00 PM"),
        "inspection_notes": kw.get("inspection_notes", "No major issues noted."),
    }
    car["market_value"] = market_value(car["make"], car["model"], car["year"], car["mileage"])
    return car


# --- Hand-placed demo cars --------------------------------------------------

TRAP_VIN = "4T1B11HK5LU903318"  # the flood Camry
ODOMETER_VIN = "1HGCV1F34JA228104"  # the rolled-back Accord


def _demo_cars() -> tuple[list[dict], dict[str, list[dict]]]:
    cars = [
        _car(id="ACV-20418", source="ACV", vin="4T1B11HK2KU781245", year=2019, make="Toyota",
             model="Camry", trim="SE", color="White", mileage=58400, price=11200, city="Syracuse",
             condition_grade=4.2, seller="Finger Lakes Toyota", auction_ends="Today 2:20 PM",
             inspection_notes="Light scratches on rear bumper. Tires 70%. Clean interior."),
        _car(id="ACV-20561", source="ACV", vin="4T1C11AK7LU334109", year=2020, make="Toyota",
             model="Camry", trim="LE", color="Gray", mileage=49900, price=11900, city="Erie",
             condition_grade=4.0, seller="Keystone Honda", auction_ends="Today 2:40 PM",
             inspection_notes="Small dent on passenger door. Tires 60%. Smells clean."),
        _car(id="ACV-20733", source="ACV", vin=TRAP_VIN, year=2020, make="Toyota", model="Camry",
             trim="LE", color="Blue", mileage=41200, price=10400, city="Scranton",
             condition_grade=3.8, seller="Lehigh Auto Mall", auction_ends="Today 2:05 PM",
             inspection_notes="New carpet. Fresh paint on lower doors. Faint musty smell. "
                              "No underbody photos provided."),
        _car(id="ACV-20302", source="ACV", vin="4T1B61HK8HU117320", year=2017, make="Toyota",
             model="Camry", trim="XSE", color="Black", mileage=88100, price=9800, city="Buffalo",
             condition_grade=3.6, seller="Southtowns Auto"),
        _car(id="ACV-20877", source="ACV", vin="4T1G11AK3MU552871", year=2021, make="Toyota",
             model="Camry", trim="SE", color="Red", mileage=31800, price=14600, city="Albany",
             condition_grade=4.5, seller="Mohawk Auto Sales"),
        _car(id="CPRT-51207", source="Copart", vin="4T1B11HK9JU640552", year=2018, make="Toyota",
             model="Camry", trim="LE", color="Silver", mileage=77300, price=8900, city="Cleveland",
             condition_grade=3.4, title_status="clean", primary_damage="Minor dents/scratches",
             seller="Dealer consignment", auction_ends="Today 3:00 PM",
             inspection_notes="Run and drive. Minor dents on rear quarter panel."),
        _car(id="CPRT-51388", source="Copart", vin="4T1B11HK1KU902211", year=2019, make="Toyota",
             model="Camry", trim="SE", color="White", mileage=64200, price=5200, city="Pittsburgh",
             condition_grade=1.8, title_status="salvage", primary_damage="Front end",
             seller="State Farm"),
        _car(id="CPRT-51420", source="Copart", vin="4T1C11AK0NU118845", year=2022, make="Toyota",
             model="Camry", trim="LE", color="Gray", mileage=22900, price=7600, city="Philadelphia",
             condition_grade=1.5, title_status="salvage", primary_damage="Flood",
             seller="GEICO"),
        _car(id="CPRT-51533", source="Copart", vin="4T1B11HK4KU335678", year=2019, make="Toyota",
             model="Camry", trim="XLE", color="Black", mileage=70100, price=12900, city="Columbus",
             condition_grade=3.9, title_status="clean", primary_damage="Minor dents/scratches",
             seller="Dealer consignment"),
        _car(id="ACV-20990", source="ACV", vin=ODOMETER_VIN, year=2018, make="Honda",
             model="Accord", trim="EX", color="Black", mileage=48000, price=13100, city="Toledo",
             condition_grade=3.9, seller="Buckeye Nissan",
             inspection_notes="Clean interior. Worn driver seat bolster for the mileage."),
    ]
    history = {
        TRAP_VIN: [
            {"date": "2021-03-14", "source": "ACV", "event": "Inspection",
             "detail": "Dealer trade-in in Harrisburg, PA. Grade 4.3, 12,400 miles.", "mileage": 12400},
            {"date": "2023-08-22", "source": "Copart", "event": "Insurance total loss: flood",
             "detail": "Progressive claim. Water line at door sills; interior and electrical exposure.",
             "mileage": 33100},
            {"date": "2023-09-05", "source": "Copart", "event": "Sold as salvage",
             "detail": "Sold to a rebuilder in Akron, OH. Copart photos show a water line inside the cabin.",
             "mileage": 33100},
            {"date": "2024-02-19", "source": "Title record", "event": "Re-titled out of state",
             "detail": "New title issued in another state with no salvage brand.", "mileage": 35800},
            {"date": "2026-10-02", "source": "ACV", "event": "Listed as clean title",
             "detail": "Seller listing does not disclose the flood or salvage history.", "mileage": 41200},
        ],
        ODOMETER_VIN: [
            {"date": "2022-06-10", "source": "Copart", "event": "Sold (dealer consignment)",
             "detail": "Odometer recorded at 91,250 miles.", "mileage": 91250},
            {"date": "2026-09-28", "source": "ACV", "event": "Inspection",
             "detail": "Odometer now reads 48,000 miles.", "mileage": 48000},
        ],
    }
    return cars, history


# --- Procedural marketplace -------------------------------------------------

@lru_cache(maxsize=1)
def load_catalog() -> tuple[tuple[dict, ...], dict[str, tuple[dict, ...]]]:
    rng = random.Random(2026)
    cars, history = _demo_cars()
    models = [k for k in MODEL_BASE if k != ("Toyota", "Camry")]  # keep the Camry story controlled
    city_names = list(CITIES)

    def add(source: str, n: int, start_id: int):
        for i in range(n):
            make, model = rng.choice(models)
            year = rng.randint(2014, 2024)
            age = CURRENT_YEAR - year
            mileage = max(4000, int(rng.gauss(12500 * age, 9000)))
            value = market_value(make, model, year, mileage)
            vin = _vin(rng)
            city = rng.choice(city_names)
            if source == "ACV":
                grade = round(rng.uniform(2.8, 4.8), 1)
                price = int(value * rng.uniform(0.86, 0.98) // 50 * 50)
                car = _car(id=f"ACV-{start_id + i}", source="ACV", vin=vin, year=year, make=make,
                           model=model, trim=rng.choice(TRIMS), color=rng.choice(COLORS),
                           mileage=mileage, price=price, city=city, condition_grade=grade,
                           seller=rng.choice(DEALERS),
                           auction_ends=f"Today {rng.choice(['1', '2', '3', '4'])}:{rng.choice(['00', '15', '30', '45'])} PM")
                events = [{"date": f"{CURRENT_YEAR}-09-{rng.randint(10, 30):02d}", "source": "ACV",
                           "event": "Inspection", "detail": f"Grade {grade}. {mileage:,} miles.",
                           "mileage": mileage}]
                if rng.random() < 0.05:  # a few hidden-history traps hide in the wider market
                    lost_year = rng.randint(2021, 2024)
                    lost_miles = int(mileage * rng.uniform(0.55, 0.8))
                    events.insert(0, {"date": f"{lost_year}-0{rng.randint(1, 9)}-15", "source": "Copart",
                                      "event": f"Insurance total loss: {rng.choice(['flood', 'front end', 'side'])}",
                                      "detail": f"{rng.choice(INSURERS)} claim. Sold as salvage.",
                                      "mileage": lost_miles})
                    events.insert(1, {"date": f"{lost_year + 1}-03-01", "source": "Title record",
                                      "event": "Re-titled out of state",
                                      "detail": "New title issued with no salvage brand.",
                                      "mileage": lost_miles + 2500})
            else:
                salvage = rng.random() < 0.7
                damage = rng.choice(COPART_DAMAGE[:-2]) if salvage else rng.choice(COPART_DAMAGE[-2:])
                grade = round(rng.uniform(1.0, 2.6) if salvage else rng.uniform(2.8, 4.0), 1)
                factor = rng.uniform(0.3, 0.55) if salvage else rng.uniform(0.78, 0.92)
                car = _car(id=f"CPRT-{start_id + i}", source="Copart", vin=vin, year=year, make=make,
                           model=model, trim=rng.choice(TRIMS), color=rng.choice(COLORS),
                           mileage=mileage, price=int(value * factor // 50 * 50), city=city,
                           condition_grade=grade, title_status="salvage" if salvage else "clean",
                           primary_damage=damage,
                           seller=rng.choice(INSURERS) if salvage else "Dealer consignment",
                           auction_ends=f"Today {rng.choice(['2', '3', '4'])}:00 PM")
                events = [{"date": f"{CURRENT_YEAR}-09-{rng.randint(10, 30):02d}", "source": "Copart",
                           "event": "Insurance total loss" if salvage else "Consigned by dealer",
                           "detail": f"Primary damage: {damage}.", "mileage": mileage}]
            cars.append(car)
            history[vin] = events

    add("ACV", 140, 21000)
    add("Copart", 160, 52000)
    for car in cars:  # every car gets at least one record
        history.setdefault(car["vin"], [{"date": f"{CURRENT_YEAR}-09-30", "source": car["source"],
                                         "event": "Inspection", "detail": car["inspection_notes"],
                                         "mileage": car["mileage"]}])
    return tuple(cars), {k: tuple(v) for k, v in history.items()}


def all_cars() -> list[dict]:
    return [dict(c) for c in load_catalog()[0]]


def car_history(vin: str) -> list[dict]:
    return [dict(e) for e in load_catalog()[1].get(vin, ())]


def get_car(car_id: str) -> dict | None:
    return next((dict(c) for c in load_catalog()[0] if c["id"] == car_id), None)
