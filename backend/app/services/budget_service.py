def calculate_spend_ratio(total: float, spent: float) -> float:
    if total <= 0:
        return 0
    return round((spent / total) * 100, 2)
