# Production Patterns

Real-world Effect.ts patterns extracted from production applications.

## Overview

This section covers battle-tested patterns for:

- HTTP API clients
- Configuration management
- Retry and resilience
- Concurrency and parallelism

## Pattern Philosophy

Effect patterns follow these principles:

1. **Services for dependencies** - All external dependencies become services
2. **Typed errors** - All failure modes are typed in the error channel
3. **Composition over inheritance** - Build complex behavior from simple pieces
4. **Edge execution** - Run effects only at application boundaries

## Quick Reference

| Pattern     | File              | Use When              |
| ----------- | ----------------- | --------------------- |
| HTTP Client | `http-clients.md` | Making API requests   |
| Config      | `config.md`       | Loading configuration |
| Retry       | `retry.md`        | Adding resilience     |
| Concurrency | `concurrency.md`  | Parallel work         |

## Common Service Architecture

From production codebases:

```typescript
// services/
// ├── config.ts        # AppConfig service
// ├── logger.ts        # Logger service
// ├── database.ts      # Database service
// ├── http-client.ts   # HTTP client service
// ├── cache.ts         # Cache service
// └── index.ts         # Layer composition

// Example structure
export const AppLayer = Layer.mergeAll(
  ConfigLive, // No dependencies
  LoggerLive, // Depends on Config
  DatabaseLive, // Depends on Config, Logger
  HttpClientLive, // Depends on Config, Logger
  CacheLive, // Depends on Config, Logger
  UserServiceLive, // Depends on Database, Cache, Logger
  OrderServiceLive, // Depends on Database, Logger
);
```

## Essential Patterns

### Service with Schema Validation

```typescript
import { Schema, Effect } from "effect";

const UserSchema = Schema.Struct({
  id: Schema.String,
  name: Schema.String.pipe(Schema.minLength(1)),
  email: Schema.String.pipe(Schema.pattern(/^[^@]+@[^@]+$/)),
  role: Schema.Literal("admin", "user", "guest"),
});

type User = Schema.Schema.Type<typeof UserSchema>;

class UserService extends Context.Tag("UserService")<
  UserService,
  {
    readonly getUser: (id: string) => Effect.Effect<User, UserError>;
    readonly createUser: (
      input: unknown,
    ) => Effect.Effect<User, ValidationError | UserError>;
  }
>() {}

const UserServiceLive = Layer.effect(
  UserService,
  Effect.gen(function* () {
    const db = yield* Database;

    return {
      getUser: (id) =>
        db.query(`SELECT * FROM users WHERE id = ?`, [id]).pipe(
          Effect.flatMap(Schema.decodeUnknown(UserSchema)),
          Effect.mapError((e) => new UserError({ cause: e })),
        ),

      createUser: (input) =>
        Effect.gen(function* () {
          const validated = yield* Schema.decodeUnknown(UserSchema)(input).pipe(
            Effect.mapError((e) => new ValidationError({ issues: e.message })),
          );
          yield* db.execute(`INSERT INTO users ...`, [validated]);
          return validated;
        }),
    };
  }),
);
```

### Repository Pattern

```typescript
class UserRepository extends Context.Tag("UserRepository")<
  UserRepository,
  {
    readonly findById: (id: string) => Effect.Effect<User, NotFoundError | DbError>
    readonly findByEmail: (email: string) => Effect.Effect<User, NotFoundError | DbError>
    readonly save: (user: User) => Effect.Effect<User, DbError>
    readonly delete: (id: string) => Effect.Effect<void, DbError>
  }
>() {}

const UserRepositoryLive = Layer.effect(
  UserRepository,
  Effect.gen(function* () {
    const db = yield* Database
    const logger = yield* Logger

    return {
      findById: (id) => Effect.gen(function* () {
        yield* logger.debug(`Finding user by id: ${id}`)
        const result = yield* db.query(`SELECT * FROM users WHERE id = ?`, [id])
        if (!result) {
          return yield* Effect.fail(new NotFoundError({ entity: "User", id }))
        }
        return result
      }),

      findByEmail: (email) => /* similar */,

      save: (user) => Effect.gen(function* () {
        yield* logger.debug(`Saving user: ${user.id}`)
        yield* db.execute(`INSERT INTO users ... ON DUPLICATE KEY UPDATE ...`, [user])
        return user
      }),

      delete: (id) => db.execute(`DELETE FROM users WHERE id = ?`, [id]).pipe(
        Effect.asVoid
      )
    }
  })
)
```

### Use Case Pattern

```typescript
// Application layer - orchestrates domain logic
const createUserUseCase = (input: CreateUserInput) =>
  Effect.gen(function* () {
    const userRepo = yield* UserRepository;
    const emailService = yield* EmailService;
    const logger = yield* Logger;

    yield* logger.info("Creating new user", { email: input.email });

    // Check for existing user
    const existing = yield* userRepo.findByEmail(input.email).pipe(
      Effect.option, // Convert NotFoundError to None
    );

    if (Option.isSome(existing)) {
      return yield* Effect.fail(new UserExistsError({ email: input.email }));
    }

    // Create user
    const user = yield* userRepo.save({
      id: yield* Effect.sync(() => crypto.randomUUID()),
      ...input,
      createdAt: new Date(),
    });

    // Send welcome email (don't fail if email fails)
    yield* emailService
      .sendWelcome(user)
      .pipe(
        Effect.catchAll((e) => logger.error("Failed to send welcome email", e)),
      );

    yield* logger.info("User created", { userId: user.id });

    return user;
  });
```

## In This Reference

- [HTTP Clients](./http-clients.md) - Building resilient API clients
- [Configuration](./config.md) - Loading and validating config
- [Retry](./retry.md) - Retry policies and resilience
- [Concurrency](./concurrency.md) - Parallel execution and fibers
