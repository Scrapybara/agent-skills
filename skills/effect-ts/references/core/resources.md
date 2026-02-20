# Resource Management

Safe acquisition and release of resources using Scope.

## Overview

Effect provides `Scope` for resource management - ensuring cleanup happens even when errors occur or effects are interrupted.

```typescript
// Pattern: Acquire → Use → Release (guaranteed)
const connection =
  yield *
  Effect.acquireRelease(
    openConnection(), // Acquire
    (conn) => conn.close(), // Release (always runs)
  );
```

## Decision Tree

```
Managing resources?
├─ Simple acquire/release → Effect.acquireRelease
├─ Need cleanup on scope exit → Effect.addFinalizer
├─ Multiple resources
│  ├─ Independent → Effect.all with scoped effects
│  └─ Dependent → Sequential yield* in gen
├─ Resource as service → Layer.scoped
├─ Running scoped effect
│  ├─ In main program → Effect.scoped
│  └─ As Layer dependency → Layer provides Scope
└─ Finalizer behavior
   ├─ Run always → acquireRelease (default)
   ├─ Run on success → acquireReleaseInterruptible
   └─ Run on failure → Effect.onError
```

## Effect.acquireRelease

### Basic Pattern

```typescript
import { Effect, Scope } from "effect";

const program = Effect.gen(function* () {
  // Resource acquired here
  const connection = yield* Effect.acquireRelease(
    // Acquire - runs once
    Effect.sync(() => {
      console.log("Opening connection");
      return new DatabaseConnection();
    }),
    // Release - guaranteed to run
    (connection) =>
      Effect.sync(() => {
        console.log("Closing connection");
        connection.close();
      }),
  );

  // Use the resource
  const result = yield* connection.query("SELECT * FROM users");
  return result;
});

// Must run with scope
await Effect.runPromise(Effect.scoped(program));
```

### With Typed Errors

```typescript
class ConnectionError extends Data.TaggedError("ConnectionError")<{
  readonly cause: unknown;
}> {}

const managedConnection = Effect.acquireRelease(
  Effect.tryPromise({
    try: () => createConnection(),
    catch: (e) => new ConnectionError({ cause: e }),
  }),
  (conn) => Effect.promise(() => conn.close()),
);
```

### Release Even on Interruption

```typescript
const interruptibleResource = Effect.acquireReleaseInterruptible(
  acquire(),
  (resource, exit) => {
    // exit tells you how the scope ended
    if (Exit.isInterrupted(exit)) {
      return cleanupOnInterrupt(resource);
    }
    return cleanup(resource);
  },
);
```

## Effect.scoped

Runs a scoped effect and closes the scope afterward:

```typescript
// Without scoped - requires Scope in requirements
const needsScope: Effect.Effect<Result, Error, Scope.Scope> = program;

// With scoped - Scope requirement satisfied
const standalone: Effect.Effect<Result, Error> = Effect.scoped(program);
```

### When to Use Effect.scoped

```typescript
// At the edge of your program
const main = Effect.scoped(
  Effect.gen(function* () {
    const db = yield* acquireDatabase();
    const cache = yield* acquireCache();
    return yield* runApplication(db, cache);
  }),
);

await Effect.runPromise(main);
```

## Effect.addFinalizer

Add cleanup without acquiring a resource:

```typescript
const program = Effect.gen(function* () {
  yield* Effect.addFinalizer(() => Effect.log("Cleanup running"));

  // ... do work

  yield* Effect.addFinalizer(() => Effect.log("Another cleanup"));

  // Finalizers run in reverse order
});
```

## Multiple Resources

### Independent Resources (Parallel)

```typescript
const program = Effect.gen(function* () {
  const [db, cache, queue] = yield* Effect.all([
    acquireDatabase(),
    acquireCache(),
    acquireQueue(),
  ]);

  return yield* processWithResources(db, cache, queue);
});
// All three released when scope closes
```

### Dependent Resources (Sequential)

```typescript
const program = Effect.gen(function* () {
  const config = yield* acquireConfig();
  const db = yield* acquireDatabase(config.dbUrl);
  const cache = yield* acquireCache(config.cacheUrl);

  return yield* runApp(db, cache);
});
// Released in reverse order: cache → db → config
```

## Layer.scoped

Create a Layer from a scoped effect:

```typescript
class DatabaseConnection extends Context.Tag("DatabaseConnection")<
  DatabaseConnection,
  Connection
>() {}

const DatabaseLive = Layer.scoped(
  DatabaseConnection,
  Effect.acquireRelease(
    Effect.tryPromise(() => createConnection()),
    (conn) => Effect.promise(() => conn.close()),
  ),
);

// When layer is provided, connection is managed automatically
const program = Effect.gen(function* () {
  const db = yield* DatabaseConnection;
  return yield* db.query("SELECT 1");
}).pipe(Effect.provide(DatabaseLive));
```

