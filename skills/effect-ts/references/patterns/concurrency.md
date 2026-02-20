# Concurrency & Parallelism

Parallel execution, fibers, and concurrent patterns in Effect.

## Parallel Execution Basics

### Effect.all - Parallel by default

```typescript
// Run all in parallel, collect results
const results =
  yield * Effect.all([fetchUser(id), fetchPosts(id), fetchSettings(id)]);
// [User, Post[], Settings]

// Object syntax (named results)
const { user, posts } =
  yield *
  Effect.all({
    user: fetchUser(id),
    posts: fetchPosts(id),
  });
```

### Concurrency options

```typescript
// Unbounded parallelism (default for arrays, controlled for objects)
const results = yield * Effect.all(effects, { concurrency: "unbounded" });

// Limited concurrency
const results = yield * Effect.all(effects, { concurrency: 5 });

// Sequential
const results = yield * Effect.all(effects, { concurrency: 1 });

// Inherit from parent fiber
const results = yield * Effect.all(effects, { concurrency: "inherit" });
```

### Effect.forEach - Map with concurrency

```typescript
// Process all users in parallel
const results =
  yield * Effect.forEach(userIds, (id) => processUser(id), { concurrency: 10 });

// Discard results (side effects only)
yield *
  Effect.forEach(users, (user) => sendEmail(user), {
    concurrency: 5,
    discard: true,
  });
```

## Racing Effects

### Effect.race - First to complete wins

```typescript
// First successful response wins, others canceled
const fastest =
  yield * Effect.race([fetchFromPrimaryServer(id), fetchFromBackupServer(id)]);
```

### Effect.raceAll - Race many effects

```typescript
const first =
  yield *
  Effect.raceAll([
    fetchFromServer1(id),
    fetchFromServer2(id),
    fetchFromServer3(id),
  ]);
```

### Effect.raceWith - Custom race handling

```typescript
const result = yield* Effect.raceWith(
  effectA,
  effectB,
  {
    onSelfDone: (exitA, fiberB) => /* A finished first */,
    onOtherDone: (exitB, fiberA) => /* B finished first */
  }
)
```

## Fibers

Fibers are lightweight threads managed by Effect.

### Effect.fork - Background execution

```typescript
const program = Effect.gen(function* () {
  // Fork background task
  const fiber = yield* Effect.fork(backgroundTask);

  // Continue with main work
  const mainResult = yield* mainWork();

  // Wait for background task
  const backgroundResult = yield* Fiber.join(fiber);

  return { mainResult, backgroundResult };
});
```

### Fiber.interrupt - Cancel fiber

```typescript
const program = Effect.gen(function* () {
  const fiber = yield* Effect.fork(longRunningTask);

  // Do some work
  yield* Effect.sleep("5 seconds");

  // Cancel if still running
  yield* Fiber.interrupt(fiber);
});
```

### Fiber.await - Get result without waiting

```typescript
const program = Effect.gen(function* () {
  const fiber = yield* Effect.fork(task);

  // Non-blocking check
  const exit = yield* Fiber.poll(fiber);

  if (Option.isSome(exit)) {
    console.log("Task completed:", exit.value);
  } else {
    console.log("Task still running");
  }
});
```

### Fiber.join vs Fiber.await

```typescript
// join - waits for completion, propagates errors
const result = yield * Fiber.join(fiber);
// Returns A, fails if fiber failed

// await - returns Exit, doesn't propagate errors
const exit = yield * Fiber.await(fiber);
// Returns Exit<A, E>
```

## Structured Concurrency

### Effect.forkScoped - Fiber tied to scope

```typescript
const program = Effect.scoped(
  Effect.gen(function* () {
    // Fiber automatically interrupted when scope closes
    const fiber = yield* Effect.forkScoped(backgroundTask);

    yield* mainWork();

    // fiber interrupted here (scope ends)
  }),
);
```

### Effect.forkDaemon - Detached fiber

```typescript
// Fiber continues even after parent completes
const fiber = yield * Effect.forkDaemon(backgroundTask);
// Must be manually managed
```

### Effect.forkAll - Fork multiple

```typescript
const fibers = yield * Effect.forkAll(effects);
// Returns Fiber<A[], E>

// Wait for all
const results = yield * Fiber.join(fibers);
```

## Semaphores

Control concurrent access to resources.

```typescript
const program = Effect.gen(function* () {
  // Create semaphore with 5 permits
  const semaphore = yield* Effect.makeSemaphore(5);

  // Each call acquires 1 permit
  const results = yield* Effect.forEach(
    urls,
    (url) => semaphore.withPermits(1)(fetchUrl(url)),
    { concurrency: "unbounded" },
  );

  return results;
});
```

### Semaphore patterns

```typescript
// Database connection pool
const connectionPool = yield * Effect.makeSemaphore(10);

const withConnection = <A, E, R>(effect: Effect.Effect<A, E, R>) =>
  connectionPool.withPermits(1)(effect);

// API rate limiting
const rateLimiter = yield * Effect.makeSemaphore(100);

const rateLimitedFetch = (url: string) =>
  rateLimiter.withPermits(1)(fetchUrl(url));
```

## Queues

Concurrent queues for producer-consumer patterns.

```typescript
import { Queue } from "effect";

const program = Effect.gen(function* () {
  // Bounded queue (blocks when full)
  const queue = yield* Queue.bounded<Task>(100);

  // Producer
  const producer = Effect.gen(function* () {
    for (const task of tasks) {
      yield* Queue.offer(queue, task);
    }
    yield* Queue.shutdown(queue);
  });

  // Consumer
  const consumer = Effect.gen(function* () {
    while (true) {
      const task = yield* Queue.take(queue);
      yield* processTask(task);
    }
  }).pipe(Effect.catchAll(() => Effect.void)); // Exit on shutdown

  // Run both
  yield* Effect.all([producer, consumer], { concurrency: 2 });
});
```

