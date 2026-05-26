import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
import io

# --- CONFIGURATION FIXE ---
SERPAPI_KEY = "c1b04560d953ef47f4909bdfbf369fae31a23eea80d7aa2b5916a38eefa0a7f2"
CITY_NAME = "Toulon 83000, France"

st.set_page_config(page_title="Grille Tarifaire Hôtels - Toulon", layout="wide")
st.title("📊 Grille Comparative des Prix par Nuit (Toulon)")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("🔍 Paramètres")
    # Affichage figé pour information
    st.text_input("Ville cible", value=CITY_NAME, disabled=True)
    
    checkin = st.date_input("Date d'arrivée", date.today() + timedelta(days=7))
    checkout = st.date_input("Date de départ", date.today() + timedelta(days=12))
    stars_filter = st.multiselect("Étoiles", ["5", "4", "3", "2"], default=["3", "4", "5"])
    search_button = st.button("🚀 Générer la grille")

# --- FONCTION API ---
@st.cache_data(ttl=3600)
def fetch_hotel_prices_for_day(single_date):
    """Va chercher les prix pour une seule nuit à Toulon"""
    url = "https://serpapi.com/search.json"
    next_day = single_date + timedelta(days=1)
    params = {
        "engine": "google_hotels",
        "q": CITY_NAME,
        "check_in_date": str(single_date),
        "check_out_date": str(next_day),
        "currency": "EUR",
        "gl": "fr",
        "hl": "fr",
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get('properties', [])
    except Exception as e:
        st.error(f"Erreur API le {single_date}: {e}")
    return []

# --- LOGIQUE DE CALCUL DE LA GRILLE ---
if search_button:
    nb_nuits = (checkout - checkin).days
    
    if nb_nuits <= 0:
        st.error("La date de départ doit être au moins un jour après l'arrivée.")
    elif nb_nuits > 10:
        st.warning("⚠️ Limite de 10 jours maximum pour préserver votre quota d'appels API.")
    else:
        grid_data = {}
        liste_dates = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 1. Génération des labels de colonnes (les dates)
        for i in range(nb_nuits):
            current_date = checkin + timedelta(days=i)
            liste_dates.append(current_date.strftime("%d/%m (%a)"))

        # 2. Collecte des données jour par jour
        for i in range(nb_nuits):
            current_date = checkin + timedelta(days=i)
            date_label = liste_dates[i]
            
            status_text.text(f"Analyse de la nuit du {date_label}...")
            progress_bar.progress((i + 1) / nb_nuits)
            
            hotels_day = fetch_hotel_prices_for_day(current_date)
            
            for h in hotels_day:
                stars = str(h.get('class', 0))
                if stars not in stars_filter and stars != "0":
                    continue
                    
                hotel_name = f"{h.get('name')} ({stars}⭐)"
                price = h.get('rate_per_night', {}).get('extracted_lowest')
                
                if hotel_name not in grid_data:
                    # Initialise toutes les dates de la période à 0 par défaut pour cet hôtel
                    grid_data[hotel_name] = {d: 0 for d in liste_dates}
                
                if price:
                    grid_data[hotel_name][date_label] = float(price)

        status_text.empty()
        progress_bar.empty()

        if grid_data:
            # Transformation en DataFrame
            df_grid = pd.DataFrame.from_dict(grid_data, orient='index')
            
            # Réorganisation stricte des colonnes dans l'ordre chronologique
            df_grid = df_grid[liste_dates]
            
            st.success(f"✅ Comparatif généré avec succès pour {len(df_grid)} hôtels à Toulon.")

            # --- AFFICHAGE DE LA GRILLE ---
            st.write("### 📅 Prix par nuitée (0 = Non disponible / Complet)")
            
            # Fonction pour colorer uniquement les prix > 0 (le min exclut le 0)
            def highlight_min_valid(s):
                valid_prices = s[s > 0]
                if not valid_prices.empty:
                    is_min = (s == valid_prices.min())
                    return ['background-color: #2e7d32; color: white; font-weight: bold' if v else '' for v in is_min]
                return [''] * len(s)

            st.dataframe(
                df_grid.style.apply(highlight_min_valid, axis=0)
                .format("{:.2f} €"),
                use_container_width=True
            )

            # --- EXPORT EXCEL ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_grid.to_excel(writer, sheet_name='Grille Toulon')
            
            st.download_button(
                label="📥 Télécharger la grille (Excel)",
                data=buffer.getvalue(),
                file_name=f"grille_hotels_toulon_{checkin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Aucun hôtel trouvé. Vérifiez les filtres ou le quota SerpApi.")
