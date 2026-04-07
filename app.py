import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from PIL import Image
import statsmodels.api as sm
import uuid
import ai_felfedezo


# 1. ALAPBEÁLLÍTÁSOK ÉS GLOBÁLIS MI DEFINIÁLÁSA
st.set_page_config(page_title="Adatelemző MI", layout="wide")

# API kulcs beolvasása és a modell felébresztése
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')





# --- FŐOLDAL FEJLÉC ÉS FÜLEK ---


st.title("Adatelemző MI")

tab1, tab2, tab3, tab4 = st.tabs(["Adatelemző", "Képelemző", "Jelentés Készítése","MI Grafikonkészítő"])

with tab1:
    # A bal és jobb oszlopokat beletettük az 1. fülbe!
    bal_oszlop, jobb_oszlop = st.columns([3, 1])

    with bal_oszlop:
        st.write("Tölts fel egy CSV vagy Excel fájlt (xlsx, xls), rajzoltass grafikont!")
        # Itt hozzáadtuk az 'xls'-t a listához
        uploaded_file = st.file_uploader("Válassz egy fájlt", type=["csv", "xlsx", "xls"])

    with jobb_oszlop:
        # 1. Doboz: Tippek
        st.info(
            "💡 **Tippek a Chathez:**\n\n"
            "* Melyik oszlopban van a legnagyobb érték?\n"
            "* Mennyi az átlaga a kiválasztott adatoknak?\n"
            "* Látsz valamilyen kiugró értéket (anomáliát)?\n"
            "* Foglald össze 2 mondatban a trendeket!"
        )

        st.divider()

        # 2. Doboz: Minta adat letöltése
        st.success("📂 **Nincs saját adatod?**\n\nTölts le egy minta CSV-t a teszteléshez!")

        # Minta adat generálása a háttérben
        minta_adat = pd.DataFrame({
            "Hónap": ["Január", "Február", "Március", "Április", "Május", "Június"],
            "Bevétel_HUF": [1200000, 1350000, 1100000, 1500000, 1650000, 1400000],
            "Kiadás_HUF": [800000, 850000, 900000, 820000, 950000, 880000],
            "Vevők_száma": [120, 135, 115, 150, 165, 140]
        })
        minta_csv = minta_adat.to_csv(index=False).encode('utf-8')

        st.download_button(
            label="⬇️ Minta adat letöltése (.csv)",
            data=minta_csv,
            file_name="minta_penzugyek.csv",
            mime="text/csv",
            use_container_width=True
        )

    # --- FÁJL BEOLVASÁSA ÉS ADATOK MEGJELENÍTÉSE ---
    if uploaded_file is not None:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        df = None  # Biztonsági változó

        try:
            #  beolvasás fájltípus szerint
            if file_extension == 'csv':
                try:
                    df = pd.read_csv(uploaded_file)
                except UnicodeDecodeError:
                    uploaded_file.seek(0)  # Visszatekerjük a fájlt
                    df = pd.read_csv(uploaded_file, encoding='latin-1')

            elif file_extension == 'xls':
                # Explicit módon megadjuk az xlrd motort a régi fájlokhoz
                df = pd.read_excel(uploaded_file, engine='xlrd')
            elif file_extension == 'xlsx':
                # Az újabb fájlokhoz pedig az openpyxl-t
                df = pd.read_excel(uploaded_file, engine='openpyxl')



            st.success("Fájl sikeresen betöltve!")
        except Exception as e:
            st.error(f"Hiba történt a fájl beolvasásakor: {e}")

        # Csak akkor megyünk tovább, ha sikeres volt a beolvasás!
        if df is not None:
            # --- 1. NYERS ADATOK ---
            st.subheader("1. Nyers Adatok")
            st.markdown("**Az adatok első 5 sora:**")
            st.dataframe(df.head(), use_container_width=True)

            st.divider()

            # --- 2. ÖSSZEGZŐ STATISZTIKA ÉS MI MAGYARÁZAT EGYMÁS MELLETT ---
            stat_oszlop, mi_oszlop = st.columns([2, 1])

            with stat_oszlop:
                st.markdown("**Összegző statisztika (számított értékek):**")
                st.dataframe(df.describe(), use_container_width=True)

            with mi_oszlop:
                st.markdown("**🤖 MI Statisztikai Magyarázat**")

                # Kapcsoló az MI-hez (alapból kikapcsolva)
                kell_stat_mi = st.toggle("Kérem az MI magyarázatot", value=False, key="toggle_stat_mi")

                if kell_stat_mi:
                    # Csak akkor fut le az MI, ha a kapcsoló be van kapcsolva
                    statisztika_szoveg = df.describe().to_string()
                    stat_hash = hash(statisztika_szoveg)

                    if "mi_stat_magyarazat" not in st.session_state or st.session_state.get(
                            "last_stat_hash") != stat_hash:
                        with st.spinner("Elemzés..."):
                            prompt_stat = f"""
                            Magyarázd el röviden és közérthetően a statisztikai táblázat értékeit (mean, std, min, max, stb.).
                            Csak a matematikai fogalmakat magyarázd az adatok tükrében, max 3-4 pontban.
                            Adatok összefoglalója:
                            {statisztika_szoveg}
                            """
                            try:
                                res = model.generate_content(prompt_stat)
                                st.session_state.mi_stat_magyarazat = res.text
                                st.session_state.last_stat_hash = stat_hash
                            except Exception as e:
                                st.error(f"Hiba: {e}")

                    if "mi_stat_magyarazat" in st.session_state:
                        st.info(st.session_state.mi_stat_magyarazat)
                else:
                    # Ezt látja a felhasználó, amíg be nem kapcsolja
                    st.write("👈 Kattints a fenti kapcsolóra a részletes magyarázathoz!")

            st.divider()
            #  2. Interaktív Adatvizualizáció...

            # 2. Interaktív Adatvizualizáció (Plotly)
            st.subheader("2. Interaktív Adatvizualizáció")
            oszlopok = df.columns.tolist()

            # Memória inicializálása grafikonokhoz
            if "grafikon_idk" not in st.session_state:
                st.session_state.grafikon_idk = [0]
            if "kovetkezo_id" not in st.session_state:
                st.session_state.kovetkezo_id = 1

            # Grafikonok rajzolása
            for i, graf_id in enumerate(st.session_state.grafikon_idk):
                st.markdown(f"#### {i + 1}. Grafikon")

                # Felső beállító sor
                viz1, viz2, viz3, torles = st.columns([3, 3, 3, 1])
                with torles:
                    st.write("");
                    st.write("")
                    if st.button("❌ Törlés", key=f"torol_{graf_id}"):
                        st.session_state.grafikon_idk.remove(graf_id)
                        st.rerun()
                with viz1:
                    diagram_tipus = st.selectbox("📊 Típus:", [
                        "Oszlopdiagram", "Sávdiagram", "Vonaldiagram", "Kördiagram",
                        "Hisztogram", "Szórásdiagram", "Dobozábra",
                        "Hőtérkép (Korreláció)", "Fatérkép", "Choropleth térkép"
                    ], key=f"tipus_{graf_id}")

                with viz2:
                    x_tengely = st.selectbox("X tengely:", oszlopok, key=f"x_{graf_id}")
                with viz3:
                    y_tengely = st.selectbox("Y tengely:", oszlopok, key=f"y_{graf_id}")

                # --- DIAGRAM CÍMÉNEK MEGADÁSA ---
                alap_cim = f"{y_tengely} alakulása {x_tengely} alapján"
                egyeni_cim = st.text_input("📝 Diagram címe:", value=alap_cim, key=f"cim_{graf_id}")

                # --- EXTRA BEÁLLÍTÁSOK (Szín, X/Y Rendezés, Átlagvonal) ---
                e1, e2, e3, e4 = st.columns(4)
                with e1:
                    valasztott_szin = st.color_picker("🎨 Szín:", "#1f77b4", key=f"szin_{graf_id}")
                with e2:
                    rendezes_x = st.selectbox("↔️ X rendezés:", ["Eredeti", "Növekvő", "Csökkenő"],
                                              key=f"rend_x_{graf_id}")
                with e3:
                    rendezes_y = st.selectbox("↕️ Y rendezés:", ["Eredeti", "Növekvő", "Csökkenő"],
                                              key=f"rend_y_{graf_id}")
                with e4:
                    mutasd_az_atlagot = False
                    if diagram_tipus in ["Oszlopdiagram", "Sávdiagram", "Vonaldiagram"]:
                        st.write("")
                        mutasd_az_atlagot = st.checkbox("📈 Átlagvonal", key=f"atlag_{graf_id}")

                # --- ADATOK SORBARENDJEZÉSE ---
                plot_df = df.copy()
                rendezes_oszlopok = []
                rendezes_irany = []

                if rendezes_x == "Növekvő":
                    rendezes_oszlopok.append(x_tengely)
                    rendezes_irany.append(True)
                elif rendezes_x == "Csökkenő":
                    rendezes_oszlopok.append(x_tengely)
                    rendezes_irany.append(False)

                if rendezes_y == "Növekvő":
                    rendezes_oszlopok.append(y_tengely)
                    rendezes_irany.append(True)
                elif rendezes_y == "Csökkenő":
                    rendezes_oszlopok.append(y_tengely)
                    rendezes_irany.append(False)

                if rendezes_oszlopok:
                    plot_df = plot_df.sort_values(by=rendezes_oszlopok, ascending=rendezes_irany)

                # --- DIAGRAM RAJZOLÁSA ÉS MI ELEMZÉS (OSZTOTT NÉZET) ---
                diagram_oszlop, ai_oszlop = st.columns([3, 1])

                with diagram_oszlop:
                    try:
                        fig = None  # Biztonsági alapérték

                        if diagram_tipus == "Oszlopdiagram":
                            fig = px.bar(plot_df, x=x_tengely, y=y_tengely, color_discrete_sequence=[valasztott_szin])
                            if mutasd_az_atlagot and pd.api.types.is_numeric_dtype(plot_df[y_tengely]):
                                fig.add_hline(y=plot_df[y_tengely].mean(), line_dash="dash", line_color="red")

                        elif diagram_tipus == "Sávdiagram":
                            fig = px.bar(plot_df, x=y_tengely, y=x_tengely, orientation='h',
                                         color_discrete_sequence=[valasztott_szin])
                            if mutasd_az_atlagot and pd.api.types.is_numeric_dtype(plot_df[y_tengely]):
                                fig.add_vline(x=plot_df[y_tengely].mean(), line_dash="dash", line_color="red")

                        elif diagram_tipus == "Vonaldiagram":
                            fig = px.line(plot_df, x=x_tengely, y=y_tengely, color_discrete_sequence=[valasztott_szin],
                                          markers=True)
                            if mutasd_az_atlagot and pd.api.types.is_numeric_dtype(plot_df[y_tengely]):
                                fig.add_hline(y=plot_df[y_tengely].mean(), line_dash="dash", line_color="red")


                        elif diagram_tipus == "Kördiagram":

                            #Kördiagram színezés

                            fix_szinek = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#c2c2f0', '#ffb3e6', '#ff6666',
                                          '#c2f0c2', '#ffb366', '#ff99ff']

                            fig = px.pie(plot_df, names=x_tengely, values=y_tengely, hole=0.3,
                                         color_discrete_sequence=fix_szinek)

                            fig.update_traces(marker=dict(line=dict(color=valasztott_szin, width=1)))

                        # --- ÚJ DIAGRAMOK INNENTŐL ---

                        elif diagram_tipus == "Hisztogram":

                            fig = px.histogram(plot_df, x=x_tengely, color_discrete_sequence=[valasztott_szin])




                        elif diagram_tipus == "Szórásdiagram":

                            kapcs_1, kapcs_2, kapcs_3 = st.columns(3)

                            with kapcs_1:

                                vonal_mutatasa = st.toggle("Pontok összekötése", key=f"vonal_szoras_{graf_id}")

                            with kapcs_2:

                                trend_vonal = st.toggle("Trendvonal (Statsmodels)", key=f"trend_szoras_{graf_id}")

                            with kapcs_3:

                                atlag_vonal = st.toggle("Átlagvonal", key=f"atlag_szoras_{graf_id}")

                            # 1. Alap diagram megrajzolása

                            fig = px.scatter(plot_df, x=x_tengely, y=y_tengely,
                                             color_discrete_sequence=[valasztott_szin])

                            # 2. Kézi Trendvonal (Explicit statsmodels használat)

                            if trend_vonal:

                                # Leellenőrizzük, hogy mindkét tengelyen számok vannak-e

                                if pd.api.types.is_numeric_dtype(plot_df[x_tengely]) and pd.api.types.is_numeric_dtype(
                                        plot_df[y_tengely]):

                                    try:

                                        # Üres cellák kiszűrése a pontos számításhoz

                                        tiszta_df = plot_df.dropna(subset=[x_tengely, y_tengely])

                                        # --- STATSMODELS MATEMATIKA INNENTŐL ---

                                        # X értékekhez hozzáadunk egy konstanst (az y = mx + b egyenlethez)

                                        X_stat = sm.add_constant(tiszta_df[x_tengely])

                                        Y_stat = tiszta_df[y_tengely]

                                        # Lineáris regressziós modell (OLS) felépítése és illesztése

                                        modell = sm.OLS(Y_stat, X_stat).fit()

                                        # Y pontok kiszámítása a trendvonalhoz

                                        trend_y = modell.predict(X_stat)

                                        # A kiszámolt vonal rárajzolása a meglévő grafikonra

                                        fig.add_scatter(x=tiszta_df[x_tengely], y=trend_y, mode='lines',
                                                        name='Trendvonal', line=dict(color='orange', width=3))

                                    except Exception as e:

                                        st.warning(f"⚠️ Hiba a trendvonal generálásakor: {e}")

                                else:

                                    # hiba jelzése

                                    st.warning(
                                        "⚠️ Trendvonalat csak akkor lehet rajzolni, ha mindkét tengelyen számok (pl. Kiadás és Profit) vannak, nem szöveg!")

                            # 3. Eredeti pontok összekötése (ha kérik)

                            if vonal_mutatasa:
                                fig.update_traces(mode='lines+markers', selector=dict(type='scatter', mode='markers'))

                            # 4. Átlagvonal

                            if atlag_vonal and pd.api.types.is_numeric_dtype(plot_df[y_tengely]):
                                fig.add_hline(y=plot_df[y_tengely].mean(), line_dash="dash", line_color="red",
                                              annotation_text="Átlag")

                        elif diagram_tipus == "Dobozábra":
                            # Adatok eloszlása és kiugró értékek (outliers)
                            fig = px.box(plot_df, x=x_tengely, y=y_tengely, color_discrete_sequence=[valasztott_szin])

                        elif diagram_tipus == "Hőtérkép (Korreláció)":
                            # numerikus adatok
                            numerikus_df = plot_df.select_dtypes(include='number')
                            if not numerikus_df.empty:
                                korrelacio = numerikus_df.corr()
                                fig = px.imshow(korrelacio, text_auto=True, aspect="auto",
                                                color_continuous_scale='RdBu_r')
                                egyeni_cim = "Korrelációs Mátrix (Hőtérkép)"
                            else:
                                st.warning("Nincs elegendő numerikus oszlop a korrelációs mátrixhoz.")


                        elif diagram_tipus == "Fatérkép":

                            # A terület (values) ÉS a szín (color) is az Y tengelyt tükrözi!

                            # Létrehozunk egy színskálát a fehértől

                            fig = px.treemap(

                                plot_df,

                                path=[px.Constant("Összes"), x_tengely],

                                values=y_tengely,

                                color=y_tengely,

                                color_continuous_scale=["#f0f0f0", valasztott_szin]
                                # Világosszürkétől a választott színig

                            )


                        elif diagram_tipus == "Choropleth térkép":

                            try:

                                fig = px.choropleth(plot_df, locations=x_tengely, color=y_tengely,
                                                    locationmode='country names', color_continuous_scale='Blues')

                            except Exception as e:

                                st.warning("🌍 Térkép hiba: Angol országnevek (pl. Hungary) kellenek az X tengelyre!")

                                fig = None

                            # ---------------------------------------------------------


                        if fig is not None:


                            fig.update_layout(title_text=f"<b>{egyeni_cim}</b>", title_x=0.5)

                            st.plotly_chart(fig, use_container_width=True)


                            if "mentett_grafikonok" not in st.session_state:
                                st.session_state.mentett_grafikonok = {}

                            import time

                            # Minden mentésnél kap egy egyedi számot (időbélyeget),
                            # így nem írják felül egymást a szótárban.
                            idobelyeg = int(time.time())
                            graf_id = f"graf_{idobelyeg}"

                            # Elmentjük a listába a grafikont és a címét
                            graf_id = f"{diagram_tipus}_{egyeni_cim}".replace(" ", "_")
                            st.session_state.mentett_grafikonok[graf_id] = {
                                "fig": fig,
                                "cim": egyeni_cim,
                                "tipus": diagram_tipus,  # <--- Ezt adjuk hozzá
                                "x_tengely": x_tengely,  # <--- Ezt adjuk hozzá
                                "y_tengely": y_tengely  # <--- Ezt adjuk hozzá
                            }



                    except Exception as e:

                        st.warning(f"⚠️ Ebből az oszlop-kombinációból nem rajzolható a kiválasztott diagram. (Ok: {e})")

                # --- A JOBB OLDALI MI ELEMZŐ SÁV ---
                with ai_oszlop:
                    st.markdown("### 🤖 MI Elemzés")

                    # Egyedi kapcsoló minden egyes grafikonhoz

                    kell_graf_mi = st.toggle(
                        "Kérem az MI elemzést",
                        value=False,
                        # beletesszük a diagram_tipus-t is a kulcsba!
                        key=f"mi_kapcsolo_{graf_id}"
                    )

                    if kell_graf_mi:
                        atlag_szoveg = ""
                        if mutasd_az_atlagot and pd.api.types.is_numeric_dtype(plot_df[y_tengely]):
                            atlag_ertek = plot_df[y_tengely].mean()
                            felette = (plot_df[y_tengely] > atlag_ertek).sum()
                            alatta = (plot_df[y_tengely] < atlag_ertek).sum()
                            osszes = len(plot_df)
                            szazalek_felett = (felette / osszes) * 100 if osszes > 0 else 0
                            szazalek_alatt = (alatta / osszes) * 100 if osszes > 0 else 0
                            atlag_szoveg = f"\nFONTOS: Az átlagvonal be van kapcsolva! Az átlag: {atlag_ertek:.2f}. A statisztika szerint az adatok {szazalek_felett:.1f}%-a ez felett, {szazalek_alatt:.1f}%-a pedig ez alatt van. Ezt az arányt mindenképp említsd meg a vázlatban!"

                        jelenlegi_allapot = f"{diagram_tipus}_{x_tengely}_{y_tengely}_{rendezes_x}_{rendezes_y}_{mutasd_az_atlagot}"

                        if f"ai_allapot_{graf_id}" not in st.session_state or st.session_state.get(
                                f"ai_allapot_{graf_id}") != jelenlegi_allapot:
                            with st.spinner("Elemzés..."):
                                prompt = f"""
                                                Te egy profi adatelemző vagy. Írj egy nagyon rövid, vázlatos (1-2 bulletpontos) összefoglalót a diagram trendjeiről.
                                                Diagram típusa: {diagram_tipus}, X tengely: {x_tengely}, Y tengely: {y_tengely}.
                                                {atlag_szoveg}

                                                Itt vannak az adatok (első pár sor):
                                                {plot_df[[x_tengely, y_tengely]].head(20).to_string()}
                                                """
                                try:
                                    valasz = model.generate_content(prompt)
                                    st.session_state[f"ai_szoveg_{graf_id}"] = valasz.text
                                    st.session_state[f"ai_allapot_{graf_id}"] = jelenlegi_allapot
                                except Exception as e:
                                    st.session_state[f"ai_szoveg_{graf_id}"] = f"⚠️ Hiba az MI elérésekor: {e}"

                        if f"ai_szoveg_{graf_id}" in st.session_state:
                            st.info(st.session_state[f"ai_szoveg_{graf_id}"])
                    else:
                        st.write("👈 Kapcsold be a gombot a grafikon trendjeinek elemzéséhez!")

                st.divider()

            # --- Új grafikon hozzáadása gomb ---
            if st.button("➕ Új grafikon hozzáadása"):
                st.session_state.grafikon_idk.append(st.session_state.kovetkezo_id)
                st.session_state.kovetkezo_id += 1
                st.rerun()

                # 3. Adatelőkészítés az MI-nek
            # 3. Adatelőkészítés az MI-nek
            st.subheader("3. MI Elemzés")

            statisztika = df.describe().to_string()

            if st.button("Generálj összefoglalót!"):
                if not api_key:
                    st.warning("Kérlek, először add meg az API kulcsot a bal oldalsávban!")
                else:
                    try:
                        with st.spinner("Az MI elemzi az adatokat..."):
                            genai.configure(api_key=api_key)
                            model = genai.GenerativeModel('gemini-2.5-flash')
                            prompt = f"""
                                    Te egy szenior adatelemző és üzleti tanácsadó vagy.
                                    A feladatod, hogy értelmezd az alábbi adathalmaz statisztikai összefoglalóját.

                                    Gondold végig az elemzést lépésről lépésre:
                                    1. Melyek az adatok legfőbb jellemzői (átlagok, minimumok, maximumok)?
                                    2. Milyen anomáliákat vagy kiugró értékeket látsz?
                                    3. Milyen üzleti következtetést lehet ebből levonni?

                                    Formázd a válaszod átlátható, rövid bekezdésekkel és felsorolásokkal!

                                    Az adatok statisztikája:
                                    {statisztika}
                                    """
                            response = model.generate_content(
                                prompt,
                                generation_config=genai.types.GenerationConfig(temperature=0.3)
                            )
                            # --- Elmentjük a memóriába! ---
                            st.session_state.mi_osszefoglalo = response.text

                    except Exception as e:
                        st.error(f"Hiba történt az API hívás során: {e}")

            # ---  Ha már le lett generálva korábban, akkor is kiírjuk a képernyőre ---
            if "mi_osszefoglalo" in st.session_state:
                st.write(st.session_state.mi_osszefoglalo)

        # --- 4. CHAT FUNKCIÓ (Multimodális - Kép + Szöveg) ---
        st.divider()
        st.subheader("💬 Kérdezz az adatokról vagy csatolj egy képet!")
        st.write("Használd a chatmező melletti gemkapocs ikont a képfeltöltéshez!")

        # 1. Chat történet (memória) inicializálása
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # 2. Korábbi üzenetek megjelenítése a képernyőn (képekkel együtt)
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                # Ha az üzenethez el volt mentve egy kép, azt is kirajzoljuk
                if "image" in message and message["image"] is not None:
                    st.image(message["image"], width=300)

        # 3. KÉPES CHAT BEMENET (st.chat_input accept_file paraméterrel)
        prompt = st.chat_input("Kérdezz, vagy csatolj képet...", accept_file=True,
                               file_type=["jpg", "jpeg", "png"])

        if prompt:
            # Kinyerjük a szöveget és a fájlt a bemenetből
            felhasznalo_kerdese = prompt.text
            feltoltott_kep = prompt.files[0] if prompt.files else None

            # Azonnal megjelenítjük a felhasználó kérdését és képét a chaten
            with st.chat_message("user"):
                if felhasznalo_kerdese:
                    st.markdown(felhasznalo_kerdese)
                if feltoltott_kep:
                    img = Image.open(feltoltott_kep)
                    st.image(img, width=300)

            # Mentjük a memóriába
            st.session_state.messages.append({
                "role": "user",
                "content": felhasznalo_kerdese if felhasznalo_kerdese else "📷 *[Kép elküldve]*",
                "image": img if feltoltott_kep else None
            })

            # --- TITKOS KONTEXTUS ÉPÍTÉSE A GEMININEK ---
            grafikon_kontextus = "A felhasználó a következő grafikonokat generálta és látja éppen a képernyőn:\n"
            if "mentett_grafikonok" in st.session_state and st.session_state.mentett_grafikonok:
                i = 1
                for graf_id, data in st.session_state.mentett_grafikonok.items():
                    cim = data.get("cim", "Ismeretlen cím")
                    tipus = data.get("tipus", "Ismeretlen típus")
                    x = data.get("x_tengely", "N/A")
                    y = data.get("y_tengely", "N/A")
                    korabbi_elemzes = st.session_state.get(f"ai_szoveg_{graf_id}", "Nincs korábbi elemzés.")

                    grafikon_kontextus += f"{i}. Grafikon címe: '{cim}' (Típus: {tipus}, X tengely: {x}, Y tengely: {y})\nKorábbi MI megállapítás: {korabbi_elemzes}\n\n"
                    i += 1
            else:
                grafikon_kontextus += "Jelenleg nincsenek generált grafikonok a képernyőn.\n"

            # Opcionális minta az adatokból
            adat_minta = f"Az adatbázis első 5 sora referenciaként:\n{df.head().to_markdown()}\n" if 'df' in locals() and df is not None else ""

            # MI válasz generálása
            with st.chat_message("assistant"):
                try:
                    with st.spinner("A Gemini elemzi a kérést és a kontextust..."):
                        # HA KÜLDÖTT KÉPET A FELHASZNÁLÓ (Kép + Szöveg elemzés):
                        if feltoltott_kep:
                            alap_kerdes = felhasznalo_kerdese if felhasznalo_kerdese else "Kérlek, vizuálisan elemezd ezt a képet, és írd le, mit látsz rajta!"
                            multimodalis_prompt = f"""Képzett adatelemzőként válaszolj az alábbi, jelenleg képernyőn lévő adatok ismeretében:
                                    {grafikon_kontextus}

                                    Kérdés/Kérés a mellékelt képpel kapcsolatban: {alap_kerdes}"""
                            # Elküldjük a képet ÉS a szöveget egyszerre
                            chat_valasz = model.generate_content([multimodalis_prompt, img])

                        # HA CSAK SZÖVEGET KÜLDÖTT (Sima CSV adat-chat + Grafikon kontextus):
                        else:
                            few_shot_prompt = f"""
                                    Te egy precíz adatelemző asszisztens vagy egy Streamlit alkalmazásban.

                                    [RENDSZERINFORMÁCIÓ A JELENLEGI ÁLLAPOTRÓL (Ezt látja a felhasználó)]:
                                    {grafikon_kontextus}
                                    {adat_minta}

                                    Az alábbi adatok statisztikája alapján (és a fenti grafikonok ismeretében) válaszolj a felhasználó kérdésére. 
                                    Ha a felhasználó az "első" vagy "második" grafikonra hivatkozik, használd a rendszerinformációt a beazonosításukhoz!

                                    [ADATOK STATISZTIKÁJA]:
                                    {statisztika}

                                    [AKTUÁLIS KÉRDÉS]
                                    Felhasználó: {felhasznalo_kerdese}
                                    Asszisztens:
                                    """
                            chat_valasz = model.generate_content(few_shot_prompt)

                    # Válasz kiírása és mentése
                    st.markdown(chat_valasz.text)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": chat_valasz.text, "image": None})

                except Exception as e:
                    st.error(f"Hiba a chat során: {e}")

