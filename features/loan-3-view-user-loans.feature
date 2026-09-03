@loans
Feature: View all loans for a user

  As a library user
  I want to see all my loans, newest first, one page at a time
  So that I can keep track of what I have borrowed and what is still due

  The request takes the user id and is paginated with the same scheme as
  the catalog search: a 1-indexed page that defaults to 1 and a page size
  that defaults to 20 and must not exceed 100. The response reports the
  page, the page size actually applied, and the total count, where the
  total counts every loan of the user, not only the loans on the current
  page.
  The loans are sorted by created_at descending — newest first. If two
  loans share the same created_at, either order of the two is acceptable.
  Only the requested user's loans are returned. All four statuses appear:
  PENDING, ACTIVE, REJECTED and RETURNED — rejected and returned loans
  persist and stay queryable (LOAN-1, LOAN-2), so they are never filtered
  out of the list.
  Each result entry contains the loan id, the user id, the isbn, the
  status, the due date and the created_at. PENDING and REJECTED loans have
  no due date; ACTIVE and RETURNED loans keep it (LOAN-2).
  A page beyond the last matching page returns an empty result list with
  the total count unchanged. A user that exists but has no loans gets an
  empty list with total 0. A request for a user id that does not exist is
  answered with a 404 Not Found, as borrow requests are (LOAN-1).

  Background:
    Given the loan service is running
    And the catalog service is running
    And a user with name "Anna Schmidt" and email "anna.schmidt@example.com"

  Scenario: The user's loans are listed newest first in all four statuses
    Given the user has a loan for the book with isbn "978-0-20-163361-0" in status REJECTED created at 2026-01-04T09:00:00
    And the user has a loan for the book with isbn "978-0-13-468599-1" in status ACTIVE created at 2026-01-05T09:00:00
    And the user has a loan for the book with isbn "978-0-42-104410-0" in status PENDING created at 2026-01-06T09:00:00
    And the user has a loan for the book with isbn "978-0-67-977354-9" in status RETURNED created at 2026-01-07T09:00:00
    When the user's loans are requested
    Then the request succeeds with a 200 OK
    And the result list contains exactly "978-0-67-977354-9", "978-0-42-104410-0", "978-0-13-468599-1" and "978-0-20-163361-0" in this order
    And the total count is 4
    And the response reports page 1 and page size 20
    And each result entry contains the loan id, the user id, the isbn, the status, the due date and the created_at
    And the ACTIVE and RETURNED loans have a due date while the PENDING and REJECTED loans have none

  Scenario: A user's loan list does not include other users' loans
    Given the user has a loan for the book with isbn "978-0-20-163361-0" in status ACTIVE created at 2026-01-05T09:00:00
    And a user with name "Ben Meyer" and email "ben.meyer@example.com"
    And the user "Ben Meyer" has a loan for the book with isbn "978-0-13-468599-1" in status ACTIVE created at 2026-01-07T09:00:00
    When the user's loans are requested
    Then the request succeeds with a 200 OK
    And the result list contains exactly "978-0-20-163361-0"
    And the total count is 1

  Scenario: A result set is split into pages
    Given the user has a loan for the book with isbn "978-0-20-163361-0" in status REJECTED created at 2026-01-04T09:00:00
    And the user has a loan for the book with isbn "978-0-13-468599-1" in status ACTIVE created at 2026-01-05T09:00:00
    And the user has a loan for the book with isbn "978-0-42-104410-0" in status PENDING created at 2026-01-06T09:00:00
    And the user has a loan for the book with isbn "978-0-67-977354-9" in status RETURNED created at 2026-01-07T09:00:00
    When the user's loans are requested with page <page> and page size <page_size>
    Then the request succeeds with a 200 OK
    And the result list contains exactly <isbns> in this order
    And the total count is 4
    And the response reports page <page> and page size <page_size>

    # Newest first: 978-0-67-977354-9 (01-07), 978-0-42-104410-0 (01-06),
    # 978-0-13-468599-1 (01-05), 978-0-20-163361-0 (01-04).
    Scenarios:
      | page | page_size | isbns                                                                                                       |
      | 1    | 1         | "978-0-67-977354-9"                                                                                        |
      | 2    | 1         | "978-0-42-104410-0"                                                                                        |
      | 3    | 1         | "978-0-13-468599-1"                                                                                        |
      | 4    | 1         | "978-0-20-163361-0"                                                                                        |
      | 1    | 2         | "978-0-67-977354-9", "978-0-42-104410-0"                                                                   |
      | 1    | 100       | "978-0-67-977354-9", "978-0-42-104410-0", "978-0-13-468599-1", "978-0-20-163361-0"                        |

  Scenario: A page beyond the last matching page returns no loans
    Given the user has a loan for the book with isbn "978-0-20-163361-0" in status ACTIVE created at 2026-01-05T09:00:00
    When the user's loans are requested with page 2 and page size 1
    Then the request succeeds with a 200 OK
    And the result list is empty
    And the total count is 1
    And the response reports page 2 and page size 1

  Scenario: A user without loans gets an empty list
    When the user's loans are requested
    Then the request succeeds with a 200 OK
    And the result list is empty
    And the total count is 0
    And the response reports page 1 and page size 20

  Scenario: A loan list request for an unknown user id is rejected
    When the loans of the user with user id "<user_id>" are requested
    Then the request is rejected with a 404 Not Found

    Scenarios:
      | user_id           |
      | unknown-user-id-1 |
      | unknown-user-id-2 |

  Scenario: A page or page size outside the valid range is rejected
    When the user's loans are requested where <problem>
    Then the request is rejected with a 400 Bad Request

    Scenarios:
      | problem              |
      | the page is 0        |
      | the page is -1       |
      | the page size is 0   |
      | the page size is -3  |
      | the page size is 101 |
