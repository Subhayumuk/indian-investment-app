"""
CAS (Consolidated Account Statement) Parser API Router

Best-effort text extraction from NSDL Consolidated Account Statement PDFs.
NSDL CAS layout varies across statement generators, so this uses permissive
line-based regexes and degrades to parse_status="partial"/"failed" rather
than raising, since extracted figures are a pre-fill starting point that the
user reviews on the frontend, not authoritative data.
"""
import io
import logging
import re
from typing import List

import pdfplumber
from fastapi import APIRouter, File, HTTPException, UploadFile
from pdfminer.pdfdocument import PDFEncryptionError

from app.models.cas import CASParseResponse, ParsedMutualFund, ParsedStock

logger = logging.getLogger(__name__)
router = APIRouter()

# Real NSDL CAS "Mutual Fund Folios" rows put the ISIN, the start of the
# scheme name, the folio number, and six numeric columns all on one line
# (the rest of the scheme name wraps onto separate lines below, which we
# don't attempt to stitch back together — the truncated name is enough to
# recognise and correct manually), e.g.:
#   "INF209K01397 Aditya Birla Sun 1030389775 783.516 11.3826 8,918.43 26.6400 20,872.87 11,954.44"
#   columns: ISIN, name-start, folio, units, avg cost/unit, total cost, NAV, current value, unrealised P/L, [annualised return %]
# All Indian AMFI mutual fund ISINs use the "INF" prefix.
MF_ROW_RE = re.compile(
    r"^(?P<isin>INF[A-Z0-9]{9})\s+"
    r"(?P<name>[A-Za-z][A-Za-z0-9&().,\-/ ]*?)\s+"
    r"(?P<folio>\d{4,15})\s+"
    r"(?P<units>[\d,]+\.\d{2,4})\s+"
    r"(?P<avg_cost>[\d,]+\.\d{2,4})\s+"
    r"(?P<total_cost>[\d,]+\.\d{2,4})\s+"
    r"(?P<nav>[\d,]+\.\d{2,4})\s+"
    r"(?P<value>[\d,]+\.\d{2,4})\s+"
    r"-?[\d,]+\.\d{2,4}"  # unrealised profit/(loss), not needed
    r"(?:\s+-?[\d,]+\.\d{2,4})?"  # optional trailing annualised return %
    r"\s*$"
)

# Real NSDL CAS "Equity Shares" rows follow the same ISIN-first pattern with
# four numeric columns, e.g.:
#   "INE391I01018 TELEDATA TECHNOLOGY 2.00 1,000 0.12 120.00"
#   columns: ISIN, company-name-start, face value, no. of shares, price, market value
STOCK_ROW_RE = re.compile(
    r"^(?P<isin>IN[A-Z0-9]{10})\s+"
    r"(?P<name>[A-Za-z][A-Za-z0-9&(). ]*?)\s+"
    r"(?P<face_value>[\d,]+\.\d{2})\s+"
    r"(?P<qty>[\d,]+)\s+"
    r"(?P<price>[\d,]+\.\d{2,4})\s+"
    r"(?P<value>[\d,]+\.\d{2,4})"
    r"\s*$"
)


def _to_float(raw: str) -> float:
    try:
        return float(raw.replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def _extract_mutual_funds(lines: List[str]) -> List[ParsedMutualFund]:
    funds: List[ParsedMutualFund] = []
    for line in lines:
        match = MF_ROW_RE.match(line.strip())
        if match:
            funds.append(ParsedMutualFund(
                fund_name=match.group("name").strip(),
                folio=match.group("folio"),
                units=_to_float(match.group("units")),
                nav=_to_float(match.group("nav")),
                current_value_inr=_to_float(match.group("value")),
            ))
    return funds


def _extract_stocks(lines: List[str]) -> List[ParsedStock]:
    stocks: List[ParsedStock] = []
    for line in lines:
        stripped = line.strip()
        if MF_ROW_RE.match(stripped):
            continue  # MF ISINs ("INF...") never represent equity holdings
        match = STOCK_ROW_RE.match(stripped)
        if match:
            stocks.append(ParsedStock(
                stock_name=match.group("name").strip(),
                isin=match.group("isin"),
                quantity=_to_float(match.group("qty")),
                price=_to_float(match.group("price")),
                current_value_inr=_to_float(match.group("value")),
            ))
    return stocks


@router.post("/parse-cas", response_model=CASParseResponse)
async def parse_cas(file: UploadFile = File(...)):
    """
    Best-effort parser for NSDL Consolidated Account Statement PDFs.
    Extracts mutual fund holdings (fund/folio/units/NAV/value) and demat
    stock holdings (stock/ISIN/qty/price/value) via line-based heuristics.
    Layout varies across statement generators — treat results as a
    pre-fill starting point, not authoritative data.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    raw_bytes = await file.read()

    try:
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            all_lines: List[str] = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_lines.extend(text.splitlines())
    except PDFEncryptionError:
        # pdfminer raises this (with an empty message) for encrypted PDFs
        # opened without a password — checking the exception type rather
        # than its (often blank) message is what actually catches this.
        # We don't attempt decryption — just fail gracefully, per spec.
        logger.warning(f"CAS parse failed for {file.filename}: password-protected")
        return CASParseResponse(
            parse_status="failed",
            parse_notes=(
                "This PDF is password-protected. Most NSDL CAS statements are "
                "encrypted with your PAN (uppercase) as the password by "
                "default — open it once in a PDF reader, remove the password "
                "protection (\"Save As\" / \"Print to PDF\" usually works), "
                "then re-upload. Or enter your holdings manually below."
            ),
        )
    except Exception as e:
        logger.warning(f"CAS parse failed for {file.filename}: {e}")
        return CASParseResponse(
            parse_status="failed",
            parse_notes=(
                "Could not read this PDF. It may be corrupted or in an "
                "unsupported format — please enter your holdings manually below."
            ),
        )

    mutual_funds = _extract_mutual_funds(all_lines)
    stocks = _extract_stocks(all_lines)

    if not mutual_funds and not stocks:
        status = "failed"
        notes = (
            "No mutual fund or stock holdings could be automatically detected "
            "in this statement. This parser uses best-effort text matching "
            "and may not support your CAS provider's exact layout — please "
            "add holdings manually."
        )
    else:
        notes = "Extracted figures are best-effort — please verify against your original statement before relying on them."
        status = "success" if (mutual_funds and stocks) else "partial"

    return CASParseResponse(
        parse_status=status,
        mutual_funds=mutual_funds,
        stocks=stocks,
        total_mf_value_inr=round(sum(f.current_value_inr for f in mutual_funds), 2),
        total_stock_value_inr=round(sum(s.current_value_inr for s in stocks), 2),
        parse_notes=notes,
    )
