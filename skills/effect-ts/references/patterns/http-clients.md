# HTTP Client Patterns

Building resilient, typed API clients with Effect.

## Service-Based HTTP Client

```typescript
import { Effect, Context, Layer, Schema, Data } from "effect";
import { HttpClient } from "@effect/platform";

// Error types
class ApiError extends Data.TaggedError("ApiError")<{
  readonly path: string;
  readonly status: number;
  readonly body: unknown;
}> {}

class NetworkError extends Data.TaggedError("NetworkError")<{
  readonly cause: unknown;
}> {}

class ValidationError extends Data.TaggedError("ValidationError")<{
  readonly path: string;
  readonly issues: string;
}> {}

// Client service
class ApiClient extends Context.Tag("ApiClient")<
  ApiClient,
  {
    readonly get: <A>(
      path: string,
      schema: Schema.Schema<A>,
    ) => Effect.Effect<A, ApiError | NetworkError | ValidationError>;

    readonly post: <A, B>(
      path: string,
      body: A,
      responseSchema: Schema.Schema<B>,
    ) => Effect.Effect<B, ApiError | NetworkError | ValidationError>;
  }
>() {}
```

## Effect.Service Pattern (Union Labs Style)

```typescript
export class ApiClient extends Effect.Service<ApiClient>()("app/ApiClient", {
  effect: Effect.gen(function* () {
    const http = yield* HttpClient.HttpClient;
    const config = yield* AppConfig;

    const request = <A>(
      method: "GET" | "POST" | "PUT" | "DELETE",
      path: string,
      schema: Schema.Schema<A>,
      body?: unknown,
    ): Effect.Effect<A, ApiError | NetworkError | ValidationError> =>
      Effect.gen(function* () {
        const url = `${config.apiBaseUrl}${path}`;

        const response = yield* (
          method === "GET"
            ? http.get(url)
            : http.request(url, { method, body: JSON.stringify(body) })
        ).pipe(Effect.mapError((e) => new NetworkError({ cause: e })));

        if (response.status >= 400) {
          const errorBody = yield* Effect.tryPromise(() =>
            response.json(),
          ).pipe(Effect.orElseSucceed(() => null));
          return yield* Effect.fail(
            new ApiError({
              path,
              status: response.status,
              body: errorBody,
            }),
          );
        }

        const json = yield* Effect.tryPromise({
          try: () => response.json(),
          catch: (e) => new NetworkError({ cause: e }),
        });

        return yield* Schema.decodeUnknown(schema)(json).pipe(
          Effect.mapError(
            (e) =>
              new ValidationError({
                path,
                issues: String(e),
              }),
          ),
        );
      }).pipe(Effect.timeout("10 seconds"), Effect.retry(retryPolicy));

    return {
      get: (path, schema) => request("GET", path, schema),
      post: (path, body, schema) => request("POST", path, schema, body),
      put: (path, body, schema) => request("PUT", path, schema, body),
      delete: (path, schema) => request("DELETE", path, schema),
    };
  }),
  dependencies: [HttpClient.layer],
}) {}
```

## GraphQL Client (Union Labs Pattern)

```typescript
import { print, DocumentNode } from "graphql";

class GraphqlClient extends Effect.Service<GraphqlClient>()(
  "app/GraphqlClient",
  {
    effect: Effect.gen(function* () {
      const http = yield* HttpClient.HttpClient;
      const config = yield* AppConfig;

      return {
        query: <T, V extends Record<string, unknown> = {}>(
          document: DocumentNode,
          variables?: V,
        ): Effect.Effect<T, GraphqlError | NetworkError> =>
          Effect.gen(function* () {
            const response = yield* http
              .post(config.graphqlEndpoint, {
                body: JSON.stringify({
                  query: print(document),
                  variables,
                }),
                headers: {
                  "Content-Type": "application/json",
                },
              })
              .pipe(Effect.mapError((e) => new NetworkError({ cause: e })));

            const json = yield* Effect.tryPromise(() => response.json());

            if (json.errors?.length > 0) {
              return yield* Effect.fail(
                new GraphqlError({
                  errors: json.errors,
                }),
              );
            }

            return json.data as T;
          }),
      };
    }),
    dependencies: [HttpClient.layer],
  },
) {}

// Usage
const GET_USER = gql`
  query GetUser($id: ID!) {
    user(id: $id) {
      id
      name
      email
    }
  }
`;

const program = Effect.gen(function* () {
  const client = yield* GraphqlClient;
  const result = yield* client.query<{ user: User }>(GET_USER, { id: "123" });
  return result.user;
});
```

## Response Schemas

```typescript
// Define API response schemas
const UserResponse = Schema.Struct({
  id: Schema.String,
  name: Schema.String,
  email: Schema.String,
  createdAt: Schema.DateFromString,
});

const PaginatedResponse = <A>(item: Schema.Schema<A>) =>
  Schema.Struct({
    items: Schema.Array(item),
    total: Schema.Number,
    page: Schema.Number,
    pageSize: Schema.Number,
  });

const UsersResponse = PaginatedResponse(UserResponse);

// Usage
const getUsers = (page: number) =>
  Effect.gen(function* () {
    const client = yield* ApiClient;
    return yield* client.get(`/users?page=${page}`, UsersResponse);
  });
```

## Request Building Patterns

### Headers and authentication

