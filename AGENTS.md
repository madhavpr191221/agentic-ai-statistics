# Project working agreement

This repository is a statistical performance study of agentic AI systems. The software exists to create trustworthy measurements; metrics, experimental design, and statistical interpretation take priority over framework novelty.

## Phase workflow

1. Develop each phase on a named `phase/...` branch.
2. Include a React/TypeScript UI for every user-testable phase. The UI is the primary demonstration surface; a CLI may also be retained.
3. Test the measurement logic, API, UI components, and complete browser workflow before declaring the phase complete.
4. Update the research and implementation documentation with the measurement boundary, results, and limitations.
5. Merge the completed phase into the permanent cumulative `demo` branch using `--no-ff`, then push both branches.
6. Preserve phase branches for inspection. Do not merge to `main`, delete branches, or rewrite history without explicit direction.

## Definition of done

```powershell
uv --cache-dir .uv-cache lock --check
uv --cache-dir .uv-cache sync --locked --all-groups --check
uv --cache-dir .uv-cache run pytest -q
uv --cache-dir .uv-cache run ruff check .
uv --cache-dir .uv-cache run mypy src
npm test
npm run build
npm run test:e2e
git diff --check
```

The UI must distinguish measured quantities from unavailable or inferred quantities. Never invent transport bytes, end-to-end latency, queueing time, or independence assumptions that the instrumentation cannot support.
