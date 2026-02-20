# Common Gotchas & Mistakes

Pitfalls, anti-patterns, and myths about Effect.ts.

## Critical Rules

### ❌ Never call Effect.runPromise in the middle of a pipeline

```typescript
// ❌ WRONG - breaks Effect model
const program = Effect.gen(function* () {
  const data = yield* Effect.tryPromise(() => fetch(url));

  // DON'T DO THIS - running effect inside another effect
  const parsed = await Effect.runPromise(parseData(data));

  return parsed;
});

// ✅ CORRECT - compose effects
const program = Effect.gen(function* () {
  const data = yield* Effect.tryPromise(() => fetch(url));
  const parsed = yield* parseData(data);
  return parsed;
});
```

Run effects **only at application edges** (main function, request handlers).

### ❌ Never mix async/await with Effect.gen

```typescript
// ❌ WRONG - async function in generator
const program = Effect.gen(async function* () {
  // async not allowed!
  const data = await fetch(url); // can't use await
  return data;
});

// ✅ CORRECT - use yield* with Effect wrappers
const program = Effect.gen(function* () {
  const response = yield* Effect.tryPromise(() => fetch(url));
  const data = yield* Effect.tryPromise(() => response.json());
  return data;
});
```

### ❌ Never use Effect.sync for async operations

```typescript
// ❌ WRONG - fetch is async
const fetchData = Effect.sync(() => fetch(url));
// Returns Effect<Promise<Response>> - not what you want!

// ✅ CORRECT
const fetchData = Effect.tryPromise(() => fetch(url));
// Returns Effect<Response, UnknownException>
```

### ❌ Never forget to provide Layers

```typescript
// ❌ Type error - Database not provided
const program = Effect.gen(function* () {
  const db = yield* Database;
  return yield* db.query("SELECT 1");
});
await Effect.runPromise(program); // Error!

// ✅ CORRECT - provide the layer
await Effect.runPromise(program.pipe(Effect.provide(DatabaseLive)));
```

### ❌ Never throw in Effect code

```typescript
// ❌ WRONG - throwing bypasses typed errors
const getUser = (id: string) =>
  Effect.gen(function* () {
    const user = yield* fetchUser(id);
    if (!user) {
      throw new Error("Not found"); // Becomes untyped defect!
    }
    return user;
  });

// ✅ CORRECT - use Effect.fail for typed errors
const getUser = (id: string) =>
  Effect.gen(function* () {
    const user = yield* fetchUser(id);
    if (!user) {
      return yield* Effect.fail(new UserNotFound({ userId: id }));
    }
    return user;
  });
```

### ❌ Never catch errors too early

```typescript
// ❌ WRONG - catches error, loses type info
const getUser = fetchUser(id).pipe(Effect.catchAll(() => Effect.succeed(null)));
// Error channel is now `never` - can't handle specific errors later

// ✅ CORRECT - handle at appropriate level
const getUser = fetchUser(id); // Keep error typed

// Handle specific errors where appropriate
const program = getUser.pipe(
  Effect.catchTag("NetworkError", () => retryFetch()),
  Effect.catchTag("NotFound", () => Effect.succeed(null)),
);
```

## Common Mistakes

### ❌ Using Effect.succeed for computations

```typescript
// ❌ WRONG - Date.now() called immediately
const now = Effect.succeed(Date.now());
// Value is captured at creation time, not execution time

// ✅ CORRECT - defer computation
const now = Effect.sync(() => Date.now());
```

### ❌ Forgetting Effect.scoped

```typescript
// ❌ WRONG - Scope requirement not satisfied
const connection = Effect.acquireRelease(openConnection(), (conn) =>
  closeConnection(conn),
);
await Effect.runPromise(connection); // Type error!

// ✅ CORRECT - wrap with scoped
await Effect.runPromise(
  Effect.scoped(
    Effect.gen(function* () {
      const conn = yield* connection;
      return yield* conn.query("SELECT 1");
    }),
  ),
);
```

### ❌ Ignoring Promise rejections

```typescript
// ❌ WRONG - rejection becomes defect
const data = Effect.promise(() => fetch(url));
// If fetch rejects, effect crashes with defect

// ✅ CORRECT - handle rejections
const data = Effect.tryPromise({
  try: () => fetch(url),
  catch: (e) => new FetchError({ cause: e }),
});
```

### ❌ Sync cleanup for async resources

```typescript
// ❌ WRONG - close() returns Promise, ignored
const pool = Effect.acquireRelease(
  createPool(),
  (pool) => Effect.sync(() => pool.close()), // Promise ignored!
);

// ✅ CORRECT - await the Promise
const pool = Effect.acquireRelease(createPool(), (pool) =>
  Effect.promise(() => pool.close()),
);
```

### ❌ Sequential when parallel is better

```typescript
// ❌ SLOW - sequential execution
const program = Effect.gen(function* () {
  const user = yield* getUser(id); // waits
  const posts = yield* getPosts(id); // then waits
  const settings = yield* getSettings(id); // then waits
  return { user, posts, settings };
});

// ✅ FAST - parallel execution
const program = Effect.gen(function* () {
  const { user, posts, settings } = yield* Effect.all({
    user: getUser(id),
    posts: getPosts(id),
    settings: getSettings(id),
  });
  return { user, posts, settings };
});
```

### ❌ Using any type

