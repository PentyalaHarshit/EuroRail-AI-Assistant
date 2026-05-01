import os
import smtplib
import qrcode

from io import BytesIO
from email.message import EmailMessage

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from dotenv import load_dotenv

load_dotenv()


def create_ticket_pdf(ticket: dict):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    qr_text = f"""
EuroRail Ticket
PNR: {ticket.get("pnr")}
Booking ID: {ticket.get("booking_id")}
Passenger: {ticket.get("passenger_name")}
Train: {ticket.get("train_name")}
Seat: {ticket.get("seat_number")}
Status: {ticket.get("status")}
"""

    qr_img = qrcode.make(qr_text)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(50, 800, "EuroRail Ticket")

    pdf.setFont("Helvetica", 12)

    y = 760
    fields = [
        ("Booking ID", ticket.get("booking_id")),
        ("PNR", ticket.get("pnr")),
        ("Passenger", ticket.get("passenger_name")),
        ("Passenger Type", ticket.get("passenger_type")),
        ("Train", ticket.get("train_name")),
        ("Seat", ticket.get("seat_number")),
        ("Price", f'{ticket.get("price")} {ticket.get("currency")}'),
        ("Status", ticket.get("status")),
        ("Booking Time", ticket.get("booking_time")),
    ]

    for label, value in fields:
        pdf.drawString(50, y, f"{label}: {value}")
        y -= 25

    pdf.drawString(50, y - 20, "Scan QR for verification")
    qr_reader = ImageReader(qr_buffer)
    pdf.drawImage(qr_reader, 50, y - 170, width=120, height=120)

    pdf.save()
    buffer.seek(0)

    return buffer


def email_ticket(ticket: dict, to_email: str):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_APP_PASSWORD")

    if not sender or not password:
        raise ValueError("EMAIL_USER or EMAIL_APP_PASSWORD missing in .env")

    pdf_buffer = create_ticket_pdf(ticket)

    msg = EmailMessage()
    msg["Subject"] = f"EuroRail Ticket - {ticket.get('pnr')}"
    msg["From"] = sender
    msg["To"] = to_email

    msg.set_content(
        f"""
Hello {ticket.get("passenger_name")},

Your EuroRail ticket is attached.

PNR: {ticket.get("pnr")}
Train: {ticket.get("train_name")}
Seat: {ticket.get("seat_number")}

Thank you,
EuroRail AI Assistant
"""
    )

    msg.add_attachment(
        pdf_buffer.read(),
        maintype="application",
        subtype="pdf",
        filename=f"{ticket.get('pnr')}_ticket.pdf",
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

    return True