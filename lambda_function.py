import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import List
from collections import defaultdict

import aiohttp
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
__version__ = "0.2.0"

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
    Uses pure Python instead of pandas.
    """
    billing_data = report.data.billing_data
    if not billing_data:
        return 0.0
    
    # Group data by month (YYYY-MM format)
    monthly_usage = defaultdict(float)
    for bd in billing_data:
        month_key = bd.start_date.strftime("%Y-%m")
        monthly_usage[month_key] += bd.actual_kwh
    
    # Sort months chronologically
    sorted_months = sorted(monthly_usage.items())
    
    if not sorted_months:
        return 0.0
    
    # Calculate trailing 12-month averages for each month
    trailing_averages = {}
    for i in range(len(sorted_months)):
        month, _ = sorted_months[i]
        # Get the last 12 months including current month
        start_idx = max(0, i - 11)
        window_data = sorted_months[start_idx:i + 1]
        
        if len(window_data) >= 12:
            avg_kwh = sum(kwh for _, kwh in window_data) / 12
            trailing_averages[month] = avg_kwh
    
    if not trailing_averages:
        # If we don't have 12 months of data yet, return 0
        return 0.0
    
    # Get the latest month's trailing average
    latest_month = sorted_months[-1][0]
    latest_avg = trailing_averages.get(latest_month, 0.0)
    
    return float(latest_avg)


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


async def process_data() -> dict:
    """
    Main processing logic for the Lambda function.
    """
    try:
        await ping_healthcheck_start()
        
        # In Lambda, we don't use file-based markers
        # EventBridge rules should be configured to run monthly
        report_data = await get_monthly_report()
        logger.info("Download completed.")
        
        average = calculate_trailing_12_month_average(report_data)
        logger.info(f"Calculated trailing 12-month average: {average:.2f} kWh")
        
        update_electric_bill_target(average)
        logger.info("YNAB electric bill target updated.")
        
        await ping_healthcheck()
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Successfully updated YNAB electric bill target",
                "trailing_avg_kwh": average,
                "target_amount": average * current_kwh_rate
            })
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await ping_healthcheck_failed()
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": f"Error: {str(e)}"
            })
        }


async def ping_healthcheck() -> None:
    """
    Ping the healthcheck URL if configured.
    """
    if config.healthcheck_url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    config.healthcheck_url, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        logger.info("Healthcheck ping successful.")
                    else:
                        logger.error(
                            f"Healthcheck ping failed with status code {resp.status}."
                        )
        except Exception as e:
            logger.error(f"Healthcheck ping failed: {e}")


async def ping_healthcheck_start():
    """
    Ping the healthcheck URL start endpoint if configured.
    """
    if config.healthcheck_url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{config.healthcheck_url}/start", timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        logger.info("Healthcheck start ping successful.")
                    else:
                        logger.error(
                            f"Healthcheck start ping failed with status code {resp.status}."
                        )
        except Exception as e:
            logger.error(f"Healthcheck start ping failed: {e}")


async def ping_healthcheck_failed():
    """
    Ping the healthcheck URL failure endpoint if configured.
    """
    if config.healthcheck_url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{config.healthcheck_url}/fail", timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        logger.info("Healthcheck failure ping successful.")
                    else:
                        logger.error(
                            f"Healthcheck failure ping failed with status code {resp.status}."
                        )
        except Exception as e:
            logger.error(f"Healthcheck failure ping failed: {e}")


def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    This function is triggered by an EventBridge scheduled rule.
    
    Args:
        event: EventBridge event data
        context: Lambda context object
    
    Returns:
        dict: Response with status code and body
    """
    logger.info(f"Lambda function invoked with event: {json.dumps(event)}")
    
    # Run the async processing function
    result = asyncio.run(process_data())
    
    return result
