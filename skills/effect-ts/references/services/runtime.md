# Runtime Management

Managing Effect runtimes for application lifecycle and execution.

## What is a Runtime?

A Runtime is the execution environment for Effects. It contains:

- The `Context` (service map)
- Configuration (logging, tracing, etc.)
- Fiber management

## Running Effects

### At Application Edge

```typescript
// Simple - returns Promise
await Effect.runPromise(program);

// With error handling
const exit = await Effect.runPromiseExit(program);
if (Exit.isFailure(exit)) {
  console.error(Cause.pretty(exit.cause));
}

// Synchronous (if effect is sync)
const value = Effect.runSync(program);
```

### For Applications: runMain

**Use `runMain` for real applications** - handles graceful shutdown:

```typescript
// Node.js
import { NodeRuntime } from "@effect/platform-node";
NodeRuntime.runMain(program);

// Bun
import { BunRuntime } from "@effect/platform-bun";
BunRuntime.runMain(program);

// Browser
import { BrowserRuntime } from "@effect/platform-browser";
BrowserRuntime.runMain(program);
```

Benefits of `runMain`:

- Handles SIGINT/SIGTERM gracefully
- Proper process exit codes
- Fiber interruption on shutdown
- Structured logging setup

### Basic runMain Example

```typescript
import { Effect } from "effect";
import { NodeRuntime } from "@effect/platform-node";

const main = Effect.gen(function* () {
  yield* Effect.log("Starting application...");

  // Your application logic
  yield* runServer();

  yield* Effect.log("Application started");

  // Keep running until interrupted
  yield* Effect.never;
}).pipe(Effect.provide(AppLayer), Effect.scoped);

NodeRuntime.runMain(main);
```

## ManagedRuntime for Long-Running Apps

For applications that need persistent runtime (servers, bots, etc.):

```typescript
import { ManagedRuntime } from "effect";

// Create managed runtime with layers
const runtime = ManagedRuntime.make(AppLayer);

// Run effects with the runtime
const result = await runtime.runPromise(someEffect);

// Dispose when shutting down
await runtime.dispose();
```

### Singleton Runtime Pattern

```typescript
// runtime.ts
import { ManagedRuntime, Effect, Layer } from "effect";

let runtime: ManagedRuntime.ManagedRuntime<AppServices, never> | null = null;

export const getRuntime = async () => {
  if (!runtime) {
    runtime = ManagedRuntime.make(AppLayer);
    // Wait for initialization
    await runtime.runPromise(Effect.void);
  }
  return runtime;
};

export const disposeRuntime = async () => {
  if (runtime) {
    await runtime.dispose();
    runtime = null;
  }
};

// Usage in handlers
export const handleRequest = async (req: Request) => {
  const rt = await getRuntime();
  return rt.runPromise(processRequest(req));
};
```

### Framework Integration Pattern

```typescript
// For Express/Fastify/etc.
const app = express();

const runtime = ManagedRuntime.make(AppLayer);

app.get("/users/:id", async (req, res) => {
  const result = await runtime.runPromise(
    getUserById(req.params.id).pipe(
      Effect.catchTag("NotFound", () => Effect.succeed(null)),
    ),
  );

  if (!result) {
    return res.status(404).json({ error: "Not found" });
  }
  res.json(result);
});

// Graceful shutdown
process.on("SIGTERM", async () => {
  await runtime.dispose();
  process.exit(0);
});
```

### Svelte/SvelteKit Integration

```typescript
// hooks.ts
import { ManagedRuntime } from "effect";

let runtime: ManagedRuntime.ManagedRuntime<AppServices, never> | null = null;

export const init = async () => {
  runtime = ManagedRuntime.make(AppLayer);
  await runtime.runPromise(Effect.void);
};

export const getRuntime = () => {
  if (!runtime) throw new Error("Runtime not initialized");
  return runtime;
};

// In components with Svelte 5 $effect
$effect(() => {
  const controller = new AbortController();

  Effect.runFork(myEffect.pipe(Effect.interruptible), {
    signal: controller.signal,
  });

  return () => controller.abort();
});
```

### Event-Driven Applications (Discord Bot Example)

