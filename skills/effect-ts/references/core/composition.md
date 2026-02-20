# Effect Composition

Combining, transforming, and sequencing Effects.

## Decision Tree

```
Combining multiple Effects?
├─ Sequential, need previous result
│  ├─ Complex logic → Effect.gen (generator syntax)
│  └─ Simple chain → Effect.flatMap
├─ Sequential, transform result → Effect.map
├─ Sequential, ignore result → Effect.andThen / Effect.tap
├─ Parallel execution
│  ├─ All must succeed → Effect.all([a, b, c])
│  ├─ First to succeed → Effect.race([a, b])
│  ├─ With concurrency limit → Effect.all(effects, { concurrency: 5 })
│  └─ Collect all results → Effect.allSettled
├─ Conditional
│  ├─ If/else → Effect.if
│  ├─ Execute only if true → Effect.when
│  └─ Filter based on predicate → Effect.filterOrFail
└─ Looping
   ├─ For each item → Effect.forEach
   ├─ While condition → Effect.loop
   └─ Repeat effect → Effect.repeat
```

## Generator Syntax (Preferred)

```typescript
const program = Effect.gen(function* () {
  // Sequential by default
  const user = yield* getUser(id);
  const posts = yield* getPosts(user.id);

  // Can use regular JS control flow
  if (posts.length === 0) {
    return yield* Effect.fail(new NoPostsError());
  }

  // Loops work naturally
  const enriched = [];
  for (const post of posts) {
    const comments = yield* getComments(post.id);
    enriched.push({ ...post, comments });
  }

  return { user, posts: enriched };
});
```

### Generator vs Pipe

```typescript
// Generator - better for complex logic
const withGen = Effect.gen(function* () {
  const a = yield* getA();
  const b = yield* getB(a.id);
  if (b.status === "inactive") {
    return yield* Effect.fail(new InactiveError());
  }
  const c = yield* getC(b.data);
  return { a, b, c };
});

// Pipe - better for simple transforms
const withPipe = getA().pipe(
  Effect.flatMap((a) => getB(a.id)),
  Effect.flatMap((b) => getC(b.data)),
  Effect.map((c) => c.value),
);
```

## Sequential Operations

### Effect.map - Transform success value

```typescript
const doubled = Effect.succeed(5).pipe(Effect.map((n) => n * 2));
// Result: 10
```

### Effect.flatMap - Chain to new Effect

```typescript
const program = getUser(id).pipe(
  Effect.flatMap((user) => getPosts(user.id)),
  Effect.flatMap((posts) => enrichPosts(posts)),
);
```

### Effect.tap - Side effect, keep original value

```typescript
const program = getUser(id).pipe(
  Effect.tap((user) => logUserAccess(user)),
  Effect.tap((user) => updateLastSeen(user.id)),
);
// Returns original user, not log/update results
```

### Effect.andThen - Chain, ignore previous value

```typescript
const program = saveUser(user).pipe(
  Effect.andThen(sendWelcomeEmail(user.email)),
  Effect.andThen(createAuditLog("user_created")),
);
```

### Effect.flatMap vs Effect.andThen

```typescript
// flatMap - receives previous value
getUser(id).pipe(Effect.flatMap((user) => getPosts(user.id)));

// andThen - ignores previous value (or accepts Effect directly)
saveUser(user).pipe(Effect.andThen(notifyAdmins()));
```

## Parallel Operations

### Effect.all - Run all, collect results

```typescript
// Array form
const [user, settings, notifications] =
  yield * Effect.all([getUser(id), getSettings(id), getNotifications(id)]);

// Object form (named results)
const { user, settings } =
  yield *
  Effect.all({
    user: getUser(id),
    settings: getSettings(id),
  });

// With concurrency control
const results =
  yield *
  Effect.all(effects, {
    concurrency: 5, // Max 5 concurrent
    batching: true, // Enable request batching
  });

// Unbounded concurrency
const results =
  yield *
  Effect.all(effects, {
    concurrency: "unbounded",
  });
```

### Effect.race - First to succeed wins

```typescript
const fastest =
  yield * Effect.race([fetchFromPrimary(id), fetchFromBackup(id)]);
// Returns first successful result, cancels others
```

### Effect.allSettled - Collect all results/errors

```typescript
const results =
  yield * Effect.allSettled([maybeFailsA(), maybeFailsB(), maybeFailsC()]);
// Returns Array<Exit<A, E>> - never fails
```

