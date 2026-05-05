Feature: Recording resilience
  A meeting that started on one input device should keep recording when the
  user swaps headphones, when AirPods drop out, or when devices reconnect
  mid-meeting. The recorder reacts to the active input device changing,
  regardless of why it changed.

  Scenario: A meeting with no device changes records cleanly
    Given no recording is in progress
    And the input device is "MacBook Mic"
    When the microphone-in-use detector reports started at time 0.0
    And the microphone-in-use detector reports ended at time 10.0
    Then 1 meeting is recorded
    And the mic track spans from 0.0 to 10.0 seconds
    And the mic session used "MacBook Mic"

  Scenario: The user swaps headphones mid-meeting
    Given no recording is in progress
    And the input device is "MacBook Mic"
    When the microphone-in-use detector reports started at time 0.0
    And the input device changes to "AirPods" at time 3.0
    And the microphone-in-use detector reports ended at time 6.0
    Then 1 meeting is recorded
    And the mic track spans from 0.0 to 6.0 seconds
    And the mic session used "MacBook Mic" then "AirPods"

  Scenario: The active device drops out and the OS falls back
    Given no recording is in progress
    And the input device is "AirPods"
    When the microphone-in-use detector reports started at time 0.0
    And the input device changes to "Built-in Mic" at time 4.0
    And the microphone-in-use detector reports ended at time 8.0
    Then 1 meeting is recorded
    And the mic session used "AirPods" then "Built-in Mic"

  Scenario: A device drops out and later returns
    Given no recording is in progress
    And the input device is "AirPods"
    When the microphone-in-use detector reports started at time 0.0
    And the input device changes to "Built-in Mic" at time 2.0
    And the input device changes to "AirPods" at time 5.0
    And the microphone-in-use detector reports ended at time 8.0
    Then the mic session used "AirPods" then "Built-in Mic" then "AirPods"

  Scenario: Both tracks share the same wall-clock window
    Given no recording is in progress
    And the input device is "MacBook Mic"
    When the microphone-in-use detector reports started at time 0.0
    And the microphone-in-use detector reports ended at time 10.0
    Then the mic track spans from 0.0 to 10.0 seconds
    And the loopback track spans from 0.0 to 10.0 seconds
