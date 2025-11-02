import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Streamlit Setup ---
st.set_page_config(
    page_title="Operational Efficiency Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS for consistent visuals ---
st.markdown("""
    <style>
    .stMetric-label {
        color: var(--text-color);
    }
    .stMetric-value {
        color: var(--text-color);
    }
    .stSubheader, .stMarkdown {
        color: var(--text-color);
    }
    .filter-tile {
        display: inline-block;
        padding: 8px 16px;
        margin: 4px;
        border-radius: 10px;
        cursor: pointer;
        font-weight: 600;
        border: 1px solid #444;
        background-color: #262730;
        color: #EEE;
        transition: 0.2s;
    }
    .filter-tile:hover {
        background-color: #F26A8D;
        color: white;
    }
    .selected {
        background-color: #F26A8D !important;
        color: white !important;
        border: none;
    }
    </style>
""", unsafe_allow_html=True)

# --- Data Loading and Preparation ---
@st.cache_data
def load_and_prepare_data():
    try:
        deliveries_df = pd.read_csv('deliveries.csv')
        fleet_df = pd.read_csv('fleet.csv')
    except FileNotFoundError:
        st.error("Missing data files. Ensure 'deliveries.csv' and 'fleet.csv' are in the same directory.")
        return pd.DataFrame()

    deliveries_df['date'] = pd.to_datetime(deliveries_df['date'])
    df = pd.merge(deliveries_df, fleet_df, on='vehicle_id', how='left')
    df = df.rename(columns={'city_x': 'delivery_city', 'city_y': 'vehicle_home_city'})
    df['delay_minutes'] = df['actual_minutes'] - df['planned_minutes']
    df['total_cost'] = df['fuel_cost'] + df['other_cost']
    df['cost_per_km'] = df['total_cost'] / df['distance_km']
    df['fuel_cost_per_km'] = df['fuel_cost'] / df['distance_km']
    df['month_name'] = df['date'].dt.strftime('%b %Y')
    return df

# --- KPI Calculations ---
@st.cache_data
def calculate_kpis(df):
    avg_delay = df['delay_minutes'].mean()
    on_time_rate = (df['on_time'].sum() / len(df)) * 100
    cost_per_km = df['total_cost'].sum() / df['distance_km'].sum()
    deliveries_per_vehicle = df.groupby('vehicle_id')['delivery_id'].count().mean()
    fuel_cost_ratio = (df['fuel_cost'].sum() / df['total_cost'].sum()) * 100
    return {
        "Average Delay": avg_delay,
        "On-Time Rate": on_time_rate,
        "Cost per Kilometer": cost_per_km,
        "Deliveries per Vehicle": deliveries_per_vehicle,
        "Fuel Cost Ratio": fuel_cost_ratio
    }

# --- Chart Data Preparation ---
@st.cache_data
def prepare_chart_data(df):
    delay_by_city = df.groupby('delivery_city')['delay_minutes'].mean().reset_index()
    cost_time_city = df.groupby('delivery_city').agg(
        cost_per_km=('cost_per_km', 'mean'),
        on_time_rate=('on_time', 'mean')
    ).reset_index()
    cost_time_city['on_time_rate'] *= 100
    deliveries_per_vehicle_data = df.groupby('vehicle_id')['delivery_id'].count().to_frame('deliveries_count').reset_index()
    monthly_trend = df.set_index('date').resample('M').agg(
        avg_delay=('delay_minutes', 'mean'),
        cost_per_km=('cost_per_km', 'mean')
    ).reset_index()
    monthly_trend['month_name'] = monthly_trend['date'].dt.strftime('%b %Y')
    return delay_by_city, cost_time_city, deliveries_per_vehicle_data, monthly_trend

# --- Plotly Chart Functions ---
def create_fig1(delay_by_city):
    city_colors = {"Abuja": "#CBEEF3", "Ibadan": "#F49CBB", "Lagos": "#F26A8D", "PHC": "#DD2D4A", "Kano": "#880D1E"}
    fig = px.bar(delay_by_city.sort_values('delay_minutes', ascending=False),
                 x="delivery_city", y="delay_minutes", text_auto=".2f",
                 color="delivery_city", color_discrete_map=city_colors, template="plotly_dark")
    fig.update_traces(marker_line_color="white", marker_line_width=1.5)
    fig.update_layout(
        title="Average Delay by City", xaxis_title="", yaxis_title="",
        showlegend=False, plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False), yaxis=dict(showgrid=False)
    )
    return fig

def create_fig2(cost_time_city):
    city_colors = {"Abuja": "#880D1E", "Ibadan": "#DD2D4A", "Lagos": "#F26A8D", "PHC": "#F49CBB", "Kano": "#CBEEF3"}
    cost_time_city["color"] = cost_time_city["delivery_city"].map(city_colors)
    fig = px.scatter(cost_time_city, x="cost_per_km", y="on_time_rate", text="delivery_city", template="plotly_dark")
    fig.update_traces(marker=dict(color=cost_time_city["color"], size=12, opacity=0.85, line=dict(width=1, color="white")),
                      textposition="top center")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=True, title="Cost per km"), yaxis=dict(showgrid=True, title="On-Time Rate"))
    return fig

