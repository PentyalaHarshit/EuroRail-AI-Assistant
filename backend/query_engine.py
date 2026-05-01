import re
import pandas as pd

CSV_PATH = "data/euro_rail_realistic_200_routes.csv"


def load_data():
    df = pd.read_csv(CSV_PATH)
    df = df.fillna("")

    # Normalize text columns
    for col in ["from_city", "to_city", "provider", "journey_type", "wifi", "status"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # If provider has +, treat journey as connection
    if "provider" in df.columns and "journey_type" in df.columns:
        df["journey_type"] = df.apply(
            lambda row: "Connection"
            if "+" in str(row.get("provider", ""))
            else row.get("journey_type", ""),
            axis=1,
        )

    return df


def normalize(text):
    return str(text).strip().lower()


def to_number(value, default=999999):
    try:
        if value == "" or str(value).lower() in ["nan", "none", "na"]:
            return default
        return float(value)
    except Exception:
        return default


def duration_to_minutes(duration):
    try:
        text = normalize(duration).replace(" ", "")
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
        return 999999


def extract_route(query, df):
    q = normalize(query)

    cities = sorted(
        set(df["from_city"].astype(str).tolist() + df["to_city"].astype(str).tolist()),
        key=len,
        reverse=True,
    )

    from_city = ""
    to_city = ""

    match = re.search(r"from\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+)", q)

    if match:
        raw_from = match.group(1).strip()
        raw_to = match.group(2).strip()

        for city in cities:
            if normalize(city) in raw_from:
                from_city = city
                break

        for city in cities:
            if normalize(city) in raw_to:
                to_city = city
                break

    if not from_city or not to_city:
        found = []
        for city in cities:
            if normalize(city) in q:
                found.append(city)

        if len(found) >= 1:
            from_city = found[0]
        if len(found) >= 2:
            to_city = found[1]

    return from_city, to_city


def extract_date(query):
    match = re.search(r"\d{4}-\d{2}-\d{2}", query)
    if match:
        return match.group(0)
    return ""


def rank_trains(rows, sort_by="best", passenger_type="regular"):
    def price(row):
        if passenger_type == "senior":
            return to_number(row.get("senior_price"))
        if passenger_type == "youth":
            return to_number(row.get("youth_price"))
        if passenger_type == "child":
            return to_number(row.get("child_price"))
        return to_number(row.get("base_price"))

    def seats(row):
        return int(to_number(row.get("available_seats"), 0))

    def delay(row):
        return int(to_number(row.get("delay_minutes"), 0))

    def duration(row):
        return duration_to_minutes(row.get("duration", ""))

    if sort_by == "cheapest":
        return sorted(rows, key=price)

    if sort_by == "fastest":
        return sorted(rows, key=duration)

    if sort_by == "available":
        return sorted(rows, key=lambda r: seats(r), reverse=True)

    if sort_by == "least_delay":
        return sorted(rows, key=delay)

    return sorted(rows, key=lambda r: (price(r), duration(r), delay(r), -seats(r)))


def search_trains_structured(
    from_city="",
    to_city="",
    date="",
    provider="",
    direct_only=False,
    wifi=False,
    available_only=False,
    sort_by="best",
    passenger_type="regular",
    limit=20,
):
    df = load_data()

    if from_city:
        df = df[df["from_city"].str.lower() == from_city.strip().lower()]

    if to_city:
        df = df[df["to_city"].str.lower() == to_city.strip().lower()]

    # STRICT DATE FILTER
    if date:
        df = df[df["date"].astype(str).str.strip() == date.strip()]

    if provider:
        df = df[df["provider"].str.contains(provider.strip(), case=False, na=False)]

    if direct_only:
        df = df[
            (df["journey_type"].str.lower() == "direct")
            & (~df["provider"].str.contains("\\+", na=False))
        ]

    if wifi:
        df = df[df["wifi"].str.lower().isin(["yes", "available"])]

    if available_only:
        df = df[
            (pd.to_numeric(df["available_seats"], errors="coerce").fillna(0) > 0)
            & (df["status"].str.lower() == "available")
        ]

    rows = df.to_dict(orient="records")
    rows = rank_trains(rows, sort_by=sort_by, passenger_type=passenger_type)

    return rows[:limit]


def search_similar_routes(from_city="", limit=5):
    df = load_data()

    if from_city:
        df = df[df["from_city"].str.lower() == from_city.strip().lower()]

    return df.to_dict(orient="records")[:limit]


def search_trains(query: str, k: int = 8):
    q = normalize(query)
    df = load_data()

    from_city, to_city = extract_route(query, df)
    date = extract_date(query)

    provider = ""
    providers = [
        "SNCF+DB",
        "Eurostar+DB",
        "SNCF",
        "DB",
        "Eurostar",
        "Renfe",
        "Trenitalia",
        "SBB",
        "ÖBB",
        "Italo",
        "NS",
        "SNCB",
    ]

    for p in providers:
        if p.lower() in q:
            provider = p
            break

    passenger_type = "regular"
    if "senior" in q or "senior citizen" in q:
        passenger_type = "senior"
    elif "youth" in q or "student" in q:
        passenger_type = "youth"
    elif "child" in q or "kid" in q:
        passenger_type = "child"

    sort_by = "best"

    if "cheapest" in q or "cheap" in q or "lowest price" in q:
        sort_by = "cheapest"
    elif "fastest" in q or "quickest" in q:
        sort_by = "fastest"
    elif "delay" in q:
        sort_by = "least_delay"
    elif "available seats" in q or "most seats" in q:
        sort_by = "available"

    direct_only = "direct" in q
    wifi = "wifi" in q

    # Be careful: "available" should not force only seat filtering for all query types
    available_only = False
    if "available only" in q or "with seats" in q:
        available_only = True

    rows = search_trains_structured(
        from_city=from_city,
        to_city=to_city,
        date=date,
        provider=provider,
        direct_only=direct_only,
        wifi=wifi,
        available_only=available_only,
        sort_by=sort_by,
        passenger_type=passenger_type,
        limit=k,
    )

    context = ""

    if not rows:
        context = (
            f"No exact train found"
            f"{f' from {from_city}' if from_city else ''}"
            f"{f' to {to_city}' if to_city else ''}"
            f"{f' on {date}' if date else ''}"
            f"{f' with provider {provider}' if provider else ''}."
        )
        return context, []

    for i, row in enumerate(rows, start=1):
        context += f"\n--- Train {i} ---\n"
        for key, value in row.items():
            context += f"{key}: {value}\n"

    return context, rows


if __name__ == "__main__":
    context, rows = search_trains(
        "is SNCF available from paris to lyon on 2026-05-01",
        k=5,
    )

    print("Rows found:", len(rows))
    print(context)