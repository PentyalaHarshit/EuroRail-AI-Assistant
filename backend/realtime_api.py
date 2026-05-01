import requests

DB_STATION_IDS = {
    "berlin": "8011160",
    "frankfurt": "8000105",
    "munich": "8000261",
    "hamburg": "8002549",
    "cologne": "8000207",
}


def get_db_departures(city: str, results: int = 5):
    station_id = DB_STATION_IDS.get(city.lower())

    if not station_id:
        return {
            "available": False,
            "message": "No real-time station mapping available for this city.",
            "departures": [],
        }

    try:
        url = f"https://v6.db.transport.rest/stops/{station_id}/departures"
        params = {"duration": 60, "results": results}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        departures = []

        for item in data.get("departures", []):
            departures.append(
                {
                    "line": item.get("line", {}).get("name"),
                    "direction": item.get("direction"),
                    "planned_when": item.get("plannedWhen"),
                    "actual_when": item.get("when"),
                    "delay": item.get("delay"),
                    "platform": item.get("platform"),
                    "cancelled": item.get("cancelled", False),
                }
            )

        return {"available": True, "station_id": station_id, "departures": departures}

    except Exception as e:
        return {"available": False, "message": str(e), "departures": []}