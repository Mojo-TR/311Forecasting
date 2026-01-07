import os
import io
import pandas as pd
import requests
import time
from collections import defaultdict
from sqlalchemy import create_engine, text, Table, MetaData, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime
from dotenv import load_dotenv
from app.utils.utils import category_mapping

# CONFIG
load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in your environment or .env file")

YEAR_CURRENT = datetime.now().year
YEAR_PREVIOUS = YEAR_CURRENT - 1

URL_CURRENT = f"https://hfdapp.houstontx.gov/311/311-CRIS-Public-Data-Extract-D365-YTD-compressed-{YEAR_CURRENT}.txt"
URL_PREVIOUS = f"https://hfdapp.houstontx.gov/311/311-CRIS-Public-Data-Extract-D365-YTD-compressed-{YEAR_PREVIOUS}.txt"

TABLE_CURRENT = "houston_311"
TABLE_PREVIOUS = "houston_311"

RENAME_MAP = {
    "Case Number": "CASE NUMBER",
    "Customer SuperNeighborhood": "NEIGHBORHOOD",
    "Department": "DEPARTMENT",
    "Division": "DIVISION",
    "Incident Case Type": "CASE TYPE",
    "Created Date Local": "CREATED DATE",
    "Closed Date": "CLOSED DATE",
    "Latitude": "LATITUDE",
    "Longitude": "LONGITUDE",
}

KEEP_COLS = list(RENAME_MAP.values()) + ["CATEGORY", "RESOLUTION_TIME_DAYS"]

# HELPERS
def download_file(url: str, max_retries=5) -> pd.DataFrame:
    print(f"Downloading: {url}")
    tmp_path = "tmp_311.txt"
    skip_lines = 5

    for attempt in range(1, max_retries + 1):
        try:
            # Stream download (with retry)
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()

                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=10_000_000):  # 10 MB
                        if chunk:
                            f.write(chunk)

            # If we reach here, download succeeded → break out of retry loop
            break

        except Exception as e:
            print(f"⚠ Download attempt {attempt} failed: {e}")

            # Last attempt → give up
            if attempt == max_retries:
                raise RuntimeError(
                    f"Failed to download file after {max_retries} attempts\nURL: {url}"
                )

            time.sleep(3)  # wait before retrying
            continue

    # Parse pipe-delimited data safely
    df = pd.read_csv(
        tmp_path,
        sep="|",
        dtype=str,
        engine="python",
        on_bad_lines="skip",
        skiprows=skip_lines,
        encoding="latin-1"
    )

    os.remove(tmp_path)
    return df


