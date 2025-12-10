from flask import Blueprint, request, jsonify
from middlewares.auth_middleware import auth_required
from config import get_db_connection
import bcrypt

user_bp = Blueprint("user", __name__)


# ============================
# GET PROFILE
# ============================
@user_bp.get("/profile")
@auth_required
def get_profile():
    user_id = request.user["id"]

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT id, username, email, created_at
        FROM users
        WHERE id = %s
    """, (user_id,))

    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify({"profile": user}), 200


# ============================
# UPDATE PROFILE (username & email)
# ============================
@user_bp.put("/profile")
@auth_required
def update_profile():
    user_id = request.user["id"]
    data = request.json or {}

    username = data.get("username")
    email = data.get("email")

    if not username or not email:
        return jsonify({"message": "username and email are required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE users
            SET username=%s, email=%s
            WHERE id=%s
        """, (username, email, user_id))

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({
            "message": "username or email already exists",
            "error": str(e)
        }), 400
    finally:
        cur.close()
        conn.close()

    return jsonify({"message": "profile updated"}), 200


# ============================
# UPDATE PASSWORD
# ============================
@user_bp.put("/profile/password")
@auth_required
def update_password():
    user_id = request.user["id"]
    data = request.json or {}

    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return jsonify({"message": "old_password and new_password required"}), 400

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # ambil current hash
    cur.execute("SELECT password_hash FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    if not user:
        return jsonify({"message": "User not found"}), 404

    stored_hash = bytes(user["password_hash"])

    # verify old password
    if not bcrypt.checkpw(old_password.encode(), stored_hash):
        return jsonify({"message": "old password is incorrect"}), 400

    # hash new password
    salt = bcrypt.gensalt()
    new_hash = bcrypt.hashpw(new_password.encode(), salt)

    # update
    cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user_id))
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"message": "password updated"}), 200


# ============================
# DELETE ACCOUNT
# ============================
@user_bp.delete("/profile")
@auth_required
def delete_account():
    user_id = request.user["id"]

    conn = get_db_connection()
    cur = conn.cursor()

    # delete user – rfm_results & upload_history punya FK CASCADE
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"message": "account deleted"}), 200
