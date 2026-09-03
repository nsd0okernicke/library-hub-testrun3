@loans
Feature: View overdue loans (admin)

  As a library administrator
  I want to see all loans that are still active but past their due date
  So that I can follow up on books that have not been returned

  A loan is overdue when it is ACTIVE and its due date lies strictly before
  the current time. A loan whose due date has not yet passed is not overdue.
  Loans in any other status never appear in the list: PENDING and REJECTED
  loans have no due date (LOAN-1), and a RETURNED loan keeps its due date but
  is no longer borrowed, so it drops out of the list on return even if the
  due date has passed (LOAN-4).
  The list spans all users — it is an administrative view, not filtered to a
  single user.
  The endpoint requires no authentication: the MVP has no access control.
  The response is a single list of all overdue loans — no pagination in the
  MVP. The loans are sorted by due date ascending, most overdue first. If
  two loans share the same due date, either order of the two is acceptable.
  Each entry contains the loan id, the user id, the isbn, the status, the
  due date and the created_at.

  Background:
    Given the loan service is running
    And the catalog service is running
    And a user with name "Anna Schmidt" and email "anna.schmidt@example.com"

  Scenario: An active loan past its due date is listed
    Given the user has a loan for the book with isbn "<isbn>" in status ACTIVE whose due date is <days_overdue> days before the current time
    When the overdue loans are requested
    Then the request succeeds with a 200 OK
    And the result list contains exactly "<isbn>"
    And the entry for "<isbn>" contains the loan id, the user id, the isbn "<isbn>", the status ACTIVE, the due date and the created_at

  Scenarios:
    | isbn              | days_overdue |
    | 978-0-20-163361-0 | 1            |
    | 978-0-13-468599-1 | 10           |

  Scenario: Only overdue loans appear among the other loan states
    Given the user has a loan for the book with isbn "978-0-20-163361-0" in status ACTIVE whose due date is 3 days before the current time
    And the user has a loan for the book with isbn "978-0-13-468599-1" in status ACTIVE whose due date is 5 days after the current time
    And the user has a loan for the book with isbn "978-0-42-104410-0" in status RETURNED whose due date is 3 days before the current time
    And the user has a loan for the book with isbn "978-0-67-977354-9" in status PENDING
    And the user has a loan for the book with isbn "978-0-55-338211-6" in status REJECTED
    When the overdue loans are requested
    Then the request succeeds with a 200 OK
    And the result list contains exactly "978-0-20-163361-0"

  Scenario: The overdue list spans all users and is sorted by due date ascending
    Given the user has a loan for the book with isbn "978-0-20-163361-0" in status ACTIVE whose due date is 2 days before the current time
    And a user with name "Ben Meyer" and email "ben.meyer@example.com"
    And the user "Ben Meyer" has a loan for the book with isbn "978-0-13-468599-1" in status ACTIVE whose due date is 9 days before the current time
    And the user has a loan for the book with isbn "978-0-42-104410-0" in status ACTIVE whose due date is 5 days before the current time
    When the overdue loans are requested
    Then the request succeeds with a 200 OK
    And the result list contains exactly "978-0-13-468599-1", "978-0-42-104410-0" and "978-0-20-163361-0" in this order
    And the entry for "978-0-13-468599-1" belongs to the user "Ben Meyer"

  Scenario: Without overdue loans the list is empty
    Given the user has a loan for the book with isbn "978-0-20-163361-0" in status ACTIVE whose due date is 20 days after the current time
    When the overdue loans are requested
    Then the request succeeds with a 200 OK
    And the result list is empty
