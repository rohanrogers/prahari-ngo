# Kerala 2018 Replay Data

## Purpose
This directory contains replay scenario data based on the Kerala floods of August 2018 — the worst flooding in the state in a century. The data is used by Prahari's `/replay` mode to demonstrate how the system would have detected the crisis and pre-staged response.

## Sources
- **Weather data**: Based on IMD (India Meteorological Department) published reports for August 15, 2018
- **News articles**: Headlines from Mathrubhumi, The Hindu, and Manorama Online — archived from public web records
- **Reddit posts**: Synthetic posts modeled after real r/kerala activity during the 2018 floods
- **Government advisories**: Timeline from official Kerala SDMA post-flood reports

## Key Result
Prahari's multi-source correlation would have detected the Alappuzha flooding at **08:14 AM IST** — **33 minutes before** the first mainstream news article and **2 hours before** the first government advisory.

## Directory Structure
```
replay-data/
├── timeline.json            # Minute-by-minute event sequence
├── weather-snapshots/       # IMD-style weather data
├── news-articles/           # Archived news articles (JSON)
├── reddit-posts/            # Synthetic social media posts
├── twitter-archive/         # Public archive snippets
└── volunteer-corpus/        # Synthetic NGO volunteer data
    ├── whatsapp-alappuzha.txt
    ├── whatsapp-ernakulam.txt
    ├── ngo-signup-form.pdf
    ├── handwritten-register.jpg
    └── volunteer-master.xlsx
```

## Disclaimer
Some data in this replay archive is synthetically generated to match the style, format, and timeline of real events. It is clearly labeled as "replay scenario data" and is used solely for demonstration purposes in the GDG Solution Challenge 2026.
