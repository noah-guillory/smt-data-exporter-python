from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
from pathlib import Path


class SMTConfig(BaseSettings):
    smt_username: str
    smt_password: str
    ynab_access_token: str
    ynab_budget_id: str
    ynab_category_id: str
    healthcheck_url: str | None = Field(default=None)
    kwh_rate: float
    model_config = SettingsConfigDict(env_file=".env")
