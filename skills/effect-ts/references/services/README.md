# Services & Dependency Injection

Effect's built-in system for typed dependency injection using Context and Layers.

## Overview

Effect uses a service pattern for dependency injection:

1. **Define** a service interface using `Context.Tag`
2. **Implement** the service using `Layer`
3. **Use** the service with `yield*` in generators
4. **Provide** the implementation at the application edge

```typescript
// 1. Define
class UserRepository extends Context.Tag("UserRepository")<
  UserRepository,
  { readonly findById: (id: string) => Effect.Effect<User, NotFoundError> }
>() {}

// 2. Implement
const UserRepositoryLive = Layer.succeed(UserRepository, {
  findById: (id) => Effect.tryPromise(() => db.users.find(id)),
});

// 3. Use
const program = Effect.gen(function* () {
  const repo = yield* UserRepository;
  return yield* repo.findById("123");
});

// 4. Provide
program.pipe(Effect.provide(UserRepositoryLive));
```

## Decision Tree

```
Working with services?
├─ Define service interface → Context.Tag
├─ Create implementation
│  ├─ Simple/static values → Layer.succeed
│  ├─ Needs other services → Layer.effect + Effect.gen
│  ├─ Needs resources (cleanup) → Layer.scoped
│  └─ From existing Layer → Layer.map
├─ Compose layers
│  ├─ Independent services → Layer.merge / Layer.mergeAll
│  ├─ Service depends on another → Layer.provide
│  └─ Replace service → Layer.provideMerge
├─ Use in program
│  ├─ Generator syntax → yield* ServiceTag
│  └─ Pipe syntax → Effect.flatMap(() => ServiceTag)
└─ Provide at edge
   ├─ Single layer → Effect.provide(layer)
   └─ Multiple layers → Effect.provide(Layer.mergeAll(...))
```

## Defining Services

### Context.Tag Pattern

```typescript
import { Context, Effect } from "effect";

// Service interface with tag
class Logger extends Context.Tag("Logger")<
  Logger,
  {
    readonly info: (message: string) => Effect.Effect<void>;
    readonly error: (message: string, cause?: unknown) => Effect.Effect<void>;
  }
>() {}

// The string "Logger" is the service identifier
// Must be unique across your application
```

### Effect.Service Pattern (Newer)

```typescript
// Alternative: Effect.Service creates Tag + Live layer together
export class ApiClient extends Effect.Service<ApiClient>()("app/ApiClient", {
  effect: Effect.gen(function* () {
    const http = yield* HttpClient.HttpClient;
    const config = yield* Config.string("API_BASE_URL");

    return {
      get: <A>(path: string, schema: Schema.Schema<A>) =>
        http.get(`${config}${path}`).pipe(
          Effect.flatMap((res) => res.json),
          Effect.flatMap(Schema.decodeUnknown(schema)),
        ),
    };
  }),
  dependencies: [HttpClient.layer],
}) {}

// Usage - ApiClient is both the Tag and has a .Default layer
program.pipe(Effect.provide(ApiClient.Default));
```

### Service with Methods Returning Effects

```typescript
class Database extends Context.Tag("Database")<
  Database,
  {
    // Methods return Effects with typed errors
    readonly query: <T>(sql: string) => Effect.Effect<T[], SqlError>;
    readonly execute: (sql: string) => Effect.Effect<number, SqlError>;
    readonly transaction: <A, E, R>(
      effect: Effect.Effect<A, E, R>,
    ) => Effect.Effect<A, E | TransactionError, R>;
  }
>() {}
```

## Creating Layers

### Layer.succeed - Static implementation

```typescript
const LoggerLive = Layer.succeed(Logger, {
  info: (msg) => Effect.sync(() => console.log(`[INFO] ${msg}`)),
  error: (msg, cause) =>
    Effect.sync(() => console.error(`[ERROR] ${msg}`, cause)),
});
```

### Layer.effect - Implementation needs Effects

```typescript
const DatabaseLive = Layer.effect(
  Database,
  Effect.gen(function* () {
    const config = yield* Config.all({
      host: Config.string("DB_HOST"),
      port: Config.integer("DB_PORT"),
      database: Config.string("DB_NAME"),
    });

    const pool = yield* Effect.tryPromise(() => createPool(config));

    return {
      query: (sql) =>
        Effect.tryPromise({
          try: () => pool.query(sql),
          catch: (e) => new SqlError({ sql, cause: e }),
        }),
      execute: (sql) =>
        Effect.tryPromise({
          try: () => pool.execute(sql).then((r) => r.affectedRows),
          catch: (e) => new SqlError({ sql, cause: e }),
        }),
      transaction: (effect) => Effect.scoped(/* ... */),
    };
  }),
);
```

### Layer.scoped - Implementation with resources

```typescript
const DatabaseLive = Layer.scoped(
  Database,
  Effect.gen(function* () {
    // Pool is acquired here
    const pool = yield* Effect.acquireRelease(
      Effect.tryPromise(() => createPool()),
      (pool) => Effect.promise(() => pool.end())
    )

    return {
      query: (sql) => /* use pool */,
      execute: (sql) => /* use pool */
    }
  })
)
// Pool is released when Layer is released
```

