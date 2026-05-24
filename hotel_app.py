import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# --- CONFIGURATION (D'APRÈS VOTRE CAPTURE) ---
RAPIDAPI_KEY = "fe0bf05c0fmsha6fe53849a0d181p17e53ejsn37cc55974c16"
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Comparateur Hôtels Pro", layout="wide")

st.title("🏨 Comparateur de Prix d'Hôtels")
st.markdown("Données réelles extraites de **Booking.com**")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("🔍 Recherche")
    city_name = st.text_input("Ville", "Paris")
    
    col1, col2 = st.columns(2)
    with col1:
        checkin = st.date_input("Arrivée", date.today() + timedelta(days=7))
    with col2:
        checkout = st.date_input("Départ", date.today() + timedelta(days=10))
    
    stars_filter = st.multiselect(
        "Catégorie (Étoiles)", 
        ["5", "4", "3", "2"], 
        default=["4", "5"]
    )
    
    room_filter = st.selectbox(
        "Type de chambre", 
        ["Toutes", "Standard", "Double", "Suite", "Deluxe", "Famille"]
    )
    
    search_button = st.button("🚀 Lancer la recherche")

# --- FONCTIONS API ---

def get_destination_id(city):
    """Récupère l'ID de la destination pour l'API"""
    url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchDestination"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    querystring = {"query": city}
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        if data.get('status') == True and data.get('data'):
            # On prend la première ville trouvée
            return data['data'][0]['dest_id'], data['data'][0]['search_type']
    except Exception as e:
        st.error(f"Erreur Destination : {e}")
    return None, None

def search_hotels(dest_id, s_type, arrival, departure):
    """Récupère la liste des hôtels et leurs tarifs"""
    url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchHotels"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    querystring = {
        "dest_id": dest_id,
        "search_type": s_type,
        "arrival_date": str(arrival),
        "departure_date": str(departure),
        "adults": "1",
        "room_qty": "1",
        "page_number": "1",
        "languagecode": "fr",
        "currency_code": "EUR"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        if data.get('status') == True:
            return data.get('data', {}).get('hotels', [])
    except Exception as e:
        st.error(f"Erreur Hôtels : {e}")
    return []

# --- AFFICHAGE ---

if search_button:
    if checkin >= checkout:
        st.error("La date de départ doit être après l'arrivée.")
    else:
        with st.spinner(f"Interrogation des serveurs pour {city_name}..."):
            dest_id, s_type = get_destination_id(city_name)
            
            if dest_id:
                hotels_raw = search_hotels(dest_id, s_type, checkin, checkout)
                
                if hotels_raw:
                    final_list = []
                    for h in hotels_raw:
                        # 1. Filtre Étoiles
                        prop = h.get('property', {})
                        stars = str(prop.get('propertyClass', '0'))
                        if stars not in stars_filter:
                            continue
                        
                        # 2. Filtre Chambre
                        # On cherche le nom de la chambre dans les différentes options de l'API
                        room_name = prop.get('wishlistName', 'Chambre Standard')
                        if room_filter != "Toutes" and room_filter.lower() not in room_name.lower():
                            continue
                        
                        # 3. Récupération du Prix
                        price = h.get('priceBreakdown', {}).get('grossPrice', {}).get('value', 0)
                        if price == 0: continue

                        final_list.append({
                            "Hôtel": prop.get('name', 'Sans nom'),
                            "Catégorie": f"{stars} ⭐",
                            "Chambre": room_name,
                            "Note": prop.get('reviewScore', 'N/A'),
                            "Prix Booking (€)": price,
                            "Estimation Expedia (€)": round(price * 0.98, 2),
                            "Estimation Directe (€)": round(price * 0.96, 2)
                        })

                    if final_list:
                        df = pd.DataFrame(final_list)
                        st.success(f"✅ {len(df)} établissements correspondent à vos critères.")
                        
                        # Mise en forme : Surligner le prix le plus bas de chaque ligne
                        def highlight_min(s):
                            is_min = s == s.min()
                            return ['background-color: #d4edda' if v else '' for v in is_min]

                        st.subheader("📊 Tableau Comparatif")
                        st.dataframe(
                            df.sort_values("Prix Booking (€)")
                            .style.apply(highlight_min, axis=1, subset=["Prix Booking (€)", "Estimation Expedia (€)", "Estimation Directe (€)"])
                            .format({"Prix Booking (€)": "{:.2f}", "Estimation Expedia (€)": "{:.2f}", "Estimation Directe (€)": "{:.2f}"}),
                            use_container_width=True
                        )
                        
                        # Conseil
                        cheapest = df.loc[df['Prix Booking (€)'].idxmin()]
                        st.info(f"💡 Le meilleur prix trouvé est à **{cheapest['Hôtel']}** ({cheapest['Prix Booking (€)']} €)")
                    else:
                        st.warning("Aucun hôtel trouvé pour ces critères (étoiles/chambre).")
                else:
                    st.error("Aucune disponibilité pour ces dates.")
            else:
                st.error("Ville non trouvée. Essayez un nom plus simple.")

else:
    st.info("Entrez une destination et cliquez sur le bouton pour comparer les prix.")
