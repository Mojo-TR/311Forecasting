# Data Dictionary

## Core Dimensions
| Field | Description |
|------|-------------|
| Neighborhood | Geographic area of service request |
| Department | City department responsible |
| Division | Sub-unit within department |
| Category | High-level service category |
| Case Type | Specific service request type |

## Date Fields
| Field | Description |
|------|-------------|
| Created Date | Date the request was submitted |
| Closed Date | Date the request was closed |

## Derived Metrics
| Field | Description |
|------|-------------|
| Resolution Time (Days) | Days between created and closed date |
| Monthly Volume | Count of service requests per month |
| Severity | Aggregated resolution-time–based metric |

## Forecast Fields
| Field | Description |
|------|-------------|
| y | Historical observed value |
| yhat | Forecasted value |
| yhat_lower | Lower confidence bound |
| yhat_upper | Upper confidence bound |