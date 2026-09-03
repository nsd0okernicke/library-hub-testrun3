@catalog
Feature: Increase book stock on BookReturned event

  As the catalog service
  I want to consume BookReturned events
  So that the available stock of a returned book increases automatically

  The loans service publishes a BookReturned event that carries the loan id,
  the user id and the isbn whenever a loan is returned (LOAN-4). For every
  BookReturned event it receives, the catalog service increases the
  available stock of the book with that isbn by exactly one. The available
  stock is the same field set at book creation (CAT-3) and read by the
  availability check (CAT-2).
  A BookReturned event whose isbn does not exist in the catalog — including
  an isbn that is not in the valid 13-digit format — is ignored: no book is
  created, no stock of any book changes, and the event is consumed without
  error so that later events for the same or for other isbns are still
  processed. Events are applied in the order they are received.

  Background:
    Given the catalog service is running
    And the message broker is running

  Scenario: A returned book gains one unit of available stock
    Given a book with isbn "<isbn>", title "<title>", author "<author>", genre "<genre>" and initial stock <initial_stock>
    When a BookReturned event for the isbn "<isbn>" is received
    Then the available stock of the book with isbn "<isbn>" is <final_stock>

  Scenarios:
    | isbn              | title             | author             | genre     | initial_stock | final_stock |
    | 978-0-14-103614-3 | The Great Gatsby  | F. Scott Fitzgerald | Fiction   | 0             | 1           |
    | 978-0-06-112008-4 | 1984              | George Orwell      | Dystopian | 5             | 6           |
    | 978-0-7432-7356-5 | The Da Vinci Code | Dan Brown          | Thriller  | 12            | 13          |

  Scenario: Each BookReturned event increases the stock by one
    Given a book with isbn "978-0-14-103614-3", title "The Great Gatsby", author "F. Scott Fitzgerald", genre "Fiction" and initial stock <initial_stock>
    When <returns> BookReturned events for the isbn "978-0-14-103614-3" are received
    Then the available stock of the book with isbn "978-0-14-103614-3" is <final_stock>

  Scenarios:
    | initial_stock | returns | final_stock |
    | 0             | 1       | 1           |
    | 2             | 3       | 5           |
    | 1             | 10      | 11          |

  Scenario: A BookReturned event for an unknown isbn changes nothing
    Given a book with isbn "978-0-14-103614-3", title "The Great Gatsby", author "F. Scott Fitzgerald", genre "Fiction" and initial stock 4
    When a BookReturned event for the isbn "<unknown_isbn>" is received
    Then the catalog contains no book with isbn "<unknown_isbn>"
    And the available stock of the book with isbn "978-0-14-103614-3" is 4

  # Row notes: 978-0-00-000000-1 and 978-0-13-468599-1 are not in the catalog;
  # 978-0-14-103614 has 12 digits and is not a valid isbn format.
  Scenarios:
    | unknown_isbn        |
    | 978-0-00-000000-1   |
    | 978-0-13-468599-1   |
    | 978-0-14-103614     |

  Scenario: Events after an ignored event are still processed
    Given a book with isbn "978-0-14-103614-3", title "The Great Gatsby", author "F. Scott Fitzgerald", genre "Fiction" and initial stock 1
    When a BookReturned event for the isbn "978-0-00-000000-1" is received
    And a BookReturned event for the isbn "978-0-14-103614-3" is received
    Then the catalog contains no book with isbn "978-0-00-000000-1"
    And the available stock of the book with isbn "978-0-14-103614-3" is 2

  Scenario: Returning a book does not change its metadata
    Given a book with isbn "978-0-06-112008-4", title "1984", author "George Orwell", genre "Dystopian" and initial stock 5
    When a BookReturned event for the isbn "978-0-06-112008-4" is received
    Then the available stock of the book with isbn "978-0-06-112008-4" is 6
    And its title is "1984" and its author is "George Orwell" and its genre is "Dystopian"
