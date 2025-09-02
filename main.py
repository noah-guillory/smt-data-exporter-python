import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

import aiohttp
import pandas as pd
import ynab
from smart_meter_texas import Account, Client, ClientSSLContext, Meter
from settings import SMTConfig
from models import MonthlyBillingDataResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

__author__ = "Noah Guillory"
__version__ = "0.1.0"

# Constants
DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


# Load config from environment variables
config = SMTConfig()  # type: ignore
ynab_configuration = ynab.Configuration(access_token=config.ynab_access_token)
current_kwh_rate = config.kwh_rate


async def get_monthly_report() -> MonthlyBillingDataResponse:
    """
    Fetch monthly billing report from Smart Meter Texas API.
    """
    client_ssl_ctx = ClientSSLContext()
    ssl_context = await client_ssl_ctx.get_ssl_context()
    if not ssl_context:
        raise RuntimeError("Failed to create SSL context")

    async with aiohttp.ClientSession() as websession:
        account = Account(config.smt_username, config.smt_password)
        client = Client(websession, account, ssl_context)
        await client.authenticate()
        meters: List[Meter] = await account.fetch_meters(client)
        if not meters:
            raise RuntimeError("No meters found for account.")
        meter_id = meters[0].esiid
        # Calculate start and end dates: start is one year ago today, end is today
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        start_date_str = start_date.strftime("%m/%d/%Y")
        end_date_str = end_date.strftime("%m/%d/%Y")
        response = await client.request(
            "/adhoc/monthlysynch",
            json={
                "startDate": start_date_str,
                "endDate": end_date_str,
                "reportFormat": "JSON",
                "ESIID": [meter_id],
                "versionDate": None,
                "versionNum": None,
                "versionBillingMonth": None,
            },
        )
        return MonthlyBillingDataResponse.model_validate(response)


def calculate_trailing_12_month_average(report: MonthlyBillingDataResponse) -> float:
    """
    Calculate the trailing 12-month average kWh usage from the API response object.
    Returns the average for the latest month in the dataset.
    """
    billing_data = report.data.billing_data
    if not billing_data:
        return 0.0
    df = pd.DataFrame(
        [
            {"Start date": bd.start_date, "Actual kWh": bd.actual_kwh}
            for bd in billing_data
        ]
    )
    df["Start date"] = pd.to_datetime(df["Start date"])
    monthly_usage = (
        df.groupby(df["Start date"].dt.to_period("M"))["Actual kWh"].sum().reset_index()
    )
    monthly_usage.columns = ["Month", "Total kWh"]
    monthly_usage.set_index("Month", inplace=True)
    monthly_usage["Trailing 12-Month Avg kWh"] = (
        monthly_usage["Total kWh"].rolling(window=12).mean()
    )
    latest_month = monthly_usage.index.max()
    latest_avg = monthly_usage.loc[latest_month, "Trailing 12-Month Avg kWh"]
    if pd.isna(latest_avg):
        return 0.0
    # Ensure conversion to float using pandas utility
    return float(pd.to_numeric(latest_avg, errors="coerce"))


def update_electric_bill_target(trailing_avg_kwh: float) -> None:
    """
    Update the YNAB electric bill target category based on trailing average kWh usage.
    """
    target = trailing_avg_kwh * current_kwh_rate
    goal_target = int(target * 1000)  # YNAB uses milliunits
    note = (
        f"Updated on {datetime.now().strftime('%Y-%m-%d')} to ${target:.2f} "
        f"based on {trailing_avg_kwh:.2f} kWh usage."
    )
    try:
        with ynab.ApiClient(ynab_configuration) as api_client:
            categories_api = ynab.CategoriesApi(api_client)
            budget_id = config.ynab_budget_id
            category_id = config.ynab_category_id
            data = ynab.PatchCategoryWrapper(
                category=ynab.SaveCategory(
                    goal_target=goal_target,
                    note=note,
                )
            )
            logger.info(
                f"Setting target to ${target:.2f} based on {trailing_avg_kwh:.2f} kWh usage."
            )
            response = categories_api.update_category(
                budget_id=budget_id, category_id=category_id, data=data
            )
            logger.info(f"Category update response: {response}")
    except Exception as e:
        logger.error(f"Failed to update YNAB category: {e}")


async def main() -> None:
    """
    Main entry point for the script.
    """
    try:
        report_data = await get_monthly_report()
        logger.info("Download completed.")
        average = calculate_trailing_12_month_average(report_data)
        update_electric_bill_target(average)
        logger.info("YNAB electric bill target updated.")
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
