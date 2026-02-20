# Effect.ts Core Concepts

Effect.ts is a TypeScript library for building typed, composable, and resilient applications using functional effects.

## Overview

The core type `Effect<Success, Error, Requirements>` represents:

- A lazy computation that may succeed with `Success`
- Or fail with a typed `Error`
- And requires `Requirements` (services) to run

**Key principle**: Effects are values that describe computations. They don't execute until you run them.

## Core Type Signature

```typescript
Effect<Success, Error = never, Requirements = never>
```

- `Success` - The value produced on success
- `Error` - The typed error channel (not `unknown`!)
- `Requirements` - Services needed via dependency injection

## Why Effect over Promises?

| Feature              | Promise        | Effect            |
| -------------------- | -------------- | ----------------- |
| Typed errors         | ❌ (`unknown`) | ✅ (union types)  |
| Dependency injection | ❌             | ✅ (built-in)     |
| Cancellation         | ❌             | ✅ (fibers)       |
| Retry/timeout        | Manual         | Built-in          |
| Resource safety      | Manual         | Automatic         |
| Testability          | Hard to mock   | Layer swapping    |
| Composition          | `async/await`  | Generators + pipe |

## Essential Imports

```typescript
import {
  Effect, // Core effect type and operations
  Context, // Service tags for DI
  Layer, // Service implementations
  Data, // Tagged errors, case classes
  Schema, // Runtime validation
  Config, // Configuration management
  Schedule, // Retry/repeat policies
  Scope, // Resource management
  pipe, // Function composition
} from "effect";
```

## Generator Syntax (Preferred)

```typescript
const program = Effect.gen(function* () {
  const config = yield* Config.string("API_URL");
  const response = yield* fetchData(config);
  const validated = yield* parseResponse(response);
  return validated;
});
```

**Why generators?**

- Reads like async/await
- Full type inference for errors and requirements
- Automatic error channel composition
- Better stack traces than chained pipes

## Pipe Syntax (Alternative)

```typescript
const program = fetchData(url).pipe(
  Effect.flatMap(parseResponse),
  Effect.map((data) => data.items),
  Effect.catchTag("ParseError", () => Effect.succeed([])),
);
```

Use pipe for simple transformations; use generators for complex logic.

## Running Effects

Effects are lazy - they must be explicitly run:

```typescript
// At application edge only
await Effect.runPromise(program);

// With error handling
const result = await Effect.runPromiseExit(program);
if (Exit.isFailure(result)) {
  console.error(result.cause);
}

// Synchronous (if effect is sync)
const value = Effect.runSync(program);
```

## In This Reference

- [Creating Effects](./creating-effects.md) - All ways to create Effect values
- [Composition](./composition.md) - Combining and transforming Effects
- [Error Handling](./error-handling.md) - Typed errors and recovery
- [Resources](./resources.md) - Safe resource management with Scope

## Quick Decision Tree

```
What do you need?
├─ Create an Effect → creating-effects.md
├─ Combine Effects → composition.md
├─ Handle errors → error-handling.md
├─ Manage resources → resources.md
├─ Add services → ../services/README.md
└─ Production patterns → ../patterns/README.md
```
