import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# --- CONFIGURATION ---
RAPIDAPI_KEY = "fe0bf05c0fmsha6fe53849a0d181p17e53ejsn37cc55974c16"
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Debug Comparateur", layout="wide")

st.title("🏨 Comparateur d'Hôtels")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("🔍 Critères")
    city_name = st.text_input("Ville", "Paris")
    checkin = st.date_input("Arrivée", date.today() + timedelta(days=7))
    checkout = st.date_input("Départ", date.today() + timedelta(days=10))
    
    stars_filter = st.multiselect("Étoiles", ["5", "4", "3", "2"], default=["4", "5"])
    room_filter = st.selectbox("Chambre", ["Toutes", "Standard", "Double", "Suite", "Deluxe"])
    
    search_button = st.button("🚀 Lancer la recherche")

# --- FONCTIONS TECHNIQUES ---

def get_destination_id(city):
    # On teste d'abord l'URL avec /api/, si ça échoue on pourra voir pourquoi
    url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchDestination"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    querystring = {"query": city}
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        # DEBUG : Affiche la réponse en cas de problème
        if response.status_code != 200:
            st.error(f"Erreur API ({response.status_code}): {data.get('message', 'Erreur inconnue')}")
            return None, None
            
        if data.get('data'):
            # On prend le premier résultat
            return data['data'][0]['dest_id'], data['data'][0]['search_type']
        else:
            st.warning(f"L'API n'a trouvé aucune destination pour '{city}'. Essayez un nom plus simple.")
            return None, None
            
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        return None, None

def search_hotels(dest_id, search_type, arrival, departure):
    url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchHotels"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    querystring = {
        "dest_id": dest_id,
        "search_type": search_type,
        "arrival_date": str(arrival),
        "departure_date": str(departure),
        "adults": "1", "room_qty": "1", "page_number": "1",
        "units": "metric", "languagecode": "fr", "currency_code": "EUR"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        return data.get('data', {}).get('hotels', [])
    except:
        return []

# --- EXÉCUTION ---

if search_button:
    with st.spinner(f"Recherche en cours..."):
        # 1. On cherche l'ID de la ville
        dest_id, s_type = get_destination_id(city_name)
        
        if dest_id:
            # 2. On cherche les hôtels
            hotels_raw = search_hotels(dest_id, s_type, checkin, checkout)
            
            if hotels_raw:
                processed = []
                for h in hotels_raw:
                    # Extraction sécurisée des données
                    prop = h.get('property', {})
                    hotel_stars = str(prop.get('propertyClass', '0'))
                    
                    if hotel_stars not in stars_filter:
                        continue
                    
                    price = h.get('priceBreakdown', {}).get('grossPrice', {}).get('value', 0)
                    if price == 0: continue
                    
                    name = prop.get('name', 'Hôtel')
                    room = prop.get('wishlistName', 'Chambre Standard')
                    
                    if room_filter != "Toutes" and room_filter.lower() not in room.lower():
                        continue

                    processed.append({
                        "Hôtel": name,
                        "Étoiles": f"{hotel_stars} ⭐",
                        "Chambre": room,
                        "Prix Booking (€)": price,
                        "Expedia (Simulé)": round(price * 0.98, 2),
                        "Direct (Simulé)": round(price * 0.95, 2)
                    })

                if processed:
                    df = pd.DataFrame(processed)
                    st.success(f"{len(df)} hôtels trouvés à {city_name}")
                    st.dataframe(df.sort_values("Prix Booking (€)"), use_container_width=True)
                else:
                    st.warning("Aucun hôtel ne correspond à vos filtres (étoiles/chambre).")
            else:
                st.error("Aucun hôtel trouvé pour ces dates.")
