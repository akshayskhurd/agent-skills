# Example: Minimal Production Skill

```markdown
---
name: run-db-migrate
description: >-
  Use this skill when executing database migrations, rollbacks, or validating Prisma schema integrity.
---

# Database Migration Workflow

Deterministic execution flow for database migrations.

## 1. Prerequisites
- MUST confirm active database connection: `pg_isready -h localhost -p 5432`
- MUST verify git tree is clean: `git diff-index --quiet HEAD --`

## 2. Execution Steps
1. Generate migration diff:
   `npx prisma migrate diff --from-schema-datamodel schema.prisma --to-schema-datasource schema.prisma --script`
2. Run migration:
   `npx prisma migrate deploy`

## 3. Verification
- MUST query migration log table: `npx prisma migrate status`
- NEVER proceed if status indicates unapplied migrations.
```
