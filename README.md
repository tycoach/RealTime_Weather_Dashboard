# Weather Stream Dashboard

![Weather Dashboard](https://img.icons8.com/fluency/96/000000/partly-cloudy-day.png)

A real-time weather monitoring and analytics dashboard built with Streamlit, providing comprehensive weather data visualization, forecasting, historical analysis, and predictive analytics.

## Table of Contents

- [Features](#-features)
  - [Current Weather Monitoring](#current-weather-monitoring)
  - [Analytics & Visualization](#analytics--visualization)
  - [Weather Mapping](#weather-mapping)
  - [Alert System](#alert-system)
  - [Forecasting](#forecasting)
  - [Historical Analysis](#historical-analysis)
  - [Predictive Analytics](#predictive-analytics)
- [Technology Stack](#️-technology-stack)
- [Installation & Setup](#-installation--setup)
  - [Prerequisites](#prerequisites)
  - [Installation Steps](#installation-steps)
- [Project Structure](#-project-structure)
- [Usage Guide](#-usage-guide)
  - [Filtering Data](#filtering-data)
  - [Dashboard Navigation](#dashboard-navigation)
  - [Setting Up Email Alerts](#setting-up-email-alerts)
- [Data Sources](#-data-sources)
- [Predictive Models](#-predictive-models)
- [Dashboard Metrics](#-dashboard-metrics)
  - [Weather Alert Thresholds](#weather-alert-thresholds)
- [Security Notes](#-security-notes)
- [Contributing](#-contributing)
- [License](#-license)
- [Development Roadmap](#-development-roadmap)
- [Support](#-support)


## 📊 Features

### Current Weather Monitoring
- Real-time weather conditions for multiple cities
- Temperature, humidity, pressure, wind speed, and UV index monitoring
- Visual comparison of weather metrics across regions

### Analytics & Visualization
- Interactive charts for temperature trends
- Regional weather comparisons
- Weather parameter correlations
- Customizable time periods (24 hours, weekly, monthly)

### Weather Mapping
- Interactive global weather map with temperature visualization
- Color-coded weather conditions

### Alert System
- Configurable alerts for extreme weather conditions
- Customizable thresholds for temperature, wind, precipitation, and UV index
- Email notification system for weather alerts

### Forecasting
- Multi-day weather forecast visualization
- Temperature range and precipitation predictions
- Detailed forecast tables by city

### Historical Analysis
- Long-term weather trend analysis
- Temperature patterns by hour and day
- Weather parameter correlation analysis
- Insight generation from historical data

### Predictive Analytics
- Machine learning-based temperature prediction
- Weather anomaly detection
- Feature importance visualization for prediction factors

## 🛠️ Technology Stack

- **Frontend**: Streamlit
- **Data Visualization**: Plotly, PyDeck
- **Database**: PostgreSQL (with SQLAlchemy and psycopg2)
- **Data Analysis**: Pandas, NumPy
- **Machine Learning**: Scikit-learn (RandomForest)
- **Email Alerts**: SMTP with MIMEText/MIMEMultipart

## 🚀 Installation & Setup

### Prerequisites
- Python 3.9 or higher
- PostgreSQL database

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/weather-stream-dashboard.git
   cd weather-stream-dashboard
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up secrets for database and email:
   - Create a `.streamlit` folder in the project root
   - Create a `secrets.toml` file inside with your credentials:
   ```toml
   [database]
   host = "your-database-host"
   port = 
   database = "weatherstream_db"
   user = "your-username"
   password = "your-password"

   [email]
   sender = "your-email@gmail.com"
   password = "your-app-password"
   ```

5. Run the application:
   ```bash
   streamlit run dashboard/main.py
   ```

## 🧩 Project Structure

```
WeatherStream/
├── dashboard/
│   ├── main.py                  # Main application entry point
│   ├── weather_dashboard.py     # Core dashboard components
│   ├── machine_learning.py      # ML and predictive analytics
│   └── email_alert.py           # Email alert system
├── .streamlit/
│   └── secrets.toml             # Configuration secrets (not in repo)
├── requirements.txt             # Project dependencies
└── README.md                    # This documentation
```

## 📝 Usage Guide

### Filtering Data
- Use the sidebar to select the time period (24 hours, week, month)
- Filter by country and cities
- Customize alert thresholds for different weather conditions

### Dashboard Navigation
1. **Current Weather**: View real-time conditions for selected cities
2. **Analytics**: Compare weather metrics across regions
3. **Weather Map**: Visualize global weather patterns
4. **Alerts**: Monitor active weather alerts
5. **Forecast**: Check multi-day weather predictions
6. **Historical Analysis**: Analyze long-term weather trends
7. **Predictive Analytics**: Explore ML-based predictions and anomalies

### Setting Up Email Alerts
1. Navigate to the Email Alert Configuration section
2. Toggle "Enable Email Alerts"
3. Enter recipient email addresses (comma-separated)
4. Select alert frequency and types
5. Use the "Test Email Alert" button to verify configuration

## 🔄 Data Sources

The dashboard connects to a PostgreSQL database with the following primary tables:
- `weather_analytics`: Historical and current weather data
- `weather_forecast`: Prediction data for upcoming days

Key weather parameters tracked:
- Temperature (avg, min, max)
- Humidity
- Atmospheric pressure
- Wind speed
- Precipitation
- UV index

## 🧪 Predictive Models

The dashboard includes machine learning capabilities:
- **Temperature Prediction**: RandomForest regression model
- **Anomaly Detection**: Statistical outlier detection
- **Feature Importance**: Analysis of factors influencing weather predictions

## 📈 Dashboard Metrics

### Weather Alert Thresholds
- High Temperature: 35°C
- Low Temperature: 0°C
- High Wind: 20 m/s
- Heavy Precipitation: 10 mm
- High UV Index: 8

These thresholds are customizable through the dashboard interface.

## 🔒 Security Notes

- Database credentials and email passwords are stored in Streamlit secrets
- For Gmail integration, use App Passwords instead of regular passwords
- Enable 2-Step Verification on your Gmail account before setting up email alerts

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 💡 Development Roadmap

Future enhancements planned:
- Integration with additional weather data sources
- Mobile-responsive design improvements
- Advanced ML models for more accurate forecasting
- User authentication system
- Custom dashboard layouts for different user roles
- API endpoints for external applications

## 📞 Support

For questions, feature requests, or support, please open an issue in the GitHub repository or contact [davidtaiwo56@gmail.com].
