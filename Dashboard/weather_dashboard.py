import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from datetime import datetime, timedelta
import numpy as np
import os
import pydeck as pdk
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
# Load environment variables
# POSTGRES_HOST = os.getenv("POSTGRES_HOST")
# POSTGRES_PORT = os.getenv("POSTGRES_PORT")
# POSTGRES_DB = os.getenv("POSTGRES_DB")
# POSTGRES_USER = os.getenv("POSTGRES_USER")
# POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")


# # Database connection parameters
# DB_PARAMS = {
#     "host": POSTGRES_HOST,
#     "port": POSTGRES_PORT,
#     "database": POSTGRES_DB,
#     "user": POSTGRES_USER,
#     "password": POSTGRES_PASSWORD,
# }

# Set page config
st.set_page_config(
    page_title="Weather Stream Dashboard",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# SQLAlchemy engine for pandas operations
@st.cache_resource
# In your database connection function
def get_db_engine():
    """Create a SQLAlchemy engine for database connections"""
    try:
        # Use Streamlit secrets
        db_config = st.secrets["database"]
        
        # Create SQLAlchemy engine
        db_url = f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        st.error(f"Error creating database engine: {e}")
        return None

# Direct psycopg2 connection for operations that need it
@st.cache_resource
def get_psycopg2_connection():
    """Create a direct psycopg2 connection using Streamlit secrets"""
    try:
        # Get database credentials from Streamlit secrets
        db_config = st.secrets["database"]
        
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"],
            sslmode="require",
            connect_timeout=10
        )
        return conn
    except Exception as e:
        st.error(f"Error creating psycopg2 connection: {e}")
        return None
    
# Function to execute a query and return results using SQLAlchemy
def execute_query(query, params=None):
    """Execute a query using SQLAlchemy engine connection"""
    engine = get_db_engine()
    if not engine:
        return None

    try:
        with engine.connect() as connection:
            result = connection.execute(query, params or ())
            results = result.fetchall()
            return results
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None

# Function to load data using SQLAlchemy

