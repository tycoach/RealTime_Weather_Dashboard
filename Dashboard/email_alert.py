# Add these imports if not already included
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import streamlit as st
import  pandas as pd
import os
from dotenv import load_dotenv
from weather_dashboard import load_cities
from datetime import datetime, timedelta


load_dotenv()
# Load environment variables
# EMAIL_SENDER = os.getenv("EMAIL_SENDER")
# EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  


def parse_email_list(email_string):
    """Parse comma-separated email string into a list of valid emails
    and provide warnings for invalid formats.
    """
    if not email_string or not isinstance(email_string, str):
        return []
    
    # Split by comma
    raw_emails = email_string.split(',')
    
    # Process and validate each email
    valid_emails = []
    for raw_email in raw_emails:
        email = raw_email.strip()
        
        # Skip empty strings
        if not email:
            continue
            
        # Skip single characters (like 'd') which cause RFC 5321 errors
        if len(email) <= 1:
            st.warning(f"Skipping invalid email: '{email}' (too short)")
            continue
            
        # Basic validation - must contain @ and .
        if '@' not in email or '.' not in email:
            st.warning(f"Skipping invalid email format: '{email}'")
            continue
            
        valid_emails.append(email)
    
    return valid_emails
def setup_email_alerts():
    """Set up email alert configuration with user input and validation"""
    st.markdown("## Email Alert Configuration")
    
    # Create a form to prevent sending emails until user submits all selections
    with st.form("email_alert_setup_form"):
        st.markdown("Configure your email alert preferences below:")
        
        # Enable/disable email alerts
        enable_alerts = st.toggle("Enable Email Alerts", value=False)
        
        # Default empty configuration
        email_config = {
            "enabled": False,
            "recipients": [],
            "types": [],
            "cities": [],
            "frequency": "immediate",
            "min_confidence": 0.7,
            "last_sent": {},  # Track when alerts were last sent to prevent duplicates
        }
        
        # Only show configuration options if alerts are enabled
        if enable_alerts:
            # Get recipient email addresses
            email_input = st.text_input(
                "Email Recipients (comma-separated)",
                placeholder="email@example.com, another@example.com",
                help="Enter email addresses separated by commas"
            )
            
            # City-specific filtering
            st.subheader("City Filtering")
            st.markdown(
                "Select which cities to receive alerts for. Leave blank to receive alerts for all cities."
            )
            
            # Get available cities
            cities_df = load_cities()
            if not cities_df.empty:
                available_cities = sorted(cities_df['city_name'].unique().tolist())
                selected_alert_cities = st.multiselect(
                    "Cities to monitor",
                    available_cities,
                    default=[]
                )
            else:
                selected_alert_cities = []
                st.warning("No cities available for filtering")
            
            # Alert types
            st.subheader("Alert Types")
            
            col1, col2 = st.columns(2)
            with col1:
                high_temp_alert = st.checkbox("High Temperature", value=True)
                low_temp_alert = st.checkbox("Low Temperature", value=True)
                high_wind_alert = st.checkbox("High Wind", value=True)
            
            with col2:
                high_precip_alert = st.checkbox("Heavy Precipitation", value=True)
                high_uv_alert = st.checkbox("High UV Index", value=True)
                severe_weather_alert = st.checkbox("Severe Weather", value=True)
            
            alert_types = []
            if high_temp_alert:
                alert_types.append("High Temperature")
            if low_temp_alert:
                alert_types.append("Low Temperature")
            if high_wind_alert:
                alert_types.append("High Wind")
            if high_precip_alert:
                alert_types.append("Heavy Precipitation")
            if high_uv_alert:
                alert_types.append("High UV Index")
            if severe_weather_alert:
                alert_types.append("Severe Weather")
            
            # Predictive alerts confidence threshold
            st.subheader("Predictive Alerts")
            
            min_confidence = st.slider(
                "Minimum confidence threshold for predictive alerts",
                min_value=50,
                max_value=95,
                value=70,
                step=5,
                format="%d%%",
                help="Only send predictive alerts with confidence above this threshold"
            )
            
            # Convert from percentage to decimal
            min_confidence = min_confidence / 100.0
            
            # Alert frequency
            st.subheader("Alert Frequency")
            
            frequency = st.radio(
                "How often to send alerts",
                options=["Immediate", "Hourly Digest", "Daily Digest"],
                index=0,
                help="Immediate: Send alerts as soon as detected; Digest: Group alerts and send periodically"
            )
        
        # Submit button for the form
        submit_button = st.form_submit_button("Save Alert Settings")
        
        # Process form submission
        if submit_button:
            if enable_alerts:
                recipients = [email.strip() for email in email_input.split(",") if email.strip()]
                
                if not recipients:
                    st.error("Please enter at least one email address.")
                    return email_config
                
                # Create friendly confirmation message
                city_message = "all cities" if not selected_alert_cities else ", ".join(selected_alert_cities)
                alert_message = ", ".join(alert_types)
                
                st.success(
                    f"""
                    📬 **Email Alert Setup Complete!**
                    
                    We'll notify you at {', '.join(recipients)} when weather conditions meet your criteria.
                    
                    **Monitoring:** {city_message}  
                    **Alert Types:** {alert_message}  
                    **Delivery:** {frequency}
                    
                    Sit back and relax - we'll keep an eye on the weather for you!
                    """
                )
                
                # Update config
                email_config = {
                    "enabled": True,
                    "recipients": recipients,
                    "types": alert_types,
                    "cities": selected_alert_cities,
                    "frequency": frequency.lower(),
                    "min_confidence": min_confidence,
                    "last_sent": {},  # Track when alerts were last sent to prevent duplicates
                }
                
                # Send test email on first setup
                try:
                    send_test_email(recipients, selected_alert_cities)
                    st.info("We've sent a test email to confirm your settings. Please check your inbox.")
                except Exception as e:
                    st.error(f"Error sending test email: {e}")
            else:
                st.info("Email alerts have been disabled.")
    
    # Store the config in session state so it persists across reruns
    if "email_config" not in st.session_state:
        st.session_state.email_config = email_config
    elif submit_button:
        st.session_state.email_config = email_config
    
    # Use the stored config
    return st.session_state.email_config
    
    return email_config
