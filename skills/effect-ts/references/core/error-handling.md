# Error Handling

Typed errors, recovery strategies, and error transformation in Effect.

## Decision Tree

```
Need to handle errors?
├─ Define error types
│  ├─ Simple error → class MyError extends Data.TaggedError("MyError")<{...}>
│  └─ Error hierarchy → multiple tagged error classes
├─ Handle specific error
│  ├─ By tag name → Effect.catchTag("ErrorName", handler)
│  ├─ By multiple tags → Effect.catchTags({ A: h1, B: h2 })
│  └─ By predicate → Effect.catchIf(pred, handler)
├─ Handle all errors
│  ├─ Recover completely → Effect.catchAll(handler)
│  ├─ Transform error → Effect.mapError(transform)
│  └─ Add context → Effect.mapError(e => new WrapperError({ cause: e }))
├─ Fallback strategies
│  ├─ Alternative effect → Effect.orElse(() => fallback)
│  ├─ Default value → Effect.orElseSucceed(() => default)
│  └─ Fail with different error → Effect.orElseFail(() => newError)
├─ Inspect without handling
│  ├─ Log error → Effect.tapError(e => Effect.log(e))
│  └─ Side effect on error → Effect.tapError(handler)
└─ Convert error handling
   ├─ Error to Option → Effect.option
   ├─ Error to Either → Effect.either
   └─ Absorb into defect → Effect.orDie
```

## Defining Typed Errors

### Tagged Errors (Preferred)

```typescript
import { Data, Effect } from "effect";

// Define error with tag and payload
class UserNotFound extends Data.TaggedError("UserNotFound")<{
  readonly userId: string;
}> {}

class NetworkError extends Data.TaggedError("NetworkError")<{
  readonly url: string;
  readonly status: number;
}> {}

class ValidationError extends Data.TaggedError("ValidationError")<{
  readonly field: string;
  readonly message: string;
}> {}

// Usage
const getUser = (
  id: string,
): Effect.Effect<User, UserNotFound | NetworkError> =>
  Effect.gen(function* () {
    const res = yield* fetchUser(id);
    if (!res) {
      return yield* Effect.fail(new UserNotFound({ userId: id }));
    }
    return res;
  });
```

### Why Tagged Errors?

```typescript
// Tagged errors have a _tag property for discrimination
const error = new UserNotFound({ userId: "123" });
console.log(error._tag); // "UserNotFound"
console.log(error.userId); // "123"

// Enables exhaustive pattern matching
effect.pipe(
  Effect.catchTags({
    UserNotFound: (e) => handleNotFound(e.userId),
    NetworkError: (e) => handleNetwork(e.url, e.status),
    ValidationError: (e) => handleValidation(e.field),
  }),
);
```

### Error with Cause Chain

```typescript
class ApiError extends Data.TaggedError("ApiError")<{
  readonly endpoint: string;
  readonly cause: unknown; // Original error
}> {}

const fetchData = (endpoint: string) =>
  Effect.tryPromise({
    try: () => fetch(endpoint),
    catch: (e) => new ApiError({ endpoint, cause: e }),
  });
```

## Catching Errors

### Effect.catchTag - Handle specific error

```typescript
const program = getUser(id).pipe(
  Effect.catchTag("UserNotFound", (e) =>
    Effect.succeed({ id: e.userId, name: "Guest", isGuest: true }),
  ),
);
// UserNotFound handled, NetworkError still in error channel
```

### Effect.catchTags - Handle multiple errors

```typescript
const program = getUser(id).pipe(
  Effect.catchTags({
    UserNotFound: (e) => Effect.succeed(guestUser),
    NetworkError: (e) => retryWithBackoff(e.url),
    // ValidationError NOT handled - stays in error channel
  }),
);
```

### Effect.catchAll - Handle all errors

```typescript
const program = getUser(id).pipe(
  Effect.catchAll((error) => {
    // error is UserNotFound | NetworkError | ValidationError
    return Effect.succeed(fallbackUser);
  }),
);
// Error channel becomes `never`
```

### Effect.catchIf - Handle by predicate

```typescript
const program = apiCall().pipe(
  Effect.catchIf(
    (e): e is NetworkError => e._tag === "NetworkError" && e.status === 503,
    (e) => retryAfterDelay(e.url),
  ),
);
```

### Effect.catchSome - Optionally handle

```typescript
const program = getUser(id).pipe(
  Effect.catchSome((error) => {
    if (error._tag === "NetworkError" && error.status === 404) {
      return Option.some(Effect.succeed(notFoundResponse));
    }
    return Option.none(); // Don't handle, propagate error
  }),
);
```

## Transforming Errors

### Effect.mapError - Transform error type

```typescript
// Convert internal errors to API errors
const program = internalOperation().pipe(
  Effect.mapError(
    (e) =>
      new ApiError({
        code: "INTERNAL_ERROR",
        message: e.message,
      }),
  ),
);
```

### Effect.mapBoth - Transform both channels

```typescript
const program = effect.pipe(
  Effect.mapBoth({
    onSuccess: (data) => data.items,
    onFailure: (e) => new PublicError({ cause: e }),
  }),
);
```

