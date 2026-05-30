# US2 A2A Validation

## Success Path

1. Trigger get_recommendations for a high-risk flight.
2. Verify outbound span includes source/target agent attributes.
3. Verify inbound A2A span is linked and marked completed.

## Failure Path

1. Stop recommendations agent and trigger get_recommendations.
2. Verify A2A span status is failed with recorded exception.

## Timeout Path

1. Send simulate-timeout phrase through recommendations flow.
2. Verify A2A span status is timeout.