def validate_emails(email_list):
    """Validate email addresses using regex pattern"""
    valid_emails = []
    invalid_emails = []
    
    # Basic email validation regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    for email in email_list:
        if email and re.match(email_pattern, email):
            valid_emails.append(email)
        else:
            invalid_emails.append(email)
    
    return valid_emails, invalid_emails

def send_test_email(recipients, monitored_cities):
    """Send a test email to confirm alert setup"""
 
    
    # Get email credentials from secrets
    sender_email = st.secrets["email"]["sender"]
    sender_password = st.secrets["email"]["password"]

    
    # sender_email = os.getenv("EMAIL_SENDER")
    # sender_password = os.getenv("EMAIL_PASSWORD") 
    
    # Build HTML email content
    city_message = "all cities" if not monitored_cities else ", ".join(monitored_cities)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 20px; border-radius: 10px; }}
            .header {{ text-align: center; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
            .logo {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
            .content {{ padding: 20px 0; }}
            .footer {{ margin-top: 30px; text-align: center; font-size: 12px; color: #7f8c8d; border-top: 1px solid #eee; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">⛅ Weather Stream Alert</div>
                <p>Test Email</p>
            </div>
            
            <div class="content">
                <h2>Your Weather Alert Setup is Complete!</h2>
                <p>This is a test email to confirm that your weather alerts are properly configured.</p>
                
                <h3>Your Alert Settings</h3>
                <p><strong>Monitoring:</strong> {city_message}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                
                <p>When weather conditions meet your specified criteria, you'll receive alerts like this one.</p>
            </div>
            
            <div class="footer">
                <p>This is a test email from Weather Stream Dashboard. You received this because you just set up weather alerts.</p>
                <p>To modify your alert settings, please visit the dashboard.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Connect to server
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        
        # Send to each recipient INDIVIDUALLY to avoid multiple To headers
        for recipient in recipients:
            # Create a new message for each recipient to avoid multiple To headers
            message = MIMEMultipart("alternative")
            message["Subject"] = "Test Email - Weather Stream Alerts"
            message["From"] = "Weather Alert Mailer"
            message["To"] = recipient  # Only one recipient per message
            
            # Attach HTML content
            message.attach(MIMEText(html, "html"))
            
            # Send to this individual recipient
            server.sendmail(sender_email, recipient, message.as_string())
    
    return True

def send_email(recipient, subject, body):
   
    """Send an email with the specified subject and body"""
    sender_email = st.secrets["email"]["sender"]
    sender_password = st.secrets["email"]["password"]
    if not sender_email or not sender_password:
        st.error("Email sender or password not configured.")
        return False  
    
    try:
        # Check if recipient is a dictionary (common error cause)
        if isinstance(recipient, dict):
            st.error(f"Error: Email recipient is a dictionary: {recipient}")
            return False
        
        # Convert to string and validate email format
        recipient_str = str(recipient).strip()
        
        # Check for single character email (likely the cause of your error)
        if len(recipient_str) <= 1:
            st.error(f"Error: Invalid email address - too short: '{recipient_str}'")
            return False
            
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, recipient_str):
            st.error(f"Error: Invalid email format: '{recipient_str}'")
            return False
        
        # Create message
        message = MIMEMultipart()
        message["From"] = "Weather Alert Mailer"
        message["Sender"] = sender_email
        message["To"] = recipient_str
        message["Subject"] = subject
        
        # Attach HTML body
        message.attach(MIMEText(body, "html"))
        
        # Debug output (remove in production)
        st.info(f"Attempting to send email to: '{recipient_str}'")
        
        # Connect to Gmail SMTP server
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_str, message.as_string())
        
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

def send_alert_emails(alerts, email_config):
    """Send email alerts """   
    if not email_config["enabled"] or not alerts or not email_config["recipients"]:
        return
    
    # Filter alerts by city if specified
    if email_config["cities"]:
        filtered_alerts = [
            alert for alert in alerts
            if any(city in alert["city"] for city in email_config["cities"])
        ]
    else:
        filtered_alerts = alerts
    
    if not filtered_alerts:
        return
    
    # Filter alerts by type
    filtered_alerts = [
        alert for alert in filtered_alerts
        if alert["alert_type"] in email_config["types"]
    ]
    
    if not filtered_alerts:
        return
    
    # Check for duplicates based on frequency settings
    current_time = datetime.now()
    deduped_alerts = []
    
    for alert in filtered_alerts:
        alert_key = f"{alert['city']}_{alert['alert_type']}"
        
        # Check when this alert was last sent
        last_sent = email_config["last_sent"].get(alert_key)
        
        # Determine if we should send based on frequency
        send_alert = False
        
        if not last_sent:
            # Never sent before
            send_alert = True
        elif email_config["frequency"] == "immediate":
            # For immediate, don't send the same alert more than once every 30 minutes
            if current_time - last_sent > timedelta(minutes=30):
                send_alert = True
        elif email_config["frequency"] == "hourly digest":
            # For hourly, only include if not sent in the last hour
            if current_time - last_sent > timedelta(hours=1):
                send_alert = True
        elif email_config["frequency"] == "daily digest":
            # For daily, only include if not sent today
            if current_time.date() != last_sent.date():
                send_alert = True
        
        if send_alert:
            deduped_alerts.append(alert)
            # Update the last sent time for this alert
            email_config["last_sent"][alert_key] = current_time
    
    if not deduped_alerts:
        return
    
    # Build HTML email content
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 20px; border-radius: 10px; }
            .header { text-align: center; padding-bottom: 20px; border-bottom: 1px solid #eee; }
            .logo { font-size: 24px; font-weight: bold; color: #2c3e50; }
            .alert { margin: 20px 0; padding: 15px; border-radius: 5px; background-color: #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .city { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #2c3e50; }
            .type { display: inline-block; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; margin-bottom: 10px; }
            .high-temp { background-color: #ff7675; color: white; }
            .low-temp { background-color: #74b9ff; color: white; }
            .high-wind { background-color: #fdcb6e; color: #2c3e50; }
            .high-precip { background-color: #81ecec; color: #2c3e50; }
            .severe { background-color: #e17055; color: white; }
            .high-uv { background-color: #fab1a0; color: #2c3e50; }
            .value { font-size: 16px; margin-bottom: 5px; }
            .timestamp { font-size: 12px; color: #7f8c8d; text-align: right; }
            .footer { margin-top: 30px; text-align: center; font-size: 12px; color: #7f8c8d; border-top: 1px solid #eee; padding-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">⛅ Weather Stream Alert</div>
                <p>The following weather alerts have been detected:</p>
            </div>
    """
    
    # Group alerts by city for better readability
    cities = {}
    for alert in deduped_alerts:
        city = alert["city"]
        if city not in cities:
            cities[city] = []
        cities[city].append(alert)
    
    # Add each city's alerts
    for city, city_alerts in cities.items():
        html += f'<h2>{city}</h2>'
        
        for alert in city_alerts:
            # Get CSS class for alert type
            alert_class = alert["alert_type"].lower().replace(" ", "-")
            
            html += f"""
            <div class="alert">
                <div class="city">{city}</div>
                <div class="type {alert_class}">{alert["alert_type"]}</div>
                <div class="value">Current value: <strong>{alert["value"]}</strong> (Threshold: {alert["threshold"]})</div>
                <div class="timestamp">Detected at: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
            </div>
            """
    
    html += """
            <div class="footer">
                <p>This is an automated alert from Weather Stream Dashboard. You received this because you subscribed to weather alerts.</p>
                <p>To modify your alert settings, please visit the dashboard.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Get email credentials from secrets
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
        # sender_email = os.getenv("EMAIL_SENDER")
        # sender_password = os.getenv("EMAIL_PASSWORD") 
    except Exception as e:
        st.error(f"Error accessing email credentials: {e}")
        return False
    
    # Send email
    try:
        # Create message - Fix the multiple To headers issue
        message = MIMEMultipart("alternative")
        
        if email_config["frequency"] == "immediate":
            subject = f"Weather Alert: {deduped_alerts[0]['alert_type']} in {deduped_alerts[0]['city']}"
            if len(deduped_alerts) > 1:
                subject += f" and {len(deduped_alerts) - 1} more"
        else:
            subject = f"Weather Alert Digest: {len(deduped_alerts)} alerts detected"
        
        message["Subject"] = subject
        message["From"] = "Weather Alert Mailer"
        
        # Attach HTML content
        message.attach(MIMEText(html, "html"))
        
        # Connect to server and send
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            
            # Send to each recipient INDIVIDUALLY to avoid multiple To headers
            for recipient in email_config["recipients"]:
                # Create a separate copy of the message for each recipient
                msg_copy = MIMEMultipart("alternative")
                msg_copy["Subject"] = message["Subject"]
                msg_copy["From"] = message["From"]
                msg_copy["To"] = recipient  # Set To header for this recipient only
                
                # Attach the same HTML content
                msg_copy.attach(MIMEText(html, "html"))
                
                # Send this copy to the individual recipient
                server.sendmail(sender_email, recipient, msg_copy.as_string())
        
        return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False


def send_predictive_alert_emails(alerts, email_config):
    """Send emails for predicted weather alerts """

    
    if not email_config["enabled"] or not alerts or not email_config["recipients"]:
        return
    
    # Filter alerts by city if specified
    if email_config["cities"]:
        filtered_alerts = [
            a for a in alerts 
            if any(city in a["city"] for city in email_config["cities"])
        ]
    else:
        filtered_alerts = alerts
    
    if not filtered_alerts:
        return
    
    # Filter by alert types and minimum confidence
    min_confidence = email_config.get("min_confidence", 0.7)
    
    # Extract base alert types by removing "Predicted " prefix for matching
    alert_types = [a_type.replace("Predicted ", "") for a_type in email_config["types"]]
    
    filtered_alerts = [
        a for a in filtered_alerts 
        if any(a_type in a["alert_type"] for a_type in alert_types)
        and a["confidence"] >= min_confidence
    ]
    
    if not filtered_alerts:
        return
    
    # Check for duplicates based on frequency settings
    current_time = datetime.now()
    deduped_alerts = []
    
    for alert in filtered_alerts:
        alert_key = f"{alert['city']}_{alert['alert_type']}_{pd.to_datetime(alert['predicted_time']).strftime('%Y-%m-%d_%H')}"
        
        # Check when this alert was last sent
        last_sent = email_config["last_sent"].get(alert_key)
        
        # Determine if we should send based on frequency
        send_alert = False
        
        if not last_sent:
            # Never sent before
            send_alert = True
        elif email_config["frequency"] == "immediate":
            # For immediate, don't send the same alert more than once every 30 minutes
            if current_time - last_sent > timedelta(minutes=30):
                send_alert = True
        elif email_config["frequency"] == "hourly digest":
            # For hourly, only include if not sent in the last hour
            if current_time - last_sent > timedelta(hours=1):
                send_alert = True
        elif email_config["frequency"] == "daily digest":
            # For daily, only include if not sent today
            if current_time.date() != last_sent.date():
                send_alert = True
        
        if send_alert:
            deduped_alerts.append(alert)
            # Update the last sent time for this alert
            email_config["last_sent"][alert_key] = current_time
    
    if not deduped_alerts:
        return
    
    # Build HTML email content
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 20px; border-radius: 10px; }
            .header { text-align: center; padding-bottom: 20px; border-bottom: 1px solid #eee; }
            .logo { font-size: 24px; font-weight: bold; color: #2c3e50; }
            .alert { margin: 20px 0; padding: 15px; border-radius: 5px; background-color: #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .city { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #2c3e50; }
            .type { display: inline-block; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; margin-bottom: 10px; }
            .predicted-high-temp { background-color: #ff7675; color: white; }
            .predicted-low-temp { background-color: #74b9ff; color: white; }
            .predicted-high-wind { background-color: #fdcb6e; color: #2c3e50; }
            .predicted-heavy-precipitation { background-color: #81ecec; color: #2c3e50; }
            .predicted-severe-weather { background-color: #e17055; color: white; }
            .predicted-high-uv { background-color: #fab1a0; color: #2c3e50; }
            .value { font-size: 16px; margin-bottom: 5px; }
            .confidence { font-size: 14px; margin-bottom: 5px; }
            .high { color: green; font-weight: bold; }
            .medium { color: orange; }
            .low { color: red; }
            .timestamp { font-size: 12px; color: #7f8c8d; text-align: right; }
            .footer { margin-top: 30px; text-align: center; font-size: 12px; color: #7f8c8d; border-top: 1px solid #eee; padding-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🔮 Weather Stream Prediction Alert</div>
                <p>The following weather conditions are predicted in the next few hours:</p>
            </div>
    """
    
    # Group alerts by city for better readability
    cities = {}
    for alert in deduped_alerts:
        city = alert["city"]
        if city not in cities:
            cities[city] = []
        cities[city].append(alert)
    
    # Add each city's alerts
    for city, city_alerts in cities.items():
        html += f'<h2>{city}</h2>'
        
        for alert in city_alerts:
            # Get CSS class for alert type
            alert_class = alert["alert_type"].lower().replace(" ", "-")
            
            # Format confidence
            confidence = float(alert["confidence"])
            confidence_pct = int(confidence * 100)
            
            # Determine confidence class
            confidence_class = "high" if confidence >= 0.85 else "medium" if confidence >= 0.7 else "low"
            
            # Format predicted time
            predicted_time = pd.to_datetime(alert["predicted_time"]).strftime("%Y-%m-%d %H:%M")
            
            html += f"""
            <div class="alert">
                <div class="city">{city}</div>
                <div class="type {alert_class}">{alert["alert_type"]}</div>
                <div class="value">Predicted value: <strong>{alert["value"]}</strong> (Threshold: {alert["threshold"]})</div>
                <div class="confidence">Prediction confidence: <span class="{confidence_class}">{confidence_pct}%</span></div>
                <div class="timestamp">Expected at: {predicted_time}</div>
            </div>
            """
    
    html += """
            <div class="footer">
                <p>This is an automated prediction alert from Weather Stream Dashboard. You received this because you subscribed to weather alerts.</p>
                <p>To modify your alert settings, please visit the dashboard.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Get email credentials from secrets
    try:
        # sender_email = os.getenv("EMAIL_SENDER")
        # sender_password = os.getenv("EMAIL_PASSWORD") 
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
    except Exception as e:
        st.error(f"Error accessing email credentials: {e}")
        return False
    
    # Send email
    try:
        if email_config["frequency"] == "immediate":
            subject = f"Weather Prediction Alert: {deduped_alerts[0]['alert_type']} expected in {deduped_alerts[0]['city']}"
            if len(deduped_alerts) > 1:
                subject += f" and {len(deduped_alerts) - 1} more"
        else:
            subject = f"Weather Prediction Digest: {len(deduped_alerts)} predicted conditions"
        
        # Connect to server and send
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            
            # Send to each recipient INDIVIDUALLY to avoid multiple To headers
            for recipient in email_config["recipients"]:
                # Create a separate message for each recipient
                message = MIMEMultipart("alternative")
                message["Subject"] = subject
                message["From"] = "Weather Alert Mailer"
                message["To"] = recipient  # Only one recipient per message
                
                # Attach HTML content
                message.attach(MIMEText(html, "html"))
                
                # Send to this individual recipient
                server.sendmail(sender_email, recipient, message.as_string())
        
        return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False
    
def setup_predictive_alert_controls():
    """Set up controls for predictive alerts with proper confidence threshold slider"""
    st.subheader("Predictive Alerts")
    
    # Add help icon and tooltip explanation
    help_text = """
    This slider controls how confident our prediction model needs to be 
    before showing you a weather alert. 
    
    A higher percentage means fewer alerts but more reliable ones.
    A lower percentage shows more alerts but with less certainty.
    """
    
    col1, col2 = st.columns([0.95, 0.05])
    with col1:
        st.markdown("Minimum confidence threshold for predictive alerts")
    with col2:
        st.markdown("ℹ️", help=help_text)
    
    # Fixed slider with proper percentage range (50% to 95%)
    min_confidence = st.slider(
        "",  # No label since we have the header above
        min_value=50,
        max_value=95,
        value=70,
        step=5,
        format="%d%%"  # Format as percentage
    )
    
    # Convert percentage to 0-1 scale for internal use
    return min_confidence / 100.0