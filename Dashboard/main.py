#main dashboard
# Import necessary libraries
import streamlit as st
import pandas as pd
import plotly.express as px
from weather_dashboard import (display_sidebar,
    load_analytics_data, load_forecast_data, load_historical_data, format_city_data,
    display_current_conditions, display_temperature_chart, display_comparison_metrics,
    display_weather_map, display_alerts, display_forecast, check_alerts,display_historical_analysis,get_db_engine)
from machine_learning import display_predictive_analytics
from email_alert import setup_email_alerts, send_alert_emails



# Main dashboard with all enhancements
def main():
    # Get sidebar filters
    time_period, selected_country, selected_cities = display_sidebar()
    
    # Configure email alerts
    email_config = setup_email_alerts()
    
    # Create header
    st.title("Weather Stream Dashboard")
    st.markdown(f"Showing data for the {time_period.lower()}")
    
    # Load data based on filters
    analytics_df = load_analytics_data(time_period)
    forecast_df = load_forecast_data()
    historical_df = load_historical_data(30)  # 30 days by default
    
    # Format data for display
    df = format_city_data(analytics_df, selected_cities)
    
    # Check for alerts
    alerts = check_alerts(df)
    
    # # Send email alerts if enabled
    if email_config["enabled"] and alerts:
        send_alert_emails(alerts, email_config)
    
    # Create dashboard tabs
    dashboard_tabs = st.tabs([
        "Current Weather", 
        "Analytics", 
        "Weather Map",
        "Alerts", 
        "Forecast",
        "Historical Analysis",
        "Predictive Analytics"
    ])
    
    with dashboard_tabs[0]:
        if not df.empty:
            display_current_conditions(df)
            
            # Show city-specific trends
            if len(df['city_name'].unique()) <= 10:  # Limit for readability
                display_temperature_chart(df)
            else:
                st.warning("Too many cities selected for trend display. Please select fewer cities for detailed trends.")
        else:
            st.warning("No weather data available for the selected filters.")
    
    with dashboard_tabs[1]:
        if not df.empty:
            display_comparison_metrics(df)
        else:
            st.warning("No data available for analytics.")
    
    with dashboard_tabs[2]:
        display_weather_map(df)
    
    with dashboard_tabs[3]:
        st.subheader("Weather Alerts")
        display_alerts(alerts)
    
    with dashboard_tabs[4]:
        display_forecast(forecast_df, selected_cities)
    
    with dashboard_tabs[5]:
        display_historical_analysis()
    
    with dashboard_tabs[6]:
        display_predictive_analytics(historical_df)

if __name__ == "__main__":
    main()
