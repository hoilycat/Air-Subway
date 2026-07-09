# Air-Subway

> Real-time subway survival dashboard based on congestion data, arrival information, and air quality.

Air-Subway is a Streamlit app that helps users check whether a subway ride is likely to feel comfortable, crowded, or worth delaying. It combines Seoul subway congestion statistics, real-time arrival data, and district-level air quality data into a quick "boarding recommendation" UI.

## Current Implementation

Implemented in this repository:

- Streamlit dashboard UI
- Seoul subway congestion lookup from `data/congestion_data.csv`
- Current time-slot matching in 30-minute intervals
- Real-time subway arrival lookup through the Seoul open API
- District-level fine dust lookup through the Seoul open API
- Station-to-district mapping for air quality queries
- Simple discomfort-index calculation
- Green/yellow/red style ride recommendation
- Time-of-day congestion chart and best upcoming time suggestion

This repository does not currently include a machine-learning prediction model, SQL pipeline, or CO2 sensor data ingestion. The congestion result is calculated from historical CSV statistics matched to the current day/time.

## Project Structure

```text
Air-Subway/
├── app.py                  # Streamlit UI
├── logic.py                # Data loading, API calls, and scoring logic
├── data/
│   └── congestion_data.csv # Subway congestion statistics
├── backup/
│   └── app_backup.py       # Earlier integrated prototype
└── requirements.txt
```

## Data And APIs

- `data/congestion_data.csv`: historical subway congestion statistics
- Seoul subway real-time arrival API
- Seoul real-time city air API

API keys are read from Streamlit secrets:

```toml
[seoul]
subway_key = "..."
general_key = "..."
```

## Getting Started

```bash
pip install -r requirements.txt
streamlit run app.py
```

