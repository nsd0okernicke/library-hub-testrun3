@loans
Feature: View single loan status

  As a library user
  I want to look up a loan by its loan id
  So that I can see its current status and, once it is active, its due date

  The request takes a loan id and returns the single loan record.
  Loan ids are opaque, system-generated identifiers; the retrieve endpoint
  applies no format validation, so any id that does not match a stored loan
  is answered with a 404 Not Found.
  The response contains the loan id, the user id, the isbn, the status and
  the due date. A loan is PENDING from the moment it is requested, ACTIVE
  once its reservation is fulfilled, REJECTED when the reservation is
  rejected, and RETURNED after it has been returned. The due date is set
  when the reservation is fulfilled — the request date plus the global loan
  term of 28 days — and it stays on the loan after a return. PENDING and
  REJECTED loans therefore have no due date; ACTIVE and RETURNED loans do.
  Rejected and returned loans persist and stay queryable in their status.

  Background:
    Given the loan service is running
    And the catalog service is running
    And a user with name "Anna Schmidt" and email "anna.schmidt@example.com"

  Scenario: An existing loan is returned with its details
    Given the user has a loan for the book with isbn "<isbn>" in status <status>
    When the loan is requested by its loan id
    Then the request succeeds with a 200 OK
    And the response contains the loan id, the user id, the isbn "<isbn>" and the status <status>
    And its due date is <due_date>

  Scenarios:
    | isbn              | status   | due_date                         |
    | 978-0-20-163361-0 | PENDING  | absent                           |
    | 978-0-20-163361-0 | ACTIVE   | 28 days after the borrow request |
    | 978-0-13-468599-1 | REJECTED | absent                           |
    | 978-0-13-468599-1 | RETURNED | 28 days after the borrow request |

  Scenario: A loan request for an unknown loan id is rejected
    When the loan with loan id "<loan_id>" is requested
    Then the request is rejected with a 404 Not Found

  Scenarios:
    | loan_id             |
    | unknown-loan-id-1   |
    | unknown-loan-id-2   |
