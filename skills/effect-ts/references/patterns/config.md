# Configuration Patterns

Loading, validating, and managing application configuration with Effect.

## Config Module Basics

```typescript
import { Config, Effect, Layer } from "effect";

// Simple config values
const port = Config.integer("PORT");
const apiKey = Config.string("API_KEY");
const debug = Config.boolean("DEBUG");

// With defaults
const portWithDefault = Config.integer("PORT").pipe(Config.withDefault(3000));

// Optional config
const optionalApiKey = Config.string("API_KEY").pipe(Config.option);

// Run to get config
const program = Effect.gen(function* () {
  const port = yield* Config.integer("PORT");
  const debug = yield* Config.boolean("DEBUG").pipe(Config.withDefault(false));
  return { port, debug };
});
```

## Structured Configuration

### Config.all - Combine configs

```typescript
const AppConfig = Config.all({
  server: Config.all({
    port: Config.integer("PORT").pipe(Config.withDefault(3000)),
    host: Config.string("HOST").pipe(Config.withDefault("0.0.0.0")),
  }),
  database: Config.all({
    url: Config.string("DATABASE_URL"),
    poolSize: Config.integer("DB_POOL_SIZE").pipe(Config.withDefault(10)),
    ssl: Config.boolean("DB_SSL").pipe(Config.withDefault(true)),
  }),
  features: Config.all({
    enableBeta: Config.boolean("ENABLE_BETA").pipe(Config.withDefault(false)),
    maxRetries: Config.integer("MAX_RETRIES").pipe(Config.withDefault(3)),
  }),
});

// Type is inferred:
// { server: { port: number, host: string }, database: { url: string, ... }, ... }
```

### Config as Service

```typescript
class AppConfig extends Context.Tag("AppConfig")<
  AppConfig,
  {
    readonly apiBaseUrl: string;
    readonly timeout: number;
    readonly debug: boolean;
  }
>() {}

const AppConfigLive = Layer.effect(
  AppConfig,
  Config.all({
    apiBaseUrl: Config.string("API_BASE_URL"),
    timeout: Config.integer("TIMEOUT").pipe(Config.withDefault(5000)),
    debug: Config.boolean("DEBUG").pipe(Config.withDefault(false)),
  }),
);

// Usage
const program = Effect.gen(function* () {
  const config = yield* AppConfig;
  console.log(`API URL: ${config.apiBaseUrl}`);
});
```

## Config Providers

### Default: Environment variables

```typescript
// Reads from process.env
const port = yield * Config.integer("PORT");
// Reads PORT from environment
```

### Custom providers

```typescript
import { ConfigProvider } from "effect";

// From a Map
const mapProvider = ConfigProvider.fromMap(
  new Map([
    ["PORT", "3000"],
    ["DEBUG", "true"],
  ]),
);

// From JSON object
const jsonProvider = ConfigProvider.fromJson({
  PORT: 3000,
  DEBUG: true,
});

// Use with layer
const ConfigProviderLayer = Layer.setConfigProvider(mapProvider);
```

### Chained providers (Union Labs Pattern)

```typescript
// Priority: URL params → Environment → Defaults
const urlParams = new URLSearchParams(window.location.search);

const ConfigProviderLive = Layer.setConfigProvider(
  ConfigProvider.fromMap(new Map(urlParams.entries())).pipe(
    ConfigProvider.orElse(() => ConfigProvider.fromEnv()),
  ),
);

// Now configs check URL params first, then env vars
const program = Effect.gen(function* () {
  const apiUrl = yield* Config.string("API_URL");
  // Checks ?API_URL=... first, then process.env.API_URL
}).pipe(Effect.provide(ConfigProviderLive));
```

### Nested config with prefix

```typescript
const dbConfig = Config.all({
  host: Config.string("HOST"),
  port: Config.integer("PORT"),
  name: Config.string("NAME"),
}).pipe(Config.nested("DATABASE"));

// Reads DATABASE_HOST, DATABASE_PORT, DATABASE_NAME
```

## Schema-Validated Config

```typescript
import { Schema } from "effect";

const AppConfigSchema = Schema.Struct({
  api: Schema.Struct({
    baseUrl: Schema.String.pipe(Schema.pattern(/^https?:\/\//)),
    timeout: Schema.Number.pipe(Schema.positive(), Schema.int()),
  }),
  database: Schema.Struct({
    url: Schema.String,
    maxConnections: Schema.Number.pipe(Schema.between(1, 100)),
  }),
  features: Schema.Struct({
    enableCache: Schema.Boolean,
    cachesTtl: Schema.Number.pipe(Schema.positive()),
  }),
});

type AppConfigType = Schema.Schema.Type<typeof AppConfigSchema>;

// Load and validate
const loadConfig = Effect.gen(function* () {
  const raw = yield* Effect.tryPromise(() =>
    fetch("/config.json").then((r) => r.json()),
  );
  return yield* Schema.decodeUnknown(AppConfigSchema)(raw);
});
```

## Environment-Specific Config

