import jwt
import os
from flask import request, jsonify
from functools import wraps
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

def auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"message": "missing or invalid token"}), 401

        token = auth_header.split(" ")[1]

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "token expired"}), 401
        except Exception:
            return jsonify({"message": "invalid token"}), 401

        request.user = {
            "id": payload["user_id"],
            "username": payload["username"],
            "email": payload["email"]
        }

        return f(*args, **kwargs)

    return wrapper
