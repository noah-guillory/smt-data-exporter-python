from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator


class BillingData(BaseModel):
    """
    Represents a single billing data entry for a month.
    """

    start_date: datetime = Field(..., alias="startDate")
    end_date: datetime = Field(..., alias="endDate")
    revision_date: datetime = Field(..., alias="revisionDate")
    actual_kwh: float = Field(..., alias="actualkWh")
    metered_kw: float = Field(..., alias="meteredKW")
    billed_kw: float = Field(..., alias="billedKW")
    metered_kva: float = Field(..., alias="meteredKVA")
    billed_kva: float = Field(..., alias="billedKVA")

    model_config = {"populate_by_name": True}

    @field_validator("start_date", "end_date", mode="before")
    def parse_dates(cls, value):
        """Parse date strings to datetime objects."""
        if isinstance(value, str):
            return datetime.strptime(value, "%m/%d/%Y")
        return value

    @field_validator("revision_date", mode="before")
    def parse_timestamps(cls, value):
        """Parse timestamp strings to datetime objects."""
        return (
            datetime.strptime(value, "%m/%d/%Y %H:%M:%S")
            if isinstance(value, str)
            else value
        )


class Data(BaseModel):
    """
    Container for billing data response.
    """

    trans_id: str = Field(..., alias="trans_id")
    esiid: str
    billing_data: List[BillingData] = Field(..., alias="billingData")

    model_config = {"populate_by_name": True}


class MonthlyBillingDataResponse(BaseModel):
    """
    Top-level response for monthly billing data.
    """

    data: Data

    model_config = {"populate_by_name": True}
