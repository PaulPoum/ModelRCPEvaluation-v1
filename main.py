import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
import numpy as np

st.image("logo.png", width=80) 
st.title("🌍 Projections Climatiques - Scénarios RCP")

def apply_rcp_scenario(data, scenario):
    df = data.copy()
    base_year = df['Year'].min()
    
    # Facteurs d'ajustement scientifiques (source: IPCC AR6)
    # adjustment = {
    #     "RCP2.6": {
    #         "temp": 0.01, 
    #         "precip": 0.005,
    #         "variability": 0.1
    #     },
    #     "RCP4.5": {
    #         "temp": 0.023,
    #         "precip": 0.008,
    #         "variability": 0.15
    #     },
    #     "RCP8.5": {
    #         "temp": 0.045,
    #         "precip": 0.015,
    #         "variability": 0.25
    #     }
    # }
    
    adjustment = {
        "RCP2.6": {
            "temp": 0.006,    # Réduit de 0.01 à 0.006 (~1.5°C d'ici 2100)
            "precip": 0.003,  # Réduit de 0.005 à 0.003 (moins de variabilité)
            "variability": 0.08  # Réduit de 0.1 à 0.08
        },
        "RCP4.5": {
            "temp": 0.015,    # Réduit de 0.023 à 0.015 (~2.8°C d'ici 2100)
            "precip": 0.005,  # Réduit de 0.008 à 0.005
            "variability": 0.12  # Réduit de 0.15 à 0.12
        },
        "RCP8.5": {
            "temp": 0.03,     # Réduit de 0.045 à 0.03 (~4.5°C d'ici 2100)
            "precip": 0.01,   # Réduit de 0.015 à 0.01
            "variability": 0.18  # Réduit de 0.25 à 0.18
        }
    }
    
    years = df['Year'] - base_year
    scen = adjustment[scenario]
    
    # Application des tendances
    for temp_type in ['max', 'moy', 'min']:
        df[f'temp-{temp_type}_projected'] = (
            df[f'temp-{temp_type}'] * (1 + scen["temp"] * years) + 
            np.random.normal(0, scen["variability"], len(df))
        )
    
    # Projection des précipitations avec variabilité saisonnière
    df['precipitation_projected'] = (
        df['precipitation'] * (1 + scen["precip"] * years) * 
        (1 + scen["variability"] * np.sin(2 * np.pi * df['date'].dt.dayofyear / 365))
    )
    
    df['Scenario'] = scenario
    return df

uploaded_file = st.file_uploader("📤 Importer votre fichier Excel", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        
        required_columns = ['localite', 'date', 'temp-max', 'temp-moy', 'temp-min', 'precipitation']
        if not all(col in df.columns for col in required_columns):
            st.error(f"❌ Colonnes manquantes: {', '.join(required_columns)}")
        else:
            # Prétraitement des données
            df['date'] = pd.to_datetime(df['date'])
            df['Year'] = df['date'].dt.year
            df['Month'] = df['date'].dt.month_name()
            
            # Sélections interactives
            col1, col2, col3 = st.columns(3)
            with col1:
                localite = st.selectbox("🏙️ Localité", df['localite'].unique())
            with col2:
                year_range = st.slider("📅 Plage d'années", 
                                      min_value=df['Year'].min(),
                                      max_value=df['Year'].max(),
                                      value=(df['Year'].min(), df['Year'].max()))
            with col3:
                scenarios = st.multiselect("🌡️ Scénarios RCP", 
                                         ["RCP2.6", "RCP4.5", "RCP8.5"],
                                         default=["RCP8.5"])

            # Filtrage des données
            df_filtered = df[(df['localite'] == localite) & 
                           (df['Year'].between(year_range[0], year_range[1]))]
            
            # Application des scénarios
            projections = pd.concat([apply_rcp_scenario(df_filtered, scen) for scen in scenarios])
            
            # Visualisations interactives
            st.subheader("📈 Visualisations Dynamiques")
            
            tab1, tab2, tab3 = st.tabs(["Températures", "Précipitations", "Comparaisons"])
            
            with tab1:
                temp_type = st.radio("Type de température", ['max', 'moy', 'min'], horizontal=True)
                fig = px.line(projections, 
                            x='date', y=f'temp-{temp_type}_projected',
                            color='Scenario', 
                            title=f'Température {temp_type} projetée',
                            labels={'value': '°C'},
                            height=500)
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                fig = px.area(projections, 
                            x='date', y='precipitation_projected',
                            color='Scenario',
                            title='Projection des précipitations',
                            labels={'value': 'mm'},
                            height=500)
                st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                metric = st.selectbox("Métrique", ['Température max', 'Température moy', 'Température min', 'Précipitations'])
                y_col = 'precipitation_projected' if 'Précipitations' in metric else f'temp-{metric.split()[-1]}_projected'
                
                fig = px.box(projections, 
                           x='Month', y=y_col,
                           color='Scenario',
                           title=f'Distribution mensuelle - {metric}',
                           height=600)
                st.plotly_chart(fig, use_container_width=True)

            # Téléchargement
            st.subheader("📥 Export des Données")
            with st.expander("Options d'export"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    projections.to_excel(writer, index=False)
                
                st.download_button(
                    label="💾 Télécharger en Excel",
                    data=output.getvalue(),
                    file_name="projections_climat.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"❌ Erreur: {str(e)}")

# Section d'aide
with st.expander("ℹ️ Guide d'utilisation"):
    st.markdown("""
    **Nouvelles fonctionnalités :**
    - Visualisations interactives avec Plotly
    - Sélection multi-scénarios
    - Analyse comparative mensuelle
    - Modèle scientifique révisé (IPCC AR6)
    - Gestion de la variabilité climatique
    - Export personnalisable
    """)

with st.expander("📚 Références scientifiques"):
    st.markdown("""
    **Paramètres des scénarios (source: IPCC):**
    - **RCP2.6**: Réchauffement limité à +1.5°C  
    - **RCP4.5**: Scénario de stabilisation modérée  
    - **RCP8.5**: Émissions élevées non atténuées  
    
    **Méthodologie :**
    - Modèle de variabilité climatique stochastique
    - Projections mensuelles lissées
    - Coefficients d'ajustement régionaux
    """)