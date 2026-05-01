import sqlite3
from pathlib import Path

DB_PATH = Path("eurorail.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id TEXT UNIQUE,
            pnr TEXT UNIQUE,
            route_id TEXT,
            train_name TEXT,
            passenger_name TEXT,
            passenger_type TEXT,
            seat_number TEXT,
            price REAL,
            currency TEXT,
            booking_time TEXT,
            status TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def save_booking(ticket: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO bookings (
            booking_id, pnr, route_id, train_name, passenger_name,
            passenger_type, seat_number, price, currency, booking_time, status
        )
        VALUES (
            :booking_id, :pnr, :route_id, :train_name, :passenger_name,
            :passenger_type, :seat_number, :price, :currency, :booking_time, :status
        )
        """,
        ticket,
    )

    conn.commit()
    conn.close()


def get_all_bookings():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bookings ORDER BY id DESC")
    rows = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return rows


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")