# Updated function to load data using psycopg2 connection
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_analytics_data(time_period):
    """Load analytics data for the specified time period"""
    try:
        conn = get_psycopg2_connection()
        if not conn:
            return pd.DataFrame()
        
        if time_period == "Last 24 Hours":
            time_filter = "window_start >= NOW() - INTERVAL '24 hours'"
        elif time_period == "Last Week":
            time_filter = "window_start >= NOW() - INTERVAL '7 days'"
        elif time_period == "Last Month":
            time_filter = "window_start >= NOW() - INTERVAL '30 days'"
        else:
            time_filter = "window_start >= NOW() - INTERVAL '24 hours'"
        
        query = f"""
            SELECT 
                city_name, country, window_start, window_end,
                hourly_avg_temp, hourly_max_temp, hourly_min_temp,
                hourly_avg_humidity, hourly_avg_pressure, hourly_avg_wind,
                hourly_total_precipitation, hourly_avg_uv, hourly_confidence
            FROM weather_analytics
            WHERE {time_filter}
            ORDER BY window_start DESC, city_name
        """
        
        # Use pandas read_sql with the psycopg2 connection
        df = pd.read_sql(query, conn)
        
        # Don't close the connection as it's cached and reused
        return df
    except Exception as e:
        st.error(f"Error loading analytics data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_forecast_data():
    """Load weather forecast data"""
    try:
        conn = get_psycopg2_connection()
        if not conn:
            return pd.DataFrame()
        
      
        query = """
            SELECT 
                city_name, country, window_start, window_end,
                forecast_max_temp, forecast_min_temp,
                forecast_rain_chance, forecast_condition,
                created_at
            FROM weather_forecast
            WHERE window_start >= CURRENT_DATE
            ORDER BY city_name, window_start
        """
      
        df = pd.read_sql(query, conn)
    
        column_mapping = {
            'window_start': 'forecast_date'  # Map window_start to forecast_date for compatibility
        }
        df = df.rename(columns=column_mapping)
        
        # Don't close the connection as it's cached and reused
        return df
    except Exception as e:
        st.error(f"Error loading forecast data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_cities():
    """Load list of cities for filtering"""
    try:
        conn = get_psycopg2_connection()
        if not conn:
            return pd.DataFrame()
        
        query = """
            SELECT DISTINCT city_name, country
            FROM weather_analytics
            ORDER BY country, city_name
        """
        
        # Use pandas read_sql with the psycopg2 connection
        df = pd.read_sql(query, conn)
        
        # Don't close the connection as it's cached and reused
        return df
    except Exception as e:
        st.error(f"Error loading cities: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_historical_data(days=30):
    """Load historical weather data for trend analysis"""
    try:
        conn = get_psycopg2_connection()
        if not conn:
            return pd.DataFrame()
        
        query = f"""
            SELECT 
                city_name, country, window_start, 
                hourly_avg_temp, hourly_avg_humidity, hourly_avg_pressure,
                hourly_avg_wind, hourly_total_precipitation
            FROM weather_analytics
            WHERE window_start >= NOW() - INTERVAL '{days} days'
            ORDER BY city_name, window_start
        """
        
        # Use pandas read_sql with the psycopg2 connection
        df = pd.read_sql(query, conn)
        
        # Don't close the connection as it's cached and reused
        return df
    except Exception as e:
        st.error(f"Error loading historical data: {e}")
        return pd.DataFrame()   

# Define alert thresholds
ALERT_THRESHOLDS = {
    "high_temp": 35.0,          # °C
    "low_temp": 0.0,            # °C
    "high_wind": 20.0,          # m/s
    "high_precipitation": 10.0,  # mm
    "high_uv": 8.0,             # UV index
}

def check_alerts(df):
    """Check for weather alerts based on thresholds"""
    alerts = []
    
    if df.empty:
        return alerts
    
    # Group by city to get the latest data for each
    latest_by_city = df.sort_values('window_start', ascending=False).groupby('city_name').first().reset_index()
    
    # Check for high temperature
    high_temp_cities = latest_by_city[latest_by_city['hourly_max_temp'] >= ALERT_THRESHOLDS['high_temp']]
    for _, row in high_temp_cities.iterrows():
        alerts.append({
            'city': f"{row['city_name']}, {row['country']}",
            'alert_type': 'High Temperature',
            'value': f"{row['hourly_max_temp']:.1f}°C",
            'threshold': f"{ALERT_THRESHOLDS['high_temp']}°C",
            'time': row['window_start']
        })
    
    # Check for low temperature
    low_temp_cities = latest_by_city[latest_by_city['hourly_min_temp'] <= ALERT_THRESHOLDS['low_temp']]
    for _, row in low_temp_cities.iterrows():
        alerts.append({
            'city': f"{row['city_name']}, {row['country']}",
            'alert_type': 'Low Temperature',
            'value': f"{row['hourly_min_temp']:.1f}°C",
            'threshold': f"{ALERT_THRESHOLDS['low_temp']}°C",
            'time': row['window_start']
        })
    
    # Check for high wind
    high_wind_cities = latest_by_city[latest_by_city['hourly_avg_wind'] >= ALERT_THRESHOLDS['high_wind']]
    for _, row in high_wind_cities.iterrows():
        alerts.append({
            'city': f"{row['city_name']}, {row['country']}",
            'alert_type': 'High Wind',
            'value': f"{row['hourly_avg_wind']:.1f} m/s",
            'threshold': f"{ALERT_THRESHOLDS['high_wind']} m/s",
            'time': row['window_start']
        })
    
    # Check for high precipitation
    high_precip_cities = latest_by_city[latest_by_city['hourly_total_precipitation'] >= ALERT_THRESHOLDS['high_precipitation']]
    for _, row in high_precip_cities.iterrows():
        alerts.append({
            'city': f"{row['city_name']}, {row['country']}",
            'alert_type': 'Heavy Precipitation',
            'value': f"{row['hourly_total_precipitation']:.1f} mm",
            'threshold': f"{ALERT_THRESHOLDS['high_precipitation']} mm",
            'time': row['window_start']
        })
    
    # Check for high UV
    high_uv_cities = latest_by_city[latest_by_city['hourly_avg_uv'] >= ALERT_THRESHOLDS['high_uv']]
    for _, row in high_uv_cities.iterrows():
        alerts.append({
            'city': f"{row['city_name']}, {row['country']}",
            'alert_type': 'High UV Index',
            'value': f"{row['hourly_avg_uv']:.1f}",
            'threshold': f"{ALERT_THRESHOLDS['high_uv']}",
            'time': row['window_start']
        })
    
    return alerts

# UI Components
def display_sidebar():
    """Display and handle sidebar filters"""
    st.sidebar.title("Weather Stream Dashboard")
    st.sidebar.image("https://img.icons8.com/fluency/96/000000/partly-cloudy-day.png", width=80)
    
  

    # Time period filter
    time_period = st.sidebar.selectbox(
        "Select Time Period",
        ["Last 24 Hours", "Last Week", "Last Month"]
    )
    
    # Load city list for filtering
    cities_df = load_cities()
    
    # Region/Country filter
    if not cities_df.empty:
        countries = ["All"] + sorted(cities_df['country'].unique().tolist())
        selected_country = st.sidebar.selectbox("Select Country", countries)
        
        # Filter cities by selected country
        if selected_country != "All":
            filtered_cities = cities_df[cities_df['country'] == selected_country]
        else:
            filtered_cities = cities_df
        
        city_options = ["All"] + sorted(filtered_cities['city_name'].unique().tolist())
        selected_cities = st.sidebar.multiselect("Select Cities", city_options, default=["All"])
        
        # Handle the "All" selection
        if "All" in selected_cities:
            selected_cities = filtered_cities['city_name'].unique().tolist()
    else:
        selected_country = "All"
        selected_cities = []
    
    # Alert thresholds settings
    st.sidebar.markdown("---")
    st.sidebar.subheader("Alert Thresholds")
    
    with st.sidebar.expander("Customize Alert Thresholds", expanded=False):
        high_temp = st.slider("High Temperature (°C)", 25.0, 45.0, float(ALERT_THRESHOLDS["high_temp"]), 0.5)
        low_temp = st.slider("Low Temperature (°C)", -20.0, 10.0, float(ALERT_THRESHOLDS["low_temp"]), 0.5)
        high_wind = st.slider("High Wind (m/s)", 10.0, 30.0, float(ALERT_THRESHOLDS["high_wind"]), 0.5)
        high_precipitation = st.slider("Heavy Precipitation (mm)", 5.0, 50.0, float(ALERT_THRESHOLDS["high_precipitation"]), 1.0)
        high_uv = st.slider("High UV Index", 5.0, 12.0, float(ALERT_THRESHOLDS["high_uv"]), 0.5)
        
        # Update thresholds
        ALERT_THRESHOLDS["high_temp"] = high_temp
        ALERT_THRESHOLDS["low_temp"] = low_temp
        ALERT_THRESHOLDS["high_wind"] = high_wind
        ALERT_THRESHOLDS["high_precipitation"] = high_precipitation
        ALERT_THRESHOLDS["high_uv"] = high_uv
    
    st.sidebar.markdown("---")
    st.sidebar.info("Data refreshes every 15 minutes")
    
    return time_period, selected_country, selected_cities

def format_city_data(df, selected_cities):
    """Format data for selected cities"""
    if df.empty:
        return df
    
    # Filter by selected cities if needed
    if selected_cities and "All" not in selected_cities:
        df = df[df['city_name'].isin(selected_cities)]
    
    # Format timestamps for better display
    if 'window_start' in df.columns:
        df['window_start'] = pd.to_datetime(df['window_start'])
        df['formatted_time'] = df['window_start'].dt.strftime('%Y-%m-%d %H:%M')
    
    return df

def display_current_conditions(df):
    """Display current weather conditions for selected cities"""
    if df.empty:
        st.warning("No current weather data available.")
        return
    
    st.subheader("Current Weather Conditions")
    
    # Get the most recent data for each city
    latest_by_city = df.sort_values('window_start', ascending=False).groupby('city_name').first().reset_index()
    
    # Create a card-like display for each city
    cols = st.columns(min(4, len(latest_by_city)))
    
    for i, (_, row) in enumerate(latest_by_city.iterrows()):
        col_index = i % 4
        with cols[col_index]:
            st.markdown(f"""
            <div style="border:1px solid #ddd; border-radius:5px; padding:10px; margin-bottom:10px">
                <h3>{row['city_name']}, {row['country']}</h3>
                <p style="font-size:24px; margin:0">{row['hourly_avg_temp']:.1f}°C</p>
                <p>Range: {row['hourly_min_temp']:.1f}°C to {row['hourly_max_temp']:.1f}°C</p>
                <p>Humidity: {row['hourly_avg_humidity']:.1f}%</p>
                <p>Wind: {row['hourly_avg_wind']:.1f} m/s</p>
                <p>Updated: {row['formatted_time']}</p>
            </div>
            """, unsafe_allow_html=True)

def display_temperature_chart(df):
    """Display temperature chart for selected cities"""
    if df.empty:
        return
    
    st.subheader("Temperature Trends")
    
    # Prepare data for plotting
    fig = px.line(
        df, 
        x='window_start', 
        y='hourly_avg_temp',
        color='city_name',
        line_group='city_name',
        hover_data=['hourly_min_temp', 'hourly_max_temp', 'formatted_time'],
        labels={
            'window_start': 'Time',
            'hourly_avg_temp': 'Temperature (°C)',
            'city_name': 'City'
        },
        title="Average Temperature Over Time"
    )
    
    # Add range area for min/max temps
    for city in df['city_name'].unique():
        city_data = df[df['city_name'] == city].sort_values('window_start')
        fig.add_trace(
            go.Scatter(
                x=city_data['window_start'].tolist() + city_data['window_start'].tolist()[::-1],
                y=city_data['hourly_max_temp'].tolist() + city_data['hourly_min_temp'].tolist()[::-1],
                fill='toself',
                fillcolor=f'rgba(0, 100, 80, 0.2)',
                line=dict(color='rgba(255, 255, 255, 0)'),
                showlegend=False,
                name=f"{city} Range",
            )
        )
    
    fig.update_layout(height=400, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

def display_comparison_metrics(df):
    """Display comparison metrics across cities"""
    if df.empty:
        return
    
    st.subheader("Regional Weather Comparison")
    
    # Get the latest data for each city
    latest_by_city = df.sort_values('window_start', ascending=False).groupby('city_name').first().reset_index()
    
    # Create tabs for different metrics
    metric_tabs = st.tabs(["Temperature", "Humidity & Pressure", "Wind & Precipitation", "UV Index"])
    
    with metric_tabs[0]:
        # Temperature comparison
        temp_fig = px.bar(
            latest_by_city,
            x='city_name',
            y=['hourly_avg_temp', 'hourly_min_temp', 'hourly_max_temp'],
            barmode='group',
            labels={
                'city_name': 'City',
                'value': 'Temperature (°C)',
                'variable': 'Metric'
            },
            title="Temperature Comparison by City",
            color_discrete_map={
                'hourly_avg_temp': '#636EFA',
                'hourly_min_temp': '#00CC96',
                'hourly_max_temp': '#EF553B'
            }
        )
        temp_fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ))
        st.plotly_chart(temp_fig, use_container_width=True)
    
    with metric_tabs[1]:
        # Humidity and pressure
        cols = st.columns(2)
        
        with cols[0]:
            humidity_fig = px.bar(
                latest_by_city,
                x='city_name',
                y='hourly_avg_humidity',
                labels={
                    'city_name': 'City',
                    'hourly_avg_humidity': 'Humidity (%)'
                },
                title="Humidity Comparison",
                color='hourly_avg_humidity',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(humidity_fig, use_container_width=True)
        
        with cols[1]:
            pressure_fig = px.bar(
                latest_by_city,
                x='city_name',
                y='hourly_avg_pressure',
                labels={
                    'city_name': 'City',
                    'hourly_avg_pressure': 'Pressure (hPa)'
                },
                title="Atmospheric Pressure Comparison",
                color='hourly_avg_pressure',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(pressure_fig, use_container_width=True)
    
    with metric_tabs[2]:
        cols = st.columns(2)
        
        with cols[0]:
            wind_fig = px.bar(
                latest_by_city,
                x='city_name',
                y='hourly_avg_wind',
                labels={
                    'city_name': 'City',
                    'hourly_avg_wind': 'Wind Speed (m/s)'
                },
                title="Wind Speed Comparison",
                color='hourly_avg_wind',
                color_continuous_scale='Oranges'
            )
            st.plotly_chart(wind_fig, use_container_width=True)
        
        with cols[1]:
            precip_fig = px.bar(
                latest_by_city,
                x='city_name',
                y='hourly_total_precipitation',
                labels={
                    'city_name': 'City',
                    'hourly_total_precipitation': 'Precipitation (mm)'
                },
                title="Precipitation Comparison",
                color='hourly_total_precipitation',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(precip_fig, use_container_width=True)
    
    with metric_tabs[3]:
        uv_fig = px.bar(
            latest_by_city,
            x='city_name',
            y='hourly_avg_uv',
            labels={
                'city_name': 'City',
                'hourly_avg_uv': 'UV Index'
            },
            title="UV Index Comparison",
            color='hourly_avg_uv',
            color_continuous_scale='Reds'
        )
        uv_fig.add_hline(y=ALERT_THRESHOLDS['high_uv'], line_dash="dash", line_color="red", 
                          annotation_text="High UV Alert Threshold")
        st.plotly_chart(uv_fig, use_container_width=True)

def display_alerts(alerts):
    """Display weather alerts"""
    if not alerts:
        st.info("No weather alerts at this time.")
        return
    
    # Group alerts by city
    alerts_df = pd.DataFrame(alerts)
    
    # Display in a table with color-coded rows
    st.markdown("""
    <style>
    .alert-high-temp { background-color: #ffcccc; }
    .alert-low-temp { background-color: #ccccff; }
    .alert-high-wind { background-color: #ffffcc; }
    .alert-heavy-precip { background-color: #ccffff; }
    .alert-high-uv { background-color: #ffccff; }
    </style>
    """, unsafe_allow_html=True)
    
    for city in sorted(alerts_df['city'].unique()):
        city_alerts = alerts_df[alerts_df['city'] == city]
        
        alert_html = f"<h4>{city}</h4><table width='100%' style='text-align: left;'>"
        alert_html += "<tr><th>Alert Type</th><th>Value</th><th>Threshold</th><th>Time</th></tr>"
        
        for _, alert in city_alerts.iterrows():
            css_class = ""
            if alert['alert_type'] == "High Temperature":
                css_class = "alert-high-temp"
            elif alert['alert_type'] == "Low Temperature":
                css_class = "alert-low-temp"
            elif alert['alert_type'] == "High Wind":
                css_class = "alert-high-wind"
            elif alert['alert_type'] == "Heavy Precipitation":
                css_class = "alert-heavy-precip"
            elif alert['alert_type'] == "High UV Index":
                css_class = "alert-high-uv"
                
            time_str = pd.to_datetime(alert['time']).strftime('%Y-%m-%d %H:%M')
            
            alert_html += f"<tr class='{css_class}'>"
            alert_html += f"<td>{alert['alert_type']}</td>"
            alert_html += f"<td>{alert['value']}</td>"
            alert_html += f"<td>{alert['threshold']}</td>"
            alert_html += f"<td>{time_str}</td>"
            alert_html += "</tr>"
            
        alert_html += "</table><br>"
        st.markdown(alert_html, unsafe_allow_html=True)

def display_forecast(forecast_df, selected_cities):
    """Display weather forecast"""
    if forecast_df.empty:
        st.warning("No forecast data available.")
        return
    
    # Filter by selected cities
    if selected_cities and "All" not in selected_cities:
        forecast_df = forecast_df[forecast_df['city_name'].isin(selected_cities)]
    
    if forecast_df.empty:
        st.warning("No forecast data available for selected cities.")
        return
    
    st.subheader("Weather Forecast")
    
    # Convert forecast_date to datetime if needed
    if 'forecast_date' in forecast_df.columns:
        forecast_df['forecast_date'] = pd.to_datetime(forecast_df['forecast_date'])
    
    # Group by city and create tabs
    cities = sorted(forecast_df['city_name'].unique())
    if not cities:
        st.warning("No forecast data available.")
        return
    
    city_tabs = st.tabs(cities)
    
    for i, city in enumerate(cities):
        with city_tabs[i]:
            city_forecast = forecast_df[forecast_df['city_name'] == city].sort_values('forecast_date')
            
            # Display temperature forecast
            temp_fig = px.line(
                city_forecast,
                x='forecast_date',
                y=['forecast_max_temp', 'forecast_min_temp'],
                labels={
                    'forecast_date': 'Date',
                    'value': 'Temperature (°C)',
                    'variable': 'Metric'
                },
                title=f"Temperature Forecast for {city}",
                color_discrete_map={
                    'forecast_max_temp': '#EF553B',
                    'forecast_min_temp': '#00CC96'
                }
            )
            
            # Add area between min and max
            temp_fig.add_trace(
                go.Scatter(
                    x=city_forecast['forecast_date'].tolist() + city_forecast['forecast_date'].tolist()[::-1],
                    y=city_forecast['forecast_max_temp'].tolist() + city_forecast['forecast_min_temp'].tolist()[::-1],
                    fill='toself',
                    fillcolor='rgba(0, 100, 80, 0.2)',
                    line=dict(color='rgba(255, 255, 255, 0)'),
                    showlegend=False,
                    name=f"Temperature Range",
                )
            )
            
            temp_fig.update_layout(height=300, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(temp_fig, use_container_width=True)
            
            # Display precipitation forecast - Updated to use forecast_rain_chance instead
            if 'forecast_rain_chance' in city_forecast.columns:
                precip_fig = px.bar(
                    city_forecast,
                    x='forecast_date',
                    y='forecast_rain_chance',
                    labels={
                        'forecast_date': 'Date',
                        'forecast_rain_chance': 'Rain Chance (%)'
                    },
                    title=f"Precipitation Forecast for {city}",
                    color='forecast_rain_chance',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(precip_fig, use_container_width=True)
            
            # Display forecast details in a table
            st.markdown("### Detailed Forecast")
            
            # Adjust the columns to match the schema
            forecast_columns = ['forecast_date', 'forecast_max_temp', 'forecast_min_temp']
            
            if 'forecast_rain_chance' in city_forecast.columns:
                forecast_columns.append('forecast_rain_chance')
            
            if 'forecast_condition' in city_forecast.columns:
                forecast_columns.append('forecast_condition')
                
            if 'has_alerts' in city_forecast.columns:
                forecast_columns.append('has_alerts')
            
            forecast_table = city_forecast[forecast_columns]
            
            # Create readable column names for the table
            column_display_names = {
                'forecast_date': 'Date',
                'forecast_max_temp': 'Max Temp (°C)',
                'forecast_min_temp': 'Min Temp (°C)',
                'forecast_rain_chance': 'Rain Chance (%)',
                'forecast_condition': 'Conditions',
                'has_alerts': 'Weather Alerts'
            }
            
            forecast_table = forecast_table.rename(columns=column_display_names)
            
            # Format the date
            if 'Date' in forecast_table.columns:
                forecast_table['Date'] = forecast_table['Date'].dt.strftime('%Y-%m-%d')
            
            st.dataframe(forecast_table, use_container_width=True)



def display_weather_map(df):
    """Display an interactive weather map"""
    if df.empty:
        return
    
    st.subheader("Weather Map")
    
    # Prepare data for the map
    latest_by_city = df.sort_values('window_start', ascending=False).groupby('city_name').first().reset_index()
    
    # Check if we have latitude and longitude columns
    if 'latitude' not in latest_by_city.columns or 'longitude' not in latest_by_city.columns:
        # Use a geocoding API or hardcoded values for demo
        # This is a simplified version with some example coordinates
        city_coordinates = {
            'London': {'lat': 51.5074, 'lon': -0.1278},
            'New York': {'lat': 40.7128, 'lon': -74.0060},
            'Tokyo': {'lat': 35.6762, 'lon': 139.6503},
            'Paris': {'lat': 48.8566, 'lon': 2.3522},
            'Berlin': {'lat': 52.5200, 'lon': 13.4050},
            'Sydney': {'lat': -33.8688, 'lon': 151.2093},
            'Cairo': {'lat': 30.0444, 'lon': 31.2357},
            'Mumbai': {'lat': 19.0760, 'lon': 72.8777},
            'Rio de Janeiro': {'lat': -22.9068, 'lon': -43.1729},
            'Singapore': {'lat': 1.3521, 'lon': 103.8198}
        }
        
        # Add coordinates to the dataframe
        latest_by_city['latitude'] = latest_by_city['city_name'].apply(
            lambda city: city_coordinates.get(city, {'lat': 0})['lat']
        )
        latest_by_city['longitude'] = latest_by_city['city_name'].apply(
            lambda city: city_coordinates.get(city, {'lon': 0})['lon']
        )
    
    # Create map data with temperature color mapping
    map_data = latest_by_city.copy()
    
    # Normalize temperature for color scale (from cold blue to hot red)
    temp_min = map_data['hourly_avg_temp'].min()
    temp_max = map_data['hourly_avg_temp'].max()
    map_data['temp_normalized'] = (map_data['hourly_avg_temp'] - temp_min) / (temp_max - temp_min) if temp_max > temp_min else 0.5
    
    # Create color array based on temperature (blue to red)
    map_data['color_r'] = (map_data['temp_normalized'] * 255).astype(int)
    map_data['color_g'] = ((1 - map_data['temp_normalized']) * 100).astype(int)
    map_data['color_b'] = ((1 - map_data['temp_normalized']) * 255).astype(int)
    
    # Create tooltip text
    map_data['tooltip'] = map_data.apply(
        lambda row: f"{row['city_name']}, {row['country']}<br>"
                    f"Temp: {row['hourly_avg_temp']:.1f}°C<br>"
                    f"Wind: {row['hourly_avg_wind']:.1f} m/s<br>"
                    f"Humidity: {row['hourly_avg_humidity']:.0f}%",
        axis=1
    )
    
    # Set up PyDeck layers
    layers = [
        # Temperature circles
        pdk.Layer(
            "ScatterplotLayer",
            data=map_data,
            get_position=["longitude", "latitude"],
            get_radius=50000,  # Size of the circles
            get_fill_color=["color_r", "color_g", "color_b", 180],
            pickable=True,
            auto_highlight=True,
        ),
        # City labels
        pdk.Layer(
            "TextLayer",
            data=map_data,
            get_position=["longitude", "latitude"],
            get_text="city_name",
            get_size=16,
            get_color=[0, 0, 0],
            get_angle=0,
            get_text_anchor="middle",
            get_alignment_baseline="center",
        )
    ]
    
    # Set up view state
    view_state = pdk.ViewState(
        latitude=map_data['latitude'].mean(),
        longitude=map_data['longitude'].mean(),
        zoom=1.5,
        pitch=0,
    )
    
    # Create the deck
    deck = pdk.Deck(
        map_style="light",
        initial_view_state=view_state,
        layers=layers,
        tooltip={"text": "{tooltip}"},
    )
    
    # Render the deck
    st.pydeck_chart(deck)
    
    # Add legend
    cols = st.columns([1, 3, 1])
    with cols[1]:
        st.markdown(
            """
            <div style="display: flex; justify-content: space-between; margin-top: -20px">
                <div><span style="color: blue; font-weight: bold;">Cold</span></div>
                <div style="background: linear-gradient(to right, blue, purple, red); height: 20px; width: 100%; margin: 0 10px;"></div>
                <div><span style="color: red; font-weight: bold;">Hot</span></div>
            </div>
            """,
            unsafe_allow_html=True
        )


def display_historical_analysis():
    """Display historical data analysis and trends"""
    st.subheader("Historical Weather Analysis")
    
    # Load historical data
    days = st.slider("Select Historical Period (days)", 7, 90, 30)
    hist_data = load_historical_data(days)
    
    if hist_data.empty:
        st.warning("No historical data available for analysis.")
        return
    
    # Ensure timestamp is in datetime format
    hist_data['window_start'] = pd.to_datetime(hist_data['window_start'])
    
    # Add date components for analysis
    hist_data['date'] = hist_data['window_start'].dt.date
    hist_data['month'] = hist_data['window_start'].dt.month
    hist_data['day'] = hist_data['window_start'].dt.day
    hist_data['hour'] = hist_data['window_start'].dt.hour
    hist_data['day_of_week'] = hist_data['window_start'].dt.dayofweek
    
    # Select a city for detailed analysis
    cities = sorted(hist_data['city_name'].unique())
    selected_city = st.selectbox("Select City for Analysis", cities)
    
    city_data = hist_data[hist_data['city_name'] == selected_city]
    
    if city_data.empty:
        st.warning(f"No historical data available for {selected_city}.")
        return
    
    # Daily temperature trends
    st.markdown(f"### Temperature Trends for {selected_city}")
    
    # Group by date for daily averages
    daily_temps = city_data.groupby('date').agg({
        'hourly_avg_temp': ['mean', 'min', 'max'],
        'hourly_avg_humidity': 'mean',
        'hourly_total_precipitation': 'sum'
    }).reset_index()
    
    # Flatten multi-level columns
    daily_temps.columns = ['_'.join(col).strip('_') for col in daily_temps.columns.values]
    
    # Plot temperature trends
    temp_fig = px.line(
        daily_temps,
        x='date',
        y=['hourly_avg_temp_mean', 'hourly_avg_temp_min', 'hourly_avg_temp_max'],
        labels={
            'date': 'Date',
            'value': 'Temperature (°C)',
            'variable': 'Metric'
        },
        title=f"Daily Temperature Trends for {selected_city}",
        color_discrete_map={
            'hourly_avg_temp_mean': '#636EFA',
            'hourly_avg_temp_min': '#00CC96',
            'hourly_avg_temp_max': '#EF553B'
        }
    )
    
    # Add trendline
    daily_temps['day_number'] = range(len(daily_temps))
    trend = np.polyfit(daily_temps['day_number'], daily_temps['hourly_avg_temp_mean'], 1)
    trend_fn = np.poly1d(trend)
    trend_values = trend_fn(daily_temps['day_number'])
    
    temp_fig.add_trace(
        go.Scatter(
            x=daily_temps['date'],
            y=trend_values,
            mode='lines',
            name='Trend',
            line=dict(color='black', dash='dash')
        )
    )
    
    # Calculate trend direction and magnitude
    trend_direction = "upward" if trend[0] > 0 else "downward"
    trend_magnitude = abs(trend[0] * len(daily_temps))
    
    st.plotly_chart(temp_fig, use_container_width=True)
    
    # Display trend insights
    st.info(f"Temperature Trend: {trend_direction.capitalize()} trend of {trend_magnitude:.1f}°C over the {days}-day period.")
    
    # Temperature heatmap by hour of day
    st.markdown("### Temperature Patterns by Hour and Day")
    
    # Create a pivot table for hour of day vs. day
    hourly_temp = city_data.pivot_table(
        values='hourly_avg_temp',
        index='hour',
        columns='date',
        aggfunc='mean'
    )
    
    hour_fig = px.imshow(
        hourly_temp,
        labels=dict(x="Date", y="Hour of Day", color="Temperature (°C)"),
        title=f"Temperature Heatmap by Hour for {selected_city}",
        color_continuous_scale="RdBu_r",
        aspect="auto"
    )
    
    st.plotly_chart(hour_fig, use_container_width=True)
    
    # Correlation analysis
    st.markdown("### Weather Parameter Correlations")
    
    # Select parameters for correlation
    corr_params = city_data[['hourly_avg_temp', 'hourly_avg_humidity', 
                             'hourly_avg_pressure', 'hourly_avg_wind', 
                             'hourly_total_precipitation']]
    
    corr_matrix = corr_params.corr()
    
    corr_fig = px.imshow(
        corr_matrix,
        text_auto='.2f',
        labels=dict(x="Parameter", y="Parameter", color="Correlation"),
        title=f"Weather Parameter Correlations for {selected_city}",
        color_continuous_scale="RdBu_r"
    )
    
    st.plotly_chart(corr_fig, use_container_width=True)
    
    # Insights based on correlations
    strongest_corr = abs(corr_matrix.unstack()).sort_values(ascending=False)
    strongest_corr = strongest_corr[strongest_corr < 1]  # Remove self-correlations
    
    if not strongest_corr.empty:
        param1, param2 = strongest_corr.index[0]
        corr_value = corr_matrix.loc[param1, param2]
        relationship = "positive" if corr_value > 0 else "negative"
        
        st.info(f"Key Insight: There is a strong {relationship} correlation ({corr_value:.2f}) between {param1} and {param2}.")
        
        # Scatter plot of the strongest correlation
        scatter_fig = px.scatter(
            city_data,
            x=param1,
            y=param2,
            trendline="ols",
            labels={
                param1: param1.replace('hourly_', '').replace('_', ' ').title(),
                param2: param2.replace('hourly_', '').replace('_', ' ').title()
            },
            title=f"Relationship between {param1.replace('hourly_', '').replace('_', ' ').title()} and {param2.replace('hourly_', '').replace('_', ' ').title()}"
        )
        
        st.plotly_chart(scatter_fig, use_container_width=True)


