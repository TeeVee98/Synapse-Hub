# Contributing to Synapse-Hub

[🇻🇳 Tiếng Việt](CONTRIBUTING.md) | [🇬🇧 English Edition](CONTRIBUTING.en.md)

We welcome contributions to expand and refine skills, tools, and rules in the **Synapse-Hub** ecosystem. All contributions must adhere to our **Truth Anchor** (no fake passes) and **Token-Efficiency** standards.

---

## 1. Skill Authoring Standards

Every skill resides in `.agents/skills/<skill-name>/` and must satisfy:

1. **`SKILL.md` Structure:**
   - Must contain valid YAML frontmatter with `name` and `description`.
   - `name` must exactly match the directory name in kebab-case.
   - `description` must clearly articulate the triggering scope and disambiguate itself from adjacent skills.
2. **Conciseness & Token Budget:**
   - Write instructions in concise technical English to minimize LLM token consumption.
   - Use progressive disclosure: keep `SKILL.md` between 40 and 150 lines, and offload deep code patterns to `references/` or `examples/`.
3. **Zero Project Coupling:**
   - Never hardcode specific project names, proprietary URLs, test credentials, or internal namespaces.
   - Always use generic placeholders: `<project_namespace>`, `https://app.example.com`, `APP_PASSWORD`.

---

## 2. Integrity Verification Workflow

Before submitting a pull request or committing changes:

```bash
# 1. Run regression test suite (770+ tests)
pytest tests -q

# 2. Verify all 10 DoD Quality Gates (Gate 1–10)
python3 tools/verify_all.py

# 3. Test documentation and entity references integrity
python3 tools/lint_ai_docs.py
```

---

## 3. Tool Development Guidelines

All helper scripts in `tools/` must:
1. **Rely on Standard Libraries:** Minimize third-party package dependencies so tools execute seamlessly across clean host machines and CI pipelines.
2. **Be Fast & Non-Blocking:** AST scans and regex lookups must complete in under 500ms.
3. **Zero Test File Pollution:** Tests must use `tempfile.TemporaryDirectory()` and never write temporary test artifacts to the repository tree.
4. **Handle Errors Gracefully:** Provide clear remedies and pointers rather than dumping raw stack traces.
