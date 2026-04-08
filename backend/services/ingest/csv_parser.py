from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


MAX_CSV_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".tsv"}
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "text/tab-separated-values",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",
    "",
}
FORMULA_PREFIXES = ("=", "+", "-", "@")
ASSET_CLASS_ALIASES = {
    "equity": "public_equity",
    "public equity": "public_equity",
    "public_equity": "public_equity",
    "stock": "public_equity",
    "fixed income": "fixed_income",
    "fixed_income": "fixed_income",
    "bond": "fixed_income",
    "private equity": "private_equity",
    "private_equity": "private_equity",
    "real assets": "real_assets",
    "real_assets": "real_assets",
    "real estate": "real_estate",
    "real_estate": "real_estate",
    "commodity": "commodity",
    "cash": "cash",
    "alternative": "alternative",
}


@dataclass
class ParsedCsvRow:
    ticker: str
    quantity: float
    asset_class: str
    custodian: Optional[str]
    geo_region: Optional[str]
    sector: Optional[str]
    market_segment: Optional[str]
    notes: Optional[str]
    name: Optional[str]
    position_currency: str
    price_local: Optional[float]
    price_usd: Optional[float]
    market_value_local: Optional[float]
    market_value_usd: float


def _safe_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if stripped.startswith(FORMULA_PREFIXES):
        return "'" + stripped
    return stripped


def _float_value(value: Optional[str]) -> Optional[float]:
    cleaned = _safe_string(value)
    if cleaned is None:
        return None
    normalized = cleaned.replace(",", "")
    return float(normalized)


def _normalize_asset_class(value: Optional[str]) -> Tuple[str, Optional[str]]:
    cleaned = _safe_string(value)
    if cleaned is None:
        return "public_equity", "asset_class not provided, defaulted to public_equity"
    normalized = ASSET_CLASS_ALIASES.get(cleaned.lower())
    if normalized is None:
        return "alternative", f"asset_class '{cleaned}' not recognized, defaulted to alternative"
    return normalized, None


def validate_csv_upload(filename: Optional[str], content_type: Optional[str], payload: bytes) -> str:
    display_name = Path(filename or "upload.csv").name
    extension = Path(display_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only .csv and .tsv files are accepted")
    if (content_type or "").lower() not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Unsupported CSV content type")
    if len(payload) > MAX_CSV_BYTES:
        raise ValueError("CSV upload exceeds the 25MB demo limit")
    if b"\x00" in payload:
        raise ValueError("CSV upload appears to contain binary content")
    return display_name


def parse_csv_upload(
    filename: Optional[str], content_type: Optional[str], payload: bytes
) -> Tuple[str, list[ParsedCsvRow], list[str]]:
    display_name = validate_csv_upload(filename, content_type, payload)
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV upload must be valid UTF-8 text") from exc

    sample = text[:4096]
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        if "\t" in sample and sample.count("\t") >= sample.count(","):
            delimiter = "\t"
        elif ";" in sample and sample.count(";") > sample.count(","):
            delimiter = ";"

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("CSV upload must include a header row")

    rows: list[ParsedCsvRow] = []
    warnings: list[str] = []
    for index, raw_row in enumerate(reader, start=2):
        ticker = _safe_string(raw_row.get("ticker"))
        quantity = _float_value(raw_row.get("quantity"))
        if not ticker or quantity is None:
            raise ValueError(f"Row {index} is missing required ticker or quantity")

        asset_class, warning = _normalize_asset_class(raw_row.get("asset_class"))
        if warning:
            warnings.append(f"{ticker}: {warning}")

        price_local = _float_value(raw_row.get("price_local"))
        price_usd = _float_value(raw_row.get("price_usd"))
        market_value_local = _float_value(raw_row.get("market_value_local"))
        market_value_usd = _float_value(raw_row.get("market_value_usd"))

        if market_value_usd is None:
            if price_usd is not None:
                market_value_usd = round(quantity * price_usd, 2)
            elif price_local is not None:
                market_value_usd = round(quantity * price_local, 2)
                warnings.append(f"{ticker}: market_value_usd inferred from price_local without FX conversion")
            else:
                market_value_usd = round(quantity, 2)
                warnings.append(f"{ticker}: market_value_usd missing, used quantity as placeholder")

        rows.append(
            ParsedCsvRow(
                ticker=ticker,
                quantity=quantity,
                asset_class=asset_class,
                custodian=_safe_string(raw_row.get("custodian")),
                geo_region=_safe_string(raw_row.get("geo_region")),
                sector=_safe_string(raw_row.get("sector")),
                market_segment=_safe_string(raw_row.get("market_segment")),
                notes=_safe_string(raw_row.get("notes")),
                name=_safe_string(raw_row.get("name")),
                position_currency=_safe_string(raw_row.get("position_currency")) or "USD",
                price_local=price_local,
                price_usd=price_usd,
                market_value_local=market_value_local,
                market_value_usd=market_value_usd,
            )
        )

    if not rows:
        raise ValueError("CSV upload did not contain any position rows")
    return display_name, rows, warnings
