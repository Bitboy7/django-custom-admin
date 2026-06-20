def safe_file_url(file_field):
    """Return a usable FileField URL only when the referenced file exists."""
    if not file_field:
        return ""

    name = getattr(file_field, "name", "")
    if not name or str(name).lower() == "none":
        return ""

    try:
        storage = getattr(file_field, "storage", None)
        if storage and not storage.exists(name):
            return ""
        return file_field.url or ""
    except Exception:
        return ""
