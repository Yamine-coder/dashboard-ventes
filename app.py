import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import requests

# URL du fichier Excel hébergé sur Google Drive
url = "https://docs.google.com/uc?export=download&id=1Hv7FBYQa8_Ojjh0J-j7nbFht09UNtZN8"
file_path = "data.xlsx"

# Fonction pour récupérer les données actualisées
def fetch_data():
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        df_updated = pd.read_excel(file_path, engine='openpyxl')
        df_updated['Date'] = pd.to_datetime(df_updated['Date'], format='%d/%m/%Y')
        return df_updated
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour des données : {e}")
        return pd.DataFrame()

# Initialisation de l'application avec un thème Bootstrap
app = Dash(__name__, external_stylesheets=[dbc.themes.LUX])
app.title = "Dashboard des Ventes Revu"

# Layout du dashboard
app.layout = dbc.Container([
    html.H1("📈 Dashboard des Ventes", className="text-center my-4 fw-bold"),

    # Intervalle pour recharger les données périodiquement
    dcc.Interval(
        id='interval-update',
        interval=10*1000,  # Toutes les 5 minutes
        n_intervals=0
    ),

    dbc.Row([
        dbc.Col(dcc.DatePickerRange(
            id='date-range',
            display_format='DD/MM/YYYY',
            className='w-100'
        ), width=4),
        dbc.Col(dcc.Dropdown(id='rayon-filter', placeholder="Choisir un rayon", multi=True, className='w-100'), width=4),
        dbc.Col(dcc.Dropdown(id='produit-filter', placeholder="Choisir un produit", multi=False, className='w-100'), width=4)
    ], className='mb-4'),

    dbc.Row(id='kpi-container', className='mb-4 g-3'),
    
    dbc.Row([
        dbc.Col(dcc.Graph(id='evolution-ventes'), md=8),
        dbc.Col(dcc.Graph(id='ventes-par-rayon'), md=4),
    ], className='mb-4'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='evolution-produits'), md=12),
    ])
], fluid=True)

# Callback pour charger les données et mettre à jour les options des filtres
@app.callback(
    [Output('date-range', 'start_date'),
     Output('date-range', 'end_date'),
     Output('rayon-filter', 'options'),
     Output('produit-filter', 'options')],
    Input('interval-update', 'n_intervals')
)
def update_filters(_):
    df_updated = fetch_data()
    
    if df_updated.empty:
        return None, None, [], []
    
    start_date = df_updated['Date'].min()
    end_date = df_updated['Date'].max()
    rayon_options = [{'label': r, 'value': r} for r in df_updated['Rayon'].unique()]
    produit_options = [{'label': p, 'value': p} for p in df_updated['Produit'].unique()]
    
    return start_date, end_date, rayon_options, produit_options

# Callback principal pour mettre à jour le dashboard
@app.callback(
    [Output('kpi-container', 'children'),
     Output('evolution-ventes', 'figure'),
     Output('ventes-par-rayon', 'figure'),
     Output('evolution-produits', 'figure')],
    [Input('date-range', 'start_date'),
     Input('date-range', 'end_date'),
     Input('rayon-filter', 'value'),
     Input('produit-filter', 'value'),
     Input('interval-update', 'n_intervals')]
)
def update_dashboard(start_date, end_date, selected_rayons, selected_produit, _):
    df_updated = fetch_data()

    if df_updated.empty:
        return [], {}, {}, {}

    df_filtered = df_updated[(df_updated['Date'] >= pd.to_datetime(start_date)) & 
                             (df_updated['Date'] <= pd.to_datetime(end_date))] if not df_updated.empty else df_updated

    if selected_rayons:
        df_filtered = df_filtered[df_filtered['Rayon'].isin(selected_rayons)]

    # KPI calculs
    total_ca = df_filtered['CA TTC (€)'].sum()
    total_articles = df_filtered['Nb Articles Vendus'].sum()
    moy_journaliere = df_filtered.groupby('Date')['CA TTC (€)'].sum().mean()

    kpis = [
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("💶 CA Total"), html.H3(f"{total_ca:,.2f} €")])]), md=4),
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("📦 Articles Vendus"), html.H3(f"{total_articles}")])]), md=4),
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("📅 CA Moyen/Jour"), html.H3(f"{moy_journaliere:,.2f} €")])]), md=4),
    ]

    # Graphiques
    evolution = df_filtered.groupby('Date')['CA TTC (€)'].sum().reset_index()
    fig_evolution = px.line(evolution, x='Date', y='CA TTC (€)', title="Évolution des Ventes",
                            markers=True, template='plotly_white', line_shape='spline')

    ventes_rayons = df_filtered.groupby('Rayon')['CA TTC (€)'].sum().reset_index()
    fig_ventes_rayons = px.bar(ventes_rayons, x='CA TTC (€)', y='Rayon', orientation='h',
                               title="Ventes par Rayon", template='plotly_white')
    
    if selected_produit:
        df_produit = df_filtered[df_filtered['Produit'] == selected_produit]
        evolution_produits = df_produit.groupby('Date')['CA TTC (€)'].sum().reset_index()
        fig_evolution_produits = px.line(evolution_produits, x='Date', y='CA TTC (€)',
                                         title=f"Évolution de {selected_produit}", markers=True,
                                         template='plotly_white', line_shape='spline')
    else:
        fig_evolution_produits = px.line(title="Évolution des Produits", template='plotly_white')
    
    return kpis, fig_evolution, fig_ventes_rayons, fig_evolution_produits

# Lancement de l'application
if __name__ == '__main__':
    app.run_server(debug=True)
    
server = app.server  # Ajout pour Gunicorn
