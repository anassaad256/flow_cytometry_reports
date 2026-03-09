"""Tests for output transformers."""
from src.models import MainLineItem
from src.transformers import deduplicate_markers, markers_to_display, sort_main_line_items


def test_deduplicate_markers():
    lists = [["M_CD14", "M_CD13"], ["M_CD13", "M_CD33"]]
    assert deduplicate_markers(lists) == ["M_CD14", "M_CD13", "M_CD33"]


def test_deduplicate_empty():
    assert deduplicate_markers([]) == []
    assert deduplicate_markers([[]]) == []


def test_markers_to_display():
    catalogs = [
        {"M_CD14": {"display": "CD14"}, "M_CD13": {"display": "CD13"}},
        {"M_CD33": {"display": "CD33"}},
    ]
    result = markers_to_display(["M_CD14", "M_CD33", "M_UNKNOWN"], catalogs)
    assert result == "CD14, CD33, M_UNKNOWN"


def test_sort_main_line_items():
    items = [
        MainLineItem(text="low_priority", finding_priority=500, selection_order=0),
        MainLineItem(text="high_priority", finding_priority=100, selection_order=0),
        MainLineItem(text="same_priority_later", finding_priority=100, selection_order=1),
    ]
    result = sort_main_line_items(items)
    assert result == ["high_priority", "same_priority_later", "low_priority"]
