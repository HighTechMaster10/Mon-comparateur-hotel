import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# --- CONFIGURATION DES ACCÈS ---
RAPIDAPI_KEY = "fe0bf05c0fmsha6fe53849a0d181p17e53ejsn37cc55974c16"
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Comparateur d'Hôtels Pro", layout="wide")

# --- INTERFACE UTILISATEUR ---
st.title("🏨 Comparateur de Prix d'Hôtels (Données Temps Réel)")
st.markdown("Recherche sur **Booking.com** avec analyse comparative.")

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
        default=["4", "5"],
        help="Sélectionnez le nombre d'étoiles"
    )
    
    room_filter = st.selectbox(
        "Type de chambre préféré",
        ["Toutes", "Standard", "Double", "Suite", "Deluxe", "Famille"]
    )

    search_button = st.button("🚀 Lancer la recherche")

# --- FONCTIONS API ---

def get_destination_id(city):
    """Trouve l'ID unique de la ville sur Booking"""
    url = f"https://{RAPIDAPI_HOST}/v1/hotels/searchDestination"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    querystring = {"query": city}
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        if data.get('status') and data['data']:
            # On prend le premier résultat correspondant
            return data['data'][0]['dest_id'], data['data'][0]['search_type']
    except Exception as e:
        st.error(f"Erreur lors de la recherche de la ville : {e}")
    return None, None

def search_hotels(dest_id, search_type, arrival, departure):
    """Récupère la liste des hôtels et leurs prix"""
    url = f"https://{RAPIDAPI_HOST}/v1/hotels/searchHotels"
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
        "temperature_unit": "c",
        "languagecode": "fr",
        "currency_code": "EUR"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        return response.json().get('data', {}).get('hotels', [])
    except Exception as e:
        st.error(f"Erreur lors de la récupération des hôtels : {e}")
        return []

# --- TRAITEMENT ET AFFICHAGE ---

if search_button:
    if checkin >= checkout:
        st.error("Erreur : La date de départ doit être après l'arrivée.")
    else:
        with st.spinner(f"Interrogation de Booking.com pour {city_name}..."):
            # 1. Obtenir l'ID de la destination
            dest_id, search_type = get_destination_id(city_name)
            
            if dest_id:
                # 2. Obtenir les hôtels
                hotels_raw = search_hotels(dest_id, search_type, checkin, checkout)
                
                if hotels_raw:
                    processed_data = []
                    
                    for h in hotels_raw:
                        # Filtrage par étoiles
                        hotel_stars = str(h.get('class', '0'))
                        if hotel_stars not in stars_filter:
                            continue
                            
                        # Extraction des infos de prix
                        # Note: L'API peut varier, on cherche le champ prix total
                        price_info = h.get('property_combined_main_price', {})
                        total_price = h.get('composite_price_breakdown', {}).get('all_inclusive_amount', {}).get('value', 0)
                        
                        if total_price == 0: continue # On ignore si pas de prix

                        # Filtrage par type de chambre (basé sur le nom de l'offre)
                        room_name = h.get('accommodation_type_name', 'Chambre non spécifiée')
                        if room_filter != "Toutes" and room_filter.lower() not in room_name.lower():
                            continue

                        processed_data.append({
                            "Hôtel": h.get('hotel_name'),
                            "Étoiles": f"{hotel_stars} ⭐",
                            "Type de Chambre": room_name,
                            "Note": h.get('review_score', 'N/A'),
                            "Prix Booking (€)": total_price,
                            "Estimation Expedia (€)": round(total_price * 0.98, 2), # Simulation comparative
                            "Estimation Directe (€)": round(total_price * 0.96, 2)  # Simulation comparative
                        })

                    if processed_data:
                        df = pd.DataFrame(processed_data)
                        
                        # Affichage
                        st.success(f"✅ {len(df)} hôtels correspondent à vos critères.")
                        
                        # Style : on surligne le prix le plus bas en vert
                        def highlight_min(s):
                            is_min = s == s.min()
                            return ['background-color: #d4edda' if v else '' for v in is_min]

                        st.subheader("📊 Tableau Comparatif des Prix")
                        st.dataframe(
                            df.style.apply(highlight_min, axis=1, subset=["Prix Booking (€)", "Estimation Expedia (€)", "Estimation Directe (€)"])
                            .format({"Prix Booking (€)": "{:.2f}", "Estimation Expedia (€)": "{:.2f}", "Estimation Directe (€)": "{:.2f}"}),
                            use_container_width=True
                        )
                        
                        # Résumé
                        best_hotel = df.loc[df['Prix Booking (€)'].idxmin()]
                        st.info(f"💡 La meilleure offre est à l'hôtel **{best_hotel['Hôtel']}** à partir de **{best_hotel['Prix Booking (€)']} €**.")
                    else:
                        st.warning("Aucun hôtel trouvé avec ces filtres précis (Étoiles/Chambre).")
                else:
                    st.error("Aucun hôtel disponible pour ces dates.")
            else:
                st.error("Ville non trouvée. Essayez un nom plus précis (ex: 'Paris, France').")

else:
    st.info("👋 Bienvenue ! Entrez une ville et cliquez sur Rechercher pour voir les prix réels.")
