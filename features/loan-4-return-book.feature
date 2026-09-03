@loans
Feature: Return a book

  As a library user
  I want to return a book I have borrowed
  So that my loan is closed and the library knows the book is back

  The return request takes a loan id and marks the loan as RETURNED.
  Only loans in status ACTIVE can be returned; the response succeeds with a
  200 OK and contains the loan id, the user id, the isbn and the status
  RETURNED. The due date stays on the loan after a return (LOAN-2). A
  RETURNED loan persists and stays queryable in its status.
  When a return succeeds, the system publishes a BookReturned event that
  carries the loan id, the user id and the isbn.
  Returning a loan that is not ACTIVE — PENDING, REJECTED or already
  RETURNED — is rejected with a 409 Conflict; the loan keeps its status
  and no BookReturned event is published.
  A loan id that does not match a stored loan is answered with a 404
  Not Found, as single-loan lookups are (LOAN-2).
  There is no penalty or overdue check in this version: a loan that is
  returned after its due date is closed exactly like an on-time one, with
  no flag, fee or other consequence recorded on the loan.
  In this version, returning a book does not change the book's available
  stock — that is assumed out of scope until the user confirms otherwise.

  Background:
    Given the loan service is running
    And the catalog service is running
    And a user with name "Anna Schmidt" and email "anna.schmidt@example.com"

  Scenario: An active loan is returned
    Given the user has a loan for the book with isbn "<isbn>" in status ACTIVE
    When the loan is returned by its loan id
    Then the request succeeds with a 200 OK
    And the response contains the loan id, the user id, the isbn "<isbn>" and the status RETURNED
    And the loan's due date is 28 days after the borrow request
    And the system publishes a BookReturned event for the loan id, the user id and the isbn "<isbn>"

  Scenarios:
    | isbn              |
    | 978-0-20-163361-0 |
    | 978-0-13-468599-1 |

  Scenario: A loan that is not active cannot be returned
    Given the user has a loan for the book with isbn "978-0-20-163361-0" in status <status>
    When the loan is returned by its loan id
    Then the request is rejected with a 409 Conflict
    And the loan is still in status <status>
    And no BookReturned event was published

  Scenarios:
    | status   |
    | PENDING  |
    | REJECTED |
    | RETURNED |

  Scenario: Returning after the due date closes the loan without penalty
    Given the user has a loan for the book with isbn "978-0-20-163361-0" in status ACTIVE with a due date 10 days ago
    When the loan is returned by its loan id
    Then the request succeeds with a 200 OK
    And the response contains the loan id, the user id, the isbn "978-0-20-163361-0" and the status RETURNED
    And the loan has no overdue flag, fee or penalty recorded
    And the system publishes a BookReturned event for the loan id, the user id and the isbn "978-0-20-163361-0"

  Scenario: A return request for an unknown loan id is rejected
    When the loan with loan id "<loan_id>" is returned
    Then the request is rejected with a 404 Not Found

  Scenarios:
    | loan_id             |
    | unknown-loan-id-1   |
    | unknown-loan-id-2   |
