# Sample Lean Impact Scoreboard

Representative scoreboard displayed by `/synapse-gain`:

```text
================================================================================
Metric                           Baseline (No Skill)      Lean Mode       Delta
================================================================================
Lines of Code Generated          100%                    47%            -53% 📉
Output Tokens Consumed           100%                    55%            -45% 📉
API Cost                         100%                    74%            -26% 📉
Agent Execution Time             100%                    59%            -41% ⚡
Risky Logic Shipped with Tests   68%                     98%            +30% 🛡️
Bug Detection Rate (Mutants)     46%                     66%            +20% 🎯
================================================================================
```

### Explanatory Context
- **Why less code?** Reuses existing codebase helpers, standard libraries, and native platform widgets instead of reinventing wheels.
- **Why more tests?** Enforces the completeness invariant: any non-trivial branch, loop, parser, or security logic must ship with a small test proving edge-case correctness.
