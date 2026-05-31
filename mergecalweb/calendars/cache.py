from uuid import UUID


def calendar_output_cache_key(uuid: UUID | str) -> str:
    return f"calendar_str_{uuid}"


def source_data_cache_key(url: str) -> str:
    return f"calendar_data_{url}"
