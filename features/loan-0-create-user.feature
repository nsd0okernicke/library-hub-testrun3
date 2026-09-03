@loans
Feature: Create a user account

  As a library member
  I want to register an account with my name and email
  So that I can borrow books

  The system generates the user_id; the client does not provide it.
  No password or authentication is part of the account.
  The email is the unique identity of an account: two accounts may not
  share an email.
  An email is in a valid format when it consists of a non-empty local part,
  an @ sign and a non-empty domain.

  Background:
    Given the users service is running

  Scenario: A user is created from name and email
    When a user is requested with name "<name>" and email "<email>"
    Then the request succeeds with a 201 Created
    And the response contains the name "<name>", the email "<email>" and a system-generated user id
    And a user with email "<email>" exists in the system

  Scenarios:
    | name         | email                   |
    | Anna Schmidt | anna.schmidt@example.com |
    | Ben Mueller  | ben.mueller@example.com |
    | Carla Rossi  | carla@rossi.example.net |

  Scenario: A new account gets a different user id from an existing one
    Given a user with email "anna.schmidt@example.com" already exists
    When a user is requested with name "Ben Mueller" and email "ben.mueller@example.com"
    Then the request succeeds with a 201 Created
    And the new user's user id is different from the existing user's user id

  Scenario: Creating a user with an existing email is rejected
    Given a user with email "<email>" already exists
    When a user is requested with name "<name>" and email "<email>"
    Then the request is rejected with a 409 Conflict
    And exactly one user with email "<email>" exists in the system

  Scenarios:
    | name         | email                   |
    | Anna Reiter  | anna.schmidt@example.com |
    | Ben Zweiter  | ben.mueller@example.com |

  Scenario: A user request with invalid data is rejected
    When a user is requested where <problem>
    Then the request is rejected with a 400 Bad Request
    And no user was added to the system

  Scenarios:
    | problem                                       |
    | the name is missing                           |
    | the name is empty                             |
    | the email is missing                          |
    | the email is "plainaddress" without an @ sign |
    | the email is "@example.com" without a local part |
    | the email is "user@" without a domain         |