# ==========================================
# 2. FÜL: KÉP ÉS GRAFIKON ELEMZŐ (GEMKAPCSOS CHAT)
# ==========================================
with tab2:
    st.header("Grafikon és Képelemző")
    st.write("Használd a lenti chatmezőt egy kép feltöltéséhez, és kérdezz róla szabadon!")

    # 1. Külön memória a Képelemző chatnek (hogy ne keveredjen a CSV chattel)
    if "kep_messages" not in st.session_state:
        st.session_state.kep_messages = []

    # 2. Korábbi üzenetek megjelenítése (képekkel együtt)
    for message in st.session_state.kep_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "image" in message and message["image"] is not None:
                st.image(message["image"], width=400)

    # 3. KÉPES CHAT BEMENET (accept_file=True)
    # Adunk neki egy 'key' paramétert, hogy a rendszer meg tudja különböztetni az 1. fül chatjétől!
    prompt = st.chat_input("Csatolj egy képet, vagy írj egy kérdést...", accept_file=True,
                           file_type=["jpg", "jpeg", "png"], key="kepes_chat_bemenet")

    if prompt:
        # Szöveg és kép kinyerése a bemenetből
        felhasznalo_kerdese = prompt.text
        feltoltott_kep = prompt.files[0] if prompt.files else None
        img = None

        # Üzenet megjelenítése a felhasználótól
        with st.chat_message("user"):
            if felhasznalo_kerdese:
                st.markdown(felhasznalo_kerdese)
            if feltoltott_kep:
                img = Image.open(feltoltott_kep)
                st.image(img, width=400)

        # Mentés a memóriába
        st.session_state.kep_messages.append({
            "role": "user",
            "content": felhasznalo_kerdese if felhasznalo_kerdese else "📷 *[Kép elküldve]*",
            "image": img if feltoltott_kep else None
        })

        # MI válasz generálása
        with st.chat_message("assistant"):
            with st.spinner("Az MI vizuálisan elemzi a kérést..."):
                try:
                    # Ha volt kép, ha nem, a promptot összerakjuk
                    alap_szoveg = felhasznalo_kerdese if felhasznalo_kerdese else "Képzett adatelemzőként írj egy részletes összefoglalót erről a grafikonról!"

                    # Ha küldött képet a felhasználó, betesszük a csomagba
                    if img:
                        valasz = model.generate_content([alap_szoveg, img])
                    else:
                        # Ha csak szöveget írt (kép nélkül)
                        valasz = model.generate_content(alap_szoveg)

                    # Válasz kiírása és mentése
                    st.markdown(valasz.text)
                    st.session_state.kep_messages.append({"role": "assistant", "content": valasz.text, "image": None})

                except Exception as e:
                    st.error(f"Hiba a kép elemzése során: {e}")

