def humanize_seconds(total: int) -> str:
    if total <= 0:
        return "expired"

    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return f"{seconds}s"
