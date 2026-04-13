📊 Adatelemző MI - Streamlit & Gemini 2.5 Flash
Ez a projekt egy Python és Streamlit alapú adatelemző webalkalmazás, amely a Google Gemini 2.5 Flash nagy nyelvi modelljét (LLM) használja. Célja, hogy a feltöltött nyers adatokból (CSV, Excel) laikusok számára is érthető, vizuális és szöveges elemzéseket, valamint letölthető PDF jelentéseket készítsen.

✨ Főbb funkciók
📂 Fájlkezelés és Alapstatisztika: CSV, XLS és XLSX fájlok beolvasása, hibakezeléssel. A numerikus adatokból statisztikai összegzés, magyarázat, grafikon készítés.

🤖 MI Statisztikai Magyarázat: A statisztikai mutatókat (átlag, szórás, min/max) az MI emberi nyelven, üzleti kontextusba helyezve értelmezi.

📈 Interaktív Grafikonkészítő: Több mint 10 féle Plotly diagram (oszlop, sáv, vonal, kör, hisztogram, szórás, hőtérkép, stb.) rajzolása egyedi paraméterekkel, trendvonalakkal és átlagvonalakkal.

🧠 Dinamikus MI Elemzés: Minden megrajzolt grafikonhoz egyedi, a képernyőn lévő vizualizációt és az adatokat figyelembe vevő MI összefoglaló kérhető.

💬 Multimodális Chat: Beépített chat felület, ahol a felhasználó az aktuális adatokról kérdezhet, vagy akár saját képeket (pl. más diagramokat) is feltölthet elemzésre a Gemini Vision képességeit kihasználva.

🚀 MI Felfedező (Auto-EDA): A rendszer értelmezi az adathalmazt, és  generál statisztikailag logikus, egyedi grafikonokat (JSON alapú, szigorú promptolással kikényszerített struktúrában).

📑 PDF Jelentéskészítés: Az elkészült grafikonokból, statisztikákból és MI elemzésekből egy kattintással letölthető, formázott PDF riport generálódik.

🛠️ Használt Technológiák
Frontend: Streamlit

Mesterséges Intelligencia: Google Generative AI (gemini-2.5-flash)

Adatkezelés: pandas

Adatvizualizáció: plotly.express

Statisztika: statsmodels (trendvonalakhoz)

Dokumentum generálás: fpdf (PDF export)

🚀 Telepítés és Futtatás
1. Klónozd a tárolót (Repository):
   git clone https://github.com/barnaibalazs/adatelemzo-mi.git
cd adatelemzo-mi
2. Telepítsd a szükséges csomagokat:
Győződj meg róla, hogy a Python telepítve van, majd futtasd:
pip install -r requirements.txt

3. API Kulcs beállítása:
A Gemini használatához szükséged lesz egy API kulcsra a Google AI Studio-ból.
A projekten belül, a .streamlit nevü mappában, azon belül pedig a secrets.toml fájlba írd bele az API kulcsodat: 
GEMINI_API_KEY = "ide_másold_az_api_kulcsodat"

5. Alkalmazás indítása:
Futtasd az alábbi parancsot a terminálban:
streamlit run app.py

🧠 Prompt Engineering és MI Integráció
A projekt haladó prompt technikákat alkalmaz:

Persona beállítás: Az MI "szenior adatelemző" és "üzleti tanácsadó" szerepkörökben válaszol.

Chain-of-Thought: Az elemzéseknél a prompt rákényszeríti az MI-t a lépésről lépésre történő gondolkodásra (jellemzők -> anomáliák -> üzleti következtetés).

Zero-shot strukturált kimenet (JSON): Az MI Felfedező modul szigorú paraméterezéssel (temperature=0.1) kényszeríti a modellt valid JSON tömbök generálására a kód-szintű feldolgozáshoz.

Dinamikus kontextus: A chat asszisztens a háttérben megkapja az aktuálisan generált grafikonok adatait és az adattábla mintáját is (RAG-jellegű működés).
