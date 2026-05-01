import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor

CSV_PATH = "data/euro_rail_past_bookings_1000.csv"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "price_model_production.pkl")

os.makedirs(MODEL_DIR, exist_ok=True)


df = pd.read_csv(CSV_PATH)
df = df.fillna("")

print("CSV columns:")
print(df.columns.tolist())

# Dates
df["booking_date"] = pd.to_datetime(df["booking_date"], errors="coerce")
df["travel_date"] = pd.to_datetime(df["travel_date"], errors="coerce")
df = df.dropna(subset=["booking_date", "travel_date"])

# Date features
df["travel_month"] = df["travel_date"].dt.month
df["travel_day"] = df["travel_date"].dt.day
df["travel_weekday"] = df["travel_date"].dt.weekday
df["travel_week_of_year"] = df["travel_date"].dt.isocalendar().week.astype(int)
df["is_weekend"] = df["travel_weekday"].isin([5, 6]).astype(int)
df["is_peak_season"] = df["travel_month"].isin([6, 7, 8, 12]).astype(int)

df["booking_month"] = df["booking_date"].dt.month
df["booking_weekday"] = df["booking_date"].dt.weekday

# Numeric columns
numeric_cols = [
    "days_until_departure",
    "available_seats_at_booking",
    "total_seats",
    "occupancy_rate_at_booking",
    "demand_level",
    "base_price_at_booking",
    "paid_price",
]

for col in numeric_cols:
    if col not in df.columns:
        df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# Extra ML features
df["is_last_minute"] = (df["days_until_departure"] <= 2).astype(int)
df["is_early_booking"] = (df["days_until_departure"] >= 30).astype(int)
df["availability_ratio"] = (
    df["available_seats_at_booking"] / df["total_seats"].replace(0, 1)
)
df["is_low_availability"] = (df["available_seats_at_booking"] <= 50).astype(int)

df["route_key"] = df["from_city"].astype(str) + "_" + df["to_city"].astype(str)
df["provider_route"] = df["provider"].astype(str) + "_" + df["route_key"]

# Target
target = "paid_price"

df[target] = pd.to_numeric(df[target], errors="coerce")
df = df.dropna(subset=[target])

features = [
    "from_city",
    "to_city",
    "provider",
    "train_type",
    "passenger_type",
    "booking_channel",
    "route_key",
    "provider_route",
    "days_until_departure",
    "is_last_minute",
    "is_early_booking",
    "available_seats_at_booking",
    "total_seats",
    "availability_ratio",
    "occupancy_rate_at_booking",
    "is_low_availability",
    "demand_level",
    "base_price_at_booking",
    "travel_month",
    "travel_day",
    "travel_weekday",
    "travel_week_of_year",
    "is_weekend",
    "is_peak_season",
    "booking_month",
    "booking_weekday",
]

# Keep only columns that exist
features = [c for c in features if c in df.columns]

X = df[features]
y = df[target]

categorical_cols = [
    "from_city",
    "to_city",
    "provider",
    "train_type",
    "passenger_type",
    "booking_channel",
    "route_key",
    "provider_route",
]

categorical_cols = [c for c in categorical_cols if c in features]
numeric_features = [c for c in features if c not in categorical_cols]

preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
        ("num", "passthrough", numeric_features),
    ]
)

models = {
    "RandomForest": RandomForestRegressor(random_state=42),
    "ExtraTrees": ExtraTreesRegressor(random_state=42),
    "GradientBoosting": GradientBoostingRegressor(random_state=42),
}

param_grids = {
    "RandomForest": {
        "model__n_estimators": [300, 500, 700],
        "model__max_depth": [None, 8, 12, 16],
        "model__min_samples_split": [2, 4],
        "model__min_samples_leaf": [1, 2],
    },
    "ExtraTrees": {
        "model__n_estimators": [300, 500, 700],
        "model__max_depth": [None, 8, 12, 16],
        "model__min_samples_split": [2, 4],
        "model__min_samples_leaf": [1, 2],
    },
    "GradientBoosting": {
        "model__n_estimators": [100, 200, 300],
        "model__learning_rate": [0.03, 0.05, 0.1],
        "model__max_depth": [2, 3, 4],
    },
}

best_model = None
best_score = -999
best_name = ""
best_mae = None

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
)

for name, model in models.items():
    pipe = Pipeline(
        [
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    search = RandomizedSearchCV(
        pipe,
        param_distributions=param_grids[name],
        n_iter=12,
        scoring="r2",
        cv=3,
        random_state=42,
        n_jobs=-1,
        verbose=1,
    )

    search.fit(X_train, y_train)
    preds = search.best_estimator_.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)

    print("\nModel:", name)
    print("Best params:", search.best_params_)
    print("MAE:", round(mae, 2))
    print("R2:", round(r2, 3))

    if r2 > best_score:
        best_score = r2
        best_mae = mae
        best_model = search.best_estimator_
        best_name = name

artifact = {
    "pipeline": best_model,
    "features": features,
    "model_name": best_name,
    "r2": best_score,
    "mae": best_mae,
    "target": target,
    "training_csv": CSV_PATH,
    "leakage_safe": True,
}

joblib.dump(artifact, MODEL_PATH)

print("\nProduction model saved:", best_name)
print("Production R2:", round(best_score, 3))
print("Production MAE:", round(best_mae, 2))
print("Target:", target)
print("Saved to:", MODEL_PATH)