### Layer depending on other services

```typescript
const UserServiceLive = Layer.effect(
  UserService,
  Effect.gen(function* () {
    // Get dependencies
    const db = yield* Database;
    const logger = yield* Logger;
    const cache = yield* Cache;

    return {
      getUser: (id) =>
        Effect.gen(function* () {
          // Check cache first
          const cached = yield* cache.get(`user:${id}`);
          if (cached) return cached;

          yield* logger.info(`Cache miss for user ${id}`);
          const user = yield* db.query(`SELECT * FROM users WHERE id = ?`, [
            id,
          ]);
          yield* cache.set(`user:${id}`, user);
          return user;
        }),
    };
  }),
);
```

## Composing Layers

### Layer.merge - Combine independent layers

```typescript
const InfraLayer = Layer.merge(LoggerLive, DatabaseLive);
// Provides both Logger and Database
```

### Layer.mergeAll - Combine multiple layers

```typescript
const AppLayer = Layer.mergeAll(
  LoggerLive,
  DatabaseLive,
  CacheLive,
  ConfigLive,
);
```

### Layer.provide - Satisfy dependencies

```typescript
// UserServiceLive needs Database
const UserServiceWithDeps = UserServiceLive.pipe(Layer.provide(DatabaseLive));

// Or provide multiple
const FullUserService = UserServiceLive.pipe(
  Layer.provide(Layer.mergeAll(DatabaseLive, LoggerLive, CacheLive)),
);
```

### Layer.provideMerge - Provide and merge

```typescript
// Combines providing and merging
const layer = ServiceALive.pipe(Layer.provideMerge(ServiceBLive));
```

## Using Services

### Generator syntax (preferred)

```typescript
const program = Effect.gen(function* () {
  const logger = yield* Logger;
  const db = yield* Database;

  yield* logger.info("Fetching users");
  const users = yield* db.query("SELECT * FROM users");
  yield* logger.info(`Found ${users.length} users`);

  return users;
});
```

### Accessing in Effect.flatMap

```typescript
const program = Logger.pipe(Effect.flatMap((logger) => logger.info("Hello")));
```

## Providing Layers

### At application edge

```typescript
const main = program.pipe(Effect.provide(AppLayer));

await Effect.runPromise(main);
```

### Partial providing

```typescript
// Provide some services, leave others
const partial = program.pipe(Effect.provide(DatabaseLive));
// Still requires Logger, Cache, etc.

// Provide rest later
const full = partial.pipe(
  Effect.provide(Layer.mergeAll(LoggerLive, CacheLive)),
);
```

## Layer Lifecycle

```
Layer Creation → Build (once) → Use (many times) → Release

┌─────────────────────────────────────────────────┐
│ Layer.scoped(Service, acquireRelease(...))      │
│                                                  │
│ 1. Build: acquires resource                      │
│ 2. All effects using Service run                 │
│ 3. Release: cleanup runs                         │
└─────────────────────────────────────────────────┘
```

### Memoization

Layers are memoized by default:

```typescript
const program = Effect.gen(function* () {
  const db1 = yield* Database; // First access: builds layer
  const db2 = yield* Database; // Same instance reused
  // db1 === db2
});
```

### Fresh layers

```typescript
const freshLayer = Layer.fresh(DatabaseLive);
// New instance created each time
```

## Testing with Mock Layers

```typescript
// Production implementation
const DatabaseLive = Layer.effect(Database /* real db */);

// Test implementation
const DatabaseTest = Layer.succeed(Database, {
  query: () => Effect.succeed([{ id: 1, name: "Test" }]),
  execute: () => Effect.succeed(1),
  transaction: (effect) => effect,
});

// In tests
const testResult = await Effect.runPromise(
  program.pipe(Effect.provide(DatabaseTest)),
);
```

## Real-World Service Architecture

```typescript
// Config layer (no deps)
const ConfigLive = Layer.effect(AppConfig /* load config */);

// Logger (depends on Config)
const LoggerLive = Layer.effect(Logger /* uses config */).pipe(
  Layer.provide(ConfigLive),
);

// Database (depends on Config, Logger)
const DatabaseLive = Layer.scoped(Database /* pool mgmt */).pipe(
  Layer.provide(Layer.merge(ConfigLive, LoggerLive)),
);

// Services (depend on Database, Logger)
const UserServiceLive = Layer.effect(UserService /* impl */).pipe(
  Layer.provide(Layer.merge(DatabaseLive, LoggerLive)),
);

// Compose into app layer
const AppLayer = Layer.mergeAll(
  ConfigLive,
  LoggerLive,
  DatabaseLive,
  UserServiceLive,
);

// Main program
const main = application.pipe(Effect.provide(AppLayer));
```

## In This Reference

- [Layers](./layers.md) - Deep dive into Layer composition
- [Runtime](./runtime.md) - Managing Effect runtimes for long-running apps
