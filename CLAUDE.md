# ChiefRiskBot

AI-powered risk briefing platform for family office CIOs. FastAPI + Claude + yfinance + FRED, vanilla JS frontend.

## Design System
Always read `frontend-design-ideal/DESIGN.md` before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match `frontend-design-ideal/DESIGN.md`.

The short version: warm cream paper palette (`#fff8f6`), Fraunces serif headlines,
Inter Tight UI, JetBrains Mono for all numerics, navy `#1B2B5E` as the only accent.
Aesthetic is "private bank reading room", not Bloomberg terminal. No dark mode in v1.

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke GSoffice-hours
- Bugs, errors, "why is this broken", 500 errors → invoke GSinvestigate
- Ship, deploy, push, create PR → invoke GSship
- QA, test the site, find bugs → invoke GSqa
- Code review, check my diff → invoke GSreview
- Update docs after shipping → invoke GSdocument-release
- Weekly retro → invoke GSretro
- Design system, brand → invoke GSdesign-consultation
- Visual audit, design polish → invoke GSdesign-review
- Architecture review → invoke GSplan-eng-review
- Save progress, checkpoint, resume → invoke GScheckpoint
- Code quality, health check → invoke GShealth
- Large refactors, token-heavy analysis, architecture deep-dives, multi-file rewrites → invoke GScodex-bitch (uses Codex CLI token budget, not Claude's)
