# Reddit Intelligence v1

Reddit Intelligence uses only Reddit's documented Data API through OAuth. It does
not scrape HTML, use undocumented endpoints, provide an unauthenticated fallback,
or imply endorsement, sponsorship, or partnership by Reddit.

## Architecture and OAuth

`OfficialRedditProvider` owns confidential-client OAuth, in-memory token renewal,
documented post search requests, bounded retries, rate-limit metadata, and safe
typed errors. It uses the `client_credentials` grant because v1 reads public post
listings without acting as a Reddit user. Username and password settings are not
required or used by this flow.

Configure `REDDIT_ENABLED=true`, `REDDIT_PROVIDER=official`,
`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, and a descriptive
`REDDIT_USER_AGENT`. Tokens and secrets are never persisted, returned by APIs,
placed in reports, or logged. `FixtureRedditProvider` is deterministic and
test-only; application configuration rejects it. `DisabledRedditProvider` performs
no requests.

## Retrieval and normalization

V1 supports keyword post search, optional subreddit-scoped search across multiple
communities, documented sort/time filters, and limits up to 100. It ingests `t3`
posts only. Comment count is an engagement metric; comment bodies are not fetched.

Normalized fields include post ID/fullname, title, a maximum 500-character
self-text excerpt, author (or `[deleted]`), subreddit, creation time, score,
comment count, upvote ratio, awards count when present, permalink, outbound URL,
post type, NSFW/spoiler/stickied flags, query, retrieval mode, rank, provider,
provider timestamp, and available rate-limit headers. Missing metrics remain absent.

Each post produces a deterministic `Content` ID and conservative discussion signal.
The score combines only available post-level engagement inputs and retrieval rank.
It never asserts broad trend status or fabricated cross-platform corroboration.

Declared capabilities are `SEARCH`, `COMMUNITIES`, `AUTHORS`,
`ENGAGEMENT_METRICS`, `KEYWORD_MONITORING`, `TOPIC_MONITORING`, `DATE_FILTERING`,
`FORECAST_INPUT`, and `CONTENT_DISCOVERY`. V1 does not claim `COMMENTS`,
`MONETIZATION_SIGNALS`, `REALTIME`, or `HISTORICAL`.

## Runtime behavior

- `disabled`: `REDDIT_ENABLED=false`.
- `unobserved`: enabled/configured but no execution recorded.
- `active`: a recent successful run persisted at least one post.
- `degraded`: rate-limited, timed out, or temporarily unavailable.
- `unavailable`: missing/rejected OAuth credentials, forbidden access, or a
  persistent malformed/provider response.

Retries use bounded exponential backoff for timeouts, HTTP 429, and HTTP 5xx.
Permanent 4xx responses are not retried repeatedly. Failures remain isolated by the
common orchestrator.

## Privacy, retention, and deletion

Reddit API access and permitted use are externally controlled and may change.
Operators must review Reddit's current Data API Terms, Developer Terms, attribution
requirements, and approved-use conditions before enabling production access.
Stored Reddit user content must be removed when required, must not be used to train
models without the necessary rights, and must be deleted when API access terminates
where the applicable terms require it. This connector does not automate compliance
or deletion notices; production operators remain responsible for those workflows.

## Manual poll

Use `poll_reddit.delay(query="AI video generation",
subreddits=["ArtificialInteligence"], sort="hot", time_filter="week", limit=5)`
from an API container. No Beat schedule is added; scheduling should be introduced
only with an explicit monitored-query configuration.
