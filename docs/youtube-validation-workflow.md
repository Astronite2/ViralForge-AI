# YouTube validation workflow

1. Open **Money Opportunities**.
2. Enter a focused niche/query and region.
3. ViralForge retrieves current YouTube comparisons through the existing connector.
4. Review ranked Money Scores, confidence, evidence, effort, competition, evergreen
   strength, and clearly labelled estimate ranges.
5. Select one concept and generate its production brief.
6. Independently verify every factual research prompt and license all assets.
7. Create an outcome record before production.
8. Update the record after publication with production hours, cost, views, watch
   time, CTR, subscribers, RPM, revenue, and notes.
9. Classify the result as pending, underperformed, met expectation, or outperformed.

API analysis:

```bash
curl -X POST http://localhost:8000/api/v1/money-opportunities/analyze \
  -H 'Content-Type: application/json' \
  -d '{"query":"Ancient Egypt","region":"US","limit":25}'
```

Generate a brief with `POST /api/v1/money-opportunities/{opportunity_id}/brief`
and start tracking with
`POST /api/v1/money-opportunities/{opportunity_id}/outcome`.

Recommendation accuracy should be evaluated against the saved low/base/high view
and revenue ranges plus production-hour estimate. Track calibration rate, median
absolute view error, revenue-range coverage, ranking correlation with actual
revenue per production hour, and performance by confidence band. Do not optimize
against a single published video.

Google Trends and Reddit are not dependencies. Google may remain unavailable and
Reddit may remain disabled. There is no automatic Beat analysis; a creator starts
each run intentionally.