### Effect.forEach - Map with Effect

```typescript
// Sequential
const results = yield * Effect.forEach(userIds, (id) => getUser(id));

// Parallel with concurrency
const results =
  yield * Effect.forEach(userIds, (id) => getUser(id), { concurrency: 10 });

// Discard results
yield * Effect.forEach(users, (user) => sendEmail(user), { discard: true });
```

## Conditional Execution

### Effect.if

```typescript
const dashboard =
  yield *
  Effect.if(user.isAdmin, {
    onTrue: () => getAdminDashboard(),
    onFalse: () => getUserDashboard(),
  });
```

### Effect.when - Execute only if true

```typescript
yield * Effect.when(sendAlert(message), () => severity === "critical");
// Returns Option<Result>
```

### Effect.unless - Execute only if false

```typescript
yield * Effect.unless(skipCache(), () => isCacheEnabled);
```

### Effect.filterOrFail

```typescript
const activeUser =
  yield *
  getUser(id).pipe(
    Effect.filterOrFail(
      (user) => user.status === "active",
      () => new InactiveUserError({ userId: id }),
    ),
  );
```

## Looping

### Effect.loop - While loop

```typescript
const countdown = Effect.loop(10, {
  while: (n) => n > 0,
  step: (n) => n - 1,
  body: (n) => Effect.log(`Countdown: ${n}`),
});
```

### Effect.iterate - Iterate until condition

```typescript
const result =
  yield *
  Effect.iterate(initialState, {
    while: (state) => !state.done,
    body: (state) => processNextStep(state),
  });
```

### Effect.repeat - Repeat effect

```typescript
// Repeat 5 times
yield * effect.pipe(Effect.repeat(Schedule.recurs(5)));

// Repeat forever with delay
yield * effect.pipe(Effect.repeat(Schedule.spaced("1 second")));

// Repeat while condition is true
yield * effect.pipe(Effect.repeatWhile((result) => result.hasMore));
```

## Combining Results

### Effect.zip - Combine two effects

```typescript
const program = Effect.zip(getUser(id), getSettings(id));
// Returns [User, Settings]

// With custom combiner
const program = Effect.zipWith(
  getUser(id),
  getSettings(id),
  (user, settings) => ({ user, settings }),
);
```

### Tuple vs Object results

```typescript
// Tuple - positional access
const [a, b, c] = yield * Effect.all([effectA, effectB, effectC]);

// Object - named access (preferred for clarity)
const { user, posts, comments } =
  yield *
  Effect.all({
    user: getUser(id),
    posts: getPosts(id),
    comments: getComments(id),
  });
```

## Pipeline Patterns

### Building pipelines

```typescript
const processUser = (id: string) =>
  getUser(id).pipe(
    Effect.tap((user) => validateUser(user)),
    Effect.flatMap((user) => enrichUser(user)),
    Effect.tap((user) => cacheUser(user)),
    Effect.map((user) => toUserDTO(user)),
  );
```

### Reusable pipeline stages

```typescript
const withLogging = <A, E, R>(effect: Effect.Effect<A, E, R>) =>
  effect.pipe(
    Effect.tap(() => Effect.log("Operation started")),
    Effect.tapBoth({
      onSuccess: () => Effect.log("Operation succeeded"),
      onFailure: (e) => Effect.logError("Operation failed", e),
    }),
  );

const withRetry = <A, E, R>(effect: Effect.Effect<A, E, R>) =>
  effect.pipe(
    Effect.retry(
      Schedule.exponential("100 millis").pipe(
        Schedule.compose(Schedule.recurs(3)),
      ),
    ),
  );

// Compose stages
const robustFetch = fetchData.pipe(withLogging, withRetry);
```

## Common Patterns

### Sequential with early exit

```typescript
const program = Effect.gen(function* () {
  const user = yield* getUser(id);

  if (!user.verified) {
    return { status: "unverified" as const };
  }

  const permissions = yield* getPermissions(user.id);

  if (!permissions.canAccess) {
    return { status: "forbidden" as const };
  }

  const data = yield* getData(user.id);
  return { status: "success" as const, data };
});
```

### Parallel with timeout per operation

```typescript
const results =
  yield *
  Effect.all(
    urls.map((url) => fetchUrl(url).pipe(Effect.timeout("5 seconds"))),
    { concurrency: 10 },
  );
```
