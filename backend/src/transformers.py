"""Main-tree transformers for output assembly."""
from __future__ import annotations

from .models import MainLineItem


def deduplicate_markers(marker_lists: list[list[str]]) -> list[str]:
    """Merge and deduplicate marker ID lists preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for markers in marker_lists:
        for m in markers:
            if m not in seen:
                seen.add(m)
                result.append(m)
    return result


def markers_to_display(marker_ids: list[str], panel_catalogs: list[dict]) -> str:
    """Convert marker IDs to display names using merged panel catalogs."""
    merged_catalog: dict[str, str] = {}
    for catalog in panel_catalogs:
        for mid, info in catalog.items():
            if mid not in merged_catalog:
                merged_catalog[mid] = info.get("display", mid)
    display_names = [merged_catalog.get(mid, mid) for mid in marker_ids]
    return ", ".join(display_names)


def sort_main_line_items(items: list[MainLineItem]) -> list[str]:
    """Sort main line items by finding_priority ascending, then selection_order."""
    sorted_items = sorted(items, key=lambda x: (x.finding_priority, x.selection_order))
    return [item.text for item in sorted_items]
