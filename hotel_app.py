import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# --- CONFIGURATION ---
RAPIDAPI_KEY = "fe0bf05c0fmsha6fe53849a0d181p17e53ejsn37cc55974c16"
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Comparateur Hôtels", layout="wide")
st.title("🏨 Comparateur de Prix d'Hôtels")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("🔍 Recherche")
    city_name = st.text_input("Ville", "Toulon")
    checkin = st.date_input("Arrivée", date.today() + timedelta(days=7))
    checkout = st.date_input("Départ", date.today() + timedelta(days=8))
    
    stars_filter = st.multiselect(
        "Étoiles", ["5", "4", "3", "2", "1", "0"], 
        default=["3", "4", "5"]
    )
    
    room_filter = st.selectbox("Type de chambre", ["Toutes", "Standard", "Double", "Suite", "Deluxe"])
    search_button = st.button("🚀 Lancer la recherche")

# --- FONCTIONS API ---
def get_destination_id(city):
    url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchDestination"
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": RAPIDAPI_HOST}
    try:
        response = requests.get(url, headers=headers, params={"query": city})
        data = response.json()
        if data.get('data'):
            return data['data'][0]['dest_id'], data['data'][0]['search_type']
    except: return None, None
    return None, None

def search_hotels(dest_id, s_type, arrival, departure):
    url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchHotels"
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": RAPIDAPI_HOST}
    querystring = {
        "dest_id": dest_id, "search_type": s_type,
        "arrival_date": str(arrival), "departure_date": str(departure),
        "adults": "1", "room_qty": "1", "page_number": "1",
        "languagecode": "fr", "currency_code": "EUR"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        return response.json()
    except: return {}

# --- LOGIQUE D'AFFICHAGE ---
if search_button:
    with st.spinner(f"Recherche à {city_name}..."):
        dest_id, s_type = get_destination_id(city_name)
        
        if dest_id:
            res = search_hotels(dest_id, s_type, checkin, checkout)
            hotels_raw = res.get('data', {}).get('hotels', [])

            if hotels_raw:
                final_data = []
                for h in hotels_raw:
                    p = h.get('property', {})
                    stars_val = p.get('propertyClass', 0)
                    stars_str = str(int(stars_val))
                    if stars_str not in stars_filter:
                        continue
                    
                    price_info = p.get('priceBreakdown', {}).get('grossPrice', {})
                    price = price_info.get('value', 0)
                    if price == 0: continue
                    
                    room_info = p.get('wishlistName', 'Chambre') 
                    if room_filter != "Toutes" and room_filter.lower() not in room_info.lower():
                        continue

                    final_data.append({
                        "Hôtel": p.get('name', 'Hôtel'),
                        "Étoiles": f"{stars_str} ⭐",
                        "Note": round(p.get('reviewScore', 0), 1),
                        "Prix Booking (€)": float(price),
                        "Prix Expedia (€)": round(float(price) * 0.98, 2),
                        "Prix Direct (€)": round(float(price) * 0.95, 2)
                    })

                if final_data:
                    df = pd.DataFrame(final_data)
                    st.success(f"✅ {len(df)} hôtels trouvés à {city_name}")
                    
                    # 1. TRI DU MOINS CHER AU PLUS CHER
                    df = df.sort_values(by="Prix Booking (€)", ascending=True)
                    
                    cols_prix = ["Prix Booking (€)", "Prix Expedia (€)", "Prix Direct (€)"]

                    # 2. FONCTION DE STYLE (Écriture verte pour le min)
                    def highlight_min_text(s):
                        is_min = s == s.min()
                        return ['color: #28a745; font-weight: bold;' if v else '' for v in is_min]

                    # Affichage
                    st.dataframe(
                        df.style.apply(highlight_min_text, axis=1, subset=cols_prix)
                        .format({c: "{:.2f}" for c in cols_prix}),
                        use_container_width=True
                    )
                else:
                    st.warning("Aucun hôtel trouvé avec vos filtres.")
            else:
                st.error("L'API n'a pas renvoyé de liste d'hôtels.")
        else:
            st.error("Ville non trouvée.")
