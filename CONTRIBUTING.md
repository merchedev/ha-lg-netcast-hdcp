# Contributing

Thanks for helping improve the LG NetCast HDCP integration. This project is
small and deliberately local-only.

## Before you start

Read [AGENTS.md](AGENTS.md) for the project rules. In particular:

- Work on the `AI-Developer` branch.
- Use English for code, comments, documentation, tests, and commit messages.
- Keep changes focused.
- Never commit or log a pairing key or session ID.
- Use async code and Home Assistant helpers.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt ruff
```

Run the checks before committing:

```bash
ruff check .
ruff format --check .
pytest
```

Useful commands:

```bash
pytest -q
pytest --cov=custom_components.lg_netcast_hdcp --cov-report=term-missing
ruff format .
```

## Protocol work

Protocol changes must be verified against a real TV when possible. Record new
key codes or state behavior in [docs/keycodes.md](docs/keycodes.md) or
[docs/protocol.md](docs/protocol.md).

Do not add unverified raw codes. Use named keys for confirmed three-digit
direct-input codes.

## Adding a model profile

Model-specific behavior should live in `profiles.py`, not in the integration
logic. A profile owns:

- the key map;
- direct-input keys;
- invalid channel and physical-number sentinel values;
- the no-subchannel sentinel.

If you add a model, add tests and a note to the README and docs.

## Documentation

Documentation is task-first and written in plain English:

- say what the reader needs before the steps;
- use numbered steps;
- show a result or check after important steps;
- include copyable code blocks;
- add a troubleshooting section for each device or workflow;
- do not rely on color alone;
- keep source names and examples short.

Update the docs when behavior changes. Relevant files:

- `README.md` — landing page and quick start;
- `docs/configuration.md` — options and workflows;
- `docs/ir-receiver.md` — wiring, ESPHome, code capture;
- `docs/state-and-dashboard.md` — attributes and cards;
- `docs/troubleshooting.md` — symptom/cause/fix;
- `docs/faq.md` — short answers;
- `docs/protocol.md` and `docs/keycodes.md` — protocol details.

## Release process

1. Verify the change on a real TV when it touches the protocol layer.
2. Update `custom_components/lg_netcast_hdcp/manifest.json` and
   `pyproject.toml`.
3. Add a `CHANGELOG.md` section for the version.
4. Commit with `AI: release vX.Y.Z`.
5. Tag `vX.Y.Z` and push the tag.
6. The release workflow verifies the code, tests, hassfest, and HACS validation,
   extracts the matching CHANGELOG section, and publishes the GitHub release.

The release body is the changelog section, so it appears in the Home Assistant
update dialog.

## Issue reports

Use the bug report template. Include:

- integration version;
- Home Assistant version;
- TV model and firmware;
- whether IR, CEC, or Wake-on-LAN is configured;
- debug logs;
- diagnostics after reviewing them.

Never include a pairing key, session ID, full `.storage` file, or an
unredacted backup.
