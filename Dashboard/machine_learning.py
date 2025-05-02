# Add these imports at the top
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta


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

def check_predictive_alerts(forecast_df, thresholds, prediction_window=6, min_confidence=0.7):
    """Check forecast data for potential future alerts
    """
    from datetime import datetime, timedelta
    import pandas as pd
    
    if forecast_df is None or forecast_df.empty:
        return []
    
    predicted_alerts = []
    # Use timezone-naive current time to match the format in the database
    current_time = datetime.now()
    
    # Print column names for debugging
    print("Forecast DataFrame columns:", forecast_df.columns.tolist())
    
    # Check which date column is available in the dataframe
    date_column = None
    for col in ['window_start', 'forecast_date', 'created_at']:
        if col in forecast_df.columns:
            date_column = col
            break
    
    if date_column is None:
        print("No suitable date column found in forecast dataframe")
        return []
    
    # Ensure datetime format for the date column - keeping timezone information intact
    try:
        # First check if it's already a datetime
        if not pd.api.types.is_datetime64_any_dtype(forecast_df[date_column]):
            forecast_df[date_column] = pd.to_datetime(forecast_df[date_column])
    except Exception as e:
        print(f"Error converting {date_column} to datetime: {e}")
        return []
    
    # Filter forecast data within the prediction window
    try:
        future_data = forecast_df[
            (forecast_df[date_column] > current_time) & 
            (forecast_df[date_column] <= current_time + timedelta(hours=prediction_window))
        ]
    except Exception as e:
        print(f"Error filtering forecast data: {e}")
        # Try an alternative approach if comparison fails due to timezone issues
        try:
            # Convert timestamps to string format for comparison (this eliminates timezone issues)
            current_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            future_str = (current_time + timedelta(hours=prediction_window)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Filter using string representation
            forecast_df['date_str'] = forecast_df[date_column].dt.strftime('%Y-%m-%d %H:%M:%S')
            future_data = forecast_df[
                (forecast_df['date_str'] > current_str) & 
                (forecast_df['date_str'] <= future_str)
            ]
        except Exception as e2:
            print(f"Alternative filtering also failed: {e2}")
            return []
    
    if future_data.empty:
        print(f"No forecast data found within prediction window of {prediction_window} hours")
        return []
    
    # Group by city
    try:
        for city_name, city_data in future_data.groupby('city_name'):
            # Get country if available
            country = city_data['country'].iloc[0] if 'country' in city_data.columns else ""
            
            # Process each data point
            for row_idx, row in city_data.iterrows():
                # Calculate base confidence - higher for closer predictions
                time_diff = (row[date_column] - current_time).total_seconds() / 3600  # hours
                # Confidence decreases as prediction window increases (roughly 5% per hour)
                base_confidence = max(0.6, 1.0 - (time_diff * 0.05))
                
                # Check if has_alerts flag is available
                has_alert = False
                if 'has_weather_alerts' in row:
                    has_alert = row['has_weather_alerts']
                elif 'has_alerts' in row:
                    has_alert = row['has_alerts']
                
                # Calculate the final confidence scores
                high_temp_confidence = 0.9 * base_confidence if has_alert else 0.8 * base_confidence
                low_temp_confidence = 0.9 * base_confidence if has_alert else 0.8 * base_confidence
                precip_confidence = 0.85 * base_confidence if has_alert else 0.75 * base_confidence
                wind_confidence = 0.8 * base_confidence if has_alert else 0.7 * base_confidence
                severe_confidence = 0.85 * base_confidence if has_alert else 0.75 * base_confidence
                
                # Check high temperature (only if confidence meets threshold)
                if high_temp_confidence >= min_confidence:
                    if 'forecast_max_temp' in row and pd.notna(row['forecast_max_temp']):
                        if float(row['forecast_max_temp']) >= thresholds['high_temp']:
                            predicted_alerts.append({
                                'city': f"{city_name}, {country}",
                                'alert_type': 'Predicted High Temperature',
                                'value': f"{float(row['forecast_max_temp']):.1f}°C",
                                'threshold': f"{thresholds['high_temp']}°C",
                                'predicted_time': row[date_column],
                                'confidence': high_temp_confidence
                            })
                
                # Check low temperature (only if confidence meets threshold)
                if low_temp_confidence >= min_confidence:
                    if 'forecast_min_temp' in row and pd.notna(row['forecast_min_temp']):
                        if float(row['forecast_min_temp']) <= thresholds['low_temp']:
                            predicted_alerts.append({
                                'city': f"{city_name}, {country}",
                                'alert_type': 'Predicted Low Temperature',
                                'value': f"{float(row['forecast_min_temp']):.1f}°C",
                                'threshold': f"{thresholds['low_temp']}°C",
                                'predicted_time': row[date_column],
                                'confidence': low_temp_confidence
                            })
                
                # Check for precipitation (only if confidence meets threshold)
                if precip_confidence >= min_confidence:
                    if 'forecast_rain_chance' in row and pd.notna(row['forecast_rain_chance']):
                        rain_chance = float(row['forecast_rain_chance'])
                        if rain_chance >= thresholds['high_precipitation']:
                            predicted_alerts.append({
                                'city': f"{city_name}, {country}",
                                'alert_type': 'Predicted Heavy Precipitation',
                                'value': f"{rain_chance:.1f}%",
                                'threshold': f"{thresholds['high_precipitation']}%",
                                'predicted_time': row[date_column],
                                'confidence': precip_confidence
                            })
                
                # Infer extreme weather conditions from forecast_condition text if available
                if 'forecast_condition' in row and pd.notna(row['forecast_condition']):
                    condition = str(row['forecast_condition']).lower()
                    
                    # Check for high wind conditions in the forecast text (only if confidence meets threshold)
                    if wind_confidence >= min_confidence:
                        wind_keywords = ['storm', 'gale', 'hurricane', 'typhoon', 'windy', 'gusty']
                        if any(keyword in condition for keyword in wind_keywords):
                            predicted_alerts.append({
                                'city': f"{city_name}, {country}",
                                'alert_type': 'Predicted High Wind',
                                'value': f"Wind conditions: {row['forecast_condition']}",
                                'threshold': f"Wind warning",
                                'predicted_time': row[date_column],
                                'confidence': wind_confidence
                            })
                    
                    # Check for other severe weather in the forecast text (only if confidence meets threshold)
                    if severe_confidence >= min_confidence:
                        severe_keywords = ['thunder', 'lightning', 'hail', 'blizzard', 'tornado', 'cyclone']
                        if any(keyword in condition for keyword in severe_keywords):
                            predicted_alerts.append({
                                'city': f"{city_name}, {country}",
                                'alert_type': 'Predicted Severe Weather',
                                'value': f"{row['forecast_condition']}",
                                'threshold': f"Severe weather warning",
                                'predicted_time': row[date_column],
                                'confidence': severe_confidence
                            })
    except Exception as e:
        print(f"Error processing forecast data: {e}")
        
    print(f"Found {len(predicted_alerts)} predicted alerts")
    return predicted_alerts

def display_predictive_alerts(alerts, prediction_window):
    """Display predicted weather alerts"""
    if not alerts:
        st.info(f"No predicted weather alerts for the next {prediction_window} hours.")
        return
    
    # Add custom CSS for better styling
    st.markdown("""
    <style>
    /* Modern card styling */
    .prediction-card {
        background: linear-gradient(135deg, rgba(25,25,35,0.95) 0%, rgba(35,35,45,0.95) 100%);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 18px;
        border: 1px solid rgba(100, 100, 150, 0.2);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Alert type badges */
    .alert-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 30px;
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 10px;
        color: white;
    }
    
    /* Specific alert types */
    .alert-high-temp {
        background: linear-gradient(135deg, #ff4e50 0%, #f9d423 100%);
    }
    .alert-low-temp {
        background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%);
    }
    .alert-high-wind {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    .alert-heavy-precip {
        background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
    }
    .alert-severe-weather {
        background: linear-gradient(135deg, #b92b27 0%, #1565C0 100%);
    }
    .alert-high-uv {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    
    /* City headings */
    .city-heading {
        font-size: 22px;
        font-weight: 600;
        color: white;
        margin-bottom: 15px;
    }
    
    /* Prediction details */
    .prediction-value {
        font-size: 16px;
        margin-bottom: 8px;
        color: #eee;
    }
    
    /* Confidence indicators */
    .confidence-meter {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
    }
    .confidence-text {
        font-size: 14px;
        min-width: 120px;
    }
    .confidence-bar {
        height: 8px;
        flex-grow: 1;
        border-radius: 4px;
        background-color: rgba(255,255,255,0.1);
    }
    .confidence-fill {
        height: 100%;
        border-radius: 4px;
    }
    .confidence-high {
        background: linear-gradient(90deg, #52c234 0%, #061700 100%);
    }
    .confidence-medium {
        background: linear-gradient(90deg, #f2994a 0%, #f2c94c 100%);
    }
    .confidence-low {
        background: linear-gradient(90deg, #eb3349 0%, #f45c43 100%);
    }
    
    /* Timestamp */
    .prediction-time {
        font-size: 12px;
        text-align: right;
        color: #aaa;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Group alerts by city
    alerts_df = pd.DataFrame(alerts)
    
    # Create a timeline of predicted alerts
    if not alerts_df.empty:
        st.markdown("### Predicted Weather Events Timeline")
        
        # Convert predicted_time to datetime if needed
        alerts_df['predicted_time'] = pd.to_datetime(alerts_df['predicted_time'])
        
        # Sort by time
        alerts_df = alerts_df.sort_values('predicted_time')
        
        # Create a timeline visualization
        fig = px.timeline(
            alerts_df,
            x_start='predicted_time',
            x_end=alerts_df['predicted_time'] + pd.Timedelta(hours=1),  # Assuming 1-hour duration
            y='city',
            color='alert_type',
            hover_data=['value', 'threshold', 'confidence'],
            labels={
                'predicted_time': 'Predicted Time',
                'city': 'Location',
                'alert_type': 'Alert Type'
            },
            title=f"Predicted Weather Alerts for the Next {prediction_window} Hours"
        )
        
        fig.update_layout(
            height=400, 
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            xaxis=dict(
                gridcolor='rgba(255,255,255,0.1)',
                zerolinecolor='rgba(255,255,255,0.1)'
            ),
            yaxis=dict(
                gridcolor='rgba(255,255,255,0.1)',
                zerolinecolor='rgba(255,255,255,0.1)'
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Display detailed alerts
    st.markdown("### Detailed Predictions")
    
    # For each city
    for city in sorted(alerts_df['city'].unique()):
        city_alerts = alerts_df[alerts_df['city'] == city]
        
        st.markdown(f"<h3 class='city-heading'>{city}</h3>", unsafe_allow_html=True)
        
        for _, alert in city_alerts.iterrows():
            # Determine alert badge class
            badge_class = ""
            if "High Temperature" in alert['alert_type']:
                badge_class = "alert-high-temp"
            elif "Low Temperature" in alert['alert_type']:
                badge_class = "alert-low-temp"
            elif "High Wind" in alert['alert_type']:
                badge_class = "alert-high-wind"
            elif "Heavy Precipitation" in alert['alert_type']:
                badge_class = "alert-heavy-precip"
            elif "Severe Weather" in alert['alert_type']:
                badge_class = "alert-severe-weather"
            elif "High UV" in alert['alert_type']:
                badge_class = "alert-high-uv"
                
            # Format confidence
            confidence = float(alert['confidence'])
            confidence_pct = int(confidence * 100)
            
            # Determine confidence class
            confidence_class = ""
            if confidence >= 0.85:
                confidence_class = "confidence-high"
            elif confidence >= 0.7:
                confidence_class = "confidence-medium"
            else:
                confidence_class = "confidence-low"
                
            # Format time
            time_str = pd.to_datetime(alert['predicted_time']).strftime('%Y-%m-%d %H:%M')
            
            # Create card for this alert
            st.markdown(f"""
            <div class="prediction-card">
                <div class="alert-badge {badge_class}">{alert['alert_type']}</div>
                <div class="prediction-value">
                    Predicted value: <strong>{alert['value']}</strong> (Threshold: {alert['threshold']})
                </div>
                <div class="confidence-meter">
                    <div class="confidence-text">Confidence: {confidence_pct}%</div>
                    <div class="confidence-bar">
                        <div class="confidence-fill {confidence_class}" style="width: {confidence_pct}%;"></div>
                    </div>
                </div>
                <div class="prediction-time">Expected at: {time_str}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

def setup_predictive_alert_controls():
    """Set up controls for predictive alerts"""
    st.subheader("Predictive Alerts")
    
    # Create a help tooltip
    help_text = """
    This sets the minimum confidence level for displaying predictive alerts.
    Higher values show only the most confident predictions, while lower values
    show more predictions but with less certainty.
    """
    
    col1, col2 = st.columns([0.05, 0.95])
    with col1:
        st.markdown("ℹ️")
    with col2:
        st.markdown("Minimum confidence threshold for predictive alerts")
    
    # Fix the slider range from 50% to 95%
    min_confidence = st.slider(
        "",
        min_value=0.5,
        max_value=0.95,
        value=0.7,
        step=0.05,
        format="%d%%",
        help=help_text
    )
    
    return min_confidence