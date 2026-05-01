import os
import joblib
import pandas as pd
from datetime import datetime, timedelta

MODEL_PATH = "models/price_model_production.pkl"
CSV_PATH = "data/euro_rail_past_bookings_1000.csv"


def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)


def clean_text(value):
    return str(value).strip().lower()


def get_route_template(from_city, to_city, provider=""):
    df = pd.read_csv(CSV_PATH)
    df = df.fillna("")

    # normalize columns
    df["from_clean"] = df["from_city"].astype(str).str.strip().str.lower()
    df["to_clean"] = df["to_city"].astype(str).str.strip().str.lower()
    df["provider_clean"] = df["provider"].astype(str).str.strip().str.lower()

    from_clean = clean_text(from_city)
    to_clean = clean_text(to_city)
    provider_clean = clean_text(provider)

    # exact route match
    filtered = df[
        (df["from_clean"] == from_clean)
        & (df["to_clean"] == to_clean)
    ]

    # if exact fails, try contains match
    if filtered.empty:
        filtered = df[
            df["from_clean"].str.contains(from_clean, na=False)
            & df["to_clean"].str.contains(to_clean, na=False)
        ]

    # provider filter if possible
    if provider_clean and not filtered.empty:
        provider_filtered = filtered[
            filtered["provider_clean"].str.contains(provider_clean, na=False)
            | filtered["provider_clean"].apply(lambda x: provider_clean in x)
        ]

        if not provider_filtered.empty:
            filtered = provider_filtered

    if filtered.empty:
        print("No matching route found.")
        print("Searching:", from_city, "→", to_city, "provider:", provider)
        print("Available routes:")
        print(df[["from_city", "to_city", "provider"]].drop_duplicates().head(20))
        return None

    # choose most recent booking for this route
    if "booking_date" in filtered.columns:
        filtered["booking_date"] = pd.to_datetime(
            filtered["booking_date"], errors="coerce"
        )
        filtered = filtered.sort_values("booking_date", ascending=False)

    return filtered.iloc[0].to_dict()


def predict_future_prices(from_city, to_city, provider="", days=7):
    artifact = load_model()

    if artifact is None:
        return {
            "success": False,
            "message": "Model not found. Run python train_price_model_production.py first.",
            "predictions": [],
        }

    pipeline = artifact["pipeline"]
    template = get_route_template(from_city, to_city, provider)

    if template is None:
        return {
            "success": False,
            "message": f"No matching route found for {from_city} to {to_city}.",
            "predictions": [],
        }

    predictions = []
    today = datetime.now()

    for i in range(int(days)):
        future_travel_date = today + timedelta(days=i)
        booking_date = today

        days_until_departure = max((future_travel_date - booking_date).days, 1)

        available_seats = float(template.get("available_seats_at_booking", 100) or 100)
        total_seats = float(template.get("total_seats", 400) or 400)
        occupancy_rate = float(template.get("occupancy_rate_at_booking", 0.5) or 0.5)

        availability_ratio = available_seats / total_seats if total_seats else 0

        from_value = template.get("from_city", from_city)
        to_value = template.get("to_city", to_city)
        provider_value = template.get("provider", provider or "Unknown")

        route_key = f"{from_value}_{to_value}"
        provider_route = f"{provider_value}_{route_key}"

        row = {
            "from_city": from_value,
            "to_city": to_value,
            "provider": provider_value,
            "train_type": template.get("train_type", "Unknown"),
            "passenger_type": template.get("passenger_type", "regular"),
            "booking_channel": template.get("booking_channel", "online"),
            "route_key": route_key,
            "provider_route": provider_route,
            "days_until_departure": days_until_departure,
            "is_last_minute": 1 if days_until_departure <= 2 else 0,
            "is_early_booking": 1 if days_until_departure >= 30 else 0,
            "available_seats_at_booking": available_seats,
            "total_seats": total_seats,
            "availability_ratio": availability_ratio,
            "occupancy_rate_at_booking": occupancy_rate,
            "is_low_availability": 1 if available_seats <= 50 else 0,
            "demand_level": float(template.get("demand_level", 5) or 5),
            "base_price_at_booking": float(
                template.get("base_price_at_booking", 100) or 100
            ),
            "travel_month": future_travel_date.month,
            "travel_day": future_travel_date.day,
            "travel_weekday": future_travel_date.weekday(),
            "travel_week_of_year": int(future_travel_date.isocalendar().week),
            "is_weekend": 1 if future_travel_date.weekday() in [5, 6] else 0,
            "is_peak_season": 1 if future_travel_date.month in [6, 7, 8, 12] else 0,
            "booking_month": booking_date.month,
            "booking_weekday": booking_date.weekday(),
        }

        features = artifact.get("features", list(row.keys()))
        X = pd.DataFrame([row])

        # keep only training features
        for col in features:
            if col not in X.columns:
                X[col] = 0

        X = X[features]

        pred = pipeline.predict(X)[0]

        predictions.append(
            {
                "date": future_travel_date.strftime("%Y-%m-%d"),
                "weekday": future_travel_date.strftime("%A"),
                "predicted_price": round(float(pred), 2),
                "currency": "EUR",
            }
        )

    best = min(predictions, key=lambda x: x["predicted_price"])

    return {
        "success": True,
        "from_city": from_city,
        "to_city": to_city,
        "provider": provider,
        "best_day_to_book": best,
        "predictions": predictions,
    }


if __name__ == "__main__":
    result = predict_future_prices("Paris", "Berlin", "SNCF", 7)
    print(result)