```typescript
const AuthenticatedClient = Layer.effect(
  ApiClient,
  Effect.gen(function* () {
    const http = yield* HttpClient.HttpClient;
    const auth = yield* AuthService;

    const withAuth = <A, E, R>(effect: Effect.Effect<A, E, R>) =>
      Effect.gen(function* () {
        const token = yield* auth.getToken();
        return yield* effect.pipe(
          Effect.provideService(
            HttpClient.HttpClient,
            http.pipe(
              HttpClient.mapRequest((req) =>
                req.pipe(
                  HttpClientRequest.setHeader(
                    "Authorization",
                    `Bearer ${token}`,
                  ),
                ),
              ),
            ),
          ),
        );
      });

    return {
      get: (path, schema) => withAuth(/* ... */),
      post: (path, body, schema) => withAuth(/* ... */),
    };
  }),
);
```

### Request interceptors

```typescript
const createClient = (config: ClientConfig) =>
  Layer.effect(
    ApiClient,
    Effect.gen(function* () {
      const http = yield* HttpClient.HttpClient;
      const logger = yield* Logger;

      const loggedHttp = http.pipe(
        HttpClient.tapRequest((req) =>
          logger.debug("HTTP Request", {
            method: req.method,
            url: req.url,
          }),
        ),
        HttpClient.tap((res) =>
          logger.debug("HTTP Response", {
            status: res.status,
          }),
        ),
      );

      // ... rest of implementation
    }),
  );
```

## Error Handling Patterns

### Retry on specific errors

```typescript
const resilientGet = <A>(path: string, schema: Schema.Schema<A>) =>
  apiClient.get(path, schema).pipe(
    Effect.retry({
      while: (error) =>
        error._tag === "NetworkError" ||
        (error._tag === "ApiError" && error.status >= 500),
      schedule: Schedule.exponential("100 millis").pipe(
        Schedule.compose(Schedule.recurs(3)),
      ),
    }),
  );
```

### Fallback on failure

```typescript
const getUserWithFallback = (id: string) =>
  apiClient.get(`/users/${id}`, UserSchema).pipe(
    Effect.catchTag("ApiError", (e) => {
      if (e.status === 404) {
        return Effect.succeed(null);
      }
      return Effect.fail(e);
    }),
    Effect.orElse(() => cacheClient.get(`user:${id}`)),
  );
```

### Circuit breaker pattern

```typescript
const circuitBreaker = <A, E, R>(
  effect: Effect.Effect<A, E, R>,
  config: {
    maxFailures: number;
    resetTimeout: Duration.Duration;
  },
) =>
  Effect.gen(function* () {
    const failures = yield* Ref.make(0);
    const lastFailure = yield* Ref.make<Option.Option<number>>(Option.none());

    return Effect.gen(function* () {
      const currentFailures = yield* Ref.get(failures);
      const lastFail = yield* Ref.get(lastFailure);

      // Check if circuit is open
      if (currentFailures >= config.maxFailures) {
        if (Option.isSome(lastFail)) {
          const elapsed = Date.now() - lastFail.value;
          if (elapsed < Duration.toMillis(config.resetTimeout)) {
            return yield* Effect.fail(new CircuitOpenError());
          }
        }
      }

      return yield* effect.pipe(
        Effect.tap(() => Ref.set(failures, 0)),
        Effect.tapError(() =>
          Effect.all([
            Ref.update(failures, (n) => n + 1),
            Ref.set(lastFailure, Option.some(Date.now())),
          ]),
        ),
      );
    });
  });
```

## Testing HTTP Clients

```typescript
// Mock client for tests
const MockApiClient = Layer.succeed(ApiClient, {
  get: (path, schema) => {
    if (path === "/users/123") {
      return Effect.succeed({ id: "123", name: "Test User" } as any);
    }
    return Effect.fail(new ApiError({ path, status: 404, body: null }));
  },
  post: (path, body, schema) => Effect.succeed(body as any),
});

// In tests
it("fetches user", async () => {
  const result = await Effect.runPromise(
    getUser("123").pipe(Effect.provide(MockApiClient)),
  );
  expect(result.name).toBe("Test User");
});
```

## Complete Example

```typescript
// api-client.ts
import { Effect, Layer, Schema, Data } from "effect";
import { HttpClient, HttpClientRequest } from "@effect/platform";

// Errors
export class ApiError extends Data.TaggedError("ApiError")<{
  readonly path: string;
  readonly status: number;
  readonly message: string;
}> {}

// Schemas
export const User = Schema.Struct({
  id: Schema.String,
  name: Schema.String,
  email: Schema.String,
});

// Service
export class UserApi extends Effect.Service<UserApi>()("app/UserApi", {
  effect: Effect.gen(function* () {
    const http = yield* HttpClient.HttpClient;
    const config = yield* AppConfig;

    const baseUrl = config.apiBaseUrl;

    return {
      getUser: (id: string) =>
        http.get(`${baseUrl}/users/${id}`).pipe(
          Effect.flatMap((res) => res.json),
          Effect.flatMap(Schema.decodeUnknown(User)),
          Effect.mapError(
            (e) =>
              new ApiError({
                path: `/users/${id}`,
                status: 500,
                message: String(e),
              }),
          ),
          Effect.timeout("5 seconds"),
          Effect.retry(
            Schedule.exponential("100 millis").pipe(
              Schedule.compose(Schedule.recurs(3)),
            ),
          ),
        ),

      listUsers: () =>
        http.get(`${baseUrl}/users`).pipe(
          Effect.flatMap((res) => res.json),
          Effect.flatMap(Schema.decodeUnknown(Schema.Array(User))),
          Effect.mapError(
            (e) =>
              new ApiError({
                path: "/users",
                status: 500,
                message: String(e),
              }),
          ),
        ),
    };
  }),
  dependencies: [HttpClient.layer],
}) {}
```
