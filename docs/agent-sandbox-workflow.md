# Agent Sandbox Workflow

Use this workflow when an AI agent needs room to experiment without risking the stable `main` checkout.

## When To Use It

Use a sandbox for:

- Competing UI directions or visual polish experiments.
- Risky refactors of `frontend/pages/forge.html`, auth, persistence, provider proxy, quota, or deployment behavior.
- Broad audits where separate agents inspect independent surfaces.
- Dependency-heavy work where a disposable container keeps the host clean.

Skip it for:

- Tiny copy edits.
- Small, targeted fixes already understood by the main agent.
- Any task where the extra branch and merge overhead is larger than the change.

## Recommended Pattern

1. Keep `C:\Dev\Mnemorized` as the source-of-truth repo on `main`.
2. Create one worktree per agent or experiment:

   ```powershell
   .\tools\New-MnemorizedAgentWorktree.ps1 -Name ui-polish
   ```

3. Give each agent one bounded lane and a disjoint write scope.
4. Review the worktree diff from the main repo before integrating:

   ```powershell
   git -C C:\Dev\Mnemorized-agent-worktrees\ui-polish status --short
   git -C C:\Dev\Mnemorized-agent-worktrees\ui-polish diff
   ```

5. Integrate only the useful changes into `main`, then run validation from the main repo.
6. Remove the worktree when finished:

   ```powershell
   .\tools\Remove-MnemorizedAgentWorktree.ps1 -NameOrPath ui-polish -DeleteBranch
   ```

## Main-Agent Responsibilities

The main agent keeps ownership of:

- Product and architecture decisions.
- Provider proxy safety, auth, Supabase persistence, quota, usage logging, secrets, Render, and production config.
- Final integration, validation, commits, and pushes to `origin/main`.

Subagents should return concise evidence:

- Files inspected or changed.
- Line references where possible.
- Validation run.
- Uncertainty or untested paths.

## Good Agent Lanes

- Explorer: review `backend/app/main.py` for one auth, quota, or persistence risk.
- Explorer: inspect `frontend/pages/library.html` for save/load or responsive issues.
- Explorer: inspect service worker and deployment behavior.
- Worker: update only tests under `tests/`.
- Worker: polish only `frontend/styles/app-shell.css`.
- Worker: patch one extracted frontend script under `frontend/scripts/`.

## Bad Agent Lanes

- "Fix the app."
- "Make the UI premium."
- "Rewrite auth, library, and deployment together."
- Multiple workers editing `frontend/pages/forge.html` at the same time.

## Optional Docker / Dev Container

Use Docker when an agent needs a clean dependency environment or stronger process isolation. The repo includes `.devcontainer/devcontainer.json` for editors that support Dev Containers.

For a disposable CLI container:

```powershell
docker run --rm -it `
  --name mnemorized-agent `
  --cpus=4 `
  --memory=8g `
  -p 8001:8001 `
  -v "${PWD}:/workspace" `
  -w /workspace `
  python:3.12-bookworm bash
```

Inside the container:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001
```

Do not copy real secrets into containers unless the task explicitly requires provider, Supabase, or production-like validation.