```typescript
type Environment = "development" | "staging" | "production";

const getEnv = (): Environment => {
  const env = process.env.NODE_ENV;
  if (env === "production") return "production";
  if (env === "staging") return "staging";
  return "development";
};

const createConfigLayer = (env: Environment) => {
  const baseConfig = {
    development: {
      apiUrl: "http://localhost:3000",
      logLevel: "debug",
      enableMocks: true,
    },
    staging: {
      apiUrl: "https://staging-api.example.com",
      logLevel: "info",
      enableMocks: false,
    },
    production: {
      apiUrl: "https://api.example.com",
      logLevel: "warn",
      enableMocks: false,
    },
  }[env];

  return Layer.succeed(AppConfig, baseConfig);
};

const AppConfigLive = createConfigLayer(getEnv());
```

## Secret Management

```typescript
import { Secret, Config } from "effect";

// Secrets are redacted in logs
const apiKey = Config.secret("API_KEY");
// Type: Config<Secret.Secret>

const program = Effect.gen(function* () {
  const secret = yield* Config.secret("API_KEY");

  // Access the actual value
  const value = Secret.value(secret);

  // Safe to log - shows "Secret(<redacted>)"
  console.log(secret);
});
```

## Config Patterns

### Required vs optional

```typescript
const config = Config.all({
  // Required - fails if missing
  apiKey: Config.string("API_KEY"),

  // Optional - returns Option
  analyticsId: Config.string("ANALYTICS_ID").pipe(Config.option),

  // Default - uses fallback if missing
  port: Config.integer("PORT").pipe(Config.withDefault(3000)),

  // Secret - redacted in logs
  dbPassword: Config.secret("DB_PASSWORD"),
});
```

### Validation

```typescript
const validatedPort = Config.integer("PORT").pipe(
  Config.validate({
    message: "PORT must be between 1 and 65535",
    validation: (port) => port >= 1 && port <= 65535,
  }),
);

const validatedUrl = Config.string("API_URL").pipe(
  Config.validate({
    message: "API_URL must be a valid HTTPS URL",
    validation: (url) => url.startsWith("https://"),
  }),
);
```

### Config from file

```typescript
const loadConfigFile = (path: string) =>
  Effect.gen(function* () {
    const content = yield* Effect.tryPromise(() =>
      fs.promises.readFile(path, "utf-8"),
    );

    const json = yield* Effect.try(() => JSON.parse(content));

    return yield* Schema.decodeUnknown(AppConfigSchema)(json);
  });

const AppConfigLive = Layer.effect(
  AppConfig,
  loadConfigFile("./config.json").pipe(
    Effect.catchAll(() =>
      // Fallback to environment variables
      Config.all({
        apiUrl: Config.string("API_URL"),
        port: Config.integer("PORT").pipe(Config.withDefault(3000)),
      }),
    ),
  ),
);
```

### Dynamic config reloading

```typescript
class ConfigService extends Context.Tag("ConfigService")<
  ConfigService,
  {
    readonly get: () => Effect.Effect<AppConfig>;
    readonly reload: () => Effect.Effect<void>;
  }
>() {}

const ConfigServiceLive = Layer.effect(
  ConfigService,
  Effect.gen(function* () {
    const configRef = yield* Ref.make<AppConfig>(yield* loadConfig());

    return {
      get: () => Ref.get(configRef),
      reload: () =>
        loadConfig().pipe(
          Effect.flatMap((newConfig) => Ref.set(configRef, newConfig)),
        ),
    };
  }),
);

// Reload on SIGHUP
process.on("SIGHUP", () => {
  runtime.runPromise(
    Effect.gen(function* () {
      const configService = yield* ConfigService;
      yield* configService.reload();
      yield* Effect.log("Config reloaded");
    }),
  );
});
```

## Complete Example

```typescript
// config.ts
import { Config, Layer, Effect, Schema, Secret } from "effect";

// Schema for validation
const DatabaseConfig = Schema.Struct({
  host: Schema.String,
  port: Schema.Number.pipe(Schema.int(), Schema.between(1, 65535)),
  database: Schema.String,
  username: Schema.String,
});

// Service definition
class AppConfig extends Context.Tag("AppConfig")<
  AppConfig,
  {
    readonly server: { port: number; host: string };
    readonly database: Schema.Schema.Type<typeof DatabaseConfig>;
    readonly apiKey: Secret.Secret;
    readonly features: { enableCache: boolean; cacheTtl: number };
  }
>() {}

// Layer implementation
const AppConfigLive = Layer.effect(
  AppConfig,
  Effect.gen(function* () {
    const server = yield* Config.all({
      port: Config.integer("PORT").pipe(Config.withDefault(3000)),
      host: Config.string("HOST").pipe(Config.withDefault("0.0.0.0")),
    });

    const database = yield* Config.all({
      host: Config.string("DB_HOST"),
      port: Config.integer("DB_PORT").pipe(Config.withDefault(5432)),
      database: Config.string("DB_NAME"),
      username: Config.string("DB_USER"),
    });

    // Validate database config
    yield* Schema.decodeUnknown(DatabaseConfig)(database);

    const apiKey = yield* Config.secret("API_KEY");

    const features = yield* Config.all({
      enableCache: Config.boolean("ENABLE_CACHE").pipe(
        Config.withDefault(true),
      ),
      cacheTtl: Config.integer("CACHE_TTL").pipe(Config.withDefault(3600)),
    });

    return { server, database, apiKey, features };
  }),
);

export { AppConfig, AppConfigLive };
```
