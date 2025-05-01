# Add these imports at the top
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def train_weather_model(city_data):
    """Train a simple machine learning model for temperature prediction"""
    if city_data.empty or len(city_data) < 50:  # Need enough data
        return None, None, None
    
    #  extract hour and day of week from window_start
    city_data = city_data.copy()  # Create a copy to avoid modifying the original
    
    # Ensure window_start is datetime
    city_data['window_start'] = pd.to_datetime(city_data['window_start'])
    
    # Extract time features
    city_data['hour'] = city_data['window_start'].dt.hour
    city_data['day_of_week'] = city_data['window_start'].dt.dayofweek
    
    # Select the features that actually exist in our data
    feature_cols = ['hour', 'day_of_week']
    
    # Add other available columns if they exist
    available_features = ['hourly_avg_humidity', 'hourly_avg_pressure', 'hourly_avg_wind', 
                         'hourly_total_precipitation', 'hourly_avg_uv']
    
    for feature in available_features:
        if feature in city_data.columns:
            feature_cols.append(feature)
    
    # Prepare features
    features = city_data[feature_cols]
    target = city_data['hourly_avg_temp']
    
    # Handle any missing values
    features = features.fillna(features.mean())
    
    # Normalize features
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    # Train a Random Forest model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(features_scaled, target)
    
    # Calculate feature importance
    importance = model.feature_importances_
    feature_importance = pd.DataFrame({
        'feature': features.columns,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    return model, scaler, feature_importance, feature_cols

def detect_anomalies(city_data, model, scaler, feature_cols):
    """Detect weather anomalies using the trained model"""
    if model is None or scaler is None:
        return pd.DataFrame()
    
    # Create a copy to avoid modifying the original
    city_data = city_data.copy()
    
    # Ensure window_start is datetime
    city_data['window_start'] = pd.to_datetime(city_data['window_start'])
    
    # Extract time features if they don't exist
    if 'hour' not in city_data.columns:
        city_data['hour'] = city_data['window_start'].dt.hour
    if 'day_of_week' not in city_data.columns:
        city_data['day_of_week'] = city_data['window_start'].dt.dayofweek
    
    # Prepare features
    features = city_data[feature_cols]
    features = features.fillna(features.mean())
    
    # Scale features
    features_scaled = scaler.transform(features)
    
    # Make predictions
    predicted_temps = model.predict(features_scaled)
    
    # Calculate residuals (difference between actual and predicted)
    city_data['predicted_temp'] = predicted_temps
    city_data['residual'] = city_data['hourly_avg_temp'] - city_data['predicted_temp']
    
    # Calculate standard deviation of residuals
    residual_std = city_data['residual'].std()
    
    # Flag anomalies (temperatures that deviate significantly from prediction)
    threshold = 2.0  # Number of standard deviations
    city_data['is_anomaly'] = abs(city_data['residual']) > (threshold * residual_std)
    
    return city_data

def display_predictive_analytics(hist_data):
    """Display predictive analytics and anomaly detection"""
    if hist_data.empty:
        st.warning("Not enough historical data for predictive analytics.")
        return
    
    st.subheader("Predictive Analytics & Anomaly Detection")
    
    # Select a city for analysis
    cities = sorted(hist_data['city_name'].unique())
    
    if not cities:
        st.warning("No cities found in the historical data.")
        return
        
    selected_city = st.selectbox("Select City for Prediction", cities, key="pred_city")
    
    city_data = hist_data[hist_data['city_name'] == selected_city].copy()
    
    if len(city_data) < 50:
        st.warning(f"Not enough data for {selected_city} to build reliable predictions. Need at least 50 data points. Current count: {len(city_data)}")
        return
    
    # Train model
    model, scaler, feature_importance, feature_cols = train_weather_model(city_data)
    
    if model is None:
        st.warning("Could not train prediction model with available data.")
        return
    
    # Display feature importance
    st.markdown("### Weather Prediction Model")
    st.write("The following features influence temperature predictions:")
    
    imp_fig = px.bar(
        feature_importance,
        x='importance',
        y='feature',
        orientation='h',
        labels={
            'importance': 'Importance Score',
            'feature': 'Feature'
        },
        title="Feature Importance for Temperature Prediction"
    )
    
    st.plotly_chart(imp_fig, use_container_width=True)
    
    # Detect anomalies
    anomaly_data = detect_anomalies(city_data, model, scaler, feature_cols)
    
    # Display anomalies
    st.markdown("### Temperature Anomaly Detection")
    
    # Count anomalies
    anomaly_count = anomaly_data['is_anomaly'].sum()
    total_records = len(anomaly_data)
    anomaly_percentage = (anomaly_count / total_records) * 100 if total_records > 0 else 0
    
    st.metric("Anomalies Detected", f"{anomaly_count} ({anomaly_percentage:.1f}%)")
    
    # Plot actual vs predicted with anomalies highlighted
    anomaly_fig = go.Figure()
    
    # Add actual temperatures
    anomaly_fig.add_trace(
        go.Scatter(
            x=anomaly_data['window_start'],
            y=anomaly_data['hourly_avg_temp'],
            mode='lines',
            name='Actual Temperature',
            line=dict(color='blue')
        )
    )
    
    # Add predicted temperatures
    anomaly_fig.add_trace(
        go.Scatter(
            x=anomaly_data['window_start'],
            y=anomaly_data['predicted_temp'],
            mode='lines',
            name='Predicted Temperature',
            line=dict(color='green', dash='dash')
        )
    )
    
    # Add anomalies as scatter points
    anomalies = anomaly_data[anomaly_data['is_anomaly']]
    
    if not anomalies.empty:
        anomaly_fig.add_trace(
            go.Scatter(
                x=anomalies['window_start'],
                y=anomalies['hourly_avg_temp'],
                mode='markers',
                name='Anomalies',
                marker=dict(color='red', size=10, symbol='circle')
            )
        )
    
    anomaly_fig.update_layout(
        title=f"Temperature Anomaly Detection for {selected_city}",
        xaxis_title="Date",
        yaxis_title="Temperature (°C)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(anomaly_fig, use_container_width=True)
    
    # List significant anomalies
    if not anomalies.empty:
        st.markdown("### Significant Temperature Anomalies")
        
        anomalies = anomalies.sort_values(by='residual', key=abs, ascending=False)
        
        anomaly_table = anomalies[['window_start', 'hourly_avg_temp', 'predicted_temp', 'residual']].head(10)
        anomaly_table.columns = ['Timestamp', 'Actual Temp (°C)', 'Expected Temp (°C)', 'Difference (°C)']
        anomaly_table['Timestamp'] = anomaly_table['Timestamp'].dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(anomaly_table, use_container_width=True)
        
        # Provide insights
        largest_anomaly = anomalies.iloc[0]
        anomaly_date = largest_anomaly['window_start'].strftime('%Y-%m-%d %H:%M')
        diff = largest_anomaly['residual']
        direction = "higher" if diff > 0 else "lower"
        
        st.info(f"The most significant anomaly occurred on {anomaly_date} when the temperature was {abs(diff):.1f}°C {direction} than expected.")
    else:
        st.info("No significant temperature anomalies detected.")