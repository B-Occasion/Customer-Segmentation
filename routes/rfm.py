print(">>> RFM ROUTES LOADED <<<")
import os
import pandas as pd
import joblib
from flask import Blueprint, jsonify, request
from middlewares.auth_middleware import auth_required
from config import get_db_connection
from rfm_pipeline import basic_cleaning, compute_rfm, cap_and_log_transform

rfm_bp = Blueprint("rfm", __name__)

MODEL_PATH = os.getenv("MODEL_PATH")
UPLOAD_DIR = os.getenv("UPLOAD_DIR")

@rfm_bp.post("/process/<int:file_id>")
@auth_required
def process_rfm(file_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # 1. Check file belongs to user
    cur.execute("""
        SELECT filename FROM upload_history
        WHERE id=%s AND user_id=%s
    """, (file_id, request.user["id"]))

    history = cur.fetchone()

    if not history:
        return jsonify({"message": "file not found or unauthorized"}), 404

    filepath = os.path.join(UPLOAD_DIR, history["filename"])

    # 2. Load file (CSV or Excel)
    try:
        if filepath.endswith(".csv"):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 400

    # 3. Basic cleaning (drop null CustomerID, numeric fix, etc.)
    df = basic_cleaning(df)

    # 4. Compute RFM
    rfm_df = compute_rfm(df)

    # 5. Transform → cap outliers, log-transform, scale
    rfm_proc, rfm_log, rfm_scaled_df, scaler = cap_and_log_transform(rfm_df)

    # Ensure required columns exist
    required_cols = ["R_log", "F_log", "M_log"]
    for col in required_cols:
        if col not in rfm_log.columns:
            return jsonify({"error": f"Missing column: {col}"}), 400

    # 6. Load trained model
    try:
        model = joblib.load(MODEL_PATH)
    except Exception as e:
        return jsonify({"error": f"Model load error: {str(e)}"}), 500

    # 7. Model prediction
    try:
        clusters = model.predict(rfm_scaled_df)
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 400

    rfm_proc["cluster"] = clusters

    # 8. Save results to DB
    insert_count = 0
    for _, row in rfm_proc.iterrows():
        # Ambil CustomerID dari kolom. Jika tidak ada, fallback ke index (defensive).
        if "CustomerID" in rfm_proc.columns:
            cust = row["CustomerID"]
        else:
            # defensive fallback (jarang terjadi)
            cust = _

        # Cust bisa berupa float (hasil parsing). Buat string yang bersih:
        try:
            # bila integer-like, simpan tanpa .0
            cust_str = str(int(cust)) if (not pd.isna(cust) and float(cust).is_integer()) else str(cust)
        except Exception:
            cust_str = str(cust)

        cur.execute("""
            INSERT INTO rfm_results (file_id, customer_id, recency, frequency, monetary, cluster)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            file_id,
            cust_str,
            int(row["Recency"]),
            int(row["Frequency"]),
            float(row["Monetary"]),
            int(row["cluster"])
        ))
        insert_count += 1

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "message": "RFM processing complete",
        "total_customers": insert_count,
        "clusters": int(rfm_proc["cluster"].nunique())
    }), 200


@rfm_bp.get("/results/<int:file_id>")
@auth_required
def rfm_results(file_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # validate ownership
    cur.execute("""
        SELECT id FROM upload_history
        WHERE id=%s AND user_id=%s
    """, (file_id, request.user["id"]))

    if not cur.fetchone():
        return jsonify({"message": "not found or unauthorized"}), 404

    cur.execute("""
        SELECT customer_id, recency, frequency, monetary, cluster
        FROM rfm_results
        WHERE file_id=%s
    """, (file_id,))

    results = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        "message": "success",
        "file_id": file_id,
        "total": len(results),
        "data": results
    })
