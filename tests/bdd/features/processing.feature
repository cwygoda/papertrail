Feature: Document Processing Pipeline
  As a user
  I want scanned documents to be automatically processed
  So that they are OCR'd, analyzed, and organized

  Background:
    Given a processing service with mock adapters

  Scenario: Successful PDF processing
    Given a PDF file at "/inbox/scan.pdf"
    And the OCR extracts text "Invoice from Acme Corp for $100"
    And the LLM returns document info
    When I process the document
    Then the result should be successful
    And the document should be stored
    And a sidecar file should be created

  Scenario: Non-PDF file rejected
    Given a file at "/inbox/photo.jpg"
    When I process the document
    Then the result should have error "Unsupported file type: .jpg"
    And the file should be quarantined

  Scenario: Empty document quarantined
    Given a PDF file at "/inbox/blank.pdf"
    And the OCR extracts empty text
    When I process the document
    Then the result should have error "No text extracted from document"
    And the file should be quarantined

  Scenario: Keep in place mode
    Given a PDF file at "/inbox/scan.pdf"
    And the OCR extracts text "Invoice from Acme Corp"
    And the LLM returns document info
    When I process the document with keep mode
    Then the result should be successful
    And the document should remain at the original path
