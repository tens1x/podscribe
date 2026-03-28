# Packaging Notes

This project stores user secrets and runtime state locally. Do not include those files in git commits or packaged app bundles.

## Never package these paths

- Project-local env files:
  - `.env`
  - `.env.*` except `.env.example`
- Project runtime state:
  - `.podscribe/`
- Local virtual environment:
  - `venv/`
- Local outputs and build artifacts:
  - `output/`
  - `build/`
  - `dist/`
- OS/app packaging artifacts:
  - `*.app`
  - `*.dmg`
  - `*.exe`
  - `*.msi`
  - `*.zip`
  - `*.tar.gz`

## User-local data paths

These are created on the user's machine and must stay outside the packaged application:

- Config file with API key:
  - `~/.podscribe/config.json`
- History file:
  - `~/.podscribe/history.json`

## Secret handling

- `DashScope` API keys are read from `DASHSCOPE_API_KEY` or from `~/.podscribe/config.json`.
- Never hardcode API keys into source files.
- Never copy a developer's local `config.json` into a release bundle.

## Packaging rule of thumb

A release bundle should contain only:

- application code
- declared dependencies
- static assets required by the app

It must not contain:

- personal config
- API keys
- local history
- local task state
- local output files
