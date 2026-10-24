# Data Assistant for Power BI

**A tool that prepares messy data for Power BI: it detects data quality issues, proposes a cleaning plan
and generates ready-to-use Power Query (M) code.** Built with Polish data formats in mind:
Windows-1250 encoding, decimal commas, `dd.mm.yyyy` dates, postcodes, NIP (tax ID) check digits
and spelling variants with Polish characters (`Kraków` / `krakow` / `KRAKÓW`).

The interface is available in **English and Polish**.

🇵🇱 *Wersja polska poniżej.*

## How it works

1. **Upload** a CSV or Excel file. Encoding and separator are detected automatically.
2. **Quality report**: every column gets a detected type, missing values, unique counts and a list of issues.
3. **Cleaning plan**: suggested steps with checkboxes and a before/after preview.
4. **Power Query code**: paste it into Power BI (*Get data → Blank query → Advanced Editor*).
   From then on, Power BI cleans every new version of the file on refresh.

### Wide files with multi-row headers

Many official Polish datasets (e.g. air quality data from GIOŚ) are published in a *wide* layout:
several header rows and one column per measuring station. The app detects this automatically,
**unpivots** the table into a long format (one row per date and station) and generates the matching
Power Query steps (`Table.UnpivotOtherColumns`).

It can also **check codes against a dictionary** (e.g. station metadata). GIOŚ has renamed some stations
over the years: in the 2019 PM10 file, 16 of 179 station codes are missing from the current metadata -
6 can be matched through the *old code* column, 10 cannot be matched at all. Without this check those
measurements would silently disappear when filtering by city in Power BI.

## Result in Power BI

The generated code runs in Power BI Desktop without errors - every column passes the *Column quality* check
with **0% errors**:

![Power Query result](powerbi-wynik.png)

Each cleaning step appears as a named step in *Applied Steps*:

![Applied steps](powerbi-kroki.png)

## Power BI dashboard: air quality in Polish cities (GIOŚ, 2018-2024)

The app was used to prepare **~960,000 daily measurements from 296 stations** (PM10, PM2.5 and
benzo(a)pyrene) published by GIOŚ, the Polish Chief Inspectorate of Environmental Protection.
The report is in [`smog.pbix`](smog.pbix) (Power BI Desktop), and all pages are also available as a
[PDF](docs/smog-dashboard.pdf). City and year are selected with slicers, so every page works for any city.

### 1. Overview
![Overview page](docs/dashboard-overview.png)

### 2. City vs national average
![City vs Poland page](docs/dashboard-vs-poland.png)

### 3. Station map
![Station map page](docs/dashboard-map.png)

### 4. Data quality
![Data quality page](docs/dashboard-data-quality.png)

### Key findings (Kraków)

- **Days above the PM10 daily limit (50 µg/m³) fell from ~76 in 2018 to ~21 in 2024 (-72%).**
  Since 2022 Kraków has stayed below the EU limit of 35 days per year.
- **The national average fell by a similar proportion**, and many cities improved even more
  (Elbląg -95%, Warszawa -89%, Katowice -81%). The 2019 ban on solid-fuel heating in Kraków was
  probably not the only driver: weather and nationwide programmes matter too.
- Air quality follows the **heating season**: monthly PM10 is roughly twice as high in winter as in summer.
- In 2024 the worst station was **ul. Bulwarowa** (Nowa Huta, industrial district) with 30 days above the limit.
- **Benzo(a)pyrene is still above the 1 ng/m³ target** (1.11 ng/m³ in 2024).

### Data model and DAX

- Star schema: `Pomiary` (fact table, measurements) with `Stacje` (stations) and `Kalendarz` (date table) as dimensions.
- Power Query: one function (`fnGios`) loads every yearly file from a folder, unpivots it and maps
  old station codes to current ones.
- DAX measures: average per station (`AVERAGEX`), comparison with 2018 (`CALCULATE` + `REMOVEFILTERS`),
  national benchmark that ignores the city filter, a dynamic page title (`SELECTEDVALUE`).
- Comparisons return blank when one of the years has no data, so closed stations do not show a false "-100%".

## Design decisions

- **Rules first, no black box.** Profiling and cleaning are plain, deterministic Python rules.
  The same rule always gives the same result, and every step can be explained.
- **Everything is read as text.** pandas guesses types by default and can silently corrupt data
  (e.g. strip leading zeros). Types are detected in a controlled way instead.
- **One step, two implementations.** Each cleaning step exists in pandas (for the preview) and in M
  (for Power BI), so the preview matches what Power BI produces.
- **The analyst decides.** Outliers are reported but never removed automatically - a 400-item order
  may be an error or a genuine large order.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python data/generate_test_data.py  # creates a deliberately messy sample file
streamlit run app.py               # opens the app in your browser
python -m pytest                   # runs the automated tests
```

### Air quality data (GIOŚ)

Raw files are not stored in the repository (they are large). Download the yearly archives from
[powietrze.gios.gov.pl/pjp/archives](https://powietrze.gios.gov.pl/pjp/archives), unzip them and place
the `PM10_24g`, `PM25_24g` and `BaP(PM10)_24g` files plus the station metadata in `data/gios/`.

## Known limitations

- Dates written with slashes are read as day/month/year (Polish and European convention).
  US-style month/day dates are not supported - `03/05/2025` cannot be told apart from 3 May.
- Wide-layout detection works for Excel files whose first column contains dates.

## Project structure

| File | Purpose |
|---|---|
| `app.py` | user interface (Streamlit) |
| `loading.py` | file loading, encoding and separator detection |
| `profiling.py` | column profiling and data quality rules |
| `cleaning.py` | cleaning steps (pandas) and Power Query code generation (M) |
| `reshape.py` | wide-layout detection, unpivot and dictionary (lookup) checks |
| `i18n.py` | English and Polish texts |
| `tests/` | automated tests (pytest) |
| `data/generate_test_data.py` | generator of messy test data |

## Roadmap

- [x] Data quality report with Polish-specific rules
- [x] Cleaning plan with before/after preview
- [x] Power Query code generation, tested in Power BI Desktop
- [x] English and Polish interface
- [x] Wide files with multi-row headers (unpivot) and dictionary checks
- [x] Power BI dashboard: air quality in Kraków vs other Polish cities (GIOŚ data, 2018-2024)
- [ ] Detection of duplicate keys and numeric missing-value codes (e.g. -999)
- [ ] AI suggestions for additional cleaning steps (e.g. filling a missing city from the postcode)

---

## 🇵🇱 Wersja polska

**Asystent danych dla Power BI** wykrywa problemy z jakością danych, proponuje plan czyszczenia
i generuje gotowy kod Power Query. Szczególny nacisk położony jest na polskie formaty danych:
kodowanie Windows-1250, przecinek dziesiętny, daty `dd.mm.rrrr`, kody pocztowe, cyfrę kontrolną NIP
oraz warianty nazw z polskimi znakami.

Kod wygenerowany przez aplikację został przetestowany w Power BI Desktop: wszystkie kolumny
przechodzą kontrolę *Column quality* z wynikiem **0% błędów**.

Na danych GIOŚ (ok. 960 tys. pomiarów z 296 stacji, lata 2018-2024) powstał **dashboard Power BI**
o jakości powietrza w polskich miastach. Najważniejszy wniosek: w Krakowie liczba dni z przekroczeniem
normy PM10 spadła o ok. 72%, ale średnia dla całej Polski spadła w podobnym stopniu, a wiele miast
poprawiło się jeszcze bardziej.

Instrukcja uruchomienia, zrzuty dashboardu i opis plików znajdują się w części angielskiej powyżej.
