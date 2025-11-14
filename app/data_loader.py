import os
import pandas as pd


# Get the absolute path to the data file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "app/data", "Houston-311-Clean.csv")

# Load the data
df = pd.read_csv(DATA_PATH, low_memory=False)

# Clean once here
df[["CREATED DATE", "CLOSED DATE"]] = df[["CREATED DATE", "CLOSED DATE"]].apply(
    pd.to_datetime, errors="coerce"
)
df["NEIGHBORHOOD"] = df["NEIGHBORHOOD"]
df["CATEGORY"] = df["CATEGORY"]
df["DEPARTMENT"] = df["DEPARTMENT"]
df["DIVISION"] = df["DIVISION"]
df["RESOLUTION_TIME_DAYS"] = (df["CLOSED DATE"] - df["CREATED DATE"]).dt.total_seconds() / 86400

df = df.infer_objects(copy=False)