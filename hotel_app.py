import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# --- CONFIGURATION DES ACCÈS ---
RAPIDAPI_KEY = "fe0bf05c0fmsha6fe53849a0d181p17e53ejsn37cc55974c16"
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Comparateur d'Hôtels Pro", layout="wide")

st.title("🏨 Comparateur de Prix d'Hôtels (Données Temps Réel)")
st.markdown("Recherche sur **Booking.com** avec analyse comparative.")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("🔍 Critères de recherche")
    city_name = st.text_input("Ville de destination", "Paris")
    
    col1, col2 = st.columns(2)
    with col1:
        checkin = st.date_input("Date d'arrivée", date.today() + timedelta(days=7))
    with col2:
        checkout = st.date_input("Date de départ", date.today() + timedelta(days=10))
    
    stars_filter = st.multiselect(
        "Catégorie d'hôtel",
        options=["5", "4", "3", "2"],
        default=["4", "5"]
    )
    
    room_filter = st.selectbox(
        "Type de chambre préféré",
        ["Toutes", "Standard", "Double", "Suite", "Deluxe", "Famille"]
    )

    search_button = st.button("🚀 Lancer la recherche")

# --- FONCTIONS API (CORRIGÉES POUR BOOKING-COM15) ---

def get_destination_id(city):
    """Trouve l'ID unique de la ville (Ajout de /api/)"""
    url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchDestination"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    querystring = {"query": city}
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        # Correction : on vérifie la structure spécifique de booking-com15
        if data.get('status') == True and data.get('data'):
            return data['data'][0]['dest_id'], data['data'][0]['search_type']
    except Exception as e:
        st.error(f"Erreur technique (Destination) : {e}")
    return None, None

def search_hotels(dest_id, search_type, arrival, departure):
    """Récupère les hôtels et leurs prix (Ajout de /api/)"""
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
        "adults": "1",
        "room_qty": "1",
        "page_number": "1",
        "units": "metric",
        "languagecode": "fr",
        "currency_code": "EUR"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        if data.get('status') == True:
            return data.get('data', {}).get('hotels', [])
    except Exception as e:
        st.error(f"Erreur technique (Hôtels) : {e}")
    return []

# --- TRAITEMENT ---

if search_button:
    if checkin >= checkout:
        st.error("Erreur : La date de départ doit être après l'arrivée.")
    else:
        with st.spinner(f"Recherche en cours pour {city_name}..."):
            dest_id, search_type = get_destination_id(city_name)
            
            if dest_id:
                hotels_raw = search_hotels(dest_id, search_type, checkin, checkout)
                
                if hotels_raw:
                    processed_data = []
                    for h in hotels_raw:
                        # 1. Filtre Étoiles
                        hotel_stars = str(h.get('property', {}).get('propertyClass', '0'))
                        if hotel_stars not in stars_filter:
                            continue
                        
                        # 2. Récupération du prix (Structure spécifique booking-com15)
                        price_data = h.get('priceBreakdown', {}).get('grossPrice', {})
                        total_price = price_data.get('value', 0)
                        
                        if total_price == 0: continue

                        # 3. Filtre Chambre
                        hotel_name = h.get('property', {}).get('name', 'Hôtel')
                        # Note: booking-com15 met parfois le nom de chambre dans wishlistName ou ailleurs
                        room_name = h.get('property', {}).get('wishlistName', 'Chambre Standard')

                        if room_filter != "Toutes" and room_filter.lower() not in room_name.lower():
                            continue

                        processed_data.append({
                            "Hôtel": hotel_name,
                            "Étoiles": f"{hotel_stars} ⭐",
                            "Type de Chambre": room_name,
                            "Note": h.get('property', {}).get('reviewScore', 'N/A'),
                            "Prix Booking (€)": total_price,
                            "Estimation Expedia (€)": round(total_price * 0.98, 2),
                            "Estimation Directe (€)": round(total_price * 0.96, 2)
                        })

                    if processed_data:
                        df = pd.DataFrame(processed_data)
                        st.success(f"✅ {len(df)} établissements trouvés.")
                        
                        # Style du tableau
                        def highlight_min(s):
                            is_min = s == s.min()
                            return ['background-color: #d4edda' if v else '' for v in is_min]

                        st.dataframe(
                            df.sort_values("Prix Booking (€)")
                            .style.apply(highlight_min, axis=1, subset=["Prix Booking (€)", "Estimation Expedia (€)", "Estimation Directe (€)"])
                            .format({"Prix Booking (€)": "{:.2f}", "Estimation Expedia (€)": "{:.2f}", "Estimation Directe (€)": "{:.2f}"}),
                            use_container_width=True
                        )
                    else:
                        st.warning("Aucun hôtel ne correspond à vos filtres d'étoiles ou de chambre.")
                else:
                    st.error("Aucun hôtel trouvé pour ces dates.")
            else:
                st.error("Ville non trouvée. Essayez un nom simple (ex: 'Paris' au lieu de 'Paris, France').")
