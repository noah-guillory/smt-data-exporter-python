# SMT Data Exporter Python

## Overview
This script automates the download of monthly electricity usage data from Smart Meter Texas, calculates the trailing 12-month average kWh usage, and updates a YNAB (You Need A Budget) category target based on your usage and kWh rate.

## Features
- Automates browser login and report download from Smart Meter Texas
- Calculates trailing 12-month average electricity usage from downloaded CSV
- Updates your YNAB electric bill category target using the latest average and your kWh rate
- All credentials and rates are securely loaded from environment variables (see .env support below)

## Usage

### Local Usage
1. **Install dependencies**
   ```sh
   uv pip install -r requirements.txt
   ```
   Or use your preferred Python environment manager.

2. **Configure your credentials**
   - Create a `.env` file in the project root with the following variables:
     ```env
     SMT_USERNAME=your_username
     SMT_PASSWORD=your_password
     YNAB_ACCESS_TOKEN=your_ynab_access_token
     YNAB_BUDGET_ID=your_ynab_budget_id
     YNAB_CATEGORY_ID=your_ynab_category_id
     KWH_RATE=0.17754
     ```
   - **Never commit your `.env` to GitHub!**

3. **Run the script**
   ```sh
   uv run main.py
   ```
   The script will download the latest report, calculate your average, and update YNAB.

### Docker Usage
1. **Build the Docker image**
   ```sh
   docker compose build
   ```

2. **Configure environment variables**
   - You can use a `.env` file (recommended) or set variables directly in `docker-compose.yml` under `environment:`.
   - Example `.env` file:
     ```env
     CRON_SCHEDULE=0 2 * * *
     SMT_SMT_USERNAME=your_username
     SMT_SMT_PASSWORD=your_password
     SMT_YNAB_ACCESS_TOKEN=your_ynab_access_token
     SMT_YNAB_BUDGET_ID=your_ynab_budget_id
     SMT_YNAB_CATEGORY_ID=your_ynab_category_id
     SMT_KWH_RATE=0.17754
     ```

3. **Start the service**
   ```sh
   docker compose up -d
   ```
   The script will run once at startup and then on the schedule you set via `CRON_SCHEDULE`.

## Configuration
All sensitive info is now stored in environment variables, which can be set in a `.env` file or in your deployment environment. See above for variable names and examples.

## Security
- Your credentials and tokens are **never** hardcoded in the script.
- `.env` is listed in `.gitignore` by default.

## Requirements
- Python 3.10+
- `uv`, `pydantic-settings`, `pyppeteer`, `pandas`, `ynab` (see `requirements.txt`)

## License
MIT
