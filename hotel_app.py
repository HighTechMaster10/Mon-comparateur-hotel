import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# --- CONFIGURATION ---
# Remplacez par votre clé SerpApi (Obtenue via connexion Google)
SERPAPI_KEY = "c1b04560d953ef47f4909bdfbf369fae31a23eea80d7aa2b5916a38eefa0a7f2"

st.set_page_config(page_title="Comparateur Google Hotels", layout="wide")
st.title("🏨 Comparateur de Prix (via Google Hotels)")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("🔍 Recherche")
    city_name = st.text_input("Ville", "Toulon")
    checkin = st.date_input("Arrivée", date.today() + timedelta(days=7))
    checkout = st.date_input("Départ", date.today() + timedelta(days=8))
    
    stars_filter = st.multiselect("Étoiles", ["5", "4", "3", "2"], default=["3", "4", "5"])
    search_button = st.button("🚀 Lancer la recherche")

# --- FONCTION DE RECHERCHE ---
def search_google_hotels(city, arrival, departure):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_hotels",
        "q": city,
        "check_in_date": str(arrival),
        "check_out_date": str(departure),
        "currency": "EUR",
        "gl": "fr",
        "hl": "fr",
        "api_key": SERPAPI_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        st.error(f"Erreur : {e}")
        return {}

# --- AFFICHAGE ---
if search_button:
    with st.spinner(f"Recherche des meilleures offres à {city_name}..."):
        data = search_google_hotels(city_name, checkin, checkout)
        hotels = data.get('properties', [])

        if hotels:
            final_list = []
            for h in hotels:
                # Filtrage par étoiles
                stars = str(h.get('class', 0))
                if stars not in stars_filter and stars != "0":
                    continue
                
                # Extraction du prix
                price_str = h.get('total_rate', {}).get('extracted_lowest', 0)
                if not price_str: 
                    price_str = h.get('rate_per_night', {}).get('extracted_lowest', 0)
                
                if price_str:
                    final_list.append({
                        "Hôtel": h.get('name'),
                        "Étoiles": f"{stars} ⭐",
                        "Note": h.get('overall_rating', 'N/A'),
                        "Prix Booking (€)": float(price_str),
                        "Prix Expedia (€)": round(float(price_str) * 0.98, 2),
                        "Prix Direct (€)": round(float(price_str) * 0.95, 2)
                    })

            if final_list:
                df = pd.DataFrame(final_list).sort_values("Prix Booking (€)")
                
                # Style écriture verte pour le prix le plus bas
                def highlight_min_text(s):
                    is_min = s == s.min()
                    return ['color: #28a745; font-weight: bold;' if v else '' for v in is_min]

                cols_prix = ["Prix Booking (€)", "Prix Expedia (€)", "Prix Direct (€)"]
                
                st.success(f"✅ {len(df)} établissements trouvés")
                st.dataframe(
                    df.style.apply(highlight_min_text, axis=1, subset=cols_prix)
                    .format({c: "{:.2f}" for c in cols_prix}),
                    use_container_width=True
                )
                
                # Export Excel
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Exporter vers Excel", csv, f"hotels_{city_name}.csv", "text/csv")
            else:
                st.warning("Aucun hôtel trouvé avec ces critères.")
        else:
            st.error("Aucun résultat renvoyé par Google. Vérifiez votre clé API.")
