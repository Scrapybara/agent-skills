# Effect.ts

Comprehensive Effect.ts skill for AI coding agents. Provides typed functional effects, dependency injection, error handling, and resilient async operations patterns.

## Structure

- `SKILL.md` - Main skill instructions with decision trees and quick reference
- `references/` - Deep-dive reference documentation
  - `core/` - Core concepts (creating effects, composition, error handling, resources)
  - `services/` - Dependency injection (services, layers, runtime)
  - `patterns/` - Production patterns (HTTP clients, config, retry, concurrency)
  - `gotchas.md` - Common pitfalls and how to avoid them

## When to Use

- Writing or reviewing Effect-based TypeScript code
- Migrating from raw Promises to Effect.ts
- Implementing services with typed errors and dependency injection
- Adding retry logic, resilience, or structured concurrency
- Building HTTP API clients with Effect

## Core Concepts

- **Effect<Success, Error, Requirements>** - The core type
- **Generator syntax** - `Effect.gen(function* () { ... })` for readable code
- **Tagged errors** - `Data.TaggedError` for typed error handling
- **Services & Layers** - `Context.Tag` + `Layer` for dependency injection
- **Schedules** - `Schedule` for retry/repeat policies

## Reading Order

| Task                  | Start With                          | Then Read           |
| --------------------- | ----------------------------------- | ------------------- |
| Learning Effect       | core/README → core/creating-effects | core/composition    |
| Adding error handling | core/error-handling                 | gotchas             |
| Setting up DI         | services/README → services/layers   | services/runtime    |
| Building HTTP client  | patterns/http-clients               | patterns/retry      |
| Production setup      | patterns/config                     | services/runtime    |
| Debugging issues      | gotchas                             | core/error-handling |
