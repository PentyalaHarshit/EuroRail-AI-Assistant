from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from crew_logic import run_crew
from query_engine import search_trains_structured
from realtime_api import get_db_departures
from booking_engine import get_seats, create_booking
from email_ticket import email_ticket
from database import init_db, get_all_bookings
from price_predictor import predict_future_prices



app = FastAPI(title="EuroRail Live AI Assistant Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BookingRequest(BaseModel):
    route_id: str
    train_name: str
    passenger_name: str
    passenger_type: str
    seat_number: str
    price: float


class EmailTicketRequest(BaseModel):
    ticket: dict
    email: str


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def home():
    return {
        "message": "EuroRail backend is running",
        "docs": "http://127.0.0.1:8000/docs",
        "frontend": "http://localhost:5173",
    }


@app.post("/api/ask")
def api_ask(query: str = Form(...)):
    return run_crew(query)


@app.get("/api/search")
def api_search(
    from_city: str = "",
    to_city: str = "",
    date: str = "",
    provider: str = "",
    sort_by: str = "best",
    passenger_type: str = "regular",
    direct_only: bool = False,
    wifi: bool = False,
    available_only: bool = False,
):
    rows = search_trains_structured(
        from_city=from_city,
        to_city=to_city,
        date=date,
        provider=provider,
        sort_by=sort_by,
        passenger_type=passenger_type,
        direct_only=direct_only,
        wifi=wifi,
        available_only=available_only,
        limit=20,
    )
    return {"results": rows}


@app.get("/api/realtime")
def api_realtime(city: str):
    return get_db_departures(city)


@app.get("/api/seats/{route_id}")
def api_get_seats(route_id: str):
    return {"route_id": route_id, "seats": get_seats(route_id)}


@app.post("/api/book")
def api_book_ticket(request: BookingRequest):
    return create_booking(
        route_id=request.route_id,
        train_name=request.train_name,
        passenger_name=request.passenger_name,
        passenger_type=request.passenger_type,
        seat_number=request.seat_number,
        price=request.price,
    )


@app.post("/api/email-ticket")
def api_email_ticket(request: EmailTicketRequest):
    email_ticket(request.ticket, request.email)
    return {"success": True, "message": "Ticket emailed successfully"}


@app.get("/api/bookings")
def api_get_bookings():
    return {"bookings": get_all_bookings()}


@app.get("/api/predict-price")
def api_predict_price(
    from_city: str,
    to_city: str,
    provider: str = "",
    days: int = 7,
):
    return predict_future_prices(
        from_city=from_city,
        to_city=to_city,
        provider=provider,
        days=days,
    )