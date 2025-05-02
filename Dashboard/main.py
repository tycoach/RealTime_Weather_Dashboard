#main dashboard
# Import necessary libraries
import streamlit as st
import pandas as pd
import plotly.express as px
from weather_dashboard import (display_sidebar,
    load_analytics_data, load_forecast_data, load_historical_data, format_city_data,
    display_current_conditions, display_temperature_chart, display_comparison_metrics,
    display_weather_map, display_alerts, display_forecast, check_alerts,display_historical_analysis,
   get_latest_weather_data, display_current_weather_view,load_minimal_analytics_data)
from machine_learning import display_predictive_analytics, check_predictive_alerts, display_predictive_alerts
from email_alert import setup_email_alerts, send_alert_emails,send_predictive_alert_emails, setup_predictive_alert_controls
from constant import ALERT_THRESHOLDS



# Main dashboard with all enhancements
def main():
    # Get sidebar filters 
    time_period, selected_country, selected_cities, prediction_window = display_sidebar()
    
    # Configure email alerts
    email_config = setup_email_alerts()
    
    # Create header
    st.title("Weather Stream Dashboard")
    
    # Load appropriate data based on time period
    analytics_df = pd.DataFrame()
    if time_period == "Current Weather":
        st.markdown("Showing current weather conditions")
        # Load minimal historical data for the current weather context
        analytics_df = load_minimal_analytics_data()
    else:
        # Load historical data based on selected time period
        analytics_df = load_analytics_data(time_period)
        st.markdown(f"Showing data for the {time_period.lower()}")
    
    # Always load current weather data, forecast data, and historical data
    current_weather_df = get_latest_weather_data()
    forecast_df = load_forecast_data()
    historical_df = load_historical_data(30)  # 30 days by default
    
    # Format data for display
    if not analytics_df.empty:
        df = format_city_data(analytics_df, selected_cities)
    else:
        # Use current weather data as a fallback
        df = current_weather_df.copy() if not current_weather_df.empty else pd.DataFrame()
    
    # Check for current alerts
    current_alerts = []
    if not df.empty:
        current_alerts = check_alerts(df)

    prediction_window = st.sidebar.slider("Prediction Window (hours)", 1, 48, 6)
    min_confidence = setup_predictive_alert_controls()
    # Check for predictive alerts using forecast data
    try:
        predictive_alerts = check_predictive_alerts(forecast_df, ALERT_THRESHOLDS, prediction_window)
    except Exception as e:
        st.error(f"Error processing predictive alerts: {e}")
        predictive_alerts = []
    
    # Send email alerts if enabled
    if email_config["enabled"]:
        if current_alerts:
            send_alert_emails(current_alerts, email_config)
        if predictive_alerts:
            try:
                send_predictive_alert_emails(predictive_alerts, email_config)
            except Exception as e:
                st.error(f"Error sending predictive alert emails: {e}")
    
    # Create dashboard tabs (always show tabs, regardless of time period)
    dashboard_tabs = st.tabs([
        "Current Weather", 
        "Analytics", 
        "Weather Map",
        "Alerts", 
        "Forecast",
        "Historical Analysis",
        "Predictive Analytics"
    ])
    
    # Current Weather tab
    with dashboard_tabs[0]:
        if time_period == "Current Weather":
            # Display enhanced current conditions with detailed cards
            if not current_weather_df.empty:
                display_current_weather_view(current_weather_df, selected_cities)
            else:
                st.warning("No current weather data available.")
        else:
            # Regular current weather display for historical views
            if not df.empty:
                display_current_conditions(df)
                
                # Show city-specific trends
                if len(df['city_name'].unique()) <= 10:  # Limit for readability
                    display_temperature_chart(df)
                else:
                    st.warning("Too many cities selected for trend display. Please select fewer cities for detailed trends.")
            else:
                st.warning("No weather data available for the selected filters.")
    
    # Analytics tab
    with dashboard_tabs[1]:
        if not df.empty:
            display_comparison_metrics(df)
        else:
            st.warning("No data available for analytics.")
    
    # Weather Map tab
    with dashboard_tabs[2]:
        display_weather_map(df)
    
    # Alerts tab
    with dashboard_tabs[3]:
        # Create sub-tabs for current and predictive alerts
        alert_tabs = st.tabs(["Current Alerts", "Predictive Alerts"])
        
        with alert_tabs[0]:
            st.subheader("Current Weather Alerts")
            display_alerts(current_alerts)
        
        with alert_tabs[1]:
            st.subheader("Predicted Weather Alerts")
            try:
                display_predictive_alerts(predictive_alerts, prediction_window)
            except Exception as e:
                st.error(f"Error displaying predictive alerts: {e}")
                st.info("Predictive alerts feature is still in development.")
    
    # Forecast tab
    with dashboard_tabs[4]:
        try:
            display_forecast(forecast_df, selected_cities)
        except Exception as e:
            st.error(f"Error displaying forecast: {e}")
            st.info("Please check that forecast data contains the expected columns.")
    
    # Historical Analysis tab
    with dashboard_tabs[5]:
        try:
            display_historical_analysis()
        except Exception as e:
            st.error(f"Error displaying historical analysis: {e}")
    
    # Predictive Analytics tab
    with dashboard_tabs[6]:
        try:
            display_predictive_analytics(historical_df)
        except Exception as e:
            st.error(f"Error displaying predictive analytics: {e}")

if __name__ == "__main__":
    main()