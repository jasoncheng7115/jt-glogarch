# jt-glogarch Operation Audit — Tracked Operations

**Language**: **English** | [繁體中文](AUDIT-OPERATIONS-zh_TW.md)

jt-glogarch's Operation Audit tracks Graylog API operations via nginx reverse proxy syslog.
Only meaningful user operations are recorded — background polling, status checks, and static assets are automatically filtered out.

---

## Sensitive Operations (⚠)

These operations trigger notification alerts when `op_audit.alert_sensitive` is enabled.

| Category | Operation | Description |
|----------|-----------|-------------|
| **Authentication** | `auth.login` | User login |
| | `auth.logout` | User logout |
| **User Management** | `user.create` | Create user account |
| | `user.modify` | Modify user (password, permissions, status) |
| | `user.delete` | Delete user account |
| **Input Management** | `input.create` | Create input |
| | `input.modify` | Modify input configuration |
| | `input.delete` | Delete input |
| | `input.start` | Start / restart input |
| | `input.stop` | Stop input |
| **Stream Management** | `stream.create` | Create stream |
| | `stream.delete` | Delete stream |
| | `stream.pause` | Pause stream |
| | `stream.resume` | Resume stream |
| | `stream.bulk` | Bulk delete / pause / resume streams |
| **Index Set** | `indexset.create` | Create index set |
| | `indexset.modify` | Modify index set settings |
| | `indexset.delete` | Delete index set |
| **Index Operations** | `index.delete` | Delete an index |
| | `index.close` | Close an index |
| | `index.reopen` | Reopen an index |
| | `deflector.cycle` | Cycle deflector (force index rotation) |
| **Pipeline** | `pipeline.create` | Create pipeline |
| | `pipeline.modify` | Modify pipeline |
| | `pipeline.delete` | Delete pipeline |
| | `pipeline_rule.create` | Create pipeline rule |
| | `pipeline_rule.modify` | Modify pipeline rule |
| | `pipeline_rule.delete` | Delete pipeline rule |
| | `pipeline.connect` | Connect streams to pipeline |
| **Event / Alert** | `event.create` | Create event definition |
| | `event.modify` | Modify event definition |
| | `event.delete` | Delete event definition |
| | `event_notif.create` | Create event notification |
| | `event_notif.modify` | Modify event notification |
| | `event_notif.delete` | Delete event notification |
| **Dashboard / View** | `view.create` | Create dashboard or saved search |
| | `view.modify` | Modify dashboard (widgets, layout) |
| | `view.delete` | Delete dashboard or saved search |
| **System** | `cluster_config.modify` | Modify cluster configuration |
| | `cluster_config.delete` | Delete cluster configuration |
| | `field_mapping.modify` | Change field type mapping |
| | `processing.pause` | Pause message processing |
| | `processing.resume` | Resume message processing |
| | `processing.config` | Change message processor configuration |
| | `system.shutdown` | Shut down Graylog node |
| **Auth Service** | `auth_service.create` | Create authentication service (LDAP, SSO) |
| | `auth_service.modify` | Modify authentication service |
| | `auth_service.delete` | Delete authentication service |
| | `auth_service.activate` | Activate authentication service |
| | `auth_service.deactivate` | Deactivate authentication service |

---

## Normal Operations

These operations are recorded but do not trigger alerts.

| Category | Operation | Description |
|----------|-----------|-------------|
| **Search** | `search.create` | Create a new search definition (contains the query) |
| | `search.update` | Update an existing search definition (contains the query) |
| | `search.execute` | Execute a search query (sync or universal API only) |
| | `search.export` | Export search results (CSV download) |
| **Dashboard / View** | `view.open` | Open a dashboard or saved search |
| **Stream** | `stream.modify` | Modify stream settings |
| | `stream.clone` | Clone a stream |
| | `stream_rule.create` | Create stream rule |
| | `stream_rule.modify` | Modify stream rule |
| | `stream_rule.delete` | Delete stream rule |
| **Role** | `role.create` | Create role |
| | `role.modify` | Modify role |
| | `role.delete` | Delete role |
| **Sharing** | `share.modify` | Change entity sharing permissions |
| **Extractor** | `extractor.create` | Create extractor on input |
| | `extractor.modify` | Modify extractor |
| | `extractor.delete` | Delete extractor |
| **Lookup Table** | `lookup_table.create` | Create lookup table |
| | `lookup_table.modify` | Modify lookup table |
| | `lookup_table.delete` | Delete lookup table |
| **Lookup Adapter** | `lookup_adapter.create` | Create data adapter |
| | `lookup_adapter.modify` | Modify data adapter |
| | `lookup_adapter.delete` | Delete data adapter |
| **Lookup Cache** | `lookup_cache.create` | Create cache |
| | `lookup_cache.modify` | Modify cache |
| | `lookup_cache.delete` | Delete cache |
| **Content Pack** | `content_pack.install` | Install content pack |
| | `content_pack.delete` | Delete content pack |
| **Grok Pattern** | `grok.create` | Create grok pattern |
| | `grok.modify` | Modify grok pattern |
| | `grok.delete` | Delete grok pattern |
| **Output** | `output.create` | Create output |
| | `output.modify` | Modify output |
| | `output.delete` | Delete output |
| **Sidecar** | `sidecar.create` | Create sidecar collector or configuration |
| | `sidecar.modify` | Modify sidecar collector or configuration |
| | `sidecar.delete` | Delete sidecar collector or configuration |

> **Note on search operations:** When a user searches in the Graylog UI, two API calls are made: (1) create/update the search definition (contains the actual query), then (2) execute it (only contains `global_override`). Only `search.create`/`search.update` is recorded — the subsequent execute call is filtered out to avoid duplicate entries. The `search.execute` operation is only recorded for direct API searches (sync or universal endpoints).

---

## Not Tracked (Filtered)

The following are **not recorded** to avoid noise:

- Background polling (metrics, cluster health, throughput, journal status)
- Session heartbeats and validation
- System status and notification checks
- Static assets (CSS, JS, images)
- Read-only list/get operations (except `view.open` and `search.execute`)
- Field type queries, codec/input type lookups
- Graylog internal API calls (migration, telemetry, startpage)

---

## Username Resolution

| Auth Method | How username is resolved |
|-------------|------------------------|
| **Basic Auth** (username:password) | Extracted from `Authorization` header |
| **Token Auth** (token:token) | Resolved via Graylog Users API (per-user token endpoint) |
| **Session Auth** (Authorization header) | Session ID resolved via Graylog Sessions API |
| **Session Cookie** (browser, `$cookie_authentication`) | Session ID extracted from cookie, resolved via API |
| **No auth header and no cookie** | Matched by client IP from previous login record |

> When only one human Graylog user account exists, all operations are automatically attributed to that user.
>
> **Important:** The nginx `log_format` must include `"http_cookie":"$cookie_authentication"` to capture the Graylog session cookie. Without this field, browser requests from multiple users sharing the same client IP cannot be distinguished reliably.
