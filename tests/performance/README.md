# Performance Tests

## Status: nothing is implemented

**No performance benchmarks exist, and no performance claims are made anywhere in
this repository.** If you have read a number about latency or throughput in these
docs, it was a placeholder for a measurement that has not been taken. This file
exists so that is explicit rather than implied.

Tracked as known limitation **P5** in
[`docs/development/known-limitations.md`](../../docs/development/known-limitations.md).

## What should be measured

Write these down before writing any benchmark, so the measurement has a purpose.

| Flow | Metric | Why it matters |
| ---- | ------ | -------------- |
| `POST /analyst/query` | p50/p95 end-to-end latency | Dominated by the LLM; sets user expectation. Measure the fixed (non-provider) portion separately so provider latency does not hide our overhead |
| `run_sql` tool | p95 execution time on a representative query | Statement timeout is 5s; we want to know the margin |
| pgvector search | p95 with 10k / 100k / 1M chunks | Tells us when the HNSW parameters need tuning |
| Document processing | time per MB, per file type | Sizing for the Celery worker pool |
| Ingestion | rows/second through the chunk + embed pipeline | Embedding calls usually dominate |
| API list endpoints | p95 with 25/100 rows | Confirms indexes are used |

## How to measure it honestly

1. **Real components.** A benchmark that stubs the database measures the stub.
   Use a real Postgres with pgvector and a dataset of realistic size.
2. **Report the data set size and the query.** A latency number without those is
   meaningless.
3. **Warm up, then measure.** Cold-start JIT/connection numbers are a different
   (also useful) metric — label them.
4. **Report the distribution**, not the mean. Use p50/p95/p99; a mean hides the tail
   that users actually feel.
5. **Separate our overhead from the provider's.** An LLM call will dominate an
   analyst run; measure the parts we control.
6. **Record it in `database/docs/`** with a date, the change made and the effect.

## Suggested approach when this is picked up

- Start with the SQL validator and the API list endpoints — they are pure CPU/basic
  DB work, so there is little variance and a real signal.
- Add a seed command that generates a synthetic corpus of N documents and M rows,
  so benchmarks are reproducible (`database/seeds/`).
- Run benchmarks on a dedicated machine and record the hardware in the report.
- Add a regression guard only once the numbers are stable; a flaky perf gate is
  worse than none.

## Do not

- Do not add a performance job to CI before there is a stable baseline.
- Do not publish a number from a laptop as a product capability.
- Do not claim a speedup you have not measured against a comparable before/after.