def clean_and_prepare(df: pd.DataFrame) -> pd.DataFrame:
    # Rename columns
    df = df.rename(columns=RENAME_MAP)
    df = df[list(RENAME_MAP.values())]

    # Neighborhood standardization
    df["NEIGHBORHOOD"] = df["NEIGHBORHOOD"].replace({
        'HARRISBURG / MANCHESTER / SMITH ADDITION': 'HARRISBURG / MANCHESTER',
        'BRIARFOREST AREA': 'BRIAR FOREST',
        'BRAESWOOD PLACE': 'BRAESWOOD',
        'NORTHSIDE VILLAGE': 'NEAR NORTHSIDE',
        'OST / SOUTH UNION': 'GREATER OST / SOUTH UNION',
        'WASHINGTON AVENUE COALITION / MEMORIAL P': 'WASHINGTON AVENUE COALITION / MEMORIAL PARK',
        'WILLOW MEADOWS / WILLOWBEND AREA': 'NEAR SOUTHWEST'
    })

    # Category mapping
    df["CATEGORY"] = df["CASE TYPE"].map(category_mapping).fillna("Unknown")

    # Convert dates
    for col in ["CREATED DATE", "CLOSED DATE"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convert NaT → None for PostgreSQL
    for col in ["CREATED DATE", "CLOSED DATE"]:
        df[col] = df[col].where(pd.notna(df[col]), None)

    # Compute resolution time
    df["RESOLUTION_TIME_DAYS"] = (
        (df["CLOSED DATE"] - df["CREATED DATE"]).dt.total_seconds() / 86400
    )
    df["RESOLUTION_TIME_DAYS"] = df["RESOLUTION_TIME_DAYS"].round().astype("Int64")

    # Drop duplicates by case number
    df = df.drop_duplicates(subset=["CASE NUMBER"])

    # Remove cases outside Houston boundaries
    # Convert to float safely
    df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
    df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")

    df = df[
        df["LATITUDE"].between(29.5, 30.1, inclusive="both") &
        df["LONGITUDE"].between(-95.9, -94.9, inclusive="both")
    ]

    # Remove cases that have case number but no other info
    fields_to_check = [
        "NEIGHBORHOOD", "DEPARTMENT", "DIVISION",
        "CASE TYPE", "CREATED DATE", "LATITUDE", "LONGITUDE"
    ]

    df = df.dropna(subset=fields_to_check, how="all")

    # Strip whitespace
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

    return df

def table_exists(engine, table_name):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = :table
            );
        """), {"table": table_name})
        return result.scalar()

def create_table_if_missing(df, table_name, engine):
    if not table_exists(engine, table_name):
        print(f"Creating table: {table_name}")
        df.head(0).to_sql(table_name, engine, if_exists="replace", index=False)
    else:
        print(f"Table exists: {table_name}")

def delete_old_rows(table_name, engine):
    delete_sql = text(f"""
        DELETE FROM {table_name}
        WHERE "CREATED DATE" < DATE_TRUNC('month', NOW() - INTERVAL '9 years')
    """)

    with engine.begin() as conn:
        result = conn.execute(delete_sql)
        print(f"✓ Removed {result.rowcount} rows that are older than the current rolling 9-year window in {table_name}")

def upsert(df, table_name, engine):
    print(f"Upserting into {table_name}...")

    # Clean dataframe
    df = df.copy()
    
    # Convert all datetime columns: NaT → None
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            # Convert NaT to None explicitly
            df[col] = df[col].astype('object').where(pd.notna(df[col]), None)
    
    # Convert all other pandas NA types to None
    df = df.where(pd.notnull(df), None)
    
    # Convert each row to dict and handle NaT/NaN explicitly
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    
    update_cols = [col for col in df.columns if col != "CASE NUMBER"]
    update_dict = {
        table.c[col]: table.c[col]  # This will be replaced via on_conflict_do_update
        for col in update_cols
    }
    
    with engine.begin() as conn:
        for idx, row in df.iterrows():
            # Convert row to dict, explicitly handling None/NaT
            row_dict = {}
            for col in df.columns:
                val = row[col]
                # Ensure NaT becomes None
                if pd.isna(val):
                    row_dict[col] = None
                else:
                    row_dict[col] = val
            
            insert_stmt = pg_insert(table).values(**row_dict)
            
            # Build update set: col = EXCLUDED.col for each column except CASE NUMBER
            update_set = {
                table.c[col]: insert_stmt.excluded[col]
                for col in update_cols
            }
            
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=["CASE NUMBER"],
                set_=update_set
            )
            
            conn.execute(upsert_stmt)

# MAIN REFRESH
def refresh_year(url, table_name):
    print(f"\n=== Refreshing {table_name} ===")
    df_raw = download_file(url)
    df = clean_and_prepare(df_raw)

    engine = create_engine(DATABASE_URL)

    create_table_if_missing(df, table_name, engine)

    # Fix datetime conversions FIRST
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], errors="coerce")  # ensures NaT for bad values
            df[col] = df[col].dt.tz_localize(None) if hasattr(df[col], "dt") else df[col]
            df[col] = df[col].where(df[col].notna(), None)  # convert NaT → None

    # Now safely convert other null types
    df = df.where(pd.notnull(df), None)
    
    delete_old_rows(table_name, engine)

    upsert(df, table_name, engine)
    print(f"Completed refresh for {table_name}")

if __name__ == "__main__":
    current_month = datetime.now().month

    # Only refresh previous year if we are not past April
    if current_month <= 4:
        print("Month is April or earlier — refreshing previous year's data...")
        refresh_year(URL_PREVIOUS, TABLE_PREVIOUS)
    else:
        print("Month is after April — skipping previous year's data refresh.")

    # Always refresh current year
    refresh_year(URL_CURRENT, TABLE_CURRENT)

    print("\n✔ All done! Daily refresh complete.")
    
    # Run precompute after data refresh
    print("\n⚙️  Running precompute pipeline...")

    import runpy
    from pathlib import Path
    runpy.run_path(str(Path(__file__).with_name("precompute.py")), run_name="__main__")

    print("✅ Precompute complete.")