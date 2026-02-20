# Retry & Resilience

Building fault-tolerant applications with retry policies, timeouts, and resilience patterns.

## Schedule Basics

Schedules define retry/repeat policies:

```typescript
import { Schedule, Effect } from "effect";

// Fixed number of retries
const threeRetries = Schedule.recurs(3);

// Fixed delay between retries
const oneSecondDelay = Schedule.spaced("1 second");

// Exponential backoff
const exponential = Schedule.exponential("100 millis");

// Apply to effect
effect.pipe(Effect.retry(threeRetries));
```

## Decision Tree

```
What retry behavior?
├─ Fixed count → Schedule.recurs(n)
├─ Fixed delay → Schedule.spaced(duration)
├─ Exponential backoff → Schedule.exponential(base)
├─ Combine strategies
│  ├─ Both must pass → Schedule.intersect
│  └─ Either passes → Schedule.union
├─ Add limits
│  ├─ Max retries → Schedule.compose(Schedule.recurs(n))
│  ├─ Max duration → Schedule.upTo(duration)
│  └─ Until condition → Schedule.recurUntil(pred)
├─ Add jitter → Schedule.jittered
└─ Custom logic → Schedule.recurWhile / Schedule.check
```

## Common Schedules

### Fixed retry count

```typescript
// Retry up to 3 times
const policy = Schedule.recurs(3);

effect.pipe(Effect.retry(policy));
// Tries: 1 (original) + 3 (retries) = 4 total attempts
```

### Fixed delay

```typescript
// Wait 1 second between retries
const policy = Schedule.spaced("1 second");

effect.pipe(Effect.retry(policy));
// Retries forever with 1s gap
```

### Exponential backoff

```typescript
// 100ms, 200ms, 400ms, 800ms, ...
const policy = Schedule.exponential("100 millis");

// With cap (don't exceed 10 seconds)
const cappedPolicy = Schedule.exponential("100 millis").pipe(
  Schedule.either(Schedule.spaced("10 seconds")),
);
```

### Combined: Exponential with max retries

```typescript
// Exponential backoff, but max 5 retries
const policy = Schedule.exponential("100 millis").pipe(
  Schedule.compose(Schedule.recurs(5)),
);

// Alternative syntax
const policy2 = Schedule.intersect(
  Schedule.exponential("100 millis"),
  Schedule.recurs(5),
);
```

### With jitter (recommended for distributed systems)

```typescript
// Adds randomness to prevent thundering herd
const policy = Schedule.exponential("100 millis").pipe(
  Schedule.jittered,
  Schedule.compose(Schedule.recurs(5)),
);
```

## Applying Retry Policies

### Effect.retry

```typescript
const resilientFetch = fetchData(url).pipe(
  Effect.retry(
    Schedule.exponential("100 millis").pipe(
      Schedule.compose(Schedule.recurs(3)),
    ),
  ),
);
```

### Effect.retryWhile

```typescript
// Retry while error matches condition
const resilientFetch = fetchData(url).pipe(
  Effect.retryWhile(
    (error) =>
      error._tag === "NetworkError" ||
      (error._tag === "ApiError" && error.status >= 500),
  ),
);
```

### Effect.retryN

```typescript
// Simple: retry exactly N times
const resilientFetch = fetchData(url).pipe(Effect.retryN(3));
```

### Retry with custom logic

```typescript
const resilientFetch = fetchData(url).pipe(
  Effect.retry({
    schedule: Schedule.exponential("100 millis"),
    while: (error) => isRetryable(error),
    times: 5,
  }),
);
```

## Timeouts

### Effect.timeout

```typescript
// Fail if takes longer than 5 seconds
const withTimeout = effect.pipe(Effect.timeout("5 seconds"));
// Returns Option<A> - None if timed out

// With custom timeout error
const withTimeoutError = effect.pipe(
  Effect.timeoutFail({
    duration: "5 seconds",
    onTimeout: () => new TimeoutError({ operation: "fetch" }),
  }),
);
```

### Combining timeout and retry

```typescript
// Each attempt has 5s timeout, total 3 retries
const resilient = fetchData(url).pipe(
  Effect.timeout("5 seconds"),
  Effect.retry(Schedule.recurs(3)),
);

// Total operation timeout (across all retries)
const resilient2 = fetchData(url).pipe(
  Effect.retry(Schedule.recurs(3)),
  Effect.timeout("30 seconds"),
);
```

## Resilience Patterns

### Circuit breaker

