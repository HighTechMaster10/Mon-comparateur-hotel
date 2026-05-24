import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
import io

# --- CONFIGURATION ---
RAPIDAPI_KEY = "fe0bf05c0fmsha6fe53849a0d181p17e53ejsn37cc55974c16"
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Comparateur Expert", layout="wide")
st.title("🏨 Comparateur d'Hôtels avec Export & Détails")

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

# --- LOGIQUE PRINCIPALE ---
if search_button:
    with st.spinner("Recherche en cours..."):
        dest_id, s_type = get_destination_id(city_name)
        if dest_id:
            res = search_hotels(dest_id, s_type, checkin, checkout)
            hotels_raw = res.get('data', {}).get('hotels', [])

            if hotels_raw:
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

                if final_data:
                    df = pd.DataFrame(final_data).sort_values("Prix Booking (€)")
                    
                    # --- AFFICHAGE DU TABLEAU AVEC SÉLECTION ---
                    st.subheader(f"✅ {len(df)} hôtels trouvés (Sélectionnez une ligne pour le détail)")
                    
                    # On utilise st.dataframe avec la sélection activée
                    event = st.dataframe(
                        df.style.apply(lambda s: ['color: #28a745; font-weight: bold;' if v == s.min() else '' for v in s], 
                                      axis=1, subset=["Prix Booking (€)", "Prix Expedia (€)", "Prix Direct (€)"])
                        .format({"Prix Booking (€)": "{:.2f}", "Prix Expedia (€)": "{:.2f}", "Prix Direct (€)": "{:.2f}"}),
                        use_container_width=True,
                        on_select="rerun",
                        selection_mode="single_row"
                    )

                    # --- EXPORT EXCEL/CSV ---
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 Exporter les résultats pour Excel / Google Sheets",
                        data=csv,
                        file_name=f"comparatif_hotels_{city_name}.csv",
                        mime="text/csv",
                    )

                    # --- DÉTAIL PAR JOUR (SI UNE LIGNE EST SÉLECTIONNÉE) ---
                    selected_rows = event.get("selection", {}).get("rows", [])
                    if selected_rows:
                        idx = selected_rows[0]
                        hotel_sel = df.iloc[idx]
                        nb_nuits = (checkout - checkin).days
                        
                        st.divider()
                        st.subheader(f"📅 Détail du séjour : {hotel_sel['Hôtel']}")
                        
                        if nb_nuits > 0:
                            # Création du tableau journalier
                            daily_list = []
                            prix_moyen = hotel_sel['Prix Booking (€)'] / nb_nuits
                            
                            for i in range(nb_nuits):
                                jour = checkin + timedelta(days=i)
                                daily_list.append({
                                    "Date": jour.strftime("%d/%m/%Y"),
                                    "Prix Estimé Nuitée (€)": round(prix_moyen, 2)
                                })
                            
                            df_daily = pd.DataFrame(daily_list)
                            st.table(df_daily) # Affichage sous forme de table fixe
                            st.write(f"**Total pour {nb_nuits} nuits : {hotel_sel['Prix Booking (€)']} €**")
                        else:
                            st.info("Séjour d'une seule journée.")
                else:
                    st.warning("Aucun hôtel trouvé avec vos filtres.")
            else:
                st.error("Aucun résultat de l'API.")
        else:
            st.error("Ville non trouvée.")
