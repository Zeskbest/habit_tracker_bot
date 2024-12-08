import datetime
from datetime import timedelta
from io import BytesIO

import matplotlib.pyplot as plt

from db import get_logs


def fetch_logs(series_name: str, tg_id: int, period: str):
    """Fetch logs for a series within a time range"""
    logs = get_logs(series_name, tg_id, period)

    # Group timestamps for plotting
    if period == "weekday":
        # Distribution by weekday
        data = {day: 0 for day in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]}
        for log in logs:
            data[log.strftime("%a")] += 1
    else:
        # Linear distribution over time
        start_time = min(logs) if logs else datetime.datetime.now()
        end_time = max(logs) if logs else datetime.datetime.now()
        interval = {
            "day": timedelta(hours=1),
            "week": timedelta(days=1),
            "month": timedelta(days=7),
            "year": timedelta(weeks=4),
            "all": max(timedelta(seconds=1), (end_time - start_time) / 50),  # Max 50 points
        }[period]

        data = []
        current_time = start_time
        while current_time <= end_time:
            data.append((current_time, sum(1 for log in logs if current_time <= log < current_time + interval)))
            current_time += interval

    return data


def generate_graph(series_name:str, tg_id:int, period:str):
    """Generate and return a graph"""
    data = fetch_logs(series_name,tg_id, period)
    if not data:
        return None

    plt.figure(figsize=(10, 6))

    if period == "weekday":
        # Weekday graph (Sun-Sat on x-axis)
        days, counts = zip(*data.items())
        plt.bar(days, counts, color="blue", alpha=0.7)
        plt.xlabel("Weekday")
        plt.ylabel("Count")
        plt.title(f"Weekday Distribution for '{series_name}'")
    else:
        # Linear time distribution graph
        timestamps, counts = zip(*data)
        plt.plot(timestamps, counts, marker="o", linestyle="-", color="blue")
        plt.xlabel(f"Time ({period.capitalize()})")
        plt.ylabel("Count")
        plt.title(f"Activity Distribution for '{series_name}' ({period.capitalize()})")
        plt.grid(True)

    plt.xticks(rotation=45)
    plt.tight_layout()

    # return the graph
    bio = BytesIO()
    plt.savefig(bio, format="png")
    bio.seek(0)
    return bio.read()
