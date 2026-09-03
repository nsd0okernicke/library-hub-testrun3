"""Unit tests for the SearchBooks use case with a fake repository."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from catalog.application.search_books import SearchBooks
from catalog.domain.book import Book
from catalog.domain.exceptions import InvalidSearchParametersError
from catalog.domain.isbn import Isbn
from catalog.domain.search import SearchQuery, SearchResult
from tests.unit.catalog.fakes import InMemoryBooks


def make_book(isbn: str, title: str, author: str, genre: str) -> Book:
    """Build a book with default stock and description."""
    return Book(isbn=Isbn(isbn), title=title, author=author, genre=genre, available_stock=1)


def seed_catalog() -> InMemoryBooks:
    """Store the scenario books, deliberately out of title order."""
    repo = InMemoryBooks()
    asyncio.run(
        repo.save(make_book("978-0-441-17271-9", "Dune", "Frank Herbert", "Science Fiction"))
    )
    asyncio.run(repo.save(make_book("978-0-201-48567-7", "Refactoring", "Martin Fowler", "Craft")))
    asyncio.run(
        repo.save(make_book("978-0-547-92822-7", "The Hobbit", "J.R.R. Tolkien", "Fantasy"))
    )
    return repo


def search(repo: InMemoryBooks, **kwargs: Any) -> SearchResult:
    """Run the use case with the given query parameters."""
    return asyncio.run(SearchBooks(repo).execute(SearchQuery(**kwargs)))


def titles(result: SearchResult) -> list[str]:
    """Extract the result titles in order."""
    return [book.title for book in result.items]


def test_unfiltered_search_returns_every_book_sorted_by_title_then_isbn() -> None:
    """A bare search returns all books ordered by title, ties by ISBN."""
    result = search(seed_catalog())

    assert titles(result) == ["Dune", "Refactoring", "The Hobbit"]
    assert result.total == 3


def test_title_filter_matches_case_insensitive_substring() -> None:
    """A title filter matches any book whose title contains it, ignoring case."""
    repo = seed_catalog()

    assert titles(search(repo, title="dune")) == ["Dune"]
    assert titles(search(repo, title="HOBBIT")) == ["The Hobbit"]


def test_author_and_genre_filters_match_case_insensitive_substrings() -> None:
    """Author and genre filters behave like the title filter."""
    repo = seed_catalog()

    assert titles(search(repo, author="herbert")) == ["Dune"]
    assert titles(search(repo, author="TOLKIEN")) == ["The Hobbit"]
    assert titles(search(repo, genre="science")) == ["Dune"]
    assert titles(search(repo, genre="fantasy")) == ["The Hobbit"]


def test_substring_filter_matching_several_books_returns_all_of_them() -> None:
    """A short filter that fits several titles returns every match."""
    result = search(seed_catalog(), title="e")

    assert titles(result) == ["Dune", "Refactoring", "The Hobbit"]
    assert result.total == 3


def test_filters_combine_with_and() -> None:
    """A book must match every specified filter."""
    assert titles(search(seed_catalog(), title="the", author="tolkien")) == ["The Hobbit"]


def test_unmatchable_filter_combination_returns_empty_result_with_zero_total() -> None:
    """Filters that cannot match together yield no books and total 0."""
    result = search(seed_catalog(), title="hobbit", author="herbert")

    assert titles(result) == []
    assert result.total == 0


def test_title_ties_broken_by_isbn_digits() -> None:
    """Books with the same title are ordered by their 13-digit ISBN."""
    repo = InMemoryBooks()
    asyncio.run(repo.save(make_book("978-1-56619-909-4", "Moby-Dick", "H. Melville", "Adventure")))
    asyncio.run(
        repo.save(make_book("978-0-14-041488-8", "Moby-Dick", "Herman Melville", "Classic"))
    )

    assert titles(search(repo)) == ["Moby-Dick", "Moby-Dick"]
    isbn_order = [book.isbn.digits for book in search(repo).items]
    assert isbn_order == ["9780140414888", "9781566199094"]


def test_pagination_splits_the_result_set() -> None:
    """Pages carve the sorted result set into page-size slices."""
    repo = seed_catalog()

    assert titles(search(repo, page=1, page_size=1)) == ["Dune"]
    assert titles(search(repo, page=2, page_size=1)) == ["Refactoring"]
    assert titles(search(repo, page=3, page_size=1)) == ["The Hobbit"]
    assert titles(search(repo, page=1, page_size=2)) == ["Dune", "Refactoring"]
    assert titles(search(repo, page=2, page_size=2)) == ["The Hobbit"]


def test_total_counts_every_match_not_just_the_current_page() -> None:
    """The total reflects the full match count, regardless of paging."""
    assert search(seed_catalog(), page=2, page_size=1).total == 3


def test_page_beyond_the_last_returns_empty_items_with_total_unchanged() -> None:
    """A page past the end is empty but still reports the total."""
    result = search(seed_catalog(), page=4, page_size=1)

    assert titles(result) == []
    assert result.total == 3


def test_result_reports_the_page_and_page_size_it_was_given() -> None:
    """The result echoes the pagination values applied to it."""
    result = search(seed_catalog(), page=3, page_size=100)

    assert result.page == 3
    assert result.page_size == 100


def test_filtered_search_paginates_the_matches_not_the_whole_catalog() -> None:
    """Paging applies to the filtered subset."""
    repo = seed_catalog()
    asyncio.run(repo.save(make_book("978-0-14-044913-6", "Emma", "Jane Austen", "Fiction")))
    asyncio.run(
        repo.save(make_book("978-0-679-74656-8", "Pride and Prejudice", "Jane Austen", "Fiction"))
    )

    first = search(repo, author="austen", page=1, page_size=1)
    second = search(repo, author="austen", page=2, page_size=1)
    assert titles(first) == ["Emma"]
    assert titles(second) == ["Pride and Prejudice"]
    assert first.total == 2
    assert second.total == 2


@pytest.mark.parametrize(
    "kwargs", [{"page": 0}, {"page": -1}, {"page_size": 0}, {"page_size": 101}]
)
def test_invalid_pagination_is_rejected(kwargs: dict[str, int]) -> None:
    """Invalid page or page size raises before any lookup happens."""
    with pytest.raises(InvalidSearchParametersError):
        search(seed_catalog(), **kwargs)
