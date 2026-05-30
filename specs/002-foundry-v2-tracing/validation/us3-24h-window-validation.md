# 24-Hour Review Window Validation

## Validation Criteria

- Coverage query functions clamp to a minimum 24-hour window.
- Dashboard summary reports the effective window.
- Queries return deterministic output for values below 24h.

## Test Cases

- Requested 1h -> effective 24h
- Requested 12h -> effective 24h
- Requested 48h -> effective 48h
