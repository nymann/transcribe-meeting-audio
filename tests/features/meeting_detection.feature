Feature: Meeting detection
  Recording starts and stops in response to the universal "microphone in use"
  signal, regardless of which app opened the input. The active call app, when
  recognised, labels the resulting meeting.

  Scenario: Recording starts when any app opens the microphone
    Given no recording is in progress
    And the input device is "Built-in Mic"
    When the microphone-in-use detector reports started at time 0.0
    And the microphone-in-use detector reports ended at time 5.0
    Then 1 meeting is recorded
    And the mic track is finalized
    And the loopback track is finalized

  Scenario: A detected Teams meeting is labelled "Teams"
    Given no recording is in progress
    And the input device is "Built-in Mic"
    And "Teams" is the running call app
    When the microphone-in-use detector reports started at time 0.0
    And the microphone-in-use detector reports ended at time 5.0
    Then meeting 1 is labelled "Teams"

  Scenario: A meeting with no recognised app is labelled "Unknown"
    Given no recording is in progress
    And the input device is "Built-in Mic"
    And no call app is running
    When the microphone-in-use detector reports started at time 0.0
    And the microphone-in-use detector reports ended at time 5.0
    Then meeting 1 is labelled "Unknown"

  Scenario: Two back-to-back meetings produce two recordings
    Given no recording is in progress
    And the input device is "Built-in Mic"
    When the microphone-in-use detector reports started at time 0.0
    And the microphone-in-use detector reports ended at time 5.0
    And the microphone-in-use detector reports started at time 15.0
    And the microphone-in-use detector reports ended at time 20.0
    Then 2 meetings are recorded

  Scenario: Brief microphone toggling does not split a meeting
    Given no recording is in progress
    And the input device is "Built-in Mic"
    When the microphone-in-use detector reports started at time 0.0
    And the microphone-in-use detector reports ended at time 3.0
    And the microphone-in-use detector reports started at time 4.0
    And the microphone-in-use detector reports ended at time 8.0
    Then 1 meeting is recorded
