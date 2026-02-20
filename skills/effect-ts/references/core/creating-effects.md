# Creating Effects

All the ways to create Effect values, from simple values to complex async operations.

## Decision Tree

```
Do you have a value already?
├─ Yes, synchronous value
│  ├─ Always succeeds → Effect.succeed(value)
│  └─ Might throw → Effect.try(() => value)
├─ No, need to compute
│  ├─ Synchronous
│  │  ├─ Pure computation → Effect.sync(() => compute())
│  │  └─ Might throw → Effect.try(() => riskyCompute())
│  └─ Asynchronous
│     ├─ Returns Promise → Effect.promise(() => asyncOp())
│     ├─ Promise might reject → Effect.tryPromise(() => asyncOp())
│     └─ Callback-based → Effect.async((resume) => {...})
├─ Want to fail → Effect.fail(error)
└─ Need to decide at runtime → Effect.if / Effect.suspend
```

## From Synchronous Values

### Effect.succeed - Known value

```typescript
const five = Effect.succeed(5);
const user = Effect.succeed({ id: 1, name: "Alice" });

// Type: Effect<number, never, never>
// Never fails, no requirements
```

### Effect.fail - Known error

```typescript
class UserNotFound extends Data.TaggedError("UserNotFound")<{
  readonly userId: string;
}> {}

const error = Effect.fail(new UserNotFound({ userId: "123" }));

// Type: Effect<never, UserNotFound, never>
// Never succeeds
```

### Effect.sync - Lazy synchronous computation

```typescript
const now = Effect.sync(() => Date.now());
const random = Effect.sync(() => Math.random());

// Computation runs when Effect is executed
// Use for side effects that don't throw
```

### Effect.try - Computation that might throw

```typescript
const parseJson = (str: string) =>
  Effect.try({
    try: () => JSON.parse(str),
    catch: (e) => new ParseError({ input: str, cause: e }),
  });

// Shorter form (wraps in UnknownException)
const parseJsonSimple = (str: string) => Effect.try(() => JSON.parse(str));
```

## From Promises

### Effect.promise - Promise that always resolves

```typescript
const delay = (ms: number) =>
  Effect.promise(() => new Promise((resolve) => setTimeout(resolve, ms)));

// Use when you're certain the Promise won't reject
```

### Effect.tryPromise - Promise that might reject

```typescript
const fetchUser = (id: string) =>
  Effect.tryPromise({
    try: () => fetch(`/api/users/${id}`).then((r) => r.json()),
    catch: (e) => new FetchError({ userId: id, cause: e }),
  });

// Always use tryPromise for fetch, database calls, etc.
```

### Converting existing Promise functions

```typescript
// Before (Promise)
async function getUser(id: string): Promise<User> {
  const res = await fetch(`/users/${id}`);
  if (!res.ok) throw new Error("Not found");
  return res.json();
}

// After (Effect)
const getUser = (id: string): Effect.Effect<User, GetUserError> =>
  Effect.gen(function* () {
    const res = yield* Effect.tryPromise({
      try: () => fetch(`/users/${id}`),
      catch: (e) => new GetUserError({ cause: e }),
    });

    if (!res.ok) {
      return yield* Effect.fail(new GetUserError({ status: res.status }));
    }

    return yield* Effect.tryPromise({
      try: () => res.json(),
      catch: (e) => new GetUserError({ cause: e }),
    });
  });
```

## From Callbacks

### Effect.async - Callback-based APIs

```typescript
const readFile = (path: string) =>
  Effect.async<string, NodeError>((resume) => {
    fs.readFile(path, "utf8", (err, data) => {
      if (err) {
        resume(Effect.fail(new NodeError({ cause: err })));
      } else {
        resume(Effect.succeed(data));
      }
    });

    // Optional: return cleanup function
    return Effect.sync(() => {
      // Cancel operation if needed
    });
  });
```

### With AbortSignal support

```typescript
const fetchWithAbort = (url: string) =>
  Effect.async<Response, FetchError>((resume, signal) => {
    fetch(url, { signal })
      .then((res) => resume(Effect.succeed(res)))
      .catch((e) => resume(Effect.fail(new FetchError({ cause: e }))));
  });

// Effect will pass AbortSignal when fiber is interrupted
```

## Conditional Creation

### Effect.if - Choose based on condition

```typescript
const program = Effect.if(user.isAdmin, {
  onTrue: () => getAdminDashboard(),
  onFalse: () => getUserDashboard(),
});
```

### Effect.when - Execute only if true

```typescript
const maybeLog = Effect.when(Effect.log("Debug info"), () => config.debug);
// Returns Option<void>
```

### Effect.suspend - Defer creation

```typescript
// Useful for recursive effects or lazy evaluation
const factorial = (n: number): Effect.Effect<number> =>
  Effect.suspend(() =>
    n <= 1
      ? Effect.succeed(1)
      : factorial(n - 1).pipe(Effect.map((x) => x * n)),
  );
```

## From Option/Either

### Effect.fromOption

```typescript
const effect = Option.some(5).pipe(
  Effect.fromOption,
  Effect.mapError(() => new NotFoundError()),
);
```

### Effect.fromEither

```typescript
const validated = Schema.decodeEither(UserSchema)(data);
const effect = Effect.fromEither(validated);
```

## Quick Reference Table

| Situation              | Function                        |
| ---------------------- | ------------------------------- |
| Known success value    | `Effect.succeed(value)`         |
| Known failure          | `Effect.fail(error)`            |
| Lazy sync, won't throw | `Effect.sync(() => ...)`        |
| Lazy sync, might throw | `Effect.try(() => ...)`         |
| Promise, won't reject  | `Effect.promise(() => ...)`     |
| Promise, might reject  | `Effect.tryPromise(() => ...)`  |
| Callback-based         | `Effect.async((resume) => ...)` |
| From Option            | `Effect.fromOption`             |
| From Either            | `Effect.fromEither`             |
| Unit value (void)      | `Effect.void` / `Effect.unit`   |
| Never completes        | `Effect.never`                  |

## Common Gotchas

### ❌ Don't use Effect.sync for async operations

```typescript
// Wrong - fetch is async!
const bad = Effect.sync(() => fetch(url));

// Correct
const good = Effect.tryPromise(() => fetch(url));
```

### ❌ Don't forget error mapping in tryPromise

```typescript
// Gives UnknownException - hard to handle
const bad = Effect.tryPromise(() => fetch(url));

// Gives typed error - easy to handle
const good = Effect.tryPromise({
  try: () => fetch(url),
  catch: (e) => new FetchError({ cause: e }),
});
```

### ❌ Don't use Effect.succeed for computations

```typescript
// Wrong - Date.now() called immediately, not when Effect runs
const bad = Effect.succeed(Date.now());

// Correct - computation deferred
const good = Effect.sync(() => Date.now());
```
