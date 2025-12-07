from dotenv import load_dotenv
import os
import pandas as pd
from sqlalchemy import create_engine

load_dotenv()
db_url = os.getenv("DATABASE_URL")

# Connect to your Postgres database
engine = create_engine(db_url)

# Load the table into a DataFrame
df = pd.read_sql("SELECT * FROM houston_311", engine)

cols = ["NEIGHBORHOOD", "DEPARTMENT", "DIVISION", "CATEGORY", "CASE TYPE"]

for c in cols:
    df[c] = (
        df[c]
        .astype(str)
        .str.strip()
        .str.title()
        .str.replace("\s+", " ", regex=True)
    )

# Convert date columns to datetime
df[["CREATED DATE", "CLOSED DATE"]] = df[["CREATED DATE", "CLOSED DATE"]].apply(
    pd.to_datetime, errors="coerce"
)

if "CREATED DATE" in df.columns:
    df["Year"] = df["CREATED DATE"].dt.year.astype("Int64")
else:
    df["Year"] = pd.NA

df["MonthName"] = df["CREATED DATE"].dt.month_name()

df = df.infer_objects(copy=False)