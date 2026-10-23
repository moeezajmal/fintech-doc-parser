import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Transaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: dt.date
    description: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(description="Negative = money out, positive = money in")
    balance: Decimal | None = Field(
        default=None, description="Running balance after this transaction, if shown"
    )
    source_page: int = Field(ge=1, description="1-based page number in the source PDF")

    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("amount", "balance", mode="before")
    @classmethod
    def parse_money(cls, v):
        if isinstance(v, str):
            s = v.strip().replace("$", "").replace(",", "")
            if s.startswith("(") and s.endswith(")"):
                s = "-" + s[1:-1]
            return s
        return v


class Statement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank_name: str
    account_last4: str = Field(pattern=r"^\d{4}$")
    period_start: dt.date
    period_end: dt.date
    opening_balance: Decimal
    closing_balance: Decimal
    transactions: list[Transaction]

    @model_validator(mode="after")
    def check_reconciliation(self):
        total = sum((t.amount for t in self.transactions), Decimal("0"))
        if self.opening_balance + total != self.closing_balance:
            raise ValueError("Statement does not reconcile")
        return self
