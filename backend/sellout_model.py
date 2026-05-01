import os
import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

CSV_PATH = "data/euro_rail_realistic_200_routes.csv"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "sellout_model.pkl")

os.makedirs(MODEL_DIR, exist_ok=True)


def duration_to_minutes(duration):
    try:
        text = str(duration).lower().replace(" ", "")
        h, m = 0, 0

        if "h" in text:
            h = int(text.split("h")[0])
            rest = text.split("h")[1]
            if "m" in rest:
                m = int(rest.replace("m", ""))
        elif "m" in text:
            m = int(text.replace("m", ""))

        return h * 60 + m
    except Exception:
        return 0


def prepare_data():
    df = pd.read_csv(CSV_PATH)
    df = df.fillna("")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    numeric_cols = [
        "available_seats",
        "total_seats",
        "base_price",
        "delay_minutes",
    ]

    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["duration_minutes"] = df["duration"].apply(duration_to_minutes)

    df["weekday"] = df["date"].dt.weekday
    df["is_weekend"] = df["weekday"].isin([5, 6]).astype(int)

    df["occupancy_rate"] = 1 - (
        df["available_seats"] / df["total_seats"].replace(0, 1)
    )

    # ML target:
    # if seats are low OR occupancy is high, mark as likely to sell out soon
    df["sellout_soon"] = (
        (df["occupancy_rate"] >= 0.75) |
        (df["available_seats"] <= 50)
    ).astype(int)

    features = [
        "available_seats",
        "total_seats",
        "base_price",
        "delay_minutes",
        "duration_minutes",
        "weekday",
        "is_weekend",
        "occupancy_rate",
    ]

    X = df[features]
    y = df["sellout_soon"]

    return X, y, features


def train_sellout_model():
    X, y, features = prepare_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y if y.nunique() > 1 else None,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        random_state=42,
        class_weight="balanced",
    )

    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)

    print("Sellout model trained.")
    print("Accuracy:", round(acc, 3))
    print(classification_report(y_test, preds))

    artifact = {
        "model": model,
        "features": features,
        "accuracy": acc,
    }

    joblib.dump(artifact, MODEL_PATH)

    print("Saved:", MODEL_PATH)


def load_sellout_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            "Sellout model not found. Run: python sellout_model.py"
        )

    return joblib.load(MODEL_PATH)


def predict_sellout(train: dict):
    artifact = load_sellout_model()
    model = artifact["model"]

    available_seats = float(train.get("available_seats", 0) or 0)
    total_seats = float(train.get("total_seats", 1) or 1)
    base_price = float(train.get("base_price", 0) or 0)
    delay_minutes = float(train.get("delay_minutes", 0) or 0)
    duration_minutes = duration_to_minutes(train.get("duration", ""))

    try:
        date = pd.to_datetime(train.get("date"))
        weekday = date.weekday()
    except Exception:
        weekday = 0

    is_weekend = 1 if weekday in [5, 6] else 0
    occupancy_rate = 1 - (available_seats / total_seats if total_seats else 0)

    X = pd.DataFrame(
        [
            {
                "available_seats": available_seats,
                "total_seats": total_seats,
                "base_price": base_price,
                "delay_minutes": delay_minutes,
                "duration_minutes": duration_minutes,
                "weekday": weekday,
                "is_weekend": is_weekend,
                "occupancy_rate": occupancy_rate,
            }
        ]
    )

    probability = model.predict_proba(X)[0][1]
    prediction = model.predict(X)[0]

    if probability >= 0.7:
        risk = "HIGH"
    elif probability >= 0.4:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    recommendation = "BOOK NOW" if risk in ["HIGH", "MEDIUM"] else "SAFE TO WAIT"

    return {
        "success": True,
        "sellout_probability": round(float(probability), 3),
        "sellout_percentage": round(float(probability) * 100, 1),
        "prediction": int(prediction),
        "risk": risk,
        "recommendation": recommendation,
        "model_accuracy": round(float(artifact.get("accuracy", 0)), 3),
    }


if __name__ == "__main__":
    train_sellout_model()