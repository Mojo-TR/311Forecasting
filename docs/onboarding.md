# Onboarding & Operational Workflows

## Refresh Workflow (Routine)
Used to ingest new 311 data and rebuild analytics outputs.

Steps:
1. Ensure PostgreSQL is running and environment variables are set
2. Run `refresh_data.py`
3. Monitor logs for completion and warnings
4. Verify updated data appears in the dashboard

Expected results:
- New records inserted or updated in `houston_311`
- Precomputed Parquet files regenerated
- Forecasts rebuilt or flagged as unreliable if data is insufficient

---

## Update Workflow (Code Changes)
Use when modifying aggregation, forecasting, or configuration logic.

Guidelines:
- Changes to aggregation or preprocessing require a full refresh
- Forecast parameter changes require regenerating forecasts
- UI-only changes do not require data refresh

Recommended steps:
1. Test changes locally
2. Run refresh if data logic changed
3. Validate results in the dashboard
4. Commit and document changes

---

## QA Workflow (Sanity Checks)
Run after refreshes or major changes.

Data checks:
- Monthly volumes are continuous (no unexpected gaps)
- Resolution times are non-negative
- No large unexplained spikes or drops

Forecast checks:
- Forecasts exist only when sufficient data is available
- Reliability flags behave as expected
- Confidence intervals are reasonable

Operational checks:
- No unhandled exceptions in logs
- Database queries complete successfully