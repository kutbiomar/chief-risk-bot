# Onboarding Test Uploads

Use these files to test the live onboarding and document-upload flows.

## Files

- `portfolio_onboarding_sample.csv`
  - sample portfolio CSV for Step 1 onboarding import
- `pe_nav_statement_q1_2026.pdf`
  - private-equity style quarterly NAV statement
- `pe_capital_call_apr_2026.pdf`
  - capital call notice
- `pe_distribution_notice_may_2026.pdf`
  - distribution notice

## Source Files

These PDFs are generated from the HTML source files in this same folder:

- `pe_nav_statement_q1_2026.html`
- `pe_capital_call_apr_2026.html`
- `pe_distribution_notice_may_2026.html`

If you need to regenerate the PDFs locally:

```bash
.venv/bin/python admin/demo/test_uploads/generate_test_pdfs.py
```

## Suggested Test Order

1. Upload `portfolio_onboarding_sample.csv`
2. Upload `pe_nav_statement_q1_2026.pdf` as `private_equity`
3. Upload `pe_capital_call_apr_2026.pdf` as `capital_calls` or `private_equity`
4. Upload `pe_distribution_notice_may_2026.pdf` as `distribution_notices` or `private_equity`
