from __future__ import annotations


def classify_document(raw_text: str, filename: str = "") -> dict:
    text = f"{filename}\n{raw_text}".lower()
    if "capital call" in text:
        return {"document_type": "capital_call", "confidence": 92}
    if "limited partner statement" in text or "lp statement" in text:
        return {"document_type": "lp_statement", "confidence": 90}
    if "quarterly report" in text or "portfolio summary" in text:
        return {"document_type": "quarterly_report", "confidence": 88}
    if "due diligence" in text or "investment memorandum" in text:
        return {"document_type": "dd_document", "confidence": 85}
    return {"document_type": "other", "confidence": 55}
