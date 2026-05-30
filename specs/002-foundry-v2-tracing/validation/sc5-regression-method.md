# SC-005 Regression-Rate Comparison Method

## Baseline Window

- 7 days pre-change

## Post-Change Window

- 7 days post-change

## Metric

- User-visible conversation failure rate attributable to tracing changes

## Calculation

failure_rate = failed_conversations / total_conversations
regression_pct = ((post_rate - pre_rate) / pre_rate) * 100

Pass criterion: regression_pct <= 5
