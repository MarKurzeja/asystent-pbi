"""
Generuje celowo "brudny" plik z zamówieniami sklepu internetowego.
Uruchom: python data/generate_test_data.py

Plik ma typowe problemy polskich danych:
- kodowanie Windows-1250 i średnik jako separator,
- daty w różnych formatach,
- kwoty z przecinkiem dziesiętnym i spacjami tysięcy,
- warianty nazw miast, zbędne spacje, braki, duplikaty, wartości odstające.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)  # stałe ziarno -> za każdym razem ten sam plik

CITIES = ["Kraków", "Warszawa", "Gdańsk", "Wrocław", "Łódź", "Poznań"]
CITY_TYPOS = {"Kraków": ["krakow", "KRAKÓW", "Krakow "], "Łódź": ["Lodz", "łódź"], "Wrocław": ["Wroclaw"]}
POSTCODES = {"Kraków": "30-001", "Warszawa": "00-950", "Gdańsk": "80-001",
             "Wrocław": "50-001", "Łódź": "90-001", "Poznań": "60-001"}
PRODUCTS = [("Kawa ziarnista 1 kg", 89.99), ("Ekspres przelewowy", 349.00),
            ("Młynek do kawy", 159.50), ("Kubek termiczny", 64.90), ("Filtry papierowe", 12.99)]


def fmt_date(d: date) -> str:
    style = random.choices(["pl", "iso", "slash"], weights=[70, 20, 10])[0]
    return {"pl": d.strftime("%d.%m.%Y"), "iso": d.isoformat(), "slash": d.strftime("%d/%m/%Y")}[style]


def fmt_amount(x: float) -> str:
    text = f"{x:,.2f}".replace(",", " ").replace(".", ",")  # 1 234,56
    return text if random.random() > 0.05 else "brak"


rows = []
start = date(2025, 1, 1)
for i in range(1, 301):
    city = random.choice(CITIES)
    city_written = random.choice(CITY_TYPOS[city]) if city in CITY_TYPOS and random.random() < 0.3 else city
    name, price = random.choice(PRODUCTS)
    qty = random.randint(1, 4)
    if random.random() < 0.01:
        qty = 400  # błąd wprowadzania - wartość odstająca
    rows.append({
        "id_zamowienia": f"ZAM-{i:04d}",
        "data_zamowienia": fmt_date(start + timedelta(days=random.randint(0, 270))),
        "miasto": city_written if random.random() > 0.04 else "",
        "kod_pocztowy": POSTCODES[city],
        "produkt": name if random.random() > 0.1 else f"  {name}",
        "ilosc": str(qty),
        "kwota_brutto": fmt_amount(price * qty),
        "email_klienta": f"klient{random.randint(1, 120)}@example.pl",
    })

# Duplikaty: kilka zamówień wpisanych dwa razy
rows += random.sample(rows, 6)
random.shuffle(rows)

out = Path(__file__).parent / "zamowienia_brudne.csv"
with open(out, "w", encoding="cp1250", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter=";")
    writer.writeheader()
    writer.writerows(rows)

print(f"Zapisano {len(rows)} wierszy do {out}")
