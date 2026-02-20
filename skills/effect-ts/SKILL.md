---
name: effect-ts
description:
  Effect.ts patterns for typed functional effects, dependency injection, error
  handling, and resilient async operations. Use when writing or reviewing
  Effect-based code, migrating from Promises, or implementing services with
  typed errors. Triggers on Effect.gen, Effect.succeed, Effect.fail, Context.Tag,
  Layer, Data.TaggedError, Schedule, Schema, pipe, yield*, ManagedRuntime.
license: MIT
metadata:
  author: scrapybara
  version: "1.0.0"
references:
  - core
  - services
  - patterns
---

# Effect.ts Skill

Comprehensive guidance for building applications with Effect.ts - a TypeScript library for typed functional effects with dependency injection, structured concurrency, and resilient error handling.

## Quick Reference

```typescript
import { Effect, Context, Layer, Data, Config, Schema, Schedule } from "effect";
import { NodeRuntime } from "@effect/platform-node"; // For applications
```

**Core type**: `Effect<Success, Error, Requirements>`

- `Success` - The value type on success
- `Error` - The error type (typed errors!)
- `Requirements` - Services/dependencies needed to run

## Quick Decision Trees

### "How do I create an Effect?"

```
Do you have a value already?
├─ Yes, synchronous value → Effect.succeed(value)
├─ Yes, but computation might throw → Effect.try(() => riskyValue)
├─ No, need to compute
│  ├─ Synchronous computation → Effect.sync(() => compute())
│  └─ Asynchronous computation
│     ├─ Returns Promise → Effect.promise(() => asyncOp())
│     ├─ Promise might reject → Effect.tryPromise(() => asyncOp())
│     └─ Callback-based → Effect.async((resume) => { ... })
└─ Want to fail immediately → Effect.fail(error)
```

→ See `references/core/creating-effects.md`

### "How do I compose Effects?"

```
Combining multiple Effects?
├─ Sequential, need previous result → Effect.gen (generator syntax)
├─ Sequential, transform result → .pipe(Effect.map(...))
├─ Sequential, chain to new Effect → .pipe(Effect.flatMap(...))
├─ Parallel, independent operations → Effect.all([a, b, c])
├─ Parallel, first to succeed → Effect.race([a, b])
├─ Parallel, with concurrency limit → Effect.all(effects, { concurrency: 5 })
└─ Conditional execution → Effect.if / Effect.when
```

→ See `references/core/composition.md`

### "How do I handle errors?"

```
Need to handle errors?
├─ Define typed error → class MyError extends Data.TaggedError("MyError")<{...}>
├─ Handle specific error type → .pipe(Effect.catchTag("MyError", handler))
├─ Handle all errors → .pipe(Effect.catchAll(handler))
├─ Recover with fallback → .pipe(Effect.orElse(() => fallback))
├─ Transform error type → .pipe(Effect.mapError(transform))
├─ Catch and rethrow → .pipe(Effect.tapError(logError))
└─ Ignore errors (return Option) → .pipe(Effect.option)
```

→ See `references/core/error-handling.md`

### "How do I use dependency injection?"

```
Need dependency injection?
├─ Define service interface → class MyService extends Context.Tag("MyService")<...>
├─ Create implementation → Layer.succeed(MyService, implementation)
├─ Implementation needs other services → Layer.effect(MyService, Effect.gen(...))
├─ Compose layers → Layer.merge / Layer.provide
├─ Provide at runtime edge → Effect.provide(layer)
└─ Access service in Effect → yield* MyService (in generator)
```

→ See `references/services/README.md`

### "How do I run an Effect?"

```
Need to execute the Effect?
├─ In application entry point
│  ├─ Simple run → Effect.runPromise(effect)
│  ├─ Run and exit process → Effect.runMain(effect)
│  └─ Get sync result → Effect.runSync(effect)
├─ Long-running application
│  ├─ Managed runtime → ManagedRuntime.make(layer)
│  └─ Singleton pattern → Runtime as module variable
└─ Testing → Effect.runPromise with test layers
```

→ See `references/services/runtime.md`

### "How do I add retry/resilience?"

```
Need retry logic?
├─ Fixed retry count → Schedule.recurs(n)
├─ Fixed delay between retries → Schedule.spaced(duration)
├─ Exponential backoff → Schedule.exponential(base)
├─ Combine strategies → Schedule.union / Schedule.compose
├─ Add jitter → Schedule.jittered
└─ Apply to Effect → effect.pipe(Effect.retry(schedule))
```

→ See `references/patterns/retry.md`

## Generator Syntax (Preferred)

```typescript
const program = Effect.gen(function* () {
  const user = yield* getUser(id);
  const posts = yield* getPosts(user.id);
  return { user, posts };
});
```

**Why generators?**

- Reads like async/await
- Full type inference
- Automatic error channel composition
- Better stack traces

## Tagged Errors (Preferred)

```typescript
class UserNotFound extends Data.TaggedError("UserNotFound")<{
  readonly userId: string;
}> {}

class NetworkError extends Data.TaggedError("NetworkError")<{
  readonly url: string;
  readonly cause: unknown;
}> {}

// Type-safe error handling
effect.pipe(
  Effect.catchTag("UserNotFound", (e) => Effect.succeed(null)),
  Effect.catchTag("NetworkError", (e) => retryWithBackoff(e.url)),
);
```

