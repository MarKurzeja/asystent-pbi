"""
Generuje celowo "brudny" plik z zamówieniami sklepu internetowego.
Uruchom: python data/generate_test_data.py

Plik ma typowe problemy polskich danych:
- kodowanie Windows-1250 i średnik jako separator,
- daty w różnych formatach,
- kwoty z przecinkiem dziesiętnym i spacjami tysięcy,
- warianty nazw miast, zbędne spacje, braki, duplikaty, wartości odstające,
- numery NIP w różnych formatach, część z błędną cyfrą kontrolną.
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


NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)


def make_nip() -> str:
    """Losuje poprawny NIP (10 cyfr, ostatnia to cyfra kontrolna)."""
    while True:
        digits = [random.randint(1, 9)] + [random.randint(0, 9) for _ in range(8)]
        check = sum(d * w for d, w in zip(digits, NIP_WEIGHTS)) % 11
        if check != 10:  # 10 nie może być cyfrą kontrolną - losujemy jeszcze raz
            return "".join(map(str, digits + [check]))


def fmt_nip(nip: str) -> str:
    """Zapisuje NIP w jednym z formatów spotykanych w prawdziwych plikach."""
    if random.random() < 0.05:  # 5% NIP-ów z literówką (zmieniona ostatnia cyfra)
        nip = nip[:9] + str((int(nip[9]) + 1) % 10)
    style = random.choices(["plain", "dashes", "pl"], weights=[60, 30, 10])[0]
    if style == "dashes":
        return f"{nip[:3]}-{nip[3:6]}-{nip[6:8]}-{nip[8:]}"
    if style == "pl":
        return "PL" + nip
    return nip


CUSTOMER_NIPS = {i: make_nip() for i in range(1, 121)}  # każdy klient ma swój NIP


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
    customer = random.randint(1, 120)
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
        "email_klienta": f"klient{customer}@example.pl",
        "nip_klienta": fmt_nip(CUSTOMER_NIPS[customer]),
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