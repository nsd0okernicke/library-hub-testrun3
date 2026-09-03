@catalog
Feature: Create a new book in the catalog

  As a catalog operator
  I want to register a book with its metadata and initial stock
  So that it can be searched, retrieved and lent out

  An ISBN is in a valid format when it consists of exactly 13 digits,
  with hyphens allowed between the digits. No check-digit validation is applied.
  A book request without description is equivalent to one with an empty description.

  Background:
    Given the catalog service is running

  Scenario: A book is created from valid metadata and initial stock
    When a book is requested with isbn "<isbn>", title "<title>", author "<author>", genre "<genre>" and initial stock <initial_stock>
    Then the request succeeds with a 201 Created
    And a book with isbn "<isbn>" exists in the catalog
    And its title is "<title>" and its author is "<author>" and its genre is "<genre>"
    And its available stock is <initial_stock>

  Scenarios:
    | isbn              | title             | author             | genre         | initial_stock |
    | 978-0-14-103614-3 | The Great Gatsby  | F. Scott Fitzgerald | Fiction      | 5             |
    | 978-0-06-112008-4 | 1984              | George Orwell      | Dystopian     | 0             |
    | 978-0-7432-7356-5 | The Da Vinci Code | Dan Brown          | Thriller      | 1             |

  Scenario: An optional description is stored with the book
    When a book is requested with isbn "<isbn>", title "<title>", author "<author>", genre "<genre>", initial stock 3 and description "<description>"
    Then the request succeeds with a 201 Created
    And a book with isbn "<isbn>" exists in the catalog
    And its description is "<description>"

  Scenarios:
    | isbn              | title           | author        | genre     | description                          |
    | 978-0-553-21316-7 | Brave New World | Aldous Huxley | Dystopian | A satire of a dystopian future       |
    | 978-0-14-044792-9 | Animal Farm     | George Orwell | Allegory  | A novella about farm animals rebelling |

  Scenario: Creating a book with an existing isbn is rejected
    Given a book with isbn "<isbn>" already exists in the catalog
    When a book is requested with isbn "<isbn>"
    Then the request is rejected with a 409 Conflict
    And the catalog contains exactly one book with isbn "<isbn>"

  Scenarios:
    | isbn              |
    | 978-0-20-163361-0 | # pre-seeded book (Dune)       |
    | 978-0-13-468599-1 | # pre-seeded book (Refactoring) |

  Scenario: A book request with an invalid isbn format is rejected
    When a book is requested with isbn "<isbn>", title "Test Book", author "Test Author", genre "Fiction" and initial stock 1
    Then the request is rejected with a 400 Bad Request
    And no book was added to the catalog

  Scenarios:
    | isbn             |
    | 978-0-14-103614   | # 12 digits          |
    | 978-0-14-103614-34 | # 14 digits         |
    | 978-0-14-103614-X | # letter, not digit  |
    | 0-14-103614-3     | # ISBN-10 length     |

  Scenario: A book request with invalid required data is rejected
    When a book is requested where <problem>
    Then the request is rejected with a 400 Bad Request
    And no book was added to the catalog

  Scenarios:
    | problem                                  |
    | the title is missing                     |
    | the author is missing                    |
    | the genre is missing                     |
    | the initial stock is negative (-1)       |
