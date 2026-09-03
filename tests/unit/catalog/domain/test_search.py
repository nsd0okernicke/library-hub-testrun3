"""Unit tests for the catalog search query value object."""

from __future__ import annotations

import pytest

from catalog.domain.exceptions import InvalidSearchParametersError
from catalog.domain.search import SearchQuery


def test_defaults_are_page_one_and_page_size_twenty() -> None:
    """A bare query searches everything from the first page with the default size."""
    query = SearchQuery()

    assert query.title is None
    assert query.author is None
    assert query.genre is None
    assert query.page == 1
    assert query.page_size == 20


def test_filters_may_be_specified_independently() -> None:
    """Any subset of the optional filters can be set."""
    query = SearchQuery(title="dune", author="herbert", genre="science")

    assert query.title == "dune"
    assert query.author == "herbert"
    assert query.genre == "science"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"page": 0}, "page"),
        ({"page": -1}, "page"),
        ({"page_size": 0}, "page size"),
        ({"page_size": -3}, "page size"),
        ({"page_size": 101}, "page size"),
    ],
)
def test_invalid_page_or_page_size_is_rejected(kwargs: dict[str, int], message: str) -> None:
    """A page below 1 or a page size outside 1..100 raises."""
    with pytest.raises(InvalidSearchParametersError, match=message):
        SearchQuery(**kwargs)


def test_page_and_page_size_at_the_bounds_are_accepted() -> None:
    """Page 1 and page size 1..100 are valid."""
    assert SearchQuery(page=1, page_size=1).page_size == 1
    assert SearchQuery(page_size=100).page_size == 100
