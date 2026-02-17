# BDD feature: Health checks (job requirement: BDD)
# Scenario: Operations team checks service health

Feature: Health
  In order to ensure the API is running
  As an operator
  I want to get health status

  Scenario: Liveness check
    When I request "GET" "/api/v1/health"
    Then the response status should be 200
    And the response body should have "status" equals "ok"

  Scenario: Readiness check
    When I request "GET" "/api/v1/health/ready"
    Then the response status should be 200
    And the response body should have "status" equals "ready"
