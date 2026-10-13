# Asystent danych dla Power BI

Narzędzie, które przygotowuje „brudne” dane do Power BI: wykrywa problemy z jakością,
proponuje kroki czyszczenia i generuje gotowy kod Power Query (M) oraz miary DAX.
Szczególny nacisk na **polskie formaty danych**: kodowanie Windows-1250, przecinek
dziesiętny, daty `dd.mm.rrrr`, kody pocztowe, warianty nazw z polskimi znakami.

> Status: **etap 1 – wczytywanie i raport jakości danych** ✅

## Jak uruchomić

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

python data/generate_test_data.py   # tworzy przykładowy brudny plik
streamlit run app.py                # otwiera aplikację w przeglądarce
```

## Co już działa

- automatyczne wykrywanie kodowania (UTF-8 / Windows-1250) i separatora CSV,
- wykrywanie typu każdej kolumny: liczby (z przecinkiem i kropką), daty w różnych formatach,
  kody pocztowe, e-maile, tekst,
- wykrywanie problemów: braki, duplikaty, zbędne spacje, mieszane formaty dat,
  wartości niepasujące do typu, wartości odstające (IQR), warianty tej samej wartości
  („Kraków” / „krakow” / „KRAKÓW”),
- raport jakości do pobrania jako CSV.

## Struktura

| Plik | Rola |
|---|---|
| `app.py` | interfejs (Streamlit) |
| `loading.py` | wczytywanie plików, wykrywanie kodowania i separatora |
| `profiling.py` | profilowanie kolumn i wykrywanie problemów |
| `data/generate_test_data.py` | generator brudnych danych testowych |

## Decyzje projektowe

- **Wszystko wczytuję jako tekst.** pandas domyślnie zgaduje typy i potrafi po cichu
  zepsuć dane (np. obciąć zera wiodące). Typy wykrywam sama, w kontrolowany sposób.
- **Profilowanie bez AI.** Ta część musi być przewidywalna i powtarzalna. Model językowy
  pojawi się dopiero na etapie proponowania kroków czyszczenia – i dostanie tylko profil
  danych, nie cały plik.

## Plan

- [x] Etap 1 – wczytywanie i profilowanie
- [ ] Etap 2 – rozszerzone reguły (NIP, PESEL, wartości typu „brak”/„-”, kodowanie)
- [ ] Etap 3 – kroki czyszczenia + generowanie kodu Power Query (M)
- [ ] Etap 4 – AI proponuje plan czyszczenia
- [ ] Etap 5 – miary DAX + case study na prawdziwych danych
