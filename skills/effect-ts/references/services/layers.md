# Layer Composition

Deep dive into creating, composing, and managing Layers for dependency injection.

## What is a Layer?

A Layer describes how to build a service. Think of it as a recipe:

```typescript
Layer<ProvidedService, Error, RequiredServices>;
```

- `ProvidedService` - What this layer provides
- `Error` - Errors that can occur during build
- `RequiredServices` - What this layer needs to build

## Context: The Service Map

Services are stored in a `Context`, which works like a typed Map:

```typescript
// Conceptually:
Map<Tag, Implementation>;

// Context.Tag creates a unique key
class Database extends Context.Tag("Database")<Database, DbConnection>() {}

// Layer.succeed adds to the map
Layer.succeed(Database, myConnection);
// Result: Map { Database → myConnection }
```

## Layer Creation

### Layer.succeed - Static implementation

```typescript
const LoggerLive = Layer.succeed(Logger, {
  info: (msg) => Effect.sync(() => console.log(msg)),
  error: (msg) => Effect.sync(() => console.error(msg)),
});
// Layer<Logger, never, never>
// No errors, no requirements
```

### Layer.effect - Effectful creation

```typescript
const ConfigLive = Layer.effect(
  AppConfig,
  Effect.gen(function* () {
    const env = yield* Effect.sync(() => process.env);
    return {
      apiUrl: env.API_URL ?? "http://localhost:3000",
      debug: env.DEBUG === "true",
    };
  }),
);
// Layer<AppConfig, never, never>
```

### Layer.scoped - With resource lifecycle

```typescript
const DatabaseLive = Layer.scoped(
  Database,
  Effect.acquireRelease(
    Effect.tryPromise(() => createPool()),
    (pool) => Effect.promise(() => pool.end()),
  ),
);
// Layer<Database, Error, never>
// Pool created when layer builds, closed when released
```

### Layer.function - Function as service

```typescript
class Hash extends Context.Tag("Hash")<Hash, (input: string) => string>() {}

const HashLive = Layer.function(
  Hash,
  () => (input) => crypto.createHash("sha256").update(input).digest("hex"),
);
```

### Effect.Service - Combined pattern

```typescript
// Creates both Tag and Default layer
export class ApiClient extends Effect.Service<ApiClient>()("app/ApiClient", {
  effect: Effect.gen(function* () {
    const http = yield* HttpClient.HttpClient;
    return {
      get: (path: string) => http.get(path),
    };
  }),
  dependencies: [HttpClient.layer],
}) {}

// Use as tag
const client = yield * ApiClient;

// Use the layer
Effect.provide(program, ApiClient.Default);
```

## Layer Composition

### Vertical Composition: Dependencies

When Layer A needs Layer B:

```typescript
// UserService needs Database
const UserServiceLive = Layer.effect(
  UserService,
  Effect.gen(function* () {
    const db = yield* Database; // Requires Database
    return {
      getUser: (id) => db.query(`SELECT * FROM users WHERE id = ?`, [id]),
    };
  }),
);
// Layer<UserService, never, Database>

// Satisfy the requirement
const UserServiceWithDeps = UserServiceLive.pipe(Layer.provide(DatabaseLive));
// Layer<UserService, Error, never>
```

### Horizontal Composition: Merging

Combine independent layers:

```typescript
// Each provides different service
const InfraLayer = Layer.merge(LoggerLive, ConfigLive);
// Layer<Logger | Config, never, never>

// Multiple layers
const AppLayer = Layer.mergeAll(
  LoggerLive,
  ConfigLive,
  DatabaseLive,
  CacheLive,
);
// Layer<Logger | Config | Database | Cache, Error, never>
```

### Combined: Provide and Merge

```typescript
const FullLayer = UserServiceLive.pipe(
  Layer.provideMerge(DatabaseLive), // Satisfy + keep Database available
  Layer.provideMerge(LoggerLive),
);
// Layer<UserService | Database | Logger, Error, never>
```

## Layer Memoization

**Layers are memoized by default** - built once and shared:

```typescript
const ExpensiveLayer = Layer.effect(
  ExpensiveService,
  Effect.gen(function* () {
    yield* Effect.log("Building expensive service..."); // Logs once
    return {
      /* ... */
    };
  }),
);

const program = Effect.gen(function* () {
  const a = yield* ExpensiveService; // First access: builds
  const b = yield* ExpensiveService; // Same instance
  const c = yield* ExpensiveService; // Same instance
});
// "Building expensive service..." appears only once
```

### Layer.fresh - Disable memoization

```typescript
const FreshLayer = Layer.fresh(ExpensiveLayer);
// New instance created each time

// Useful for:
// - Test isolation
// - Per-request services
// - Stateful services that shouldn't be shared
```

## Providing Layers to Effects

### Effect.provide - Single layer

```typescript
const result = await Effect.runPromise(program.pipe(Effect.provide(AppLayer)));
```

### Effect.provide - Multiple layers