# --- 3. JELENTÉS KÉSZÍTÉSE FÜL ---
with tab3:
    st.header("📑 Jelentés készítő")

    # Ez a gomb törli a memóriából a korábban "beragadt" grafikonokat
    if st.button("🗑️ Összes mentett grafikon törlése"):
        st.session_state.mentett_grafikonok = {}
        st.success("A lista kiürítve! Most már generálhatsz új, egyedi grafikonokat az 1. fülön.")


    st.divider()  # Húzunk egy vonalat a két gomb közé

    st.write("Készíts PDF jelentést a teljes elemzésről (statisztika, MI összefoglalók, diagramok).")

    if st.button("📄 Jelentés elkészítése"):
        st.warning(f"Memóriában lévő grafikonok: {list(st.session_state.mentett_grafikonok.keys())}")
        if "mentett_grafikonok" not in st.session_state or len(st.session_state.mentett_grafikonok) == 0:
            st.warning("⚠️ Még nincsenek grafikonjaid! Kérlek, készíts párat az adatvizualizációs fülön!")
        else:
            with st.spinner("Jelentés összeállítása (ez eltarthat 10-20 másodpercig)..."):

                # --- 1. FEHÉR HÁTTERŰ ELŐNÉZET (UI) ---
                st.markdown(
                    '<div style="background-color: #0f1116; padding: 30px; border-radius: 10px; color: black; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">',
                    unsafe_allow_html=True)
                st.markdown("<h1 style='text-align: center; color: white;'>Adatelemzési Jelentés</h1><hr>",
                            unsafe_allow_html=True)

                # --- PDF INICIALIZÁLÁS ---
                from fpdf import FPDF
                import tempfile
                import os

                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(200, 10, txt="Adatelemzesi Jelentes", ln=True, align='C')
                pdf.ln(5)


                # Ékezet-telenítő funkció a PDF hibák elkerülésére
                def tiszta_szoveg(szoveg):
                    if not szoveg: return ""
                    return str(szoveg).replace('ő', 'o').replace('ű', 'u').replace('Ő', 'O').replace('Ű', 'U').replace(
                        '–', '-').encode('latin-1', 'replace').decode('latin-1')


                # ==========================================
                # 1. ÖSSZEGZŐ STATISZTIKA ÉS MI MAGYARÁZAT
                # ==========================================
                st.markdown("<h3 style='color: white;'>1. Összegző Statisztika</h3>", unsafe_allow_html=True)
                pdf.set_font("Arial", "B", 14)
                pdf.cell(200, 10, txt="1. Osszegzo Statisztika", ln=True)

                if 'df' in locals() and df is not None:
                    # Megjelenítés a fehér UI dobozban
                    st.dataframe(df.describe())

                    # Beírás a PDF-be (Courier betűtípussal, hogy oszlopban maradjanak a számok)
                    pdf.set_font("Courier", "", 9)
                    stat_szoveg = df.describe().round(2).to_string()
                    pdf.multi_cell(0, 5, txt=tiszta_szoveg(stat_szoveg))
                    pdf.ln(5)

                    # Ha van MI magyarázat a statisztikához
                    if "mi_stat_magyarazat" in st.session_state:
                        st.markdown(
                            f"<p style='color: #333;'><b>Statisztikai MI Értékelés:</b><br>{st.session_state.mi_stat_magyarazat}</p>",
                            unsafe_allow_html=True)

                        pdf.set_font("Arial", "I", 11)
                        pdf.multi_cell(0, 6, txt=tiszta_szoveg(
                            "Statisztikai MI Ertekeles:\n" + st.session_state.mi_stat_magyarazat))
                        pdf.ln(5)

                # ==========================================
                # 2. ÁLTALÁNOS MI ELEMZÉS (Az 1. fül 3. pontja)
                # ==========================================

                altalanos_mi = st.session_state.get("mi_osszefoglalo", "")

                if altalanos_mi:
                    st.markdown("<h3 style='color: white;'>2. Általános MI Elemzés</h3>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color: #333;'>{altalanos_mi}</p>", unsafe_allow_html=True)

                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(200, 10, txt="2. Altalanos MI Elemzes", ln=True)
                    pdf.set_font("Arial", "", 12)
                    pdf.multi_cell(0, 6, txt=tiszta_szoveg(altalanos_mi))
                    pdf.ln(5)

                # ==========================================
                # 3. DIAGRAMOK ÉS RÉSZLETES MI ELEMZÉSEK
                # ==========================================
                st.markdown("<h3 style='color: white;'>3. Vizualizációk és Trendek</h3>", unsafe_allow_html=True)
                pdf.set_font("Arial", "B", 14)
                pdf.cell(200, 10, txt="3. Vizualizaciok es Trendek", ln=True)
                pdf.ln(5)

                temp_files = []


                for graf_id, data in st.session_state.mentett_grafikonok.items():
                    fig = data["fig"]
                    cim = data["cim"]

                    # Cím kiírása a fehér lapra
                    st.markdown(f"<h4 style='color: #2e86c1; margin-top: 20px;'>{cim}</h4>", unsafe_allow_html=True)

                    # 1. KÉPERNYŐS ELŐNÉZET
                    import copy
                    import uuid

                    fig_elonezet = copy.deepcopy(fig)
                    fig_elonezet.update_layout(paper_bgcolor='#0f1116', plot_bgcolor='#0f1116', font_color='black')

                    egyedi_kulcs = f"elonezet_{graf_id}_{uuid.uuid4().hex[:8]}"
                    st.plotly_chart(fig_elonezet, use_container_width=True, key=egyedi_kulcs)

                    # 2. MI Szöveg kiírása (ha van)
                    ai_szoveg = st.session_state.get(f"ai_szoveg_{graf_id}", "")
                    if ai_szoveg:
                        st.markdown(
                            f"<p style='color: #1a1a1a; font-style: italic; padding: 10px; background-color: #f9f9f9; border-left: 4px solid #2e86c1;'><b>MI Elemzés:</b><br>{ai_szoveg}</p>",
                            unsafe_allow_html=True)
                    st.markdown("<hr style='border: 0.5px solid #ddd; margin: 20px 0;'>", unsafe_allow_html=True)

                    # 3. PDF KÉP MENTÉSE
                    try:
                        import tempfile

                        fig_mentes = copy.deepcopy(fig)
                        fig_mentes.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='black')

                        temp_kep = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        fig_mentes.write_image(temp_kep.name, format="png", width=800, height=400, scale=2)
                        temp_files.append(temp_kep.name)

                        # 4. Kép és szöveg PDF-be írása
                        pdf.add_page()
                        pdf.set_font("Arial", "B", 12)
                        pdf.cell(200, 10, txt=tiszta_szoveg(cim), ln=True)
                        pdf.image(temp_kep.name, x=10, w=190)
                        pdf.ln(5)

                        if ai_szoveg:
                            pdf.set_font("Arial", "I", 11)
                            pdf.multi_cell(0, 6, txt=tiszta_szoveg("MI Elemzes:\n" + ai_szoveg))

                    except Exception as e:
                        st.error(f"Hiba a PDF mentésekor ({cim}): {e}")

                # Fehér doboz lezárása a ciklus UTÁN!
                st.markdown('</div>', unsafe_allow_html=True)

                # Fehér előnézeti doboz lezárása
                st.markdown('</div>', unsafe_allow_html=True)

                # --- PDF LETÖLTÉS GENERÁLÁSA ---
                pdf_output = pdf.output(dest='S').encode('latin-1')

                # Szemét (ideiglenes képek) eltakarítása a merevlemezről
                for tmp_file in temp_files:
                    try:
                        os.remove(tmp_file)
                    except:
                        pass

                # Letöltés gomb megjelenítése
                st.success("✅ A komplex jelentés sikeresen elkészült!")
                st.download_button(
                    label="📥 PDF Letöltése",
                    data=pdf_output,
                    file_name="Teljes_Adatelemzesi_Jelentes.pdf",
                    mime="application/pdf"
                )





# --- 4.  FÜL ---
with tab4:

    if 'df' in locals() and df is not None:
        ai_felfedezo.render_negyedik_ful(df)
    else:
        st.info("Kérlek tölts fel egy adatbázist a bal oldali menüben!")