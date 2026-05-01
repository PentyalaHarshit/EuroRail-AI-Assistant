import os
import re
from dotenv import load_dotenv
from groq import Groq

from query_engine import search_trains
from sellout_model import predict_sellout
from price_predictor import predict_future_prices

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.1-8b-instant"

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def call_llm(prompt, max_tokens=220):
    if client is None:
        return "LLM is not available because GROQ_API_KEY is missing."

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"LLM error: {str(e)}"


def is_sellout_query(query: str):
    q = query.lower()
    keywords = [
        "sell out",
        "sellout",
        "sold out soon",
        "will this train sell",
        "will seats finish",
        "seats finish",
        "availability risk",
        "high demand",
    ]
    return any(k in q for k in keywords)


def is_price_decision_query(query: str):
    q = query.lower()
    keywords = [
        "should i book",
        "book today or later",
        "book now or later",
        "wait or book",
        "best day to book",
        "future price",
        "price prediction",
        "will price drop",
        "will price increase",
    ]
    return any(k in q for k in keywords)


def extract_route_from_query(query: str):
    q = query.strip()

    patterns = [
        r"book\s+(.+?)\s+to\s+(.+?)\s+(today|now|later|tomorrow|next|this|$)",
        r"from\s+(.+?)\s+to\s+(.+?)\s+(today|now|later|tomorrow|next|this|$)",
        r"(.+?)\s+to\s+(.+?)\s+(today|now|later|tomorrow|next|this|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, q, re.IGNORECASE)

        if match:
            from_city = match.group(1).strip(" ?.,").title()
            to_city = match.group(2).strip(" ?.,").title()

            remove_words = [
                "Should I",
                "Can I",
                "I",
                "Train",
                "Ticket",
                "Price",
                "Should",
                "Book",
            ]

            for word in remove_words:
                from_city = from_city.replace(word, "").strip()
                to_city = to_city.replace(word, "").strip()

            return from_city, to_city

    return "", ""


def safe_float(value, default=0):
    try:
        return float(value)
    except Exception:
        return default


def get_train_label(train):
    train_name = (
        train.get("train_name")
        or train.get("train")
        or train.get("service_name")
        or "Unknown Train"
    )

    train_number = (
        train.get("train_number")
        or train.get("train_id")
        or train.get("train_no")
        or train.get("route_id")
        or ""
    )

    train_name = str(train_name).strip()
    train_number = str(train_number).strip()

    if train_number and train_number not in train_name:
        return f"{train_name} ({train_number})"

    return train_name


def same_route(row, from_city, to_city):
    row_from = str(row.get("from_city", "")).strip().lower()
    row_to = str(row.get("to_city", "")).strip().lower()

    return (
        row_from == str(from_city).strip().lower()
        and row_to == str(to_city).strip().lower()
    )


def build_price_decision_answer(query, rows):
    from_city, to_city = extract_route_from_query(query)

    if not from_city or not to_city:
        if rows:
            from_city = rows[0].get("from_city")
            to_city = rows[0].get("to_city")
        else:
            return {
                "answer": "Please mention route like: Should I book Paris to Berlin today or later?",
                "context": "Route extraction failed",
                "rows": [],
            }

    matching_rows = [row for row in rows if same_route(row, from_city, to_city)]

    if not matching_rows:
        matching_rows = rows

    answer_parts = []
    answer_parts.append(f"Route: {from_city} → {to_city}")
    answer_parts.append("")
    answer_parts.append("Future booking recommendation for available trains:")
    answer_parts.append("")

    for idx, train in enumerate(matching_rows[:5], start=1):
        train_label = get_train_label(train)
        provider = str(train.get("provider", "") or "")
        status = str(train.get("status", "") or "")
        date = train.get("date", "")
        seats = f"{train.get('available_seats')}/{train.get('total_seats')}"
        current_price = safe_float(train.get("base_price"), 0)

        try:
            prediction = predict_future_prices(
                from_city=from_city,
                to_city=to_city,
                provider=provider,
                days=7,
            )

            if prediction.get("success"):
                prices = prediction["predictions"]
                best = prediction["best_day_to_book"]

                today_price = safe_float(prices[0]["predicted_price"], current_price)
                best_price = safe_float(best["predicted_price"], today_price)

                booking_price = current_price if current_price > 0 else today_price
                saving = round(booking_price - best_price, 2)

                if status.lower() in ["sold out", "cancelled"]:
                    booking_status = status.upper()
                elif saving >= 5:
                    booking_status = "WAIT"
                else:
                    booking_status = "BOOK NOW"

                answer_parts.append(f"{idx}. Train: {train_label}")
                answer_parts.append(f"   Date: {date}")
                answer_parts.append(f"   Provider: {provider}")
                answer_parts.append(f"   Status: {status}")
                answer_parts.append(f"   Seats: {seats}")
                answer_parts.append(f"   Booking status: {booking_status}")
                answer_parts.append(f"   Current booking price: {booking_price} EUR")
                answer_parts.append(
                    f"   Best future price: {best_price} EUR on {best['date']} ({best['weekday']})"
                )
                answer_parts.append(f"   Potential saving: {saving if saving > 0 else 0} EUR")
                answer_parts.append("")

            else:
                answer_parts.append(f"{idx}. Train: {train_label}")
                answer_parts.append(f"   Date: {date}")
                answer_parts.append(f"   Provider: {provider}")
                answer_parts.append(f"   Status: {status}")
                answer_parts.append(f"   Seats: {seats}")
                answer_parts.append(f"   Booking status: BOOK NOW")
                answer_parts.append(f"   Current booking price: {current_price} EUR")
                answer_parts.append("")

        except Exception:
            answer_parts.append(f"{idx}. Train: {train_label}")
            answer_parts.append(f"   Date: {date}")
            answer_parts.append(f"   Provider: {provider}")
            answer_parts.append(f"   Status: {status}")
            answer_parts.append(f"   Seats: {seats}")
            answer_parts.append(f"   Booking status: BOOK NOW")
            answer_parts.append(f"   Current booking price: {current_price} EUR")
            answer_parts.append("")

    return {
        "answer": "\n".join(answer_parts).strip(),
        "context": "ML Future Booking Recommendation Used For Train List",
        "rows": matching_rows,
    }


def build_structured_train_answer(rows):
    parts = []
    parts.append("Here are the matching trains:\n")

    for i, train in enumerate(rows[:5], start=1):
        train_label = get_train_label(train)

        date = train.get("date", "")
        provider = train.get("provider", "")
        status = train.get("status", "")
        route = f"{train.get('from_city')} → {train.get('to_city')}"
        dep = train.get("departure_time", "")
        arr = train.get("arrival_time", "")
        seats = f"{train.get('available_seats')}/{train.get('total_seats')}"
        price = train.get("base_price", "")
        currency = train.get("currency", "EUR")
        delay = train.get("delay_minutes", 0)

        parts.append(
            f"{i}. Train: {train_label}\n"
            f"   Date: {date}\n"
            f"   Route: {route}\n"
            f"   Provider: {provider}\n"
            f"   Time: {dep} → {arr}\n"
            f"   Status: {status}\n"
            f"   Seats: {seats}\n"
            f"   Price: {price} {currency}\n"
            f"   Delay: {delay} minutes\n"
        )

    return "\n".join(parts).strip()


def run_crew(query: str):
    try:
        context, rows = search_trains(query, k=5)
    except Exception as e:
        return {
            "answer": f"Search error: {str(e)}",
            "context": "",
            "rows": [],
        }

    # Future booking recommendation for all searched trains
    if is_price_decision_query(query):
        return build_price_decision_answer(query, rows)

    if not rows:
        return {
            "answer": "No matching trains are available in the provided rail data.",
            "context": context,
            "rows": [],
        }

    # ML sell-out prediction
    if is_sellout_query(query):
        train = rows[0]

        try:
            sellout = predict_sellout(train)
            train_label = get_train_label(train)

            answer = f"""
Train: {train_label}
Date: {train.get("date")}
Route: {train.get("from_city")} → {train.get("to_city")}

Available seats: {train.get("available_seats")}/{train.get("total_seats")}
Status: {train.get("status")}
Current price: {train.get("base_price")} {train.get("currency", "EUR")}

Sell-out chance: {sellout["sellout_percentage"]}%
Risk level: {sellout["risk"]}

Recommendation: {sellout["recommendation"]}
""".strip()

            return {
                "answer": answer,
                "context": "ML Sellout Prediction Used",
                "rows": rows,
                "ml_result": sellout,
            }

        except Exception:
            available = safe_float(train.get("available_seats"))
            total = safe_float(train.get("total_seats"), 1)
            occupancy = 1 - (available / total if total else 0)

            if available <= 50 or occupancy >= 0.75:
                risk = "HIGH"
                recommendation = "BOOK NOW"
                chance = 90
            elif available <= 100 or occupancy >= 0.55:
                risk = "MEDIUM"
                recommendation = "BOOK SOON"
                chance = 60
            else:
                risk = "LOW"
                recommendation = "SAFE TO WAIT"
                chance = 25

            train_label = get_train_label(train)

            return {
                "answer": f"""
Train: {train_label}
Date: {train.get("date")}
Route: {train.get("from_city")} → {train.get("to_city")}

Available seats: {train.get("available_seats")}/{train.get("total_seats")}
Status: {train.get("status")}
Current price: {train.get("base_price")} {train.get("currency", "EUR")}

Sell-out chance: {chance}%
Risk level: {risk}

Recommendation: {recommendation}
""".strip(),
                "context": "Fallback Sellout Logic Used",
                "rows": rows,
            }

    # Structured answer with date always included
    return {
        "answer": build_structured_train_answer(rows),
        "context": "Structured train answer with date",
        "rows": rows,
    }