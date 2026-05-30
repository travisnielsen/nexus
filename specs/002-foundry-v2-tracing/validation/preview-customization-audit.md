# Preview Customization Audit

## Retained

- Instance-level AG-UI context synchronization wrapper in patches/agui_event_stream.py.

## Retired / Disabled by Default

- Global class monkey patch toggle PATCH_AGUI_CONTEXT_SYNC now defaults to false.

## Rationale

Current supported Agent Framework and telemetry behavior no longer requires global patching for normal operation, while instance-level synchronization preserves required activeFilter behavior.