## Real-World Patterns

### File Handle

```typescript
const withFile = (path: string) =>
  Effect.acquireRelease(
    Effect.tryPromise({
      try: () => fs.promises.open(path, "r"),
      catch: (e) => new FileError({ path, cause: e }),
    }),
    (handle) => Effect.promise(() => handle.close()),
  );

const program = Effect.scoped(
  Effect.gen(function* () {
    const file = yield* withFile("/data/config.json");
    const content = yield* Effect.tryPromise(() => file.readFile("utf8"));
    return JSON.parse(content);
  }),
);
```

### HTTP Client Session

```typescript
const withHttpSession = Effect.acquireRelease(
  Effect.sync(() => new HttpSession()),
  (session) => Effect.sync(() => session.close()),
);

const fetchWithSession = Effect.scoped(
  Effect.gen(function* () {
    const session = yield* withHttpSession;
    const auth = yield* session.authenticate(credentials);
    const data = yield* session.get("/api/data", { auth });
    return data;
  }),
);
```

### Database Transaction

```typescript
const withTransaction = <A, E, R>(
  effect: Effect.Effect<A, E, R>,
): Effect.Effect<A, E | TransactionError, R | DatabaseConnection> =>
  Effect.scoped(
    Effect.gen(function* () {
      const db = yield* DatabaseConnection;

      const tx = yield* Effect.acquireRelease(
        db.beginTransaction(),
        (tx, exit) => (Exit.isSuccess(exit) ? tx.commit() : tx.rollback()),
      );

      return yield* effect;
    }),
  );

// Usage
const program = withTransaction(
  Effect.gen(function* () {
    yield* insertUser(user);
    yield* insertAuditLog(log);
    return "success";
  }),
);
```

### Connection Pool

```typescript
const ConnectionPool = Context.Tag<ConnectionPool>();

const ConnectionPoolLive = Layer.scoped(
  ConnectionPool,
  Effect.gen(function* () {
    const pool = yield* Effect.acquireRelease(
      Effect.sync(() => createPool({ min: 5, max: 20 })),
      (pool) => Effect.promise(() => pool.end()),
    );

    return {
      withConnection: <A, E, R>(
        fn: (conn: Connection) => Effect.Effect<A, E, R>,
      ) =>
        Effect.acquireUseRelease(
          Effect.tryPromise(() => pool.connect()),
          fn,
          (conn) => Effect.sync(() => conn.release()),
        ),
    };
  }),
);
```

## Scope Hierarchy

Scopes can be nested:

```typescript
const outer = Effect.scoped(
  Effect.gen(function* () {
    const outerResource = yield* acquireOuter();

    // Inner scope - closes before outer
    const innerResult = yield* Effect.scoped(
      Effect.gen(function* () {
        const innerResource = yield* acquireInner();
        return yield* useInner(innerResource);
      }),
    );

    // Inner resource already released here
    return yield* useOuter(outerResource, innerResult);
  }),
);
```

## Ensuring Cleanup

### Effect.ensuring

```typescript
const program = doWork().pipe(Effect.ensuring(cleanup()));
// cleanup runs regardless of success/failure
```

### Effect.onExit

```typescript
const program = doWork().pipe(
  Effect.onExit((exit) => {
    if (Exit.isSuccess(exit)) {
      return logSuccess(exit.value);
    } else {
      return logFailure(exit.cause);
    }
  }),
);
```

### Effect.onError

```typescript
const program = doWork().pipe(Effect.onError((cause) => reportError(cause)));
// Only runs on failure
```

## Common Gotchas

### ❌ Forgetting Effect.scoped

```typescript
// Wrong - Scope requirement not satisfied
const program = acquireResource(); // Effect<R, E, Scope>
await Effect.runPromise(program); // Type error!

// Correct
await Effect.runPromise(Effect.scoped(program));
```

### ❌ Resource used after scope closes

```typescript
// Wrong - connection escapes scope
const getConnection = Effect.scoped(
  Effect.acquireRelease(openConn(), closeConn),
);
// Connection is closed when this returns!

// Correct - use resource within scope
const useConnection = Effect.scoped(
  Effect.gen(function* () {
    const conn = yield* acquireConnection();
    return yield* conn.query("SELECT 1"); // Used within scope
  }),
);
```

### ❌ Sync cleanup for async resources

```typescript
// Wrong - close() returns Promise, but wrapped in sync
const bad = Effect.acquireRelease(
  openAsync(),
  (r) => Effect.sync(() => r.close()), // Promise ignored!
);

// Correct
const good = Effect.acquireRelease(openAsync(), (r) =>
  Effect.promise(() => r.close()),
);
```
