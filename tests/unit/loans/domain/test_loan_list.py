"""Unit tests for the LoanListQuery pagination value object."""

from __future__ import annotations

import dataclasses

import pytest

from loans.domain.exceptions import InvalidLoanListParametersError
from loans.domain.loan_list import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    LoanListQuery,
    LoanListResult,
)


@pytest.mark.parametrize(
    ("page", "page_size"),
    [
        (0, 20),
        (-1, 20),
        (1, 0),
        (1, -3),
        (1, 101),
        (2, 200),
    ],
)
def test_query_rejects_out_of_range_pagination(page: int, page_size: int) -> None:
    """Page and page size outside the valid range are rejected."""
    with pytest.raises(InvalidLoanListParametersError):
        LoanListQuery(user_id="user-1", page=page, page_size=page_size)


@pytest.mark.parametrize(
    ("page", "page_size"),
    [
        (1, 20),
        (1, 1),
        (1, 100),
        (4, 2),
        (7, 50),
    ],
)
def test_query_accepts_in_range_pagination(page: int, page_size: int) -> None:
    """Page >= 1 and 1 <= page size <= 100 are accepted and remembered."""
    query = LoanListQuery(user_id="user-1", page=page, page_size=page_size)

    assert query.page == page
    assert query.page_size == page_size


def test_query_defaults_match_the_catalog_search_scheme() -> None:
    """Default page is 1 and default page size is 20, as in the catalog search."""
    query = LoanListQuery(user_id="user-1")

    assert query.page == DEFAULT_PAGE == 1
    assert query.page_size == DEFAULT_PAGE_SIZE == 20
    assert MAX_PAGE_SIZE == 100


def test_query_rejects_an_empty_user_id() -> None:
    """An empty user id names no user and is invalid list data."""
    with pytest.raises(InvalidLoanListParametersError):
        LoanListQuery(user_id="")


def test_query_is_immutable() -> None:
    """LoanListQuery is a frozen value object; its fields cannot be reassigned."""
    query = LoanListQuery(user_id="user-1")

    with pytest.raises(dataclasses.FrozenInstanceError):
        query.page = 2  # type: ignore[misc]


def test_result_defaults_to_an_empty_page() -> None:
    """A result without items reports an empty first page with total 0."""
    result = LoanListResult()

    assert result.items == []
    assert result.total == 0
    assert result.page == DEFAULT_PAGE
    assert result.page_size == DEFAULT_PAGE_SIZE
