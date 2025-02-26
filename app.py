import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

# Initialisation de l'application avec un thème Bootstrap moderne
app = Dash(__name__, external_stylesheets=[dbc.themes.LUX])
app.title = "Dashboard des Ventes Revu"

# Fonction pour créer des cartes KPI stylées
def create_kpi_card(title, value, icon):
    return dbc.Card([
        dbc.CardBody([
            html.H6([icon, f" {title}"], className="card-title text-muted"),
            html.H3(value, className="card-text fw-bold")
        ])
    ], className="shadow rounded-4 text-center", style={"backgroundColor": "#fefefe"})

# Filtres
filtres = dbc.Row([
    dbc.Col(dcc.DatePickerRange(
        id='date-range',
        start_date=None,
        end_date=None,
        display_format='DD/MM/YYYY',
        className='w-100'
    ), width=4),
    dbc.Col(dcc.Dropdown(
        id='rayon-filter',
        placeholder="Choisir un rayon",
        multi=True,
        className='w-100'
    ), width=4),
    dbc.Col(dcc.Dropdown(
        id='produit-filter',
        placeholder="Choisir un produit",
        multi=False,
        className='w-100'
    ), width=4)
], className='mb-4')

# Layout du dashboard
app.layout = dbc.Container([
    html.H1("📈 Dashboard des Ventes", className="text-center my-4 fw-bold"),
    filtres,
    
    dcc.Interval(
        id='interval-component',
        interval=60000,  # Rafraîchissement automatique toutes les 60 secondes
        n_intervals=0
    ),

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
     Output('evolution-produits', 'figure'),
     Output('date-range', 'start_date'),
     Output('date-range', 'end_date'),
     Output('rayon-filter', 'options'),
     Output('produit-filter', 'options')],
    [Input('date-range', 'start_date'),
     Input('date-range', 'end_date'),
     Input('rayon-filter', 'value'),
     Input('produit-filter', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_dashboard(start_date, end_date, selected_rayons, selected_produit, n_intervals):
    df = pd.read_excel("Tableau_Ventes_Fictives_Avec_Dates_Ajuste.xlsx")
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    
    if start_date is None:
        start_date = df['Date'].min()
    if end_date is None:
        end_date = df['Date'].max()
    
    df_filtered = df[(df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))]
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

    # Options filtres
    rayons_options = [{'label': r, 'value': r} for r in df['Rayon'].unique()]
    produits_options = [{'label': p, 'value': p} for p in df['Produit'].unique()]
    
    # Évolution des produits avec condition sur la sélection
    if selected_produit:
        df_produit = df_filtered[df_filtered['Produit'] == selected_produit]
        evolution_produits = df_produit.groupby('Date')['CA TTC (€)'].sum().reset_index()
        title = f"Évolution de {selected_produit}"
        fig_evolution_produits = px.line(evolution_produits, x='Date', y='CA TTC (€)', title=title,
                                         markers=True, template='plotly_white', line_shape='spline',
                                         color_discrete_sequence=['#ff7f0e'])
    else: 
        fig_evolution_produits = px.line(title="Évolution des Produits (sélectionnez un produit)", template='plotly_white')

    return kpis, fig_evolution, fig_ventes_rayons, fig_evolution_produits, start_date, end_date, rayons_options, produits_options

# Lancement de l'application
if __name__ == '__main__':
    app.run_server(debug=True)

server = app.server  # Ajout pour Gunicorn

