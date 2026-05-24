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
        default=["1", "2", "3", "4", "5", "0"]
    )
    room_filter = st.selectbox("Type de chambre", ["Toutes", "Standard", "Double", "Suite", "Deluxe"])
    
    debug_mode = st.checkbox("Afficher les données brutes (Debug)")
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
        "units": "metric", "languagecode": "fr", "currency_code": "EUR"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        return response.json()
    except: return {}

# --- EXÉCUTION ---

if search_button:
    with st.spinner("Recherche en cours..."):
        dest_id, s_type = get_destination_id(city_name)
        
        if dest_id:
            full_response = search_hotels(dest_id, s_type, checkin, checkout)
            hotels_raw = full_response.get('data', {}).get('hotels', [])

            # DEBUG : Affiche ce que l'API renvoie vraiment si on ne trouve rien
            if debug_mode or not hotels_raw:
                with st.expander("🔍 Analyse des données reçues (Debug)"):
                    st.write(full_response)

            if hotels_raw:
                final_list = []
                for h in hotels_raw:
                    # On essaie plusieurs chemins pour trouver les infos (plus robuste)
                    prop = h.get('property', h) # Parfois c'est à la racine
                    
                    # 1. Étoiles (parfois propertyClass, parfois class)
                    stars_val = prop.get('propertyClass', prop.get('class', 0))
                    try: stars = str(int(float(stars_val)))
                    except: stars = "0"
                    
                    if stars not in stars_filter:
                        continue
                    
                    # 2. Prix (on teste plusieurs emplacements courants)
                    price_bd = h.get('priceBreakdown', {})
                    price = price_bd.get('grossPrice', {}).get('value', 
                            price_bd.get('allInclusivePrice', {}).get('value', 
                            h.get('min_total_price', 0)))
                    
                    if price == 0: continue
                    
                    # 3. Chambre
                    room_name = prop.get('wishlistName', h.get('hotel_name', 'Chambre'))
                    if room_filter != "Toutes" and room_filter.lower() not in room_name.lower():
                        continue

                    final_list.append({
                        "Hôtel": prop.get('name', h.get('hotel_name')),
                        "Étoiles": f"{stars} ⭐",
                        "Chambre": room_name,
                        "Prix Booking (€)": float(price),
                        "Expedia (Est.)": round(float(price) * 0.98, 2),
                        "Direct (Est.)": round(float(price) * 0.95, 2)
                    })

                if final_list:
                    df = pd.DataFrame(final_list)
                    st.success(f"✅ {len(df)} hôtels trouvés")
                    st.dataframe(df.sort_values("Prix Booking (€)"), use_container_width=True)
                else:
                    st.warning("Aucun hôtel ne correspond à vos filtres après analyse.")
            else:
                st.error("L'API n'a renvoyé aucun hôtel pour ces dates.")
        else:
            st.error("Ville non trouvée.")
