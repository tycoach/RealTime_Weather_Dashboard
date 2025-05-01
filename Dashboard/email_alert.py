# Add these imports if not already included
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import streamlit as st
import  pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
# Load environment variables
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  


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
    """Configure email alert settings with improved validation"""
    st.subheader("Email Alert Configuration")
    
    enable_email = st.toggle("Enable Email Alerts", value=False)
    
    if enable_email:
        email_recipients = st.text_input(
            "Email Recipients (comma-separated)",
            placeholder="example@gmail.com, another@example.com"
        )
        
        alert_frequency = st.selectbox(
            "Alert Frequency",
            ["Immediate", "Hourly Digest", "Daily Digest"]
        )
        
        alert_types = st.multiselect(
            "Alert Types",
            ["High Temperature", "Low Temperature", "High Wind", "Heavy Precipitation", "High UV Index"],
            default=["High Temperature", "High Wind", "Heavy Precipitation"]
        )
        
        # Parse and validate emails immediately to provide feedback
        parsed_emails = []
        if email_recipients:
            parsed_emails = parse_email_list(email_recipients)
            
            if parsed_emails:
                st.success(f"Valid email(s): {', '.join(parsed_emails)}")
            else:
                st.error("No valid email addresses found. Please enter valid emails separated by commas.")
        
        if st.button("Test Email Alert"):
            if parsed_emails:
                success = test_email_alert(parsed_emails)
                if success:
                    st.success("Test email sent! Please check your inbox.")
            else:
                st.error("Please enter at least one valid email recipient.")
        
        return {
            "enabled": enable_email,
            "recipients": parsed_emails,
            "frequency": alert_frequency,
            "types": alert_types
        }
    
    return {"enabled": False}
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

def test_email_alert(recipients):
    """Send a test email alert with better validation"""
    if not recipients:
        st.error("No recipients provided")
        return False
    
    if isinstance(recipients, str):
        # If a single string was passed, make it a list
        recipients = [recipients]
    
    # Filter out any invalid or single character emails
    valid_recipients = []
    for email in recipients:
        email_str = str(email).strip()
        if len(email_str) > 1 and '@' in email_str and '.' in email_str:
            valid_recipients.append(email_str)
        else:
            st.warning(f"Skipping invalid email: '{email_str}'")
    
    if not valid_recipients:
        st.error("No valid email recipients found")
        return False
    
    # Send test email to each valid recipient
    all_success = True
    for email in valid_recipients:
        success = send_email(
            email,
            "Weather Dashboard - Test Alert",
            "<p>This is a test alert from your Weather Dashboard. If you received this email, alerts are configured correctly.</p>"
        )
        if not success:
            all_success = False
    
    return all_success

def send_email(recipient, subject, body):
   
    # Replace these with your actual email and app password
    sender_email = EMAIL_SENDER
    
    # Use an app password instead of your regular password
    sender_password = EMAIL_PASSWORD
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
        message["From"] = sender_email
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

def send_alert_emails(alerts, alert_config):
    """Send emails for new weather alerts"""
    if not alert_config["enabled"] or not alerts or not alert_config["recipients"]:
        return
    
    # Validate recipient emails
    valid_recipients, _ = validate_emails(alert_config["recipients"])
    
    if not valid_recipients:
        st.error("No valid email recipients configured for alerts.")
        return
    
    # Filter alerts by selected types
    filtered_alerts = [a for a in alerts if a["alert_type"] in alert_config["types"]]
    
    if not filtered_alerts:
        return
    
    # Build HTML email content
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            .alert { margin-bottom: 15px; padding: 10px; border-left: 4px solid red; background-color: #ffe6e6; }
            .alert h3 { margin-top: 0; }
        </style>
    </head>
    <body>
        <h2>Weather Alert Notification</h2>
        <p>The following weather alerts have been triggered:</p>
    """
    
    for alert in filtered_alerts:
        html += f"""
        <div class="alert">
            <h3>{alert['city']} - {alert['alert_type']}</h3>
            <p>Current value: <strong>{alert['value']}</strong> (Threshold: {alert['threshold']})</p>
            <p>Detected at: {pd.to_datetime(alert['time']).strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        """
    
    html += """
        <p>This is an automated alert from your Weather Dashboard.</p>
    </body>
    </html>
    """
    
    # Send to each valid recipient
    for recipient in valid_recipients:
        send_email(
            recipient,
            f"Weather Alert: {len(filtered_alerts)} condition(s) detected",
            html
        )