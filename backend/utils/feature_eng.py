def is_peak_hour(hour: int) -> int:
    return 1 if (7 <= hour <= 10) or (17 <= hour <= 20) else 0