### Wrapping errors with context

```typescript
class ServiceError extends Data.TaggedError("ServiceError")<{
  readonly service: string;
  readonly operation: string;
  readonly cause: unknown;
}> {}

const withServiceContext =
  (service: string, operation: string) =>
  <A, E, R>(effect: Effect.Effect<A, E, R>) =>
    effect.pipe(
      Effect.mapError(
        (cause) => new ServiceError({ service, operation, cause }),
      ),
    );

// Usage
const program = getUser(id).pipe(withServiceContext("UserService", "getUser"));
```

## Fallback Strategies

### Effect.orElse - Alternative effect

```typescript
const program = fetchFromPrimary(id).pipe(
  Effect.orElse(() => fetchFromBackup(id)),
  Effect.orElse(() => fetchFromCache(id)),
);
```

### Effect.orElseSucceed - Fallback value

```typescript
const program = getSettings(userId).pipe(
  Effect.orElseSucceed(() => defaultSettings),
);
```

### Effect.orElseFail - Different error

```typescript
const program = internalOp().pipe(
  Effect.orElseFail(() => new PublicError({ message: "Operation failed" })),
);
```

## Inspecting Errors

### Effect.tapError - Side effect on error

```typescript
const program = operation().pipe(
  Effect.tapError((e) => Effect.log(`Error: ${e._tag}`, e)),
  Effect.tapError((e) => recordMetric("error", { tag: e._tag })),
);
// Error still propagates after tap
```

### Effect.tapBoth - Side effects for both outcomes

```typescript
const program = operation().pipe(
  Effect.tapBoth({
    onSuccess: (result) => Effect.log("Success", result),
    onFailure: (error) => Effect.logError("Failure", error),
  }),
);
```

### Effect.tapDefect - Handle unexpected errors

```typescript
const program = operation().pipe(
  Effect.tapDefect((defect) => reportToSentry(defect)),
);
// Defects are unexpected/untyped errors (thrown exceptions)
```

## Error Channel Conversion

### Effect.either - Error to Either

```typescript
const program = operation().pipe(Effect.either);
// Effect<Either<Error, Result>, never, R>

const result = yield * program;
if (Either.isLeft(result)) {
  console.log("Error:", result.left);
} else {
  console.log("Success:", result.right);
}
```

### Effect.option - Error to Option

```typescript
const maybeUser = yield * getUser(id).pipe(Effect.option);
// Option<User> - None if any error occurred
```

### Effect.exit - Full Exit information

```typescript
const exit = yield * operation().pipe(Effect.exit);
// Exit<Result, Error>

Exit.match(exit, {
  onSuccess: (value) => console.log("Value:", value),
  onFailure: (cause) => console.log("Cause:", Cause.pretty(cause)),
});
```

### Effect.orDie - Absorb error as defect

```typescript
// Converts typed error to untyped defect (throws)
const program = operation().pipe(Effect.orDie);
// Effect<Result, never, R>

// Only for errors that "should never happen"
```

## Error Recovery Patterns

### Retry then fallback

```typescript
const resilientFetch = (url: string) =>
  fetchData(url).pipe(
    Effect.retry(
      Schedule.exponential("100 millis").pipe(
        Schedule.compose(Schedule.recurs(3)),
      ),
    ),
    Effect.orElse(() => fetchFromCache(url)),
    Effect.orElseSucceed(() => defaultData),
  );
```

### Partial recovery

```typescript
const program = Effect.gen(function* () {
  const user = yield* getUser(id).pipe(
    Effect.catchTag("UserNotFound", () => Effect.succeed(guestUser)),
  );

  // NetworkError still propagates here
  const posts = yield* getPosts(user.id);

  return { user, posts };
});
```

### Accumulating errors

```typescript
const validateAll = (data: Input) =>
  Effect.all(
    [validateName(data.name), validateEmail(data.email), validateAge(data.age)],
    { mode: "either" },
  ).pipe(
    Effect.flatMap((results) => {
      const errors = results.filter(Either.isLeft).map((e) => e.left);
      if (errors.length > 0) {
        return Effect.fail(new ValidationErrors({ errors }));
      }
      return Effect.succeed(results.map((e) => e.right));
    }),
  );
```

## Defects vs Errors

| Aspect     | Errors (E channel)     | Defects                    |
| ---------- | ---------------------- | -------------------------- |
| Type       | Typed, union           | Unknown                    |
| Recovery   | Expected, handled      | Unexpected, crash          |
| Created by | `Effect.fail()`        | Thrown exceptions          |
| Handling   | `catchTag`, `catchAll` | `catchAllDefect`           |
| Best for   | Business errors        | Bugs, invariant violations |

```typescript
// Error - expected, handled gracefully
const userNotFound = Effect.fail(new UserNotFound({ userId: id }));

// Defect - unexpected, usually bugs
const program = Effect.sync(() => {
  throw new Error("This becomes a defect");
});

// Handle defects explicitly
program.pipe(
  Effect.catchAllDefect((defect) =>
    Effect.logError("Unexpected error", defect),
  ),
);
```
