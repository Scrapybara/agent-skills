# Agent Skills

A collection of skills for AI coding agents by [Capy](https://capy.ai).

Skills follow the [Agent Skills](https://skills.sh/) format.

## Available Skills

### effect-ts

Effect.ts patterns for typed functional effects, dependency injection, error handling, and resilient async operations.

**Use when:**
- Writing or reviewing Effect-based TypeScript code
- Migrating from Promises to Effect.ts
- Implementing services with typed errors and dependency injection
- Adding retry logic, resilience, or structured concurrency
- Building HTTP API clients with Effect

**Topics covered:**
- Core concepts (creating effects, composition, error handling, resources)
- Services & dependency injection (Context.Tag, Layers, Runtime)
- Production patterns (HTTP clients, configuration, retry, concurrency)
- Common gotchas and troubleshooting

## Installation

```bash
npx skills add scrapybara/agent-skills
```

## Usage

Skills are automatically available once installed. The agent will use them when relevant tasks are detected.

**Examples:**
```
Help me build an Effect.ts service with dependency injection
```
```
Add retry logic with exponential backoff to this API call
```
```
Migrate this Promise-based code to Effect.ts
```

## Skill Structure

Each skill contains:
- `SKILL.md` - Instructions for the agent
- `references/` - Supporting documentation
- `metadata.json` - Version and metadata
- `README.md` - Human-readable overview

## License

MIT