```typescript
const makeCircuitBreaker = <A, E>(
  maxFailures: number,
  resetTimeout: Duration.DurationInput,
) =>
  Effect.gen(function* () {
    const state = yield* Ref.make<{
      failures: number;
      lastFailure: Option.Option<number>;
      status: "closed" | "open" | "half-open";
    }>({ failures: 0, lastFailure: Option.none(), status: "closed" });

    return <R>(effect: Effect.Effect<A, E, R>) =>
      Effect.gen(function* () {
        const current = yield* Ref.get(state);

        // Check if circuit is open
        if (current.status === "open") {
          const elapsed =
            Date.now() - Option.getOrElse(current.lastFailure, () => 0);
          if (elapsed < Duration.toMillis(resetTimeout)) {
            return yield* Effect.fail(new CircuitOpenError() as any);
          }
          yield* Ref.update(state, (s) => ({ ...s, status: "half-open" }));
        }

        return yield* effect.pipe(
          Effect.tap(() =>
            Ref.set(state, {
              failures: 0,
              lastFailure: Option.none(),
              status: "closed",
            }),
          ),
          Effect.tapError(() =>
            Ref.update(state, (s) => {
              const failures = s.failures + 1;
              return {
                failures,
                lastFailure: Option.some(Date.now()),
                status: failures >= maxFailures ? "open" : s.status,
              };
            }),
          ),
        );
      });
  });

// Usage
const circuitBreaker = yield * makeCircuitBreaker(5, "30 seconds");
const protectedCall = circuitBreaker(apiCall());
```

### Bulkhead (concurrency limit)

```typescript
// Limit concurrent API calls
const bulkhead = Effect.gen(function* () {
  const semaphore = yield* Effect.makeSemaphore(10);

  return <A, E, R>(effect: Effect.Effect<A, E, R>) =>
    semaphore.withPermits(1)(effect);
});

// Usage
const limitedCall = bulkhead.flatMap((protect) =>
  Effect.forEach(urls, (url) => protect(fetch(url)), {
    concurrency: "unbounded",
  }),
);
```

### Retry with fallback

```typescript
const resilientFetch = (url: string) =>
  fetchFromPrimary(url).pipe(
    Effect.retry(Schedule.recurs(2)),
    Effect.orElse(() =>
      fetchFromSecondary(url).pipe(Effect.retry(Schedule.recurs(2))),
    ),
    Effect.orElse(() => fetchFromCache(url)),
    Effect.orElseSucceed(() => defaultValue),
  );
```

### Hedged requests (race multiple attempts)

```typescript
// Send request, if no response in 200ms, send another
const hedgedFetch = (url: string) =>
  Effect.race(
    fetchData(url),
    Effect.sleep("200 millis").pipe(Effect.andThen(fetchData(url))),
  );
```

## Schedule Composition

### Schedule.intersect - Both must pass

```typescript
// Exponential backoff AND max 5 retries
const policy = Schedule.intersect(
  Schedule.exponential("100 millis"),
  Schedule.recurs(5),
);
```

### Schedule.union - Either passes

```typescript
// Retry on either schedule
const policy = Schedule.union(Schedule.spaced("1 second"), Schedule.recurs(3));
```

### Schedule.compose - Sequential

```typescript
// First exponential, then fixed delay
const policy = Schedule.compose(
  Schedule.exponential("100 millis").pipe(Schedule.take(3)),
  Schedule.spaced("10 seconds"),
);
```

### Schedule.andThen - After first completes

```typescript
// 3 quick retries, then slower retries
const policy = Schedule.recurs(3).pipe(
  Schedule.andThen(Schedule.spaced("10 seconds").pipe(Schedule.take(5))),
);
```

## Logging and Observability

```typescript
const withRetryLogging = <A, E, R>(effect: Effect.Effect<A, E, R>) =>
  effect.pipe(
    Effect.tapError((e) => Effect.log(`Attempt failed: ${e}`)),
    Effect.retry(
      Schedule.exponential("100 millis").pipe(
        Schedule.compose(Schedule.recurs(3)),
        Schedule.tapOutput((attempt) => Effect.log(`Retry attempt ${attempt}`)),
      ),
    ),
    Effect.tapBoth({
      onSuccess: () => Effect.log("Operation succeeded"),
      onFailure: (e) =>
        Effect.logError("Operation failed after all retries", e),
    }),
  );
```

## Complete Example

```typescript
// Resilient API client with all patterns
const createResilientClient = Effect.gen(function* () {
  const semaphore = yield* Effect.makeSemaphore(10);
  const circuitBreaker = yield* makeCircuitBreaker(5, "30 seconds");

  const retryPolicy = Schedule.exponential("100 millis").pipe(
    Schedule.jittered,
    Schedule.compose(Schedule.recurs(3)),
  );

  return {
    fetch: <A>(url: string, schema: Schema.Schema<A>) =>
      fetchData(url).pipe(
        // Per-request timeout
        Effect.timeout("5 seconds"),
        // Retry transient failures
        Effect.retry({
          schedule: retryPolicy,
          while: (e) => isTransientError(e),
        }),
        // Circuit breaker
        circuitBreaker,
        // Concurrency limit
        semaphore.withPermits(1),
        // Validate response
        Effect.flatMap(Schema.decodeUnknown(schema)),
        // Total timeout including retries
        Effect.timeout("30 seconds"),
        // Logging
        Effect.tapError((e) => Effect.logWarning(`API call failed: ${url}`, e)),
      ),
  };
});
```
