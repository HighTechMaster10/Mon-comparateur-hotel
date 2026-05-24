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
    
    col1, col2 = st.columns(2)
    with col1:
        checkin = st.date_input("Arrivée", date.today() + timedelta(days=7))
    with col2:
        checkout = st.date_input("Départ", date.today() + timedelta(days=10))
    
    stars_filter = st.multiselect(
        "Catégorie (Étoiles)", 
        ["5", "4", "3", "2", "1", "0"], 
        default=["3", "4", "5"]
    )
    
    room_filter = st.selectbox(
        "Type de chambre", 
        ["Toutes", "Standard", "Double", "Suite", "Deluxe", "Chambre"]
    )
    
    search_button = st.button("🚀 Lancer la recherche")

# --- FONCTIONS API ---

def get_destination_id(city):
    url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchDestination"
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": RAPIDAPI_HOST}
    try:
        response = requests.get(url, headers=headers, params={"query": city})
        data = response.json()
        if data.get('status') and data.get('data'):
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
        return response.json().get('data', {}).get('hotels', [])
    except: return []

# --- AFFICHAGE ---

if search_button:
    with st.spinner(f"Recherche en cours..."):
        dest_id, s_type = get_destination_id(city_name)
        if dest_id:
            hotels_raw = search_hotels(dest_id, s_type, checkin, checkout)
            if hotels_raw:
                final_list = []
                for h in hotels_raw:
                    prop = h.get('property', {})
                    
                    # 1. Extraction Étoiles
                    stars = str(int(prop.get('propertyClass', 0)))
                    if stars not in stars_filter:
                        continue
                    
                    # 2. Extraction Prix
                    price = h.get('priceBreakdown', {}).get('grossPrice', {}).get('value', 0)
                    if price == 0: continue
                    
                    # 3. Extraction Nom de Chambre (plus flexible)
                    # L'API utilise souvent 'wishlistName' pour la description courte
                    room_name = prop.get('wishlistName', 'Chambre')
                    
                    # Filtrage chambre (si "Toutes", on laisse passer)
                    if room_filter != "Toutes":
                        if room_filter.lower() not in room_name.lower():
                            continue

                    final_list.append({
                        "Hôtel": prop.get('name'),
                        "Étoiles": f"{stars} ⭐",
                        "Chambre": room_name,
                        "Note": prop.get('reviewScore', 'N/A'),
                        "Prix Booking (€)": price,
                        "Estimation Expedia (€)": round(price * 0.98, 2),
                        "Estimation Directe (€)": round(price * 0.96, 2)
                    })

                if final_list:
                    df = pd.DataFrame(final_list)
                    st.success(f"✅ {len(df)} établissements trouvés à {city_name}")
                    
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
                    st.warning("⚠️ Aucun hôtel ne correspond à vos filtres. Essayez de mettre 'Toutes' dans Type de chambre.")
            else:
                st.error("Aucun hôtel trouvé pour ces dates.")
        else:
            st.error("Ville non trouvée.")
