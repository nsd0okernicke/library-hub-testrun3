@catalog
Feature: Check book availability by ISBN

  As a catalog consumer such as the Loan Service
  I want to check the current available count of a book by its ISBN
  So that I can perform a cheap availability check without retrieving full metadata

  The request uses the same ISBN format as book creation: exactly 13 digits with
  hyphens allowed between the digits. No check-digit validation is applied.
  The response contains only the two fields isbn and available_count — no title,
  author, genre or description.

  Background:
    Given the catalog service is running

  Scenario: An existing book is returned with its isbn and available stock
    Given a book with isbn "<isbn>", title "<title>", author "<author>", genre "<genre>" and initial stock <available_stock>
    When the availability of the book with isbn "<isbn>" is requested
    Then the request succeeds with a 200 OK
    And the response contains only isbn "<isbn>" and available stock <available_stock>
    And the response contains no title, author, genre or description

  Scenarios:
    | isbn              | title             | author             | genre     | available_stock |
    | 978-0-14-103614-3 | The Great Gatsby  | F. Scott Fitzgerald | Fiction   | 5               |
    | 978-0-06-112008-4 | 1984              | George Orwell      | Dystopian | 0               |
    | 978-0-7432-7356-5 | The Da Vinci Code | Dan Brown          | Thriller  | 1               |

  Scenario: Checking availability of a book that does not exist is rejected
    When the availability of the book with isbn "<isbn>" is requested
    Then the request is rejected with a 404 Not Found

  Scenarios:
    | isbn              |
    | 978-0-20-163361-0 |
    | 978-0-13-468599-1 |

  Scenario: A request with an invalid isbn format is rejected
    When the availability of the book with isbn "<isbn>" is requested
    Then the request is rejected with a 400 Bad Request

  # Row notes: 978-0-14-103614 has 12 digits; 978-0-14-103614-34 has 14 digits;
  # 978-0-14-103614-X contains a letter; 0-14-103614-3 is an ISBN-10 length.
  Scenarios:
    | isbn              |
    | 978-0-14-103614   |
    | 978-0-14-103614-34 |
    | 978-0-14-103614-X |
    | 0-14-103614-3     |
