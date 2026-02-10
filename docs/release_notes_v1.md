# Release Notes - v1.0.0 (Production Ready)

## 🚀 Key Features
- **Executive AI Agent:** Automated generation of monthly and annual HR reports.
- **Semantic Cube Architecture:** Deterministic data retrieval with probabilistic AI insights.
- **Dynamic Visualization:** Integration with frontend for color-coded, theme-aware charts.

## 🛠️ Tech Stack Upgrades
- **Python 3.11** base image.
- **Google Cloud Run** optimization with Gunicorn + Uvicorn workers.
- **Vertex AI** integration for enhanced reasoning.

## 🐛 Fixes & Improvements
- Fixed pagination limits for large datasets.
- Improved error handling in `HR Agent`.
- Standardized API responses for `VisualDataPackage`.

## ⚠️ Known Limitations
- Listing queries strictly limited to 50 records per page (by design).
- "Why?" analysis requires sufficient historical data in BigQuery.
