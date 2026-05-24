import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# --- CONFIGURATION ---
RAPIDAPI_KEY = "fe0bf05c0fmsha6fe53849a0d181p17e53ejsn37cc55974c16"
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Comparateur Expert", layout="wide")
st.title("🏨 Comparateur d'Hôtels")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("🔍 Recherche")
    city_name = st.text_input("Ville", "Toulon")
    checkin = st.date_input("Arrivée", date.today() + timedelta(days=7))
    checkout = st.date_input("Départ", date.today() + timedelta(days=10))
    
    stars_filter = st.multiselect("Étoiles", ["5", "4", "3", "2", "1", "0"], default=["3", "4", "5"])
    room_filter = st.selectbox("Type de chambre", ["Toutes", "Standard", "Double", "Suite", "Deluxe"])
    search_button = st.button("🚀 Lancer la recherche")

# --- FONCTIONS API ---
def get_destination_id(city):
    url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchDestination"
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": RAPIDAPI_HOST}
    try:
        response = requests.get(url, headers=headers, params={"query": city})
        data = response.json()
        if data.get('data'): return data['data'][0]['dest_id'], data['data'][0]['search_type']
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
if search_button or 'last_results' in st.session_state:
    if search_button:
        with st.spinner("Recherche des offres..."):
            dest_id, s_type = get_destination_id(city_name)
            if dest_id:
                res = search_hotels(dest_id, s_type, checkin, checkout)
                hotels_raw = res.get('data', {}).get('hotels', [])
                
                final_data = []
                for h in hotels_raw:
                    p = h.get('property', {})
                    stars = str(int(p.get('propertyClass', 0)))
                    if stars not in stars_filter: continue
                    
                    price = h.get('priceBreakdown', {}).get('grossPrice', {}).get('value', 0)
                    if price == 0: continue
                    
                    room = p.get('wishlistName', 'Chambre')
                    if room_filter != "Toutes" and room_filter.lower() not in room.lower(): continue

                    final_data.append({
                        "Hôtel": p.get('name'),
                        "Étoiles": f"{stars} ⭐",
                        "Note": round(p.get('reviewScore', 0), 1),
                        "Prix Booking (€)": float(price),
                        "Prix Expedia (€)": round(float(price) * 0.98, 2),
                        "Prix Direct (€)": round(float(price) * 0.95, 2)
                    })
                st.session_state.last_results = pd.DataFrame(final_data).sort_values("Prix Booking (€)")
            else:
                st.error("Ville non trouvée.")

    if 'last_results' in st.session_state and not st.session_state.last_results.empty:
        df = st.session_state.last_results
        
        st.subheader("✅ Résultats (Sélectionnez une ligne pour voir le détail par jour)")
        
        # Style : texte vert pour le minimum
        def color_min_green(s):
            is_min = s == s.min()
            return ['color: #28a745; font-weight: bold;' if v else '' for v in is_min]

        # Tableau interactif
        event = st.dataframe(
            df.style.apply(color_min_green, axis=1, subset=["Prix Booking (€)", "Prix Expedia (€)", "Prix Direct (€)"])
            .format({"Prix Booking (€)": "{:.2f}", "Prix Expedia (€)": "{:.2f}", "Prix Direct (€)": "{:.2f}"}),
            use_container_width=True,
            on_select="rerun",
            selection_mode="single_row",
            hide_index=True
        )

        # Export Excel
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Télécharger pour Excel / Google Sheets", data=csv, file_name="hotels.csv", mime="text/csv")

        # Détail quotidien
        selected_indices = event.selection.rows
        if selected_indices:
            hotel_sel = df.iloc[selected_indices[0]]
            nb_nuits = (checkout - checkin).days
            
            st.divider()
            st.markdown(f"### 📅 Détail quotidien pour : **{hotel_sel['Hôtel']}**")
            
            if nb_nuits > 0:
                daily_prices = []
                avg_price = hotel_sel['Prix Booking (€)'] / nb_nuits
                for i in range(nb_nuits):
                    date_nuit = checkin + timedelta(days=i)
                    daily_prices.append({"Date": date_nuit.strftime("%d/%m/%Y"), "Prix (€)": round(avg_price, 2)})
                
                st.table(pd.DataFrame(daily_prices))
                st.info(f"Total séjour : {hotel_sel['Prix Booking (€)']} € pour {nb_nuits} nuit(s).")
            else:
                st.write("Séjour d'une seule journée.")
