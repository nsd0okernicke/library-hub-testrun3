@loans
Feature: Borrow a book

  As a library user
  I want to request to borrow a book by its ISBN
  So that my loan is registered and, once the stock is reserved, I get a due date

  The borrow request takes a user id and an isbn and is answered immediately.
  It succeeds with a 202 Accepted as soon as the loan record exists in status
  PENDING — the reservation of stock happens later, out of band.
  The isbn must be in the same format as book creation: exactly 13 digits with
  hyphens allowed between the digits. No check-digit validation is applied.
  When the reservation is fulfilled, the loan becomes ACTIVE with a due date
  that is the request date plus the global loan term of 28 days, and the book's
  available stock decreases by one. The 28-day term is a single global
  configuration value; it is not overridable per borrow request.
  When the reservation is rejected, the loan record persists in status REJECTED
  with no due date, stays queryable, and the book's available stock is
  unchanged.
  There is no limit on concurrent active loans per user, and a user may borrow
  an ISBN for which they already hold an active loan.

  Background:
    Given the loan service is running
    And the catalog service is running
    And a user with name "Anna Schmidt" and email "anna.schmidt@example.com"

  Scenario: A borrow request for an available book is accepted and then fulfilled
    Given a book with isbn "<isbn>" and initial stock <stock>
    When the user requests to borrow the book with isbn "<isbn>"
    Then the request succeeds with a 202 Accepted
    And the response contains a system-generated loan id, the user id, the isbn "<isbn>" and the status PENDING
    When the reservation for the book with isbn "<isbn>" is fulfilled
    Then the loan is in status ACTIVE
    And the loan's due date is 28 days after the borrow request
    And the available stock of the book with isbn "<isbn>" is one less than <stock>

  Scenarios:
    | isbn              | stock |
    | 978-0-20-163361-0 | 3     |
    | 978-0-13-468599-1 | 1     |

  Scenario: A borrow request for an unavailable book is accepted and then rejected
    Given a book with isbn "<isbn>" and initial stock 0
    When the user requests to borrow the book with isbn "<isbn>"
    Then the request succeeds with a 202 Accepted
    And the response contains a system-generated loan id, the user id, the isbn "<isbn>" and the status PENDING
    When the reservation for the book with isbn "<isbn>" is rejected
    Then the loan is in status REJECTED
    And the loan has no due date
    And the loan remains queryable in status REJECTED
    And the available stock of the book with isbn "<isbn>" is unchanged at 0

  Scenarios:
    | isbn              |
    | 978-0-20-163361-0 |
    | 978-0-13-468599-1 |

  Scenario: A user may hold several active loans at once
    Given a book with isbn "<isbn_first>" and initial stock 5
    And a book with isbn "<isbn_second>" and initial stock 5
    And the user has an active loan for the book with isbn "<isbn_first>"
    When the user requests to borrow the book with isbn "<isbn_second>"
    Then the request succeeds with a 202 Accepted
    And the response contains a system-generated loan id, the user id, the isbn "<isbn_second>" and the status PENDING
    When the reservation for the book with isbn "<isbn_second>" is fulfilled
    Then the loan is in status ACTIVE
    And the user has an active loan for the book with isbn "<isbn_first>" and another active loan for the book with isbn "<isbn_second>"

  # Row notes: the first row borrows the same ISBN the user already holds.
  Scenarios:
    | isbn_first          | isbn_second         |
    | 978-0-20-163361-0   | 978-0-20-163361-0   |
    | 978-0-20-163361-0   | 978-0-13-468599-1   |

  Scenario: A borrow request for an unknown user is rejected
    Given a book with isbn "978-0-20-163361-0" and initial stock 5
    When a borrow request is made for the book with isbn "978-0-20-163361-0" for a user id that does not exist
    Then the request is rejected with a 404 Not Found
    And no loan was created
    And the available stock of the book with isbn "978-0-20-163361-0" is unchanged at 5

  Scenario: A borrow request with invalid data is rejected
    When a borrow request is made where <problem>
    Then the request is rejected with a 400 Bad Request
    And no loan was created

  # Row notes: 978-0-14-103614 has 12 digits; 978-0-14-103614-34 has 14 digits;
  # 978-0-14-103614-X contains a letter.
  Scenarios:
    | problem                                            |
    | the user id is missing                             |
    | the isbn is missing                                |
    | the isbn "978-0-14-103614" has 12 digits           |
    | the isbn "978-0-14-103614-34" has 14 digits        |
    | the isbn "978-0-14-103614-X" contains a letter     |
