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
    
    # On ajoute "0" pour les établissements sans étoiles officielles
    stars_filter = st.multiselect(
        "Étoiles", ["5", "4", "3", "2", "1", "0"], 
        default=["2", "3", "4", "5"]
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
                    # On entre dans l'objet 'property' comme vu dans le debug
                    p = h.get('property', {})
                    
                    # 1. Extraction des Étoiles
                    stars_val = p.get('propertyClass', 0)
                    stars_str = str(int(stars_val))
                    
                    if stars_str not in stars_filter:
                        continue
                    
                    # 2. Extraction du Prix (Caché dans property -> priceBreakdown -> grossPrice)
                    price_info = p.get('priceBreakdown', {}).get('grossPrice', {})
                    price = price_info.get('value', 0)
                    
                    if price == 0: continue
                    
                    # 3. Nom de l'hôtel et Chambre
                    name = p.get('name', 'Hôtel')
                    # Le type de chambre n'est pas toujours clair, on utilise wishlistName ou accessibilityLabel
                    room_info = p.get('wishlistName', 'Chambre') 

                    if room_filter != "Toutes" and room_filter.lower() not in room_info.lower():
                        continue

                    final_data.append({
                        "Hôtel": name,
                        "Étoiles": f"{stars_str} ⭐",
                        "Prix Booking (€)": round(float(price), 2),
                        "Note": p.get('reviewScore', 'N/A'),
                        "Ville": p.get('wishlistName', city_name),
                        "Expedia (Simulé)": round(float(price) * 0.98, 2),
                        "Direct (Simulé)": round(float(price) * 0.95, 2)
                    })

                if final_data:
                    df = pd.DataFrame(final_data)
                    st.success(f"✅ {len(df)} hôtels trouvés")
                    
                    # Style du tableau (Surligne le moins cher)
                    def highlight_min(s):
                        is_min = s == s.min()
                        return ['background-color: #d4edda' if v else '' for v in is_min]

                    st.dataframe(
                        df.sort_values("Prix Booking (€)")
                        .style.apply(highlight_min, axis=1, subset=["Prix Booking (€)", "Expedia (Est.)", "Direct (Est.)"], ignore_index=True)
                        .format({"Prix Booking (€)": "{:.2f}", "Expedia (Est.)": "{:.2f}", "Direct (Est.)": "{:.2f}"}),
                        use_container_width=True
                    )
                else:
                    st.warning("Aucun hôtel trouvé avec vos filtres d'étoiles/chambres.")
            else:
                st.error("L'API n'a pas renvoyé de liste d'hôtels.")
        else:
            st.error("Ville non trouvée.")
