@catalog
Feature: Manually add copies to a book's available stock

  As a catalog operator
  I want to add a given number of copies to a book's available stock directly
  So that I can correct stock drift, register new acquisitions and recover
  from missed BookReturned events

  The stock increase is a manual operator action on the catalog service.
  It requires no loan record and no BookReturned event, and it behaves the
  same whether or not a loan for the book exists — it is not the user-facing
  return flow (LOAN-4). The request names an isbn and a number of copies.
  The isbn must use the same format as book creation (CAT-3): exactly
  13 digits with hyphens allowed between the digits, no check-digit
  validation. The number of copies must be a positive integer.
  The available stock of an existing book increases by exactly the number
  of requested copies; the book's other metadata is unchanged.
  A stock increase for an isbn that does not exist in the catalog is
  rejected: no book is created and the stock of no book changes.
  Consistent with the other operator endpoints, no authentication applies.

  Background:
    Given the catalog service is running

  Scenario: Copies are added to the available stock of an existing book
    Given a book with isbn "<isbn>", title "<title>", author "<author>", genre "<genre>" and initial stock <initial_stock>
    When <copies> copies are added to the stock of the book with isbn "<isbn>"
    Then the request succeeds with a 200 OK
    And the available stock of the book with isbn "<isbn>" is <final_stock>
    And its title is "<title>" and its author is "<author>" and its genre is "<genre>"

  Scenarios:
    | isbn              | title             | author              | genre     | initial_stock | copies | final_stock |
    | 978-0-14-103614-3 | The Great Gatsby  | F. Scott Fitzgerald | Fiction   | 0             | 1      | 1           |
    | 978-0-06-112008-4 | 1984              | George Orwell       | Dystopian | 5             | 3      | 8           |
    | 978-0-7432-7356-5 | The Da Vinci Code | Dan Brown           | Thriller  | 12            | 10     | 22          |

  Scenario: The stock increase works without any loan for the book
    Given a book with isbn "978-0-14-103614-3", title "The Great Gatsby", author "F. Scott Fitzgerald", genre "Fiction" and initial stock 2
    And no loan for isbn "978-0-14-103614-3" exists
    When 4 copies are added to the stock of the book with isbn "978-0-14-103614-3"
    Then the request succeeds with a 200 OK
    And the available stock of the book with isbn "978-0-14-103614-3" is 6

  Scenario: A stock increase for an unknown isbn is rejected
    Given a book with isbn "978-0-14-103614-3", title "The Great Gatsby", author "F. Scott Fitzgerald", genre "Fiction" and initial stock 4
    When 2 copies are added to the stock of the book with isbn "<isbn>"
    Then the request is rejected with a 404 Not Found
    And the catalog contains no book with isbn "<isbn>"
    And the available stock of the book with isbn "978-0-14-103614-3" is 4

  Scenarios:
    | isbn              |
    | 978-0-20-163361-0 |
    | 978-0-13-468599-1 |

  Scenario: A stock increase with an invalid isbn format is rejected
    When <copies> copies are added to the stock of the book with isbn "<isbn>"
    Then the request is rejected with a 400 Bad Request
    And no book was added to the catalog

  # Row notes: 978-0-14-103614 has 12 digits; 978-0-14-103614-34 has 14 digits;
  # 978-0-14-103614-X contains a letter; 0-14-103614-3 is an ISBN-10 length.
  Scenarios:
    | isbn               | copies |
    | 978-0-14-103614    | 2      |
    | 978-0-14-103614-34 | 2      |
    | 978-0-14-103614-X  | 2      |
    | 0-14-103614-3      | 2      |

  Scenario: A stock increase with a non-positive number of copies is rejected
    Given a book with isbn "978-0-14-103614-3", title "The Great Gatsby", author "F. Scott Fitzgerald", genre "Fiction" and initial stock 4
    When <copies> copies are added to the stock of the book with isbn "978-0-14-103614-3"
    Then the request is rejected with a 400 Bad Request
    And the available stock of the book with isbn "978-0-14-103614-3" is 4

  Scenarios:
    | copies |
    | 0      |
    | -3     |
