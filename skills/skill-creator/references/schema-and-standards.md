# Skill Schema & Directives Standard

## 1. Naming & Frontmatter Requirements

- **Skill Name (`name`)**: MUST use lowercase kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`). NEVER use underscores, camelCase, or uppercase characters.
- **Description (`description`)**:
  - MUST state exact trigger scenarios in third-person.
  - MUST specify concrete intent phrases, tool names, or file types that invoke the skill.
  - MUST remain under 80 words to conserve startup context.
  - NEVER include step-by-step procedures in the frontmatter description.

## 2. Token Budget & Directory Structure

- **`SKILL.md` Budget**: MUST NOT exceed 200 lines. Heavy manuals, schemas, and API definitions MUST reside in `references/`.
- **`scripts/` Directory**: Complex bash/python workflows MUST be extracted into executable scripts rather than inlined as fragile multi-line shell strings.
- **`references/` Directory**: Supplementary architectural diagrams, JSON schemas, and API endpoints. Linked relatively from `SKILL.md`.
- **`examples/` Directory**: Concrete input/output pairs, edge cases, and anti-patterns.

## 3. Imperative Language Standards

- **Directive Keywords**: Instructions MUST exclusively use `ALWAYS`, `NEVER`, and `MUST`.
- **Forbidden Phrases**: NEVER use hedging or advisory language (`should`, `could`, `might`, `try to`, `please`, `consider`).
- **Failure Handlers**: Every action step MUST specify failure handling deterministically (e.g., *"If exit code != 0, MUST halt and report stderr"*).
