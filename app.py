import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import requests

# URL du fichier Excel hébergé sur Google Drive
url = "https://docs.google.com/uc?export=download&id=1Hv7FBYQa8_Ojjh0J-j7nbFht09UNtZN8"
file_path = "data.xlsx"

# Télécharger le fichier Excel depuis Google Drive
try:
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("✅ Fichier téléchargé avec succès.")
except Exception as e:
    print(f"❌ Erreur lors du téléchargement : {e}")

# Lecture des données
try:
    df = pd.read_excel(file_path, engine='openpyxl')
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
except Exception as e:
    print(f"❌ Erreur lors de la lecture du fichier Excel : {e}")
    df = pd.DataFrame()

# Initialisation de l'application avec un thème Bootstrap moderne
app = Dash(__name__, external_stylesheets=[dbc.themes.LUX])
app.title = "Dashboard des Ventes Revu"

# Fonction pour créer des cartes KPI stylées
def create_kpi_card(title, value, icon):
    return dbc.Card([
        dbc.CardBody([
            html.H6([icon, f" {title}"], className="card-title text-muted"),
            html.H3(value, className="card-text fw-bold"),
        ])
    ], className="shadow rounded-4 text-center", style={"backgroundColor": "#fefefe"})

# Filtres
filtres = dbc.Row([
    dbc.Col(dcc.DatePickerRange(
        id='date-range',
        start_date=df['Date'].min() if not df.empty else None,
        end_date=df['Date'].max() if not df.empty else None,
        display_format='DD/MM/YYYY',
        className='w-100'
    ), width=4),
    dbc.Col(dcc.Dropdown(
        id='rayon-filter',
        options=[{'label': rayon, 'value': rayon} for rayon in df['Rayon'].unique()] if not df.empty else [],
        placeholder="Choisir un rayon",
        multi=True,
        className='w-100'
    ), width=4),
    dbc.Col(dcc.Dropdown(
        id='produit-filter',
        options=[{'label': produit, 'value': produit} for produit in df['Produit'].unique()] if not df.empty else [],
        placeholder="Choisir un produit",
        multi=False,
        className='w-100'
    ), width=4)
], className='mb-4')

# Layout du dashboard
app.layout = dbc.Container([
    html.H1("📈 Dashboard des Ventes", className="text-center my-4 fw-bold"),
    filtres,

    dbc.Row(id='kpi-container', className='mb-4 g-3'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='evolution-ventes'), md=8),
        dbc.Col(dcc.Graph(id='ventes-par-rayon'), md=4),
    ], className='mb-4'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='evolution-produits'), md=12),
    ])
], fluid=True)

# Callback
@app.callback(
    [Output('kpi-container', 'children'),
     Output('evolution-ventes', 'figure'),
     Output('ventes-par-rayon', 'figure'),
     Output('evolution-produits', 'figure')],
    [Input('date-range', 'start_date'),
     Input('date-range', 'end_date'),
     Input('rayon-filter', 'value'),
     Input('produit-filter', 'value')]
)
def update_dashboard(start_date, end_date, selected_rayons, selected_produit):
    df_filtered = df[(df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))] if not df.empty else df
    if selected_rayons:
        df_filtered = df_filtered[df_filtered['Rayon'].isin(selected_rayons)]

    # KPI calculs
    total_ca = df_filtered['CA TTC (€)'].sum()
    total_articles = df_filtered['Nb Articles Vendus'].sum()
    moy_journaliere = df_filtered.groupby('Date')['CA TTC (€)'].sum().mean()

    kpis = [
        dbc.Col(create_kpi_card("CA Total", f"{total_ca:,.2f} €", "💶"), md=4),
        dbc.Col(create_kpi_card("Articles Vendus", f"{total_articles}", "📦"), md=4),
        dbc.Col(create_kpi_card("CA Moyen/Jour", f"{moy_journaliere:,.2f} €", "📅"), md=4),
    ]

    # Évolution des ventes
    evolution = df_filtered.groupby('Date')['CA TTC (€)'].sum().reset_index()
    fig_evolution = px.line(evolution, x='Date', y='CA TTC (€)', title="Évolution des Ventes",
                            markers=True, template='plotly_white', line_shape='spline')

    # Ventes par rayon
    ventes_rayons = df_filtered.groupby('Rayon')['CA TTC (€)'].sum().reset_index()
    fig_ventes_rayons = px.bar(ventes_rayons, x='CA TTC (€)', y='Rayon', orientation='h',
                               title="Ventes par Rayon", template='plotly_white', color_discrete_sequence=['#6f42c1'])
    
    # Évolution des produits
    if selected_produit:
        df_produit = df_filtered[df_filtered['Produit'] == selected_produit]
        evolution_produits = df_produit.groupby('Date')['CA TTC (€)'].sum().reset_index()
        fig_evolution_produits = px.line(evolution_produits, x='Date', y='CA TTC (€)', title=f"Évolution de {selected_produit}",
                                         markers=True, template='plotly_white', line_shape='spline')
    else:
        fig_evolution_produits = px.line(title="Évolution des Produits (sélectionnez un produit)", template='plotly_white')
    
    return kpis, fig_evolution, fig_ventes_rayons, fig_evolution_produits

# Lancement de l'application
if __name__ == '__main__':
    app.run_server(debug=True)
    
server = app.server  # Ajout pour Gunicorn