```typescript
const result = await Effect.runPromise(
  program.pipe(
    Effect.provide(Layer.mergeAll(DatabaseLive, LoggerLive, ConfigLive)),
  ),
);
```

### Effect.provideService - Inline service

```typescript
// Quick way to provide a simple service
const result = await Effect.runPromise(
  program.pipe(Effect.provideService(Logger, consoleLogger)),
);
```

### Partial providing

```typescript
// Provide some, leave others
const partial = program.pipe(Effect.provide(DatabaseLive));
// Still needs Logger, Config

// Provide rest elsewhere
const full = partial.pipe(Effect.provide(LoggerLive));
```

## Optional Services

Use `Effect.serviceOption` when a service may not be provided:

```typescript
class Analytics extends Context.Tag("Analytics")<
  Analytics,
  { readonly track: (event: string) => Effect.Effect<void> }
>() {}

const program = Effect.gen(function* () {
  const maybeAnalytics = yield* Effect.serviceOption(Analytics);

  if (Option.isSome(maybeAnalytics)) {
    yield* maybeAnalytics.value.track("page_view");
  }
  // Analytics not required in type signature
});
// Effect<void, never, never> - no requirements!
```

## Layer Dependency Graph

Build complex dependency graphs:

```typescript
/*
  AppLayer
    ├── ConfigLive (no deps)
    ├── LoggerLive (depends on Config)
    ├── DatabaseLive (depends on Config, Logger)
    └── UserServiceLive (depends on Database, Logger)
*/

const ConfigLive = Layer.effect(Config, loadConfig);

const LoggerLive = Layer.effect(
  Logger,
  Effect.gen(function* () {
    const config = yield* Config;
    return createLogger(config.logLevel);
  }),
).pipe(Layer.provide(ConfigLive));

const DatabaseLive = Layer.scoped(
  Database,
  Effect.gen(function* () {
    const config = yield* Config;
    const logger = yield* Logger;
    return yield* createPool(config.dbUrl, logger);
  }),
).pipe(Layer.provide(Layer.merge(ConfigLive, LoggerLive)));

const UserServiceLive = Layer.effect(
  UserService,
  Effect.gen(function* () {
    const db = yield* Database;
    const logger = yield* Logger;
    return createUserService(db, logger);
  }),
).pipe(Layer.provide(Layer.merge(DatabaseLive, LoggerLive)));

// Final layer provides everything
const AppLayer = Layer.mergeAll(
  ConfigLive,
  LoggerLive,
  DatabaseLive,
  UserServiceLive,
);
```

## Testing with Layers

### Mock layer pattern

```typescript
// Production
const UserRepositoryLive = Layer.effect(UserRepository /* real impl */);

// Test
const UserRepositoryTest = Layer.succeed(UserRepository, {
  findById: (id) => Effect.succeed({ id, name: "Test User" }),
  save: (user) => Effect.succeed(user),
  delete: (id) => Effect.succeed(void 0),
});

// Test layer composition
const TestLayer = Layer.mergeAll(
  UserRepositoryTest,
  LoggerTest,
  Layer.succeed(Config, testConfig),
);

// In tests
it("should find user", async () => {
  const result = await Effect.runPromise(
    findUser("123").pipe(Effect.provide(TestLayer)),
  );
  expect(result.name).toBe("Test User");
});
```

### Test spy pattern

```typescript
const UserRepositoryTestWithSpy = Layer.effect(
  UserRepository,
  Effect.gen(function* () {
    const calls = yield* Ref.make<Array<string>>([]);

    return {
      findById: (id) =>
        Ref.update(calls, (c) => [...c, `findById:${id}`]).pipe(
          Effect.as({ id, name: "Test" }),
        ),
      getCalls: () => Ref.get(calls),
    };
  }),
);
```

## Layer Lifecycle

```
Application Start
    │
    ▼
┌─────────────────────────┐
│  Layer Build Phase      │  ← Effect.provide triggers
│  - Allocate resources   │
│  - Connect to DB        │
│  - Initialize caches    │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  Application Running    │  ← Program executes
│  - Services are used    │
│  - Memoized instances   │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  Layer Release Phase    │  ← On shutdown/scope close
│  - Close connections    │
│  - Release resources    │
│  - Cleanup              │
└─────────────────────────┘
```

## Common Patterns

### Environment-based layers

```typescript
const AppLayer =
  process.env.NODE_ENV === "test"
    ? TestLayer
    : process.env.NODE_ENV === "development"
      ? DevLayer
      : ProdLayer;
```

### Feature flag layers

```typescript
const AnalyticsLayer = config.analyticsEnabled
  ? RealAnalyticsLive
  : Layer.succeed(Analytics, { track: () => Effect.void });
```

### Layer with configuration

```typescript
const createDatabaseLayer = (config: DbConfig) =>
  Layer.scoped(
    Database,
    Effect.acquireRelease(
      Effect.tryPromise(() => createPool(config)),
      (pool) => Effect.promise(() => pool.end()),
    ),
  );

// Use
const DatabaseLive = createDatabaseLayer({
  host: "localhost",
  port: 5432,
  database: "myapp",
});
```