```typescript
// ❌ WRONG - loses type safety
const parseResponse = (data: any) => Effect.succeed(data.user);

// ✅ CORRECT - use Schema for runtime validation
const UserResponse = Schema.Struct({
  user: Schema.Struct({
    id: Schema.String,
    name: Schema.String,
  }),
});

const parseResponse = (data: unknown) =>
  Schema.decodeUnknown(UserResponse)(data);
```

### ❌ Point-free style (tacit)

```typescript
// ❌ BAD - loses type info, unclear stack traces
Effect.map(processUser);

// ✅ GOOD - explicit, type-safe
Effect.map((user) => processUser(user));
```

## Myths About Effect

### Myth: "Effect is slow"

**Reality**: Effect has overhead for micro-operations like `1+1`, but real applications don't notice. The overhead is negligible compared to I/O operations, and you gain:

- Type safety
- Error handling
- Resource management
- Retry/timeout built-in

### Myth: "Bundle size is huge"

**Reality**: Minimum ~25kb gzipped. Effect tree-shakes well - you only pay for what you use.

### Myth: "Effect is impossible to learn"

**Reality**: Start with these 15 functions:

- Creating: `Effect.succeed`, `Effect.fail`, `Effect.sync`, `Effect.tryPromise`
- Composing: `Effect.gen`, `Effect.map`, `Effect.flatMap`, `Effect.tap`, `Effect.andThen`
- Running: `Effect.runPromise`
- Errors: `Effect.catchTag`, `Effect.catchAll`
- Resources: `Effect.acquireRelease`, `Effect.acquireUseRelease`
- DI: `Effect.provide`, `Effect.provideService`

Learn the rest progressively as needed.

### Myth: "Effect is the same as RxJS"

**Reality**: Different goals:

- **Effect**: Single-shot (like async/await), typed errors, DI
- **RxJS**: Multi-shot streams, event-based

Use Effect for request/response, use RxJS/streams for continuous data.

## Error Types

### Expected Errors (Failures) vs Unexpected Errors (Defects)

| Aspect           | Expected (E channel)        | Unexpected (Defects)  |
| ---------------- | --------------------------- | --------------------- |
| Tracked in types | ✅ Yes                      | ❌ No                 |
| Created by       | `Effect.fail(error)`        | `throw`, `Effect.die` |
| Recovery         | `catchTag`, `catchAll`      | `catchAllDefect`      |
| Use for          | Business errors, validation | Bugs, invariants      |
| Like             | Checked exceptions          | Unchecked exceptions  |

```typescript
// Expected error - part of the API contract
class UserNotFound extends Data.TaggedError("UserNotFound")<{
  readonly userId: string;
}> {}

const getUser = (id: string): Effect.Effect<User, UserNotFound> =>
  Effect.gen(function* () {
    const user = yield* db.findUser(id);
    if (!user) {
      return yield* Effect.fail(new UserNotFound({ userId: id }));
    }
    return user;
  });

// Unexpected error - indicates a bug
const assertPositive = (n: number): Effect.Effect<number> =>
  n > 0
    ? Effect.succeed(n)
    : Effect.die(new Error(`Expected positive number, got ${n}`));
```

## Service Gotchas

### ❌ Using module-level state

```typescript
// ❌ WRONG - global mutable state
let connectionPool: Pool | null = null;

const getPool = () => {
  if (!connectionPool) {
    connectionPool = createPool();
  }
  return connectionPool;
};

// ✅ CORRECT - use Effect services
class ConnectionPool extends Context.Tag("ConnectionPool")<
  ConnectionPool,
  Pool
>() {}

const ConnectionPoolLive = Layer.scoped(
  ConnectionPool,
  Effect.acquireRelease(
    Effect.sync(() => createPool()),
    (pool) => Effect.promise(() => pool.end()),
  ),
);
```

### ❌ Forgetting Layer memoization

```typescript
// Layers are memoized by default - same instance is reused
const program = Effect.gen(function* () {
  const db1 = yield* Database; // Creates pool
  const db2 = yield* Database; // Same pool instance!
  // db1 === db2
});

// If you need fresh instances, use Layer.fresh
const FreshDatabaseLive = Layer.fresh(DatabaseLive);
```

## Debugging Tips

### Enable detailed logging

```typescript
import { Logger, LogLevel } from "effect";

const program = myEffect.pipe(
  Effect.provide(Logger.minimumLogLevel(LogLevel.Debug)),
);
```

### Trace effect execution

```typescript
const traced = myEffect.pipe(
  Effect.tap(() => Effect.log("Step 1 complete")),
  Effect.tapError((e) => Effect.logError("Failed at step 1", e)),
);
```

### Inspect error causes

```typescript
import { Cause } from "effect";

const result = await Effect.runPromiseExit(program);
if (Exit.isFailure(result)) {
  console.log(Cause.pretty(result.cause));
}
```

## Migration Checklist

When converting Promise code to Effect:

- [ ] Replace `async function` with `Effect.gen(function* () {...})`
- [ ] Replace `await` with `yield*`
- [ ] Replace `Promise.all` with `Effect.all`
- [ ] Replace `try/catch` with `Effect.catchTag` / `Effect.catchAll`
- [ ] Replace `throw` with `Effect.fail`
- [ ] Add typed error classes with `Data.TaggedError`
- [ ] Create services for external dependencies
- [ ] Use `Effect.tryPromise` for all Promise-returning calls
- [ ] Add `Effect.scoped` for resource management
- [ ] Run with `Effect.runPromise` only at edges
