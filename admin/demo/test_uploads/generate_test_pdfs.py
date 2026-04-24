from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf(lines: list[str]) -> bytes:
    content_lines = ["BT", "/F1 12 Tf", "72 760 Td", "16 TL"]
    for index, line in enumerate(lines):
        escaped = _escape_pdf_text(line)
        if index == 0:
            content_lines.append(f"({escaped}) Tj")
        else:
            content_lines.append("T*")
            content_lines.append(f"({escaped}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream",
    ]

    parts = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets: list[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(f"{index} 0 obj\n".encode("latin-1"))
        parts.append(obj)
        parts.append(b"\nendobj\n")

    xref_offset = sum(len(part) for part in parts)
    parts.append(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    parts.append(b"0000000000 65535 f \n")
    for offset in offsets:
        parts.append(f"{offset:010d} 00000 n \n".encode("latin-1"))
    parts.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
    )
    return b"".join(parts)


def main() -> None:
    documents = {
        "pe_nav_statement_q1_2026.pdf": [
            "Oak Hill Growth Partners IV",
            "Q1 2026 NAV Statement",
            "General Partner: Oak Hill Capital Advisors",
            "Statement period: Q1 2026",
            "Capital account balance and holdings summary for the limited partner.",
            "Ticker Security Name Quantity Market Value USD Asset Class Sector Region Market Segment",
            "ALPHA Alpha Data Centers LLC 1 1850000 Private Equity Infrastructure North America Mid Market",
            "BETA Beta Healthcare Platforms Inc 1 1325000 Private Equity Health Care North America Growth",
            "GAMMA Gamma Logistics Europe GmbH 1 975000 Private Equity Industrials Europe Mid Market",
            "Net Asset Value 4150000 USD",
        ],
        "pe_capital_call_apr_2026.pdf": [
            "Capital Call Notice",
            "Fund: Cedar Ridge Opportunities Fund III",
            "General Partner: Cedar Ridge Partners",
            "Date: 2026-04-17",
            "Please fund your drawdown amount of $275,000 by 2026-04-30.",
            "Wire instructions",
            "Bank: Northern Trust",
            "Account Number: 4455667788",
            "Routing / ABA: 071000152",
            "Reference: Cedar Ridge Fund III Capital Call April 2026",
        ],
        "pe_distribution_notice_may_2026.pdf": [
            "Distribution Notice",
            "Fund: West Harbor Co-Invest Program II",
            "General Partner: West Harbor Capital",
            "Date: 2026-05-12",
            "This distribution notice confirms a cash distribution of $148,000 payable on 2026-05-20.",
            "Please confirm settlement instructions with your operations team.",
        ],
    }

    for filename, lines in documents.items():
        output = ROOT / filename
        output.write_bytes(_build_pdf(lines))
        print(f"generated {output}")


if __name__ == "__main__":
    main()
