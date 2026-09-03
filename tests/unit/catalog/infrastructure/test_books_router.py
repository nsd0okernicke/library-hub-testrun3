"""Unit tests for the catalog HTTP API (POST /books) with a fake repository."""

from starlette.testclient import TestClient

from catalog.domain.ports import BookRepository
from catalog.infrastructure.api.main import create_app
from tests.unit.catalog.fakes import InMemoryBooks


def make_client(repo: BookRepository) -> TestClient:
    """Build a TestClient around the catalog app wired to the given repo."""
    return TestClient(create_app(repo))


def test_create_book_returns_201_and_book() -> None:
    repo = InMemoryBooks()
    client = make_client(repo)

    response = client.post(
        "/books",
        json={
            "isbn": "978-0-14-103614-3",
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "genre": "Fiction",
            "initial_stock": 5,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["isbn"] == "978-0-14-103614-3"
    assert body["title"] == "The Great Gatsby"
    assert body["author"] == "F. Scott Fitzgerald"
    assert body["genre"] == "Fiction"
    assert body["available_stock"] == 5
    assert len(repo.books) == 1


def test_create_book_without_description_stores_empty_string() -> None:
    repo = InMemoryBooks()
    client = make_client(repo)

    client.post(
        "/books",
        json={
            "isbn": "978-0-06-112008-4",
            "title": "1984",
            "author": "George Orwell",
            "genre": "Dystopian",
            "initial_stock": 0,
        },
    )

    assert list(repo.books.values())[0].description == ""


def test_create_book_with_description_stores_it() -> None:
    repo = InMemoryBooks()
    client = make_client(repo)

    response = client.post(
        "/books",
        json={
            "isbn": "978-0-553-21316-7",
            "title": "Brave New World",
            "author": "Aldous Huxley",
            "genre": "Dystopian",
            "initial_stock": 3,
            "description": "A satire of a dystopian future",
        },
    )

    assert response.status_code == 201
    assert response.json()["description"] == "A satire of a dystopian future"


def test_duplicate_isbn_returns_409() -> None:
    repo = InMemoryBooks()
    client = make_client(repo)
    payload = {
        "isbn": "978-0-20-163361-0",
        "title": "Dune",
        "author": "Frank Herbert",
        "genre": "Sci-Fi",
        "initial_stock": 2,
    }

    assert client.post("/books", json=payload).status_code == 201
    response = client.post("/books", json=payload)

    assert response.status_code == 409
    assert len(repo.books) == 1


def test_invalid_isbn_returns_400() -> None:
    repo = InMemoryBooks()
    client = make_client(repo)

    response = client.post(
        "/books",
        json={
            "isbn": "978-0-14-103614",
            "title": "Test Book",
            "author": "Test Author",
            "genre": "Fiction",
            "initial_stock": 1,
        },
    )

    assert response.status_code == 400
    assert len(repo.books) == 0


def test_missing_title_returns_400() -> None:
    repo = InMemoryBooks()
    client = make_client(repo)

    response = client.post(
        "/books",
        json={
            "isbn": "978-0-20-163361-0",
            "author": "Frank Herbert",
            "genre": "Sci-Fi",
            "initial_stock": 1,
        },
    )

    assert response.status_code == 400
    assert len(repo.books) == 0


def test_negative_stock_returns_400() -> None:
    repo = InMemoryBooks()
    client = make_client(repo)

    response = client.post(
        "/books",
        json={
            "isbn": "978-0-20-163361-0",
            "title": "Dune",
            "author": "Frank Herbert",
            "genre": "Sci-Fi",
            "initial_stock": -1,
        },
    )

    assert response.status_code == 400
    assert len(repo.books) == 0