```typescript
import { ManagedRuntime, Effect, Layer } from "effect"
import { Client, Events } from "discord.js"

// Setup runtime
const runtime = ManagedRuntime.make(
  Layer.mergeAll(
    DiscordServiceLive,
    DatabaseLive,
    LoggerLive
  )
)

// Initialize client
const client = new Client({ intents: [...] })

// Event handlers run effects
client.on(Events.MessageCreate, (message) => {
  runtime.runPromise(
    handleMessage(message).pipe(
      Effect.catchAll((e) => Effect.logError("Handler failed", e))
    )
  )
})

// Graceful shutdown
const shutdown = async () => {
  await runtime.runPromise(Effect.log("Shutting down..."))
  client.destroy()
  await runtime.dispose()
  process.exit(0)
}

process.on("SIGINT", shutdown)
process.on("SIGTERM", shutdown)

// Start
await client.login(token)
```

## Fiber Management

### Running concurrent fibers

```typescript
const program = Effect.gen(function* () {
  // Fork a background task
  const fiber = yield* Effect.fork(backgroundTask);

  // Main work continues
  yield* mainWork();

  // Wait for background task
  const result = yield* Fiber.join(fiber);

  return result;
});
```

### Fiber interruption

```typescript
const program = Effect.gen(function* () {
  const fiber = yield* Effect.fork(longRunningTask);

  // Set timeout
  yield* Effect.sleep("5 seconds");

  // Interrupt if still running
  yield* Fiber.interrupt(fiber);
});
```

### Running with AbortSignal

```typescript
// Integrate with external abort signals
const runWithAbort = (effect: Effect.Effect<A, E, R>, signal: AbortSignal) =>
  Effect.runPromise(
    effect.pipe(
      Effect.interruptible,
      Effect.onInterrupt(() => Effect.log("Interrupted by abort signal")),
    ),
    { signal },
  );

// Usage
const controller = new AbortController();
runWithAbort(longOperation(), controller.signal);

// Later
controller.abort();
```

## Runtime Configuration

### Custom runtime with config

```typescript
const customRuntime = Runtime.defaultRuntime.pipe(
  Runtime.withLogLevel(LogLevel.Debug),
  Runtime.withTracer(myTracer),
);

// Use
Runtime.runPromise(customRuntime)(program);
```

### Layer-based configuration

```typescript
const AppLayer = Layer.mergeAll(
  ServiceLayers,
  Logger.minimumLogLevel(LogLevel.Info),
  Logger.structured, // Structured JSON logging
);

const runtime = ManagedRuntime.make(AppLayer);
```

## Testing Runtime

### Test runtime with mock layers

```typescript
describe("UserService", () => {
  const testRuntime = ManagedRuntime.make(TestLayer);

  afterAll(async () => {
    await testRuntime.dispose();
  });

  it("fetches user", async () => {
    const result = await testRuntime.runPromise(getUserById("123"));
    expect(result.name).toBe("Test User");
  });
});
```

### Per-test runtime

```typescript
it("isolated test", async () => {
  const runtime = ManagedRuntime.make(TestLayer);
  try {
    const result = await runtime.runPromise(myTest);
    expect(result).toBe(expected);
  } finally {
    await runtime.dispose();
  }
});
```

## Common Patterns

### Application bootstrap

```typescript
// main.ts
import { Effect, Layer } from "effect";
import { NodeRuntime } from "@effect/platform-node";

const AppLayer = Layer.mergeAll(
  ConfigLive,
  LoggerLive,
  DatabaseLive,
  HttpServerLive,
);

const main = Effect.gen(function* () {
  yield* Effect.log("Initializing...");

  const server = yield* HttpServer;
  yield* server.start();

  yield* Effect.log("Server started on port 3000");

  // Keep alive
  yield* Effect.never;
}).pipe(Effect.provide(AppLayer), Effect.scoped);

NodeRuntime.runMain(main);
```

### Request-scoped services

```typescript
// Create request-specific layer
const createRequestLayer = (req: Request) =>
  Layer.mergeAll(
    Layer.succeed(RequestContext, {
      requestId: crypto.randomUUID(),
      userId: req.headers.get("x-user-id"),
    }),
    Layer.succeed(Logger, createRequestLogger(req)),
  );

// Handler
const handleRequest = (req: Request) =>
  runtime.runPromise(
    processRequest().pipe(Effect.provide(createRequestLayer(req))),
  );
```

### Metrics and observability

```typescript
const withMetrics = <A, E, R>(effect: Effect.Effect<A, E, R>) =>
  Effect.gen(function* () {
    const start = Date.now();
    const result = yield* effect;
    const duration = Date.now() - start;

    yield* Effect.sync(() => {
      metrics.histogram("effect.duration", duration);
    });

    return result;
  });

// Apply to all handlers
const handler = processRequest().pipe(withMetrics);
```
