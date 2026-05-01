import uuid
from datetime import datetime
from database import save_booking

BOOKINGS = {}
SEAT_STORE = {}


def generate_seats(total=40):
    seats = []
    rows = range(1, 11)
    cols = ["A", "B", "C", "D"]

    for r in rows:
        for c in cols:
            seats.append({"seat_number": f"{r}{c}", "available": True})

    return seats[:total]


def get_seats(route_id: str):
    if route_id not in SEAT_STORE:
        SEAT_STORE[route_id] = generate_seats()
    return SEAT_STORE[route_id]


def create_booking(route_id, train_name, passenger_name, passenger_type, seat_number, price):
    seats = get_seats(route_id)

    selected = None
    for seat in seats:
        if seat["seat_number"] == seat_number:
            selected = seat
            break

    if not selected:
        return {"success": False, "message": "Seat not found"}

    if not selected["available"]:
        return {"success": False, "message": "Seat already booked"}

    selected["available"] = False

    ticket = {
        "booking_id": "BK-" + str(uuid.uuid4())[:8].upper(),
        "pnr": "PNR" + str(uuid.uuid4())[:6].upper(),
        "route_id": route_id,
        "train_name": train_name,
        "passenger_name": passenger_name,
        "passenger_type": passenger_type,
        "seat_number": seat_number,
        "price": price,
        "currency": "EUR",
        "booking_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Confirmed",
    }

    BOOKINGS[ticket["booking_id"]] = ticket

    try:
        save_booking(ticket)
    except Exception as e:
        print("Warning: booking not saved:", e)

    return {"success": True, "ticket": ticket}