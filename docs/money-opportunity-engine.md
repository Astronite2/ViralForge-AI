# Money Opportunity Engine v1

ViralForge ranks YouTube concepts by relative opportunity attractiveness. A Money
Score is not revenue, expected earnings, or a guarantee.

## Formula

The engine normalizes available factors to 0–100 and calculates a weighted sum:

| Factor | Weight |
|---|---:|
| Demand | 14% |
| Momentum | 10% |
| Competition opportunity (`100 - competition pressure`) | 10% |
| Evergreen | 10% |
| Advertiser value | 12% |
| Audience value | 8% |
| Watch-time potential | 7% |
| Click-through potential | 6% |
| Production feasibility (`100 - difficulty`) | 8% |
| Monetization safety | 7% |
| Evidence confidence | 5% |
| Channel fit | 3% |

When no channel profile exists, channel fit is absent and active weights are
renormalized. Every response contains inputs, effective weights, contributions,
evidence references, engine version, assumptions, and limitations. AI cannot change
the calculation.

Demand uses retrieved comparison views. Momentum uses upload recency and view
velocity proxies. Competition includes sample size, title similarity, recent-upload
share, and large-channel dominance. A small sample lowers confidence and never
supports a confident “low competition” claim. Evergreen considers successful older
videos, age distribution, and event-specific wording.

## Revenue ranges

View ranges require at least three retrieved YouTube comparisons and use their
25th percentile, median, and 75th percentile. Without that evidence, view and
revenue ranges are unavailable.

RPM uses explicitly stored comparable RPM observations only when at least three
exist. Otherwise it uses versioned, configurable broad-category benchmarks from
`RPM_BENCHMARKS` settings (`rpm-benchmarks-v1`). Benchmark RPM is labelled
`benchmark`; it is never described as observed. Revenue is views × RPM ÷ 1,000.

Confidence combines sample coverage, competition/longevity evidence, and whether
RPM is observed or benchmark-based. Actual results can differ because of audience
geography, seasonality, format, retention, ad inventory, channel fit, and execution.

## Safety and limitations

Monetization safety is a transparent title/query keyword screen, not a policy
decision. Manual YouTube policy review remains mandatory. Competitor results are a
retrieved sample rather than a full market census. No audience demographics,
advertiser demand, channel revenue history, RPM, or future views are fabricated.
