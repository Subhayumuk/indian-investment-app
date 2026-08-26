import io

import pytest
from fastapi.testclient import TestClient

from app.api.cas_parser import (
    _extract_life_insurance,
    _extract_mutual_funds,
    _extract_stocks,
    _to_float,
)
from app.main import create_app

# Real NSDL CAS row shapes, per the comments in app/api/cas_parser.py.
MF_LINE = "INF209K01397 Aditya Birla Sun 1030389775 783.516 11.3826 8,918.43 26.6400 20,872.87 11,954.44"
STOCK_LINE = "INE391I01018 TELEDATA TECHNOLOGY 2.00 1,000 0.12 120.00"
INSURANCE_LINE = "Life Insurance 1 1 10,00,000.00"


def test_to_float_parses_comma_separated_numbers():
    assert _to_float("8,918.43") == 8918.43


def test_to_float_returns_zero_for_garbage():
    assert _to_float("not-a-number") == 0.0


def test_extract_mutual_funds_matches_real_cas_row_shape():
    funds = _extract_mutual_funds([MF_LINE, "some unrelated line of text"])
    assert len(funds) == 1
    fund = funds[0]
    assert fund.fund_name == "Aditya Birla Sun"
    assert fund.isin == "INF209K01397"
    assert fund.folio == "1030389775"
    assert fund.units == pytest.approx(783.516)
    assert fund.nav == pytest.approx(26.64)
    assert fund.current_value_inr == pytest.approx(20872.87)


def test_extract_stocks_matches_real_cas_row_shape():
    stocks = _extract_stocks([STOCK_LINE])
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.stock_name == "TELEDATA TECHNOLOGY"
    assert stock.isin == "INE391I01018"
    assert stock.quantity == pytest.approx(1000)
    assert stock.current_value_inr == pytest.approx(120.00)


def test_extract_stocks_ignores_mutual_fund_rows():
    stocks = _extract_stocks([MF_LINE])
    assert stocks == []


def test_extract_mutual_funds_ignores_non_matching_lines():
    funds = _extract_mutual_funds(["Statement Period: 01-Apr-2025 to 31-Mar-2026", ""])
    assert funds == []


def test_extract_life_insurance_matches_real_cas_summary_row():
    policies = _extract_life_insurance([INSURANCE_LINE, "some unrelated line of text"])
    assert len(policies) == 1
    policy = policies[0]
    assert policy.policy_type == "Life Insurance"
    assert policy.num_policies == 1
    assert policy.sum_assured_inr == pytest.approx(1000000.0)


def test_extract_life_insurance_ignores_non_matching_lines():
    # A similarly-shaped summary row for an unrelated asset class shouldn't match.
    policies = _extract_life_insurance(["Mutual Fund Folios 15 Folios 15 24,55,653.24"])
    assert policies == []


@pytest.fixture
def client():
    return TestClient(create_app())


def test_parse_cas_rejects_non_pdf_upload(client):
    response = client.post(
        "/api/parse-cas",
        files={"file": ("statement.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )
    assert response.status_code == 400


def test_parse_cas_handles_unreadable_pdf_gracefully(client):
    response = client.post(
        "/api/parse-cas",
        files={"file": ("statement.pdf", io.BytesIO(b"this is not a real pdf"), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["parse_status"] == "failed"
    assert data["mutual_funds"] == []
    assert data["stocks"] == []
    assert data["life_insurance"] == []
