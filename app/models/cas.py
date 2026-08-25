from pydantic import BaseModel
from typing import List


class ParsedMutualFund(BaseModel):
    fund_name: str
    folio: str = ""
    units: float = 0.0
    nav: float = 0.0
    current_value_inr: float = 0.0


class ParsedStock(BaseModel):
    stock_name: str
    isin: str = ""
    quantity: float = 0.0
    price: float = 0.0
    current_value_inr: float = 0.0


class CASParseResponse(BaseModel):
    mutual_funds: List[ParsedMutualFund] = []
    stocks: List[ParsedStock] = []
    total_mf_value_inr: float = 0.0
    total_stock_value_inr: float = 0.0
    parse_status: str  # "success" | "partial" | "failed"
    parse_notes: str = ""
