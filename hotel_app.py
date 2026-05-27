import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
import io
import os  # Pour lire les variables d'environnement

# --- CONFIGURATION SÉCURISÉE ---
# 1) En priorité : clé stockée dans les secrets Streamlit (Cloud)
# 2) Sinon : variable d'environnement Windows SERPAPI_KEY
SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", os.environ.get("SERPAPI_KEY", ""))

CITY_NAME = "Toulon 83000, France"

# Ta liste exacte des noms d'hôtels renvoyés par l'API
HOTELS_CIBLES = [
    "Grand Hôtel Dauphiné Toulon - Boutique Hotel & Suites",
    "Grand Hôtel de la Gare Toulon - Boutique Hôtel",
    "Hôtel Amirauté",
    "Hôtel ibis Styles Toulon Centre Port",
    "Hôtel ibis budget Toulon Centre",
    "B&B HOTEL Toulon Centre Gare",
    "L' Eautel Toulon Port",
    "OKKO Hotels Toulon Centre",
    "Holiday Inn Toulon City Centre",
    "Best Western Plus Hôtel La Corniche",
    "Hôtel Les Voiles"
]

st.set_page_config(page_title="Grille Tarifaire Hôtels - Toulon", layout="wide")

# --- MASQUER LE COMPTE, LE BOUTON DE DEPLOIEMENT ET LE MENU DEVELOPPEUR ---
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stStatusWidget"] {visibility: hidden;}
    [data-testid="stDecoration"] {display:none;}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📊 Grille Comparative Ciblée - Toulon (83000)")

# --- SIGNATURE ---
st.markdown("*Application réalisée par Christophe ARNAUD, (droits réservés)*")
st.write("---") 

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("🔍 Paramètres")
    st.text_input("Ville cible", value=CITY_NAME, disabled=True)
    
    checkin = st.date_input("Date d'arrivée", date.today() + timedelta(days=7))
    checkout = st.date_input("Date de départ", date.today() + timedelta(days=12))
    search_button = st.button("🚀 Générer la grille ciblée")

# --- FONCTION API ---
@st.cache_data(ttl=3600)
def fetch_hotel_prices_for_day(single_date):
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
    # Double vérification pour bloquer le script si la clé est vide
    if not SERPAPI_KEY:
        st.error(
            "❌ Clé API introuvable.\n\n"
            "- Sur Streamlit Cloud : ajoute SERPAPI_KEY dans *Settings → Secrets*.\n"
            "- En local Windows : crée la variable d'environnement SERPAPI_KEY."
        )
    else:
        nb_nuits = (checkout - checkin).days
        
        if nb_nuits <= 0:
            st.error("La date de départ doit être au moins un jour après l'arrivée.")
        elif nb_nuits > 10:
            st.warning("⚠️ Limite de 10 jours maximum pour préserver votre quota d'appels API.")
        else:
            # Création des en-têtes de colonnes (Dates)
            liste_dates = [(checkin + timedelta(days=i)).strftime("%d/%m (%a)") for i in range(nb_nuits)]
            
            # Initialisation de la grille
            grid_data = {name: {d: 0.0 for d in liste_dates} for name in HOTELS_CIBLES}
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Collecte des données jour par jour
            for i in range(nb_nuits):
                current_date = checkin + timedelta(days=i)
                date_label = liste_dates[i]
                
                status_text.text(f"Analyse de la nuit du {date_label}...")
                progress_bar.progress((i + 1) / nb_nuits)
                
                hotels_day = fetch_hotel_prices_for_day(current_date)
                
                for h in hotels_day:
                    api_hotel_name = h.get('name', '').strip()
                    price = h.get('rate_per_night', {}).get('extracted_lowest')
                    
                    matched_name = None
                    for cible in HOTELS_CIBLES:
                        c_low = cible.lower().strip()
                        a_low = api_hotel_name.lower().strip()
                        
                        if c_low in a_low or a_low in c_low:
                            matched_name = cible
                            break
                    
                    if matched_name and price:
                        grid_data[matched_name][date_label] = float(price)

            status_text.empty()
            progress_bar.empty()

            if grid_data:
                df_grid = pd.DataFrame.from_dict(grid_data, orient='index')
                df_grid = df_grid[liste_dates]
                
                st.success(f"✅ Comparatif généré avec succès pour tes {len(df_grid)} hôtels cibles.")

                st.write("### 📅 Prix par nuitée (0.00 € = Complet ou non trouvé)")
                
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

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_grid.to_excel(writer, sheet_name='Grille Toulon Ciblée')
                
                st.download_button(
                    label="📥 Télécharger la grille ciblée en format Excel",
                    data=buffer.getvalue(),
                    file_name=f"grille_hotels_toulon_{checkin}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("Aucune donnée n'a pu être extraite. Vérifie ton quota SerpApi.")
