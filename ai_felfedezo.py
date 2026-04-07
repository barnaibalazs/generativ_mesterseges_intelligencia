import streamlit as st
import plotly.express as px
import pandas as pd
import tempfile
import copy
import uuid
import os
import json
import google.generativeai as genai
from fpdf import FPDF


# Ékezet-telenítő a PDF-hez
def tiszta_szoveg(szoveg):
    if not szoveg: return ""
    return str(szoveg).replace('ő', 'o').replace('ű', 'u').replace('Ő', 'O').replace('Ű', 'U').replace('–', '-').encode(
        'latin-1', 'replace').decode('latin-1')


def render_negyedik_ful(df):
    st.header("MI Grafikonkészítő")
    st.write("Hagyd, hogy a Mesterséges Intelligencia elemezze az adatokat, és mutasson rá a rejtett összefüggésekre!")

    if df is None or df.empty:
        st.warning("Kérlek, előbb tölts be egy adatbázist az oldalsávban!")
        return

    # Gomb a generálás indításához
    if st.button("🚀 Generálj grafikonokat!", type="primary"):
        with st.spinner("A Gemini tanulmányozza az oszlopokat és kitalálja a legjobb grafikonokat..."):
            try:
                # 1. Felkészítjük az adatokat a prompt-hoz (Megmondjuk az MI-nek, mik a lehetőségek)
                oszlop_infok = []
                for col in df.columns:
                    tipus = str(df[col].dtype)
                    egyedi_ertekek = df[col].nunique()
                    oszlop_infok.append(f"- Oszlopnév: '{col}', Típus: {tipus}, Egyedi értékek: {egyedi_ertekek}")

                oszlop_lista = "\n".join(oszlop_infok)


                prompt = f"""
                Te egy zseniális adatelemző vagy. Az alábbi táblázat oszlopai alapján találj ki 2 db logikus, statisztikailag és üzletileg érdekes diagramot!
                FONTOS: 
                - Ne keverd össze a szöveges és számos oszlopokat!
                - Ha pl. 'pie' (Kördiagram) a típus, az 'x' legyen a kategória (szöveg), az 'y' pedig az érték (szám).

                Az oszlopok listája:
                {oszlop_lista}

                KÉRLEK KIZÁRÓLAG EGY ÉRVÉNYES JSON TÖMBÖT VÁLASZOLJ, markdown formázás nélkül! A struktúra ez legyen:
                [
                  {{
                    "tipus": "bar" (lehet "bar", "scatter", "line", vagy "pie"),
                    "x": "az x tengelyre szánt oszlop PONTOS neve",
                    "y": "az y tengelyre szánt oszlop PONTOS neve",
                    "cim": "A grafikon profi címe",
                    "magyarazat": "Egy 2-3 mondatos szakmai elemzés, hogy mit és miért vizsgálsz ezzel."
                  }}
                ]
                """

                # 3. Gemini API hívás
                api_key = st.secrets["GEMINI_API_KEY"]
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')

                #  Alacsony temperature a szigorú JSON formátum kikényszerítéséhez
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(temperature=0.1)
                )

                # 4. JSON szöveg megtisztítása és feldolgozása
                valasz_szoveg = response.text.strip()
                if valasz_szoveg.startswith("```json"): valasz_szoveg = valasz_szoveg[7:]
                if valasz_szoveg.startswith("```"): valasz_szoveg = valasz_szoveg[3:]
                if valasz_szoveg.endswith("```"): valasz_szoveg = valasz_szoveg[:-3]

                utasitasok = json.loads(valasz_szoveg.strip())

                # 5. A receptek alapján megrajzoljuk a valódi grafikonokat!
                generalt_elemek = []
                for u in utasitasok:
                    tipus = u.get("tipus")
                    x_col = u.get("x")
                    y_col = u.get("y")
                    cim = u.get("cim")
                    magyarazat = u.get("magyarazat")

                    if x_col in df.columns and y_col in df.columns:
                        fig = None
                        if tipus == "bar":
                            fig = px.bar(df, x=x_col, y=y_col, title=cim)
                            fig.update_traces(marker_color='#2e86c1')  # 🔵 Profi Adat-Kék
                        elif tipus == "scatter":
                            fig = px.scatter(df, x=x_col, y=y_col, title=cim)
                            fig.update_traces(marker=dict(size=10, color='#e74c3c'))  # 🔴 Élénk Piros
                        elif tipus == "line":
                            fig = px.line(df, x=x_col, y=y_col, title=cim, markers=True)
                            fig.update_traces(line=dict(color='#27ae60', width=3),
                                              marker=dict(color='#27ae60', size=8))  # 🟢 Zöld
                        elif tipus == "pie":
                            # 🌈 Kellemes, színes paletta a kördiagramnak
                            szinek = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#c2c2f0', '#ffb3e6']
                            fig = px.pie(df, names=x_col, values=y_col, title=cim, hole=0.3,
                                         color_discrete_sequence=szinek)

                        if fig:
                            generalt_elemek.append({"cim": cim, "fig": fig, "szoveg": magyarazat})

                if generalt_elemek:
                    st.session_state.ai_generalt_grafikonok = generalt_elemek
                    st.success("✨ Kész! A Gemini önállóan kielemezte az oszlopokat és megrajzolta az új diagramokat!")
                else:
                    st.warning("A Gemini nem talált jó oszlopkombinációt a grafikonokhoz.")

            except Exception as e:
                st.error(f"Hiba történt az okos generálás közben: {e}")

    # ==========================================
    # MEGJELENÍTÉS (Balra grafikon, Jobbra szöveg)
    # ==========================================
    if "ai_generalt_grafikonok" in st.session_state:
        st.divider()
        st.subheader("📊 Felfedezett összefüggések")

        for elem in st.session_state.ai_generalt_grafikonok:
            col_graf, col_szoveg = st.columns([3, 2])  # 3:2 arány

            with col_graf:
                #  duplikációmentes megjelenítés
                fig_mutat = copy.deepcopy(elem["fig"])
                fig_mutat.update_layout(paper_bgcolor='white', plot_bgcolor='white', font_color='black')
                st.plotly_chart(fig_mutat, use_container_width=True, key=f"ai_graf_{uuid.uuid4().hex[:8]}")

            with col_szoveg:
                st.markdown(f"### {elem['cim']}")
                st.info(elem['szoveg'])

            st.markdown("<hr style='border: 0.5px solid #444;'>", unsafe_allow_html=True)

        # ==========================================
        # PDF LETÖLTÉS GOMB
        # ==========================================
        if st.button("📥 Generált Elemzés Letöltése (PDF)"):
            with st.spinner("PDF generálása..."):
                pdf = FPDF()
                temp_files = []

                for elem in st.session_state.ai_generalt_grafikonok:
                    try:
                        fig_mentes = copy.deepcopy(elem["fig"])

                        # ---  Hozzáadtuk a template="plotly" részt! ---
                        fig_mentes.update_layout(
                            template="plotly",
                            paper_bgcolor='white',
                            plot_bgcolor='white',
                            font_color='black'
                        )

                        temp_kep = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        fig_mentes.write_image(temp_kep.name, format="png", width=800, height=400, scale=2)
                        temp_files.append(temp_kep.name)

                        pdf.add_page()
                        pdf.set_font("Arial", "B", 14)
                        pdf.cell(200, 10, txt=tiszta_szoveg(elem['cim']), ln=True)

                        pdf.image(temp_kep.name, x=10, w=190)
                        pdf.ln(5)

                        pdf.set_font("Arial", "", 12)
                        pdf.multi_cell(0, 6, txt=tiszta_szoveg(elem['szoveg']))
                    except Exception as e:
                        st.error(f"Hiba a PDF generálásakor: {e}")

                pdf_output = pdf.output(dest='S').encode('latin-1')

                for tmp_file in temp_files:
                    try:
                        os.remove(tmp_file)
                    except:
                        pass

                st.download_button("⬇️ Kattints ide a PDF letöltéséhez", data=pdf_output,
                                   file_name="AI_Felfedezo_Jelentes.pdf", mime="application/pdf")

    # ==========================================
    # CHAT AZ MI-VEL (A grafikonokról)
    # ==========================================
    st.divider()
    st.subheader("💬 Beszélgess a Geminivel a látottakról!")

    # Egyedi kulcsot adunk a chatnek, hogy ne akadjon össze az 1. füllel
    if "chat_history_felfedezo" not in st.session_state:
        st.session_state.chat_history_felfedezo = []

    # Korábbi üzenetek megjelenítése
    for uzenet in st.session_state.chat_history_felfedezo:
        with st.chat_message(uzenet["szerep"]):
            st.markdown(uzenet["szoveg"])

    # Új kérdés bekérése
    kerdes = st.chat_input("Kérdezz rá egy anomáliára, vagy kérj mélyebb magyarázatot...", key="ai_felfedezo_chat")

    if kerdes:
        # Felhasználó kérdésének rögzítése
        st.session_state.chat_history_felfedezo.append({"szerep": "user", "szoveg": kerdes})
        with st.chat_message("user"):
            st.markdown(kerdes)

        # --- GEMINI VÁLASZGENERÁLÁS A GRAFIKONOK ALAPJÁN ---
        grafikon_kontextus = "A felhasználó a következő MI által generált grafikonokat látja:\n"
        if "ai_generalt_grafikonok" in st.session_state:
            for i, elem in enumerate(st.session_state.ai_generalt_grafikonok):
                grafikon_kontextus += f"{i + 1}. Grafikon címe: {elem['cim']}\nMagyarázat hozzá: {elem['szoveg']}\n\n"


        # Kinyerjük az adatok statisztikáját és egy mintát, pont mint az 1. fülön
        adat_statisztika = df.describe().to_string()
        adat_minta = df.head().to_string()

        prompt = f"""
        Te egy profi adatelemző asszisztens vagy. A felhasználó kérdése a generált grafikonokkal és az adatokkal kapcsolatban:
        "{kerdes}"

        [A KÉPERNYŐN LÉVŐ GRAFIKONOK ÉS MAGYARÁZATOK]:
        {grafikon_kontextus}

        [AZ ADATBÁZIS PONTOS STATISZTIKÁJA]:
        (Használd ezeket a számokat, ha a felhasználó konkrét értékekre, átlagokra, vagy maximumokra kíváncsi!)
        {adat_statisztika}

        [ADATMINTA (Első 5 sor)]:
        {adat_minta}

        Kérlek, válaszolj szakszerűen, pontos számokkal és tényekkel a fenti adatok alapján!
        """


        with st.spinner("A Gemini gondolkodik..."):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(prompt)
                mi_valasz = response.text

                st.session_state.chat_history_felfedezo.append({"szerep": "assistant", "szoveg": mi_valasz})
                with st.chat_message("assistant"):
                    st.markdown(mi_valasz)
            except Exception as e:
                st.error(f"Hiba történt a chat során: {e}")