### Queue types

```typescript
// Bounded - blocks producer when full
const bounded = yield * Queue.bounded<A>(capacity);

// Unbounded - never blocks, use with caution
const unbounded = yield * Queue.unbounded<A>();

// Dropping - drops new items when full
const dropping = yield * Queue.dropping<A>(capacity);

// Sliding - drops old items when full
const sliding = yield * Queue.sliding<A>(capacity);
```

## Pub/Sub

```typescript
import { PubSub } from "effect";

const program = Effect.gen(function* () {
  const pubsub = yield* PubSub.bounded<Event>(100);

  // Publisher
  const publish = (event: Event) => PubSub.publish(pubsub, event);

  // Subscriber
  const subscriber = yield* PubSub.subscribe(pubsub);

  const consume = Effect.gen(function* () {
    while (true) {
      const event = yield* Queue.take(subscriber);
      yield* handleEvent(event);
    }
  });

  yield* Effect.fork(consume);
});
```

## Concurrency Patterns

### Fan-out / Fan-in

```typescript
// Process items in parallel, collect results
const fanOutFanIn = <A, B>(
  items: A[],
  process: (a: A) => Effect.Effect<B>,
  concurrency: number,
) => Effect.forEach(items, process, { concurrency });

// Usage
const results = yield * fanOutFanIn(urls, fetchUrl, 10);
```

### Worker pool

```typescript
const createWorkerPool = <A, B>(
  workers: number,
  process: (a: A) => Effect.Effect<B>,
) =>
  Effect.gen(function* () {
    const queue = yield* Queue.bounded<A>(1000);
    const results = yield* Ref.make<B[]>([]);

    const worker = Effect.gen(function* () {
      while (true) {
        const item = yield* Queue.take(queue);
        const result = yield* process(item);
        yield* Ref.update(results, (r) => [...r, result]);
      }
    }).pipe(
      Effect.forever,
      Effect.catchAll(() => Effect.void),
    );

    // Start workers
    yield* Effect.forkAll(Array.from({ length: workers }, () => worker));

    return {
      submit: (item: A) => Queue.offer(queue, item),
      getResults: () => Ref.get(results),
      shutdown: () => Queue.shutdown(queue),
    };
  });
```

### Batching

```typescript
// Batch individual requests
const batchedFetch = <A>(
  requests: Array<{ id: string; resolve: (a: A) => void }>,
  batchFetch: (ids: string[]) => Effect.Effect<Map<string, A>>,
) =>
  Effect.gen(function* () {
    const ids = requests.map((r) => r.id);
    const results = yield* batchFetch(ids);

    for (const req of requests) {
      const result = results.get(req.id);
      if (result) req.resolve(result);
    }
  });
```

### Parallel with early termination

```typescript
// Return first N results
const firstN = <A>(effects: Effect.Effect<A>[], n: number) =>
  Effect.gen(function* () {
    const results = yield* Ref.make<A[]>([]);
    const done = yield* Deferred.make<void>();

    yield* Effect.forEach(
      effects,
      (effect) =>
        effect.pipe(
          Effect.tap((result) =>
            Ref.updateAndGet(results, (r) => [...r, result]).pipe(
              Effect.tap((r) =>
                r.length >= n ? Deferred.succeed(done, void 0) : Effect.void,
              ),
            ),
          ),
          Effect.fork,
        ),
      { discard: true },
    );

    yield* Deferred.await(done);
    return yield* Ref.get(results);
  });
```

## Interruptibility

### Making effects interruptible

```typescript
// Effect can be interrupted
const interruptible = effect.pipe(Effect.interruptible);

// Effect cannot be interrupted
const uninterruptible = effect.pipe(Effect.uninterruptible);
```

### Handling interruption

```typescript
const program = effect.pipe(
  Effect.onInterrupt(() => Effect.log("Interrupted! Cleaning up...")),
  Effect.ensuring(cleanup()),
);
```

### Disconnect (ignore interruption result)

```typescript
// Background task continues even if parent is interrupted
const detached = effect.pipe(Effect.disconnect);
```

## Scheduling Work

### Effect.repeat

```typescript
// Repeat forever with delay
const poller = checkStatus().pipe(Effect.repeat(Schedule.spaced("10 seconds")));

// Repeat until condition
const poller2 = checkStatus().pipe(
  Effect.repeat(Schedule.recurUntil((status) => status === "complete")),
);
```

### Effect.schedule

```typescript
// Run effect on a schedule
const scheduled = effect.pipe(
  Effect.schedule(Schedule.cron("0 * * * *")), // Every hour
);
```

## Complete Example

```typescript
// Parallel API fetcher with rate limiting
const parallelFetcher = Effect.gen(function* () {
  const rateLimiter = yield* Effect.makeSemaphore(10);
  const retryPolicy = Schedule.exponential("100 millis").pipe(
    Schedule.compose(Schedule.recurs(3)),
  );

  const fetchWithControls = (url: string) =>
    rateLimiter.withPermits(1)(
      fetchUrl(url).pipe(
        Effect.timeout("5 seconds"),
        Effect.retry(retryPolicy),
      ),
    );

  return {
    fetchAll: (urls: string[]) =>
      Effect.forEach(urls, fetchWithControls, { concurrency: 50 }),

    fetchFirst: (urls: string[]) => Effect.raceAll(urls.map(fetchWithControls)),
  };
});
```
