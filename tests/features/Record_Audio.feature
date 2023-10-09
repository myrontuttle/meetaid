Feature: Record Audio
  As a meeting participant
  I want my aid to record audio of the meeting
  So that I can have it transcribed and summarized

  Scenario: Record Audio
    Given a meeting
    When I select record
    Then the audio from my computer is recorded
