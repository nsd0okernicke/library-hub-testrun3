@catalog
Feature: Retrieve a single book by ISBN

  As a catalog consumer
  I want to look up a book by its ISBN
  So that I can see its full metadata and the current available stock count

  The request uses the same ISBN format as book creation: exactly 13 digits with
  hyphens allowed between the digits. No check-digit validation is applied.
  The response returns the book's stored metadata unchanged.
  A book created without a description has an empty description.

  Background:
    Given the catalog service is running

  Scenario: An existing book is returned with its full metadata and available stock
    Given a book with isbn "<isbn>", title "<title>", author "<author>", genre "<genre>", description "<description>" and initial stock <available_stock>
    When the book with isbn "<isbn>" is requested
    Then the request succeeds with a 200 OK
    And the response contains isbn "<isbn>", title "<title>", author "<author>", genre "<genre>" and description "<description>"
    And its available stock is <available_stock>

  Scenarios:
    | isbn              | title             | author              | genre     | description                    | available_stock |
    | 978-0-14-103614-3 | The Great Gatsby  | F. Scott Fitzgerald | Fiction   | A jazz-age novel about money   | 5               |
    | 978-0-06-112008-4 | 1984              | George Orwell       | Dystopian | A novel about totalitarianism  | 0               |
    | 978-0-7432-7356-5 | The Da Vinci Code | Dan Brown           | Thriller  | An art-historical thriller     | 3               |

  Scenario: A book created without a description is returned with an empty description
    Given a book with isbn "978-0-553-21316-7", title "Brave New World", author "Aldous Huxley", genre "Dystopian" and initial stock 2
    When the book with isbn "978-0-553-21316-7" is requested
    Then the request succeeds with a 200 OK
    And the response contains title "Brave New World", author "Aldous Huxley" and genre "Dystopian"
    And its available stock is 2
    And its description is empty

  Scenario: Requesting a book that does not exist is rejected
    When the book with isbn "<isbn>" is requested
    Then the request is rejected with a 404 Not Found

  Scenarios:
    | isbn              |
    | 978-0-20-163361-0 |
    | 978-0-13-468599-1 |

  Scenario: A request with an invalid isbn format is rejected
    When the book with isbn "<isbn>" is requested
    Then the request is rejected with a 400 Bad Request

  # Row notes: 978-0-14-103614 has 12 digits; 978-0-14-103614-34 has 14 digits;
  # 978-0-14-103614-X contains a letter; 0-14-103614-3 is an ISBN-10 length.
  Scenarios:
    | isbn               |
    | 978-0-14-103614    |
    | 978-0-14-103614-34 |
    | 978-0-14-103614-X  |
    | 0-14-103614-3      |
