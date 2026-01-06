# Database Schema (PostgreSQL)

## Table: houston_311
**Purpose:**  
Stores normalized Houston 311 service request records. Each row represents a single service request and serves as the primary fact table for analytics and forecasting.

**Grain:**  
One row per 311 service request.

**Primary Identifier:**  
- `CASE NUMBER`

---

### Core Fields

| Column | Type | Description |
|------|-----|-------------|
| CASE NUMBER | text | Unique identifier for the service request |
| CREATED DATE | timestamp | Date the request was submitted |
| CLOSED DATE | timestamp | Date the request was closed (nullable) |
| RESOLUTION_TIME_DAYS | bigint | Days between created and closed dates |

---

### Classification Dimensions

| Column | Type | Description |
|------|-----|-------------|
| NEIGHBORHOOD | text | Geographic area associated with the request |
| DEPARTMENT | text | City department responsible |
| DIVISION | text | Sub-unit within department |
| CATEGORY | text | High-level service category |
| CASE TYPE | text | Specific service request type |

---

### Geographic Fields

| Column | Type | Description |
|------|-----|-------------|
| LATITUDE | double precision | Latitude coordinate |
| LONGITUDE | double precision | Longitude coordinate |

---

### Notes
- `RESOLUTION_TIME_DAYS` is derived during ingestion
- Some fields may be null depending on request status
- Table is optimized for analytics and downstream aggregation