## Service Pattern

```typescript
// 1. Define interface
class Database extends Context.Tag("Database")<
  Database,
  {
    readonly query: (sql: string) => Effect.Effect<unknown[], SqlError>;
  }
>() {}

// 2. Create implementation
const DatabaseLive = Layer.succeed(Database, {
  query: (sql) =>
    Effect.tryPromise({
      try: () => db.query(sql),
      catch: (e) => new SqlError({ cause: e }),
    }),
});

// 3. Use in program
const program = Effect.gen(function* () {
  const db = yield* Database;
  return yield* db.query("SELECT * FROM users");
});

// 4. Provide layer at edge
program.pipe(Effect.provide(DatabaseLive));
```

## Running Applications

Use platform-specific `runMain` for real applications:

```typescript
// Node.js - handles SIGINT/SIGTERM, proper exit codes
import { NodeRuntime } from "@effect/platform-node";
NodeRuntime.runMain(program);

// Bun
import { BunRuntime } from "@effect/platform-bun";
BunRuntime.runMain(program);

// Browser
import { BrowserRuntime } from "@effect/platform-browser";
BrowserRuntime.runMain(program);
```

For simple scripts, use `Effect.runPromise(program)` at the edge.

## Essential Functions (Start Here)

These 15 functions cover most use cases:

| Category  | Functions                                                                    |
| --------- | ---------------------------------------------------------------------------- |
| Creating  | `Effect.succeed`, `Effect.fail`, `Effect.sync`, `Effect.tryPromise`          |
| Composing | `Effect.gen`, `Effect.map`, `Effect.flatMap`, `Effect.tap`, `Effect.andThen` |
| Running   | `Effect.runPromise`                                                          |
| Errors    | `Effect.catchTag`, `Effect.catchAll`                                         |
| Resources | `Effect.acquireRelease`, `Effect.acquireUseRelease`                          |
| DI        | `Effect.provide`, `Effect.provideService`                                    |

## Essential Imports

| Import             | Purpose                               |
| ------------------ | ------------------------------------- |
| `Effect`           | Core effect type and operations       |
| `Context`          | Service tags for dependency injection |
| `Layer`            | Service implementations               |
| `Data`             | Tagged errors, case classes           |
| `Schema`           | Runtime validation                    |
| `Config`           | Configuration management              |
| `Schedule`         | Retry/repeat policies                 |
| `Scope`            | Resource management                   |
| `Runtime`          | Effect execution                      |
| `ManagedRuntime`   | Long-running runtimes                 |
| `Option`, `Either` | Data types                            |
| `Match`            | Pattern matching                      |

## Reference Index

### Core Concepts

| Topic                   | Reference                             |
| ----------------------- | ------------------------------------- |
| Effect Fundamentals     | `references/core/README.md`           |
| Creating Effects        | `references/core/creating-effects.md` |
| Composition & Pipelines | `references/core/composition.md`      |
| Error Handling          | `references/core/error-handling.md`   |
| Resource Management     | `references/core/resources.md`        |

### Services & DI

| Topic             | Reference                        |
| ----------------- | -------------------------------- |
| Services Overview | `references/services/README.md`  |
| Layers            | `references/services/layers.md`  |
| Runtime           | `references/services/runtime.md` |

### Patterns

| Topic              | Reference                             |
| ------------------ | ------------------------------------- |
| Patterns Overview  | `references/patterns/README.md`       |
| HTTP Clients       | `references/patterns/http-clients.md` |
| Configuration      | `references/patterns/config.md`       |
| Retry & Resilience | `references/patterns/retry.md`        |
| Concurrency        | `references/patterns/concurrency.md`  |

### Troubleshooting

| Topic          | Reference               |
| -------------- | ----------------------- |
| Common Gotchas | `references/gotchas.md` |

## Reading Order

| Task                  | Start With                          | Then Read           |
| --------------------- | ----------------------------------- | ------------------- |
| Learning Effect       | core/README → core/creating-effects | core/composition    |
| Adding error handling | core/error-handling                 | gotchas             |
| Setting up DI         | services/README → services/layers   | services/runtime    |
| Building HTTP client  | patterns/http-clients               | patterns/retry      |
| Production setup      | patterns/config                     | services/runtime    |
| Debugging issues      | gotchas                             | core/error-handling |

## Schema Quick Reference

Schema provides runtime validation with type inference:

```typescript
import { Schema } from "effect";

const User = Schema.Struct({
  name: Schema.String.pipe(Schema.minLength(1)),
  email: Schema.String.pipe(Schema.pattern(/^[^@]+@[^@]+$/)),
  age: Schema.Number.pipe(Schema.int(), Schema.positive()),
});

type User = Schema.Schema.Type<typeof User>;

// Decode unknown data
const result = Schema.decodeUnknown(User)(rawData);

// In Effect pipeline
effect.pipe(Effect.flatMap((data) => Schema.decodeUnknown(User)(data)));
```

## See Also

- [Effect Documentation](https://effect.website/docs/introduction)
- [Effect API Reference](https://effect-ts.github.io/effect/)
- [Effect Discord](https://discord.gg/effect-ts)
- [Effect LLM Context](https://effect.website/llms-full.txt)
