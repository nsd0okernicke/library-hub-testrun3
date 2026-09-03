@catalog
Feature: Search books by title, author and genre with pagination

  As a catalog consumer
  I want to search the catalog by title, author or genre
  So that I can find books and step through long result sets one page at a time

  A search accepts optional filters for title, author and genre. A specified
  filter matches when the book's field contains the filter text as a
  case-insensitive substring, and a book is returned only when it matches
  every specified filter. A filter that is not specified is ignored, so a
  search without filters returns every book.
  The result set is sorted by title ascending; books with the same title are
  ordered by isbn ascending.
  Results are paginated with a 1-indexed page and a page size that defaults
  to 20 and must not exceed 100. The response reports the page, the page
  size actually applied, and the total number of matching books, where the
  total counts every match, not only the books on the current page. A page
  beyond the last matching page returns an empty result list with the total
  count unchanged. Each result entry carries the book's full metadata, in
  the same shape as single-book retrieval by ISBN.

  Background:
    Given the catalog service is running
    And the catalog is pre-seeded with:
      | isbn              | title        | author          | genre           |
      | 978-0-441-17271-9 | Dune         | Frank Herbert   | Science Fiction |
      | 978-0-201-48567-7 | Refactoring  | Martin Fowler   | Craft           |
      | 978-0-547-92822-7 | The Hobbit   | J.R.R. Tolkien  | Fantasy         |

  Scenario: A search without filters returns every book
    When the catalog is searched
    Then the request succeeds with a 200 OK
    And the result list contains exactly "Dune", "Refactoring" and "The Hobbit" in this order
    And the total count is 3
    And the response reports page 1 and page size 20

  Scenario: A filter matches case-insensitively as a substring
    When the catalog is searched with <field> "<text>"
    Then the request succeeds with a 200 OK
    And the result list contains exactly "<book>"
    And the total count is 1

  Scenarios:
    | field  | text    | book       |
    | title  | dune    | Dune       |
    | title  | HOBBIT  | The Hobbit |
    | author | herbert | Dune       |
    | author | TOLKIEN | The Hobbit |
    | genre  | science | Dune       |
    | genre  | fantasy | The Hobbit |

  Scenario: A filter matching several books returns all of them
    When the catalog is searched with title "e"
    Then the request succeeds with a 200 OK
    And the result list contains exactly "Dune", "Refactoring" and "The Hobbit" in this order
    And the total count is 3

  Scenario: Several filters combine with AND
    When the catalog is searched with title "the" and author "tolkien"
    Then the request succeeds with a 200 OK
    And the result list contains exactly "The Hobbit"
    And the total count is 1

  Scenario: Filters that cannot match together return no books
    When the catalog is searched with title "hobbit" and author "herbert"
    Then the request succeeds with a 200 OK
    And the result list is empty
    And the total count is 0

  Scenario: A filter matching no book returns an empty result
    When the catalog is searched with genre "Thriller"
    Then the request succeeds with a 200 OK
    And the result list is empty
    And the total count is 0

  Scenario: A result set is split into pages
    When the catalog is searched with page <page> and page size <page_size>
    Then the request succeeds with a 200 OK
    And the result list contains exactly <titles>
    And the total count is 3
    And the response reports page <page> and page size <page_size>

  Scenarios:
    | page | page_size | titles                       |
    | 1    | 1         | "Dune"                       |
    | 2    | 1         | "Refactoring"                |
    | 3    | 1         | "The Hobbit"                 |
    | 1    | 2         | "Dune", "Refactoring"        |
    | 2    | 2         | "The Hobbit"                 |

  Scenario: A page beyond the last matching page returns no books
    When the catalog is searched with page 4 and page size 1
    Then the request succeeds with a 200 OK
    And the result list is empty
    And the total count is 3
    And the response reports page 4 and page size 1

  Scenario: The maximum page size is accepted
    When the catalog is searched with page 1 and page size 100
    Then the request succeeds with a 200 OK
    And the result list contains exactly "Dune", "Refactoring" and "The Hobbit" in this order
    And the total count is 3
    And the response reports page 1 and page size 100

  Scenario: A page or page size outside the valid range is rejected
    When the catalog is searched where <problem>
    Then the request is rejected with a 400 Bad Request

  Scenarios:
    | problem              |
    | the page is 0        |
    | the page is -1       |
    | the page size is 0   |
    | the page size is -3  |
    | the page size is 101 |
