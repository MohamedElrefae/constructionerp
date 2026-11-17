# Dashboard operational source

These are the existing dashboard operating tools recovered into the app so fixes have one versioned source. They support the installed guarded dashboard; they do not replace the orchestration engine or enable production builder dispatch.

- `automatic_dashboard.py` starts only after clean, idle state admission and retains source, owner, authority-lease and startup checks.
- `fresh_restart_plan.py` validates an installed source manifest, seals current state and records an observed ready owner. It never invents ownership, resets authentication or restores an old database.
- `tools/refresh_catalog.mjs` reads the T3 registry using an explicitly provisioned read-only credential; `tools/publish_catalog.py` writes an allowlist snapshot atomically. It imports the app's `dashboard.catalog_files` helper.
- `catalogue_expiry_warning.py` reads expiry metadata only. `rotate_catalogue_credential.py` is an explicit operator action; merely installing or importing it never issues or renews a credential.
- `automatic_alert.py` reports a stopped or refused service.

Private policy, owner receipts, state and installed Python dependencies belong under the bench's `runtime/dashboard`, not in this source folder. The credential remains under the user's private state directory. The rotation tool derives the bench from its app checkout; `T3_DASHBOARD_RUNTIME` can explicitly select a different runtime root. The tools retain their existing local user-service names.

The current immutable UI snapshot predates the merged builder integration. Its guarded launch packages remain installed dependencies. Rebuilding and qualifying a live release from the consolidated app is still production work; the existence of these scripts is not a production-readiness claim. See `docs/ai/t3-integration-handover/README.md`.
