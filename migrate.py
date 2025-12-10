import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")


def run_migration():
    print("Connecting to MySQL...")

    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS
    )
    cur = conn.cursor()

    print(f"Creating database {DB_NAME} if not exists...")
    cur.execute(f"""
        CREATE DATABASE IF NOT EXISTS {DB_NAME}
        CHARACTER SET utf8mb4
        COLLATE utf8mb4_unicode_ci;
    """)
    cur.execute(f"USE {DB_NAME};")

    print("Creating tables...")

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARBINARY(200) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Upload history table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS upload_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            filename VARCHAR(255) NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)

    # RFM results table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rfm_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            file_id INT NOT NULL,
            customer_id VARCHAR(100) NOT NULL,
            recency INT,
            frequency INT,
            monetary DOUBLE,
            cluster INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES upload_history(id) ON DELETE CASCADE
        );
    """)

    # Index (safe creation)
    try:
        cur.execute("CREATE INDEX idx_rfm_file ON rfm_results(file_id);")
        print("Index idx_rfm_file created.")
    except:
        print("Index idx_rfm_file already exists. Skipping.")

    conn.commit()
    cur.close()
    conn.close()

    print("Migration completed successfully.")


if __name__ == "__main__":
    run_migration()
