import asyncio
from typing import List
from pyppeteer import launch
from pathlib import Path
from datetime import datetime, timedelta
import ynab
import pandas as pd
from settings import SMTConfig


__author__ = "Noah Guillory"
__version__ = "0.1.0"

DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Load config
config = SMTConfig()  # type: ignore
ynab_configuration = ynab.Configuration(access_token=config.ynab_access_token)
current_kwh_rate = config.kwh_rate


async def download_monthly_usage_report():
    """
    Automate downloading the monthly usage report from Smart Meter Texas.
    """
    browser = await launch(headless=False)
    page = await browser.newPage()
    await page._client.send(
        "Page.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": str(DOWNLOAD_DIR)},
    )
    await page.goto("https://smartmetertexas.com/")
    await page.setViewport({"width": 1080, "height": 1024})
    await page.type("#userid", config.smt_username)
    await page.type("#password", config.smt_password)
    await page.click("#loginform > div:nth-child(8) > button")
    title_element = await page.waitForSelector(
        "#wrapper > div.row.page-content-wrapper > main > div > div:nth-child(3) > div"
    )
    full_title = await page.evaluate("(element) => element.textContent", title_element)
    print(f"Logged in. Page title: {full_title}")
    await page.select("select#reporttype_input", "MONTHLY")
    await page.click(
        "#wrapper > div.row.page-content-wrapper > main > div > div:nth-child(6) > div.col-lg-4.col-xs-12 > div > div.row.panel > div:nth-child(1) > span > button"
    )
    await page.waitFor(1000)
    await browser.close()


def calculate_trailing_12_month_average(file_path: Path) -> float:
    """
    Calculate the trailing 12-month average kWh usage from a CSV file.
    Returns the average for the latest month in the dataset.
    """
    df = pd.read_csv(file_path)
    df["Start date"] = pd.to_datetime(df["Start date"], format="%m/%d/%Y")
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
    return pd.to_numeric(latest_avg, errors="coerce")


def update_electric_bill_target(trailing_avg_kwh: float):
    """
    Update the YNAB electric bill target category based on trailing average kWh usage.
    """
    with ynab.ApiClient(ynab_configuration) as api_client:
        categories_api = ynab.CategoriesApi(api_client)
        budget_id = config.ynab_budget_id
        category_id = config.ynab_category_id
        target = trailing_avg_kwh * current_kwh_rate
        print(
            f"Setting target to ${target:.2f} based on {trailing_avg_kwh:.2f} kWh usage."
        )
        goal_target = int(target * 1000)  # YNAB uses milliunits
        data = ynab.PatchCategoryWrapper(
            category=ynab.SaveCategory(
                goal_target=goal_target,
                note=f"Updated on {datetime.now().strftime('%Y-%m-%d')} to ${target:.2f} based on {trailing_avg_kwh:.2f} kWh usage.",
            )
        )
        print(data)
        response = categories_api.update_category(
            budget_id=budget_id, category_id=category_id, data=data
        )
        print("Category update response:", response)


# average = calculate_trailing_12_month_average(download_path / "MonthlyData.csv")
# update_electric_bill_target(average)


async def main():
    """
    Main entry point for the script.
    """
    await download_monthly_usage_report()
    print("Download completed.")
    average = calculate_trailing_12_month_average(DOWNLOAD_DIR / "MonthlyData.csv")
    update_electric_bill_target(average)


if __name__ == "__main__":
    asyncio.run(main())
