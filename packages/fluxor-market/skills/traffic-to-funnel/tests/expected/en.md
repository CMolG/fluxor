# Automated traffic analysis

## Pages: consumption (score = mean rank of views, time and 90% scroll)

| url | views | avg_time_s | scroll_90_pct | consumption_score | consumption | exit_rate | conversion_rate | signals |
|---|---|---|---|---|---|---|---|---|
| /blog/hiring-guide | 98700 | 182.7 | 58.3 | 0.905 | high | 0.801 | 0.003 | leak, no_next_step |
| /pricing | 312450 | 61.2 | 41 | 0.857 | high | 0.449 | 0.049 |  |
| / | 1234567 | 38.4 | 22.5 | 0.714 | medium | 0.415 | 0.005 |  |
| /features | 12500 | 44.1 | 30.2 | 0.667 | medium | 0.328 | 0.062 |  |
| /about | 3410 | 25 | 18.4 | 0.381 | medium | 0.601 | 0.004 |  |
| /careers | 860 | 30.5 | 12.1 | 0.333 | medium | 0.709 | 0 |  |
| /legal/privacy | 450 | 15.2 | 9.8 | 0.143 | low | 0.889 | 0 | leak |
| /old-landing | 87 | 12 | 5 | 0 | low | 0.759 | 0 | insufficient_sample |

## Leaking pages (exit rate ≥ P75 and conversion below median)

| url | views | exit_rate | scroll_90_pct | signals |
|---|---|---|---|---|
| /blog/hiring-guide | 98700 | 0.801 | 58.3 | leak, no_next_step |
| /legal/privacy | 450 | 0.889 | 9.8 | leak |

## Organic search: largest opportunity (impressions × lost CTR)

| url | query | impressions | clicks | position | ctr | expected_ctr | signals |
|---|---|---|---|---|---|---|---|
| /blog/hiring-guide | hiring guide | 125400 | 9870 | 2.1 | 0.079 | 0.15 | asset_to_defend |
| / | recruiting software | 310000 | 2480 | 11.3 | 0.008 | 0.015 | striking_distance |
| /pricing | ats for startups | 48200 | 1120 | 6.4 | 0.023 | 0.05 | striking_distance, low_ctr_for_position |
| /features | best ats | 1050 | 14 | 18.2 | 0.013 | 0.015 | striking_distance |

## URLs by organic clicks

| url | clicks | impressions | queries |
|---|---|---|---|
| /blog/hiring-guide | 9870 | 125400 | 1 |
| / | 2480 | 310000 | 1 |
| /pricing | 1120 | 48200 | 1 |
| /careers | 20 | 95 | 1 |
| /features | 14 | 1050 | 1 |

## Thresholds used

```json
{
  "min_impressions": 100,
  "pages": {
    "p25_score": 0.285,
    "p75_score": 0.75,
    "p75_exit_rate": 0.769,
    "median_conversion": 0.004
  }
}
```
