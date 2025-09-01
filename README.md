# SMT Data Exporter Python

## Overview
This script automates the download of monthly electricity usage data from Smart Meter Texas, calculates the trailing 12-month average kWh usage, and updates a YNAB (You Need A Budget) category target based on your usage and kWh rate.

## Features
- Automates browser login and report download from Smart Meter Texas
- Calculates trailing 12-month average electricity usage from downloaded CSV
- Updates your YNAB electric bill category target using the latest average and your kWh rate
- All credentials and rates are securely loaded from a TOML config file

## Usage
1. **Install dependencies**
   ```sh
   uv pip install -r requirements.txt
   ```
   Or use your preferred Python environment manager.

2. **Configure your credentials**
   - Copy `config.toml.example` to `config.toml` and fill in your Smart Meter Texas and YNAB credentials, budget/category IDs, and kWh rate.
   - **Never commit your `config.toml` to GitHub!**

3. **Run the script**
   ```sh
   uv run main.py
   ```
   The script will download the latest report, calculate your average, and update YNAB.

## Configuration
All sensitive info is stored in `config.toml`:
```toml
smt_username = "your_username"
smt_password = "your_password"
ynab_access_token = "your_ynab_access_token"
ynab_budget_id = "your_ynab_budget_id"
ynab_category_id = "your_ynab_category_id"
kwh_rate = 0.17754
```

## Security
- Your credentials and tokens are **never** hardcoded in the script.
- `config.toml` is listed in `.gitignore` by default.

## Requirements
- Python 3.10+
- `uv`, `pydantic-settings`, `pyppeteer`, `pandas`, `ynab` (see `requirements.txt`)

## License
MIT
