import streamlit as st
import pandas as pd
from datetime import date, timedelta
import random

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Comparateur d'Hôtels Pro", layout="wide")

# --- STYLE CSS PERSONNALISÉ ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stDataFrame { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏨 Comparateur de Prix d'Hôtels")
st.write("Trouvez le meilleur prix à travers différentes plateformes de réservation.")

# --- BARRE LATÉRALE : CRITÈRES ---
with st.sidebar:
    st.header("🔍 Vos Critères")
    
    destination = st.text_input("Destination", "Paris")
    
    col1, col2 = st.columns(2)
    with col1:
        checkin = st.date_input("Arrivée", date.today() + timedelta(days=7))
    with col2:
        checkout = st.date_input("Départ", date.today() + timedelta(days=10))
    
    hotel_stars = st.multiselect(
        "Type d'hôtel (Étoiles)",
        ["2⭐", "3⭐", "4⭐", "5⭐"],
        default=["3⭐", "4⭐"]
    )
    
    room_type = st.selectbox(
        "Type de chambre",
        ["Standard Single", "Double Queen", "Suite Junior", "Suite Présidentielle"]
    )
    
    search_button = st.button("🚀 Rechercher les offres")

# --- LOGIQUE DE GÉNÉRATION DE DONNÉES (SIMULATION API) ---
def fetch_hotel_data(dest, start, end, stars, room):
    # Calcul de la durée du séjour
    nights = (end - start).days
    if nights <= 0:
        return None

    # Base de données fictive d'hôtels
    hotels_db = {
        "2⭐": ["Hôtel Eco Plus", "ibis Budget", "Hôtel de la Gare"],
        "3⭐": ["Comfort Inn", "Kyriad Centre", "Best Western Plus"],
        "4⭐": ["Novotel Plaza", "Mercure Grand", "Hilton Garden"],
        "5⭐": ["Ritz-Carlton", "The Peninsula", "Four Seasons"]
    }

    results = []
    for s in stars:
        for name in hotels_db[s]:
            # Simulation de prix de base par nuit
            base_price = {"2⭐": 60, "3⭐": 110, "4⭐": 190, "5⭐": 450}[s]
            # Ajustement selon le type de chambre
            room_multiplier = {"Standard Single": 1.0, "Double Queen": 1.3, "Suite Junior": 1.8, "Suite Présidentielle": 3.5}[room]
            
            price_per_night = base_price * room_multiplier
            total_base = price_per_night * nights

            # Simulation de variations entre les plateformes
            booking_price = total_base * random.uniform(0.95, 1.05)
            expedia_price = total_base * random.uniform(0.95, 1.05)
            hotels_com_price = total_base * random.uniform(0.95, 1.05)

            prices = {
                "Booking.com": round(booking_price, 2),
                "Expedia": round(expedia_price, 2),
                "Hotels.com": round(hotels_com_price, 2)
            }
            
            best_price = min(prices.values())
            best_source = [k for k, v in prices.items() if v == best_price][0]

            results.append({
                "Hôtel": name,
                "Catégorie": s,
                "Chambre": room,
                "Booking.com (€)": prices["Booking.com"],
                "Expedia (€)": prices["Expedia"],
                "Hotels.com (€)": prices["Hotels.com"],
                "Meilleur Prix (€)": best_price,
                "Meilleure Offre via": best_source
            })
    
    return pd.DataFrame(results)

# --- AFFICHAGE DES RÉSULTATS ---
if search_button:
    if checkin >= checkout:
        st.error("La date de départ doit être postérieure à la date d'arrivée.")
    elif not hotel_stars:
        st.warning("Veuillez sélectionner au moins un type d'hôtel.")
    else:
        with st.spinner("Interrogation des plateformes de réservation..."):
            df = fetch_hotel_data(destination, checkin, checkout, hotel_stars, room_type)
            
            if df is not None and not df.empty:
                st.success(f"Nous avons trouvé {len(df)} établissements disponibles à {destination}.")
                
                # Tri par meilleur prix
                df = df.sort_values(by="Meilleur Prix (€)")

                # Mise en forme du tableau
                def highlight_min(s):
                    '''Surligne en vert le prix le plus bas de la ligne'''
                    is_min = s == s.min()
                    return ['background-color: #d4edda' if v else '' for v in is_min]

                # Affichage
                st.subheader("📋 Comparatif des prix totaux pour le séjour")
                
                # Configuration de l'affichage du tableau
                st.dataframe(
                    df.style.apply(highlight_min, axis=1, subset=["Booking.com (€)", "Expedia (€)", "Hotels.com (€)"])
                    .format({"Booking.com (€)": "{:.2f}", "Expedia (€)": "{:.2f}", "Hotels.com (€)": "{:.2f}", "Meilleur Prix (€)": "{:.2f}"}),
                    use_container_width=True
                )

                # Résumé sous forme de cartes
                st.divider()
                col_best, col_info = st.columns(2)
                
                with col_best:
                    cheapest_hotel = df.iloc[0]
                    st.metric(label="🏆 Meilleure offre trouvée", 
                              value=f"{cheapest_hotel['Meilleur Prix (€)']} €",
                              delta=f"Hôtel: {cheapest_hotel['Hôtel']}")
                    st.write(f"Réserver sur : **{cheapest_hotel['Meilleure Offre via']}**")

                with col_info:
                    st.info(f"Séjour de {(checkout-checkin).days} nuits pour 1 chambre de type '{room_type}'.")
            else:
                st.error("Aucune donnée disponible pour ces critères.")
else:
    st.info("Utilisez la barre latérale pour lancer une recherche.")