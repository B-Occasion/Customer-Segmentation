import os
import joblib
import pandas as pd
from rfm_pipeline import basic_cleaning, compute_rfm, cap_and_log_transform

from config import MODEL_PATH

def load_file_to_df(path):
    path = path
    if path.lower().endswith(".xlsx") or path.lower().endswith(".xls"):
        df = pd.read_excel(path)
    elif path.lower().endswith(".csv"):
        df = pd.read_csv(path)
    else:
        raise ValueError("Unsupported file format")
    return df

def process_and_predict(file_path, model):
    df = pd.read_csv(file_path)

    # CLEANING
    df = df.dropna(subset=["CustomerID"])
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df = df.dropna(subset=["Quantity", "UnitPrice"])
    df = df[df["Quantity"] > 0]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df = df.dropna(subset=["InvoiceDate"])

    # Compute RFM table
    rfm_table = compute_rfm(df)

    # Transform (cap, log, scale)
    rfm_proc, rfm_log, rfm_scaled_df, scaler = cap_and_log_transform(rfm_table)

    # Predict cluster
    clusters = model.predict(rfm_scaled_df)
    rfm_proc["cluster"] = clusters

    # RETURN TEPAT 2 HAL:
    # 1. rfm_proc (yang sudah punya cluster)
    # 2. rfm_log (log RFM yang dipakai untuk FE)
    return rfm_proc, rfm_log