def create_fig3(deliveries_per_vehicle_data):
    fig = px.box(deliveries_per_vehicle_data, y="deliveries_count", points="all",
                 title="Deliveries per Vehicle Distribution", color_discrete_sequence=["#F26A8D"], template="plotly_dark")
    fig.update_traces(marker=dict(color="#DD2D4A", opacity=0.6))
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Number of Deliveries per Vehicle", xaxis_title="", xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
    return fig

def create_fig4(monthly_trend):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly_trend["month_name"], y=monthly_trend["avg_delay"], mode="lines+markers",
                             name="Average Delay", line=dict(shape="spline", color="#F49CBB", width=3),
                             fill='tozeroy', fillcolor="rgba(244, 156, 187, 0.2)"))
    fig.add_trace(go.Scatter(x=monthly_trend["month_name"], y=monthly_trend["cost_per_km"], mode="lines+markers",
                             name="Cost per km", line=dict(shape="spline", color="#CBEEF3", width=3, dash="dash")))
    fig.update_layout(title="Monthly Trend: Average Delay and Cost per km",
                      template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, tickformat=".2f"),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# --- Main Streamlit App ---
def main():
    st.title("Logistics Operational Efficiency Analytics")
    st.markdown("---")

    df = load_and_prepare_data()
    if df.empty:
        return

    # --- Sidebar Filters (Tile style) ---
    st.sidebar.header("Filters")

    cities = sorted(df['delivery_city'].unique())
    months = sorted(df['month_name'].unique())

    selected_city = st.sidebar.radio("Select City", options=["All"] + cities, horizontal=True)
    selected_month = st.sidebar.radio("Select Month", options=["All"] + months, horizontal=True)

    # Apply Filters
    if selected_city != "All":
        df = df[df['delivery_city'] == selected_city]
    if selected_month != "All":
        df = df[df['month_name'] == selected_month]

    # --- KPI Section ---
    kpis = calculate_kpis(df)
    st.subheader("High-Level Performance Benchmarks")

    # Prepare monthly summary for MoM
    df_with_ratio = df.copy()
    df_with_ratio['fuel_cost_ratio'] = (df_with_ratio['fuel_cost'] / df_with_ratio['total_cost']) * 100

    monthly_summary = df_with_ratio.set_index('date').resample('M').agg(
        avg_delay=('delay_minutes', 'mean'),
        on_time_rate=('on_time', 'mean'),
        cost_per_km=('cost_per_km', 'mean'),
        deliveries_per_vehicle=('delivery_id', 'count'),
        fuel_cost_ratio=('fuel_cost_ratio', 'mean')
    ).reset_index()

    mom_values = {}
    for col in ['avg_delay', 'on_time_rate', 'cost_per_km', 'deliveries_per_vehicle', 'fuel_cost_ratio']:
        if len(monthly_summary) >= 2:
            prev, curr = monthly_summary[col].iloc[-2], monthly_summary[col].iloc[-1]
            mom = ((curr - prev) / prev) * 100 if prev != 0 else 0
        else:
            mom = 0
        mom_values[col] = mom

    kpi_map = {
        "Average Delay": "avg_delay",
        "On-Time Rate": "on_time_rate",
        "Cost per Kilometer": "cost_per_km",
        "Deliveries per Vehicle": "deliveries_per_vehicle",
        "Fuel Cost Ratio": "fuel_cost_ratio"
    }

    cols = st.columns(len(kpis))
    for col, (name, value) in zip(cols, kpis.items()):
        if "Average Delay" in name:
            display_value = f"{value:.2f}"
        elif "Deliveries" in name:
            display_value = f"{value:.0f}"
        elif "Rate" in name or "Ratio" in name:
            display_value = f"{value:.2f}%"
        else:
            display_value = f"₦{value:.2f}"
            
        mom = mom_values[kpi_map[name]]
        if name in ["Average Delay", "Cost per Kilometer", "Fuel Cost Ratio"]:
            arrow = "▲" if mom < 0 else "▼"
            color = "green" if mom < 0 else "red"
        else:
            arrow = "▲" if mom > 0 else "▼"
            color = "green" if mom > 0 else "red"
        mom_text = f"{arrow} {abs(mom):.1f}%"
        col.markdown(f"<div style='background-color:#1E1E1E; padding:15px; border-radius:12px; text-align:center;'>"
                     f"<p style='color:#DDD; font-size:18px; font-weight:bold'>{name}</p>"
                     f"<p style='font-size:40px; font-weight:bold; margin:5px 0'>{display_value}</p>"
                     f"<p style='color:{color}; font-size:16px; font-weight:bold'>{mom_text}</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- Chart Data ---
    delay_by_city, cost_time_city, deliveries_per_vehicle_data, monthly_trend = prepare_chart_data(df)

    st.subheader("Geographic and Time-Based Performance Analysis")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(create_fig1(delay_by_city), use_container_width=True)
    with col2:
        st.plotly_chart(create_fig4(monthly_trend), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(create_fig2(cost_time_city), use_container_width=True)
    with col4:
        st.plotly_chart(create_fig3(deliveries_per_vehicle_data), use_container_width=True)

if __name__ == "__main__":
    main()
  