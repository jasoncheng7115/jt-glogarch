# Test Results

| Item | Value |
|---|---|
| **Status** | ✅ ALL PASSED |
| **Version** | v1.18.3 |
| **Date** | 2026-11-06 01:07:10 UTC |
| **Platform** | Python 3.10.12 / Linux 5.15.0-202-generic x86_64 |
| **Results** | 1134 passed  / 1 skipped in 279.22s |
| **Version Check** | ✅ OK |
| **Bandit (source security)** | Bandit: OK (HIGH 0, MEDIUM 0, gated LOW 8/8; 9 LOW total, 1 owned by the except-ratchet sweep) |

## Test Output

```
============================= test session starts ==============================
collecting ... collected 1135 items

tests/test_alerting.py::test_schedule_value_is_the_current_state PASSED
tests/test_alerting.py::test_add_remove_replace_keep_other_entries_untouched PASSED
tests/test_alerting.py::test_action_validation PASSED
tests/test_alerting.py::test_plan_splits_change_unchanged_skipped PASSED
tests/test_alerting.py::test_title_tags PASSED
tests/test_alerting.py::test_disabled_definitions_stay_disabled PASSED
tests/test_alerting.py::test_a_definition_edited_after_the_preview_is_not_overwritten PASSED
tests/test_alerting.py::test_other_fields_edited_meanwhile_are_kept PASSED
tests/test_alerting.py::test_one_failure_does_not_stop_the_rest_and_is_logged 2026-11-06 09:07:37 [warning  ] Alerting change failed         definition=b error='Graylog HTTP 500: boom'
PASSED
tests/test_alerting.py::test_expired_signin_stops_the_batch PASSED
tests/test_alerting.py::test_cancel_stops_between_definitions PASSED
tests/test_alerting.py::test_graylog_storing_a_different_state_is_a_failure_not_a_success 2026-11-06 09:07:38 [warning  ] Alerting change failed         definition=off error='Graylog stored something else: state changed DISABLED -> ENABLED'
PASSED
tests/test_alerting.py::test_undo_restores_and_skips_what_was_changed_since PASSED
tests/test_alerting.py::test_a_change_sent_but_never_confirmed_can_still_be_undone PASSED
tests/test_alerting.py::test_client_sends_schedule_matching_state_and_the_whole_body PASSED
tests/test_alerting.py::test_client_maps_401_and_403 PASSED
tests/test_alerting.py::test_paging_reads_every_definition PASSED
tests/test_alerting.py::test_identity_secret_never_goes_into_the_cookie_session PASSED
tests/test_alerting.py::test_expired_identity_is_not_used PASSED
tests/test_alerting.py::test_valid_until_parsing 2026-11-06 09:07:39 [debug    ] Unreadable Graylog session expiry; assuming the default valid_until=garbage
PASSED
tests/test_alerting.py::test_login_keeps_a_graylog_session_not_the_password PASSED
tests/test_alerting.py::test_token_login_keeps_the_token 2026-11-06 09:07:39 [info     ] No Graylog session for this login (token login, or sessions unavailable) error=no server=log4
PASSED
tests/test_alerting.py::test_no_graylog_identity_asks_to_sign_in_with_403_not_401 PASSED
tests/test_alerting.py::test_preview_then_apply_runs_exactly_the_previewed_plan PASSED
tests/test_alerting.py::test_a_plan_belongs_to_the_browser_session_that_made_it PASSED
tests/test_alerting.py::test_unknown_notification_is_refused PASSED
tests/test_alerting.py::test_undo_through_the_api PASSED
tests/test_alerting.py::test_search_and_quick_filters_in_the_real_js PASSED
tests/test_alerting.py::test_logout_closes_the_graylog_session PASSED
tests/test_alerting.py::test_definition_detail_is_read_live_and_ids_are_checked PASSED
tests/test_alerting.py::test_web_url_from_api_url PASSED
tests/test_alerting.py::test_condition_and_duration_rendering_in_the_real_js PASSED
tests/test_api_error_handling.py::test_index_sets_catches_401 PASSED
tests/test_api_error_handling.py::test_streams_catches_401 PASSED
tests/test_api_error_handling.py::test_index_sets_catches_connection_error PASSED
tests/test_api_error_handling.py::test_streams_catches_connection_error PASSED
tests/test_archive_day_coverage.py::test_empty PASSED
tests/test_archive_day_coverage.py::test_counts_days_that_hold_an_archive_not_the_span PASSED
tests/test_archive_day_coverage.py::test_deleted_archives_do_not_count PASSED
tests/test_archive_day_coverage.py::test_an_archive_longer_than_a_day_covers_the_days_in_between PASSED
tests/test_archive_day_coverage.py::test_end_time_is_exclusive PASSED
tests/test_archive_day_coverage.py::test_gap_list_is_capped PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_scoped_to_time_filter PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_scoped_to_server_and_stream PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_status_completed_excludes_others PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_requires_auth PASSED
tests/test_archive_ids_endpoint.py::test_capacity_estimate_sums_volume_and_reports_fit PASSED
tests/test_archive_ids_endpoint.py::test_capacity_estimate_requires_archive_ids PASSED
tests/test_archive_streaming.py::test_streaming_returns_all_messages_incl_tricky_content 2026-11-06T01:07:49.904975Z [info     ] Archive written                messages=1000 path=/tmp/pytest-of-root/pytest-70/test_streaming_returns_all_mes0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.01
PASSED
tests/test_archive_streaming.py::test_empty_and_single 2026-11-06T01:07:49.985943Z [info     ] Archive written                messages=0 path=/tmp/pytest-of-root/pytest-70/test_empty_and_single0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:07:49.989296Z [info     ] Archive written                messages=1 path=/tmp/pytest-of-root/pytest-70/test_empty_and_single0/b/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
PASSED
tests/test_archive_streaming.py::test_batching_shape 2026-11-06T01:07:49.998799Z [info     ] Archive written                messages=105 path=/tmp/pytest-of-root/pytest-70/test_batching_shape0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
PASSED
tests/test_archive_streaming.py::test_memory_is_bounded_not_whole_file 2026-11-06T01:07:51.248611Z [info     ] Archive written                messages=20000 path=/tmp/pytest-of-root/pytest-70/test_memory_is_bounded_not_who0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.12
PASSED
tests/test_audit.py::test_decode_username_basic PASSED
tests/test_audit.py::test_decode_username_token PASSED
tests/test_audit.py::test_decode_username_session PASSED
tests/test_audit.py::test_decode_username_empty PASSED
tests/test_audit.py::test_classify_sensitive PASSED
tests/test_audit.py::test_classify_not_sensitive PASSED
tests/test_audit.py::test_classify_operation PASSED
tests/test_audit.py::test_parse_syslog_payload PASSED
tests/test_audit.py::test_parse_syslog_hostname PASSED
tests/test_audit.py::test_parse_nginx_json PASSED
tests/test_audit.py::test_process_raw_entry PASSED
tests/test_audit.py::test_process_raw_entry_no_auth PASSED
tests/test_audit.py::test_db_api_audit_insert_and_list PASSED
tests/test_audit.py::test_api_audit_config_default PASSED
tests/test_audit.py::test_api_audit_config_custom_retention PASSED
tests/test_audit.py::test_settings_has_op_audit PASSED
tests/test_audit.py::test_settings_op_audit_from_yaml PASSED
tests/test_audit.py::test_settings_op_audit_missing_retention PASSED
tests/test_audit.py::test_settings_no_op_audit_section PASSED
tests/test_audit.py::test_db_api_audit_stats_all_time PASSED
tests/test_audit.py::test_token_resolve PASSED
tests/test_audit.py::test_notify_event_sensitive PASSED
tests/test_audit.py::test_is_noise_prepare_preview PASSED
tests/test_audit.py::test_is_noise_non_api PASSED
tests/test_audit.py::test_is_noise_whitelisted PASSED
tests/test_audit.py::test_is_noise_unlisted PASSED
tests/test_audit.py::test_cleanup_uses_audit_retention 2026-11-06T01:07:53.144843Z [info     ] No archives to clean up        retention_days=1095
2026-11-06T01:07:53.154643Z [info     ] Cleaned audit records          deleted=1 retention_days=180
2026-11-06T01:07:53.155015Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
2026-11-06T01:07:53.163850Z [info     ] No archives to clean up        retention_days=1095
2026-11-06T01:07:53.164572Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
PASSED
tests/test_audit.py::test_cleanup_audit_no_config 2026-11-06T01:07:53.503080Z [info     ] No archives to clean up        retention_days=1095
2026-11-06T01:07:53.513722Z [info     ] Cleaned audit records          deleted=1 retention_days=180
2026-11-06T01:07:53.514253Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
PASSED
tests/test_audit_coverage.py::test_every_state_changing_route_is_audited PASSED
tests/test_audit_coverage.py::test_destructive_routes_are_audited PASSED
tests/test_audit_coverage.py::test_the_allowlist_does_not_cover_a_route_that_no_longer_exists PASSED
tests/test_audit_coverage.py::test_allowlist_entries_state_a_reason PASSED
tests/test_audit_coverage.py::test_the_internal_audit_log_is_reachable_from_the_ui PASSED
tests/test_audit_coverage.py::test_graylog_stats_are_hidden_on_the_internal_tab PASSED
tests/test_audit_heartbeat.py::test_probe_failure_reason_is_kept_not_debug_dropped PASSED
tests/test_audit_heartbeat.py::test_alert_body_carries_the_reason PASSED
tests/test_audit_heartbeat.py::test_a_single_transient_failure_does_not_alert PASSED
tests/test_audit_heartbeat.py::test_a_successful_probe_clears_the_streak PASSED
tests/test_audit_heartbeat.py::test_streak_state_is_initialised PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[POST-/api/users/local:admin/tokens/backup-tool-user.token_create] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[DELETE-/api/users/local:admin/tokens/aabbccddeeff001122334455-user.token_delete] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[POST-/api/users/admin/tokens/ci%20runner-user.token_create] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[POST-/api/users-user.create] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[PUT-/api/users/admin-user.modify] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[DELETE-/api/users/bob-user.delete] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[PUT-/api/users/admin/password-user.password_change] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[PUT-/api/users/admin/permissions-user.permissions_change] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[DELETE-/api/streams/aabbccddeeff001122334455/rules/rr-stream_rule.delete] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[PUT-/api/streams/aabbccddeeff001122334455/rules/rr-stream_rule.modify] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[DELETE-/api/streams/aabbccddeeff001122334455-stream.delete] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[DELETE-/api/system/indices/index_sets/aabbccddeeff001122334455-indexset.delete] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[PUT-/api/system/inputs/aabbccddeeff001122334455/extractors/xx-extractor.modify] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[DELETE-/api/events/definitions/aabbccddeeff001122334455-event.delete] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[DELETE-/api/system/pipelines/rule/abc-pipeline_rule.delete] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[POST-/api/system/sessions-auth.login] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[DELETE-/api/system/sessions/x-auth.logout] PASSED
tests/test_audit_operation_labels.py::test_operation_is_the_most_specific_match[POST-/api/views/search-search.create] PASSED
tests/test_audit_operation_labels.py::test_token_operations_are_sensitive PASSED
tests/test_audit_operation_labels.py::test_token_target_names_the_token_without_leaking_it PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/users/bob] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[PUT-/api/users/bob] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[POST-/api/users/local:admin/tokens/ci] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/users/local:admin/tokens/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[POST-/api/system/sessions] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/system/sessions/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/streams/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/system/inputs/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[PUT-/api/system/inputs/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/cluster/inputstates/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[PUT-/api/cluster/inputstates/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/system/inputstates/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[PUT-/api/system/inputstates/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[PUT-/api/system/indices/index_sets/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/system/indices/index_sets/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[PUT-/api/system/pipelines/pipeline/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/system/pipelines/pipeline/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[PUT-/api/plugins/org.graylog.plugins.pipelineprocessor/system/pipelines/pipeline/x] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/dashboards/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[PUT-/api/events/definitions/aabbccddeeff001122334455/schedule] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[PUT-/api/events/definitions/aabbccddeeff001122334455/unschedule] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[PUT-/api/events/definitions/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/events/definitions/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[POST-/api/system/authentication/services/backends] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[PUT-/api/system/authentication/services/backends/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[DELETE-/api/system/authentication/services/backends/aabbccddeeff001122334455] PASSED
tests/test_audit_operation_labels.py::test_sensitive_requests_are_stored_and_labelled[POST-/api/system/shutdown/shutdown] PASSED
tests/test_audit_operation_labels.py::test_every_sensitive_pattern_has_a_sample_request PASSED
tests/test_backpressure_stop.py::test_guard_raises_backpressure_stop_and_does_not_notify 2026-11-06T01:08:32.538475Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
2026-11-06T01:08:32.538782Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 99% (over the hard limit 90%)']
2026-11-06T01:08:32.539100Z [error    ] export stopped — backpressure did not clear signals=['JVM heap 99% (over the hard limit 90%)'] waited_sec=60
PASSED
tests/test_backpressure_stop.py::test_api_stop_ends_the_run_not_the_chunk[manual:api-1] 2026-11-06T01:08:33.105605Z [info     ] Export started                 chunks=3 job_id=j1 time_from='2026-07-01 00:00:00' time_to='2026-07-01 03:00:00'
2026-11-06T01:08:33.119210Z [info     ] Total records to export        streams=None time_from='2026-07-01 00:00:00' time_to='2026-07-01 03:00:00' total=3
2026-11-06T01:08:33.139495Z [info     ] Archive written (streaming)    messages=1 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_api_stop_ends_the_run_not0/arch/s1/all/2026/07/01/s1_all_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:08:33.169921Z [error    ] Export failed                  error='Source load did not drain for over 30 minutes (JVM heap 92%) 1 record(s) were archived in this run before the stop and stay archived; the next run continues from there.' job_id=j1
PASSED
tests/test_backpressure_stop.py::test_api_stop_ends_the_run_not_the_chunk[scheduled:api:auto-export-0] 2026-11-06T01:08:33.585957Z [info     ] Export started                 chunks=3 job_id=j1 time_from='2026-07-01 00:00:00' time_to='2026-07-01 03:00:00'
2026-11-06T01:08:33.597712Z [info     ] Total records to export        streams=None time_from='2026-07-01 00:00:00' time_to='2026-07-01 03:00:00' total=3
2026-11-06T01:08:33.609986Z [info     ] Archive written (streaming)    messages=1 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_api_stop_ends_the_run_not1/arch/s1/all/2026/07/01/s1_all_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:08:33.632195Z [error    ] Export failed                  error='Source load did not drain for over 30 minutes (JVM heap 92%) 1 record(s) were archived in this run before the stop and stay archived; the next run continues from there.' job_id=j1
PASSED
tests/test_backpressure_stop.py::test_os_stop_ends_the_run_not_the_index[manual:opensearch-1] 2026-11-06T01:08:33.966207Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-06T01:08:33.966476Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-06T01:08:33.966592Z [info     ] Found indices                  count=3 prefix=graylog
2026-11-06T01:08:33.966677Z [info     ] Skipping active write index    index=graylog_write
2026-11-06T01:08:33.967050Z [info     ] Index time range               docs=6 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-06T01:08:33.967770Z [info     ] Index time range               docs=6 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 02:59:59' index=graylog_1
2026-11-06T01:08:33.977338Z [info     ] Export plan built              grand_total_docs=12 indices=2 prefixes=1
2026-11-06T01:08:33.978084Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-06T01:08:33.995910Z [error    ] OpenSearch export failed       error='Source load did not drain for over 30 minutes (output buffer rising) 0 record(s) were archived in this run before the stop and stay archived; the next run continues from there.'
PASSED
tests/test_backpressure_stop.py::test_os_stop_ends_the_run_not_the_index[scheduled:opensearch:x-0] 2026-11-06T01:08:34.335007Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-06T01:08:34.335239Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-06T01:08:34.335338Z [info     ] Found indices                  count=3 prefix=graylog
2026-11-06T01:08:34.335437Z [info     ] Skipping active write index    index=graylog_write
2026-11-06T01:08:34.335766Z [info     ] Index time range               docs=6 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-06T01:08:34.336511Z [info     ] Index time range               docs=6 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 02:59:59' index=graylog_1
2026-11-06T01:08:34.346655Z [info     ] Export plan built              grand_total_docs=12 indices=2 prefixes=1
2026-11-06T01:08:34.347197Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-06T01:08:34.372437Z [error    ] OpenSearch export failed       error='Source load did not drain for over 30 minutes (output buffer rising) 0 record(s) were archived in this run before the stop and stay archived; the next run continues from there.'
PASSED
tests/test_backpressure_stop.py::test_scheduler_retries_a_stop_once_after_an_hour_then_notifies_once 2026-11-06T01:08:34.378044Z [warning  ] Scheduled export stopped because the source stayed under load; trying once more later retry_in_min=60 schedule=auto-export
2026-11-06T01:08:34.378283Z [error    ] Scheduled export stopped by backpressure; the next scheduled run continues retried=True schedule=auto-export
PASSED
tests/test_backpressure_stop.py::test_scheduler_late_retry_that_succeeds_sends_nothing 2026-11-06T01:08:34.381654Z [warning  ] Scheduled export stopped because the source stayed under load; trying once more later retry_in_min=60 schedule=auto-export
PASSED
tests/test_backpressure_stop.py::test_scheduler_with_late_retry_disabled_stops_at_once 2026-11-06T01:08:34.385178Z [error    ] Scheduled export stopped by backpressure; the next scheduled run continues retried=False schedule=auto-export
PASSED
tests/test_backpressure_stop.py::test_other_failures_keep_the_quick_retries 2026-11-06T01:08:34.389944Z [warning  ] Scheduled export failed, retrying attempt=1 error='database is locked' max=3 retry_in=60
2026-11-06T01:08:34.390214Z [warning  ] Scheduled export failed, retrying attempt=2 error='database is locked' max=3 retry_in=60
2026-11-06T01:08:34.390362Z [error    ] Scheduled export failed after all retries attempts=3 error='database is locked'
PASSED
tests/test_bulk_import.py::test_reserved_fields_stripped PASSED
tests/test_bulk_import.py::test_index_name_is_deflector PASSED
tests/test_bulk_import.py::test_index_name_no_timestamp PASSED
tests/test_bulk_import.py::test_stream_rewrite PASSED
tests/test_bulk_import.py::test_marker_field_injected PASSED
tests/test_bulk_import.py::test_dedup_id_uses_gl2_message_id PASSED
tests/test_bulk_import.py::test_dedup_none_no_id PASSED
tests/test_bulk_import.py::TestTimestampNormalisation::test_iso_z_becomes_native PASSED
tests/test_bulk_import.py::TestTimestampNormalisation::test_iso_without_millis PASSED
tests/test_bulk_import.py::TestTimestampNormalisation::test_timezone_offset_converts_to_utc PASSED
tests/test_bulk_import.py::TestTimestampNormalisation::test_native_format_passes_through_unchanged PASSED
tests/test_bulk_import.py::TestTimestampNormalisation::test_garbage_is_left_for_reconciliation_to_report PASSED
tests/test_bulk_import.py::TestTimestampNormalisation::test_bulk_body_applies_the_normalisation PASSED
tests/test_bulk_streaming.py::test_iter_batches_streams_in_batch_sized_chunks PASSED
tests/test_bulk_streaming.py::test_count_messages_uses_header_not_full_read PASSED
tests/test_bulk_streaming.py::test_import_path_never_calls_whole_file_loader 2026-11-06T01:08:34.458218Z [info     ] Bulk import starting           archives=1 batch_docs=50 indices_to_create=1 target_pattern=graylog total_messages=120
2026-11-06T01:08:34.463834Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-11-06T01:08:34.464107Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.0s failed=0 indexed=120 sent=120
PASSED
tests/test_bulk_streaming.py::test_corrupt_archive_does_not_abort_whole_run 2026-11-06T01:08:34.473475Z [info     ] Bulk import starting           archives=2 batch_docs=5 indices_to_create=1 target_pattern=graylog total_messages=11
2026-11-06T01:08:34.475822Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-11-06T01:08:34.476757Z [info     ] Bulk import completed          archives=2 at_destination=-1 duration=0.0s failed=0 indexed=11 sent=11
PASSED
tests/test_bulk_streaming.py::test_bulk_body_capped_by_bytes_not_just_doc_count PASSED
tests/test_bulk_streaming.py::test_single_oversized_doc_still_sent PASSED
tests/test_bulk_streaming.py::test_byte_cap_loses_no_documents 2026-11-06T01:08:35.358809Z [info     ] Bulk import starting           archives=1 batch_docs=10000 indices_to_create=1 target_pattern=graylog total_messages=400
2026-11-06T01:08:35.650060Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-11-06T01:08:35.650449Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.3s failed=0 indexed=400 sent=400
PASSED
tests/test_cleanup_race.py::test_grace_seconds_defined PASSED
tests/test_cleanup_race.py::test_recent_file_skipped PASSED
tests/test_cleanup_race.py::test_old_file_not_skipped PASSED
tests/test_cleanup_schedule_retention.py::test_schedule_retention_days_is_used 2026-11-06T01:08:35.671194Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=200 retention_source=schedule
PASSED
tests/test_cleanup_schedule_retention.py::test_falls_back_to_config_when_schedule_has_none 2026-11-06T01:08:35.682833Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=1095 retention_source=config.yaml
PASSED
tests/test_cleanup_schedule_retention.py::test_bad_config_json_does_not_break_cleanup 2026-11-06T01:08:35.696727Z [warning  ] Could not read the schedule's retention setting; falling back to config.yaml error='Expecting property name enclosed in double quotes: line 1 column 2 (char 1)' schedule=auto-cleanup
2026-11-06T01:08:35.697362Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=1095 retention_source=config.yaml
PASSED
tests/test_cleanup_schedule_retention.py::test_upgrade_does_not_shorten_retention_and_delete_data 2026-11-06T01:08:35.704607Z [warning  ] Cleanup schedule retention set back to retention.retention_days — it is shorter and was not saved by this version, so it may date from before cleanup schedules honoured their own value, and honouring it now could delete archives that version was keeping. Set it again in the Schedules page if the shorter retention is what you want; from then on it is kept. now_in_force=1095 schedule=auto-cleanup was_shown=200
PASSED
tests/test_cleanup_schedule_retention.py::test_longer_stored_retention_is_kept_it_only_retains_more PASSED
tests/test_cleanup_schedule_retention.py::test_equal_values_are_untouched PASSED
tests/test_cleanup_schedule_retention.py::test_schedule_without_retention_is_untouched PASSED
tests/test_cleanup_schedule_retention.py::test_retention_saved_from_the_ui_survives_a_restart 2026-11-06T01:08:35.731668Z [warning  ] Cleanup schedule retention set back to retention.retention_days — it is shorter and was not saved by this version, so it may date from before cleanup schedules honoured their own value, and honouring it now could delete archives that version was keeping. Set it again in the Schedules page if the shorter retention is what you want; from then on it is kept. now_in_force=1095 schedule=auto-cleanup was_shown=150
PASSED
tests/test_cleanup_schedule_retention.py::test_retention_saved_through_the_api_survives_the_startup_reconciliation 2026-11-06T01:08:36.301515Z [info     ] Schedule registered            cron='0 4 1 * *' cron_aps=None name=auto-cleanup type=cleanup
PASSED
tests/test_clear_index_set_route.py::test_list_index_sets_route_returns_200 PASSED
tests/test_clear_index_set_route.py::test_list_falls_back_to_stored_import_defaults PASSED
tests/test_clear_index_set_route.py::test_masked_password_is_reconciled_not_sent_literally PASSED
tests/test_clear_index_set_route.py::test_clear_requires_matching_confirmation PASSED
tests/test_clear_index_set_route.py::test_clear_refuses_internal_index_set_by_id PASSED
tests/test_clear_index_set_route.py::test_clear_happy_path_keeps_the_write_index 2026-11-06T01:08:44.431694Z [warning  ] Cleared index set before import deleted=1 failed=0 index_set=graylog kept_write_index=graylog_2
PASSED
tests/test_clear_index_set_route.py::test_missing_index_set_id_is_a_400 PASSED
tests/test_clear_index_set_route.py::test_endpoints_require_authentication PASSED
tests/test_cli_commands.py::test_all_commands_registered PASSED
tests/test_cli_commands.py::test_hash_password_help PASSED
tests/test_cli_commands.py::test_root_warning PASSED
tests/test_concurrent_db_writes.py::test_update_schedule_last_run_does_not_race_with_update_job PASSED
tests/test_concurrent_db_writes.py::test_backfill_audit_usernames_locks_against_writers PASSED
tests/test_concurrent_db_writes.py::test_cleanup_stale_running_jobs_marks_running_as_failed PASSED
tests/test_concurrent_db_writes.py::test_backfill_skips_blank_pairs_and_no_default PASSED
tests/test_config.py::test_default_settings PASSED
tests/test_config.py::test_config_search_paths PASSED
tests/test_config.py::test_load_from_file PASSED
tests/test_config.py::test_web_config_local_admin PASSED
tests/test_config.py::test_null_toplevel_keys_use_defaults PASSED
tests/test_config_writer.py::test_update_config_creates_and_preserves_other_keys PASSED
tests/test_config_writer.py::test_update_config_atomic_leaves_no_tempfile PASSED
tests/test_config_writer.py::test_update_config_missing_file_starts_empty PASSED
tests/test_config_writer.py::test_update_config_failure_leaves_original_intact PASSED
tests/test_config_writer.py::test_reconcile_secret_keeps_stored_when_masked_or_empty PASSED
tests/test_config_writer.py::test_mask_output_is_always_recognised_by_reconcile PASSED
tests/test_contentpack_guard.py::test_commit_is_refused[contentpacks/mail.contentpack.json-data] PASSED
tests/test_contentpack_guard.py::test_commit_is_refused[notes.json-data] PASSED
tests/test_contentpack_guard.py::test_commit_is_refused[docs/backup.txt-data] PASSED
tests/test_contentpack_guard.py::test_commit_is_refused[wrapped.json-data] PASSED
tests/test_contentpack_guard.py::test_commit_is_refused[readme_extra.md-data] PASSED
tests/test_contentpack_guard.py::test_commit_is_refused[bundle.zip-data] PASSED
tests/test_contentpack_guard.py::test_commit_is_refused[innocent.dat-data] PASSED
tests/test_contentpack_guard.py::test_commit_is_refused[backup.tar.gz-data] PASSED
tests/test_contentpack_guard.py::test_commit_is_refused[build_mail_content_pack.py-print('x')\n] PASSED
tests/test_contentpack_guard.py::test_commit_is_refused[\u5ba2\u6236\u4ea4\u4ed8\u5305/a.txt-x\n] PASSED
tests/test_contentpack_guard.py::test_commit_is_refused[contrib/graylog-parsing/src/x.py-print('x')\n] PASSED
tests/test_contentpack_guard.py::test_ordinary_files_pass PASSED
tests/test_contentpack_guard.py::test_no_verify_commit_is_still_stopped_at_push PASSED
tests/test_contentpack_guard.py::test_pack_added_then_removed_is_stopped_at_push PASSED
tests/test_contentpack_guard.py::test_new_branch_push_is_checked PASSED
tests/test_contentpack_guard.py::test_consent_lets_only_the_named_file_through PASSED
tests/test_contentpack_guard.py::test_guard_that_cannot_run_blocks PASSED
tests/test_contentpack_guard.py::test_preflight_catches_a_clone_without_hooks PASSED
tests/test_contentpack_guard.py::test_preflight_catches_a_pack_already_in_the_clone PASSED
tests/test_contentpack_guard.py::test_preflight_honours_consent_for_those_paths_only PASSED
tests/test_contentpack_guard.py::test_gate_forwards_a_clean_push PASSED
tests/test_contentpack_guard.py::test_gate_refuses_with_no_verify_and_upstream_stays_clean[a.contentpack.json-data] PASSED
tests/test_contentpack_guard.py::test_gate_refuses_with_no_verify_and_upstream_stays_clean[renamed.txt-data] PASSED
tests/test_contentpack_guard.py::test_gate_refuses_with_no_verify_and_upstream_stays_clean[b.zip-data] PASSED
tests/test_contentpack_guard.py::test_gate_sees_a_pack_buried_under_a_clean_tip PASSED
tests/test_contentpack_guard.py::test_gate_covers_new_branches_and_tags PASSED
tests/test_contentpack_guard.py::test_gate_consent_reaches_the_receiving_side PASSED
tests/test_contentpack_guard.py::test_gate_keeps_force_push_and_branch_delete_working PASSED
tests/test_contentpack_guard.py::test_gate_reports_a_refusal_from_upstream PASSED
tests/test_contentpack_guard.py::test_gate_fails_closed_when_the_guard_is_gone PASSED
tests/test_contentpack_guard.py::test_a_repository_without_a_gate_cannot_be_pushed PASSED
tests/test_contentpack_guard.py::test_preflight_catches_an_explicit_pushurl PASSED
tests/test_contentpack_guard.py::test_gate_forwards_with_its_own_key PASSED
tests/test_contentpack_guard.py::test_gate_add_gives_each_repository_its_own_key warning: You appear to have cloned an empty repository.
PASSED
tests/test_contentpack_guard.py::test_this_host_rewrites_every_github_push_to_the_gate PASSED
tests/test_contentpack_guard.py::test_the_publish_tree_holds_no_pack_but_the_published_ones PASSED
tests/test_contentpack_guard.py::test_consent_does_not_cover_an_address_or_credential_inside_the_pack PASSED
tests/test_contentpack_guard.py::test_a_credential_inside_a_pack_is_never_consentable[password] PASSED
tests/test_contentpack_guard.py::test_a_credential_inside_a_pack_is_never_consentable[api_key] PASSED
tests/test_contentpack_guard.py::test_a_credential_inside_a_pack_is_never_consentable[bearer] PASSED
tests/test_contentpack_guard.py::test_a_refusal_message_does_not_trip_the_gate_itself PASSED
tests/test_contentpack_guard.py::test_the_push_clone_location_gets_the_hooks PASSED
tests/test_contentpack_guard.py::test_audit_finds_a_pack_once_and_then_stays_quiet github audit: 1 repositories, 0 new, 0 not checked
PASSED
tests/test_contentpack_guard.py::test_audit_sees_a_pack_in_a_later_push_and_in_an_archive PASSED
tests/test_contentpack_guard.py::test_audit_leaves_an_ordinary_archive_alone github audit: 1 repositories, 0 new, 0 not checked
PASSED
tests/test_contentpack_guard.py::test_audit_that_cannot_look_never_reads_as_clean github audit: 0 repositories, 0 new, 1 not checked
COULD NOT CHECK repository list: network down
PASSED
tests/test_contentpack_guard.py::test_audit_does_not_call_code_a_pack_but_finds_one_escaped_in_a_string PASSED
tests/test_database_datetime.py::test_naive_roundtrip PASSED
tests/test_database_datetime.py::test_utc_aware_roundtrip PASSED
tests/test_database_datetime.py::test_non_utc_aware_roundtrip PASSED
tests/test_database_datetime.py::test_none_passthrough PASSED
tests/test_database_datetime.py::test_str_to_dt_with_offset PASSED
tests/test_db_rebuild.py::test_rebuild_dry_run 2026-11-06T01:09:22.245040Z [info     ] Would insert                   path=/tmp/tmpf_v1qixm/archives/server1/2026/01/test.json.gz server=test time_from=2026-01-01T00:00:00Z
PASSED
tests/test_db_rebuild.py::test_rebuild_actual PASSED
tests/test_db_rebuild.py::test_rebuild_skip_existing PASSED
tests/test_db_rebuild.py::test_backup_db PASSED
tests/test_db_rebuild.py::test_prune_backups PASSED
tests/test_export_busy_visibility.py::test_lock_state_is_readable_without_taking_it PASSED
tests/test_export_busy_visibility.py::test_trigger_export_refuses_a_busy_server PASSED
tests/test_export_busy_visibility.py::test_a_run_that_dies_before_the_exporter_still_leaves_a_row PASSED
tests/test_export_busy_visibility.py::test_the_safety_net_does_not_overwrite_a_real_row PASSED
tests/test_export_busy_visibility.py::test_the_safety_net_sanitises_secrets PASSED
tests/test_export_busy_visibility.py::test_the_safety_net_never_raises 2026-11-06T01:09:25.813490Z [warning  ] Could not record an unstarted export job error='db down' job=x
PASSED
tests/test_export_cancel_paths.py::test_flag_cancel_mid_index_never_records_a_partial_hour 2026-11-06T01:09:26.487778Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-06T01:09:26.488249Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-06T01:09:26.488501Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-06T01:09:26.488671Z [info     ] Skipping active write index    index=graylog_write
2026-11-06T01:09:26.489382Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-06T01:09:26.497566Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-06T01:09:26.498081Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-06T01:09:26.514519Z [info     ] Archive written (streaming)    messages=4 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_flag_cancel_mid_index_nev0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:09:26.535755Z [info     ] Chunk exported                 index=graylog_0 messages=4 time_from='2026-07-01 00:00:00'
2026-11-06T01:09:26.550725Z [info     ] Export cancelled by user       job_id=job-1 records_kept=4
2026-11-06T01:09:26.561990Z [info     ] OpenSearch export cancelled    exported=0 job_id=job-1 messages=4 skipped=0
2026-11-06T01:09:26.562384Z [info     ] Completion notification skipped — run was cancelled job_id=job-1
PASSED
tests/test_export_cancel_paths.py::test_the_next_run_resumes_from_the_discarded_hour 2026-11-06T01:09:27.012894Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-06T01:09:27.013257Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-06T01:09:27.013527Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-06T01:09:27.013779Z [info     ] Skipping active write index    index=graylog_write
2026-11-06T01:09:27.014466Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-06T01:09:27.029750Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-06T01:09:27.030348Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-06T01:09:27.042810Z [info     ] Archive written (streaming)    messages=4 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_the_next_run_resumes_from0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:09:27.056555Z [info     ] Chunk exported                 index=graylog_0 messages=4 time_from='2026-07-01 00:00:00'
2026-11-06T01:09:27.071838Z [info     ] Export cancelled by user       job_id=job-1 records_kept=4
2026-11-06T01:09:27.098490Z [info     ] OpenSearch export cancelled    exported=0 job_id=job-1 messages=4 skipped=0
2026-11-06T01:09:27.098785Z [info     ] Completion notification skipped — run was cancelled job_id=job-1
2026-11-06T01:09:27.112885Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-06T01:09:27.113229Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-06T01:09:27.113417Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-06T01:09:27.113569Z [info     ] Skipping active write index    index=graylog_write
2026-11-06T01:09:27.114045Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-06T01:09:27.124286Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-06T01:09:27.124825Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-06T01:09:27.125650Z [info     ] Excluding already-archived ranges from the scan docs_to_export=12 index=graylog_0 ranges_excluded=1
2026-11-06T01:09:27.148226Z [info     ] Archive written (streaming)    messages=6 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_the_next_run_resumes_from0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T010000Z_20260701T020000Z_001.json.gz size_mb=0.00
2026-11-06T01:09:27.160616Z [info     ] Chunk exported                 index=graylog_0 messages=6 time_from='2026-07-01 01:00:00'
2026-11-06T01:09:27.173845Z [info     ] Archive written (streaming)    messages=2 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_the_next_run_resumes_from0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T020000Z_20260701T030000Z_001.json.gz size_mb=0.00
2026-11-06T01:09:27.181495Z [info     ] Chunk exported                 index=graylog_0 messages=2 time_from='2026-07-01 02:00:00'
2026-11-06T01:09:27.190628Z [info     ] OpenSearch export completed    exported=1 job_id=job-2 messages=8 skipped=0
PASSED
tests/test_export_cancel_paths.py::test_callback_cancel_mid_index_ends_cancelled 2026-11-06T01:09:27.499717Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-06T01:09:27.500084Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-06T01:09:27.500260Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-06T01:09:27.500404Z [info     ] Skipping active write index    index=graylog_write
2026-11-06T01:09:27.500733Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-06T01:09:27.513790Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-06T01:09:27.514201Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-06T01:09:27.527760Z [info     ] Archive written (streaming)    messages=4 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_callback_cancel_mid_index0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:09:27.538194Z [info     ] Chunk exported                 index=graylog_0 messages=4 time_from='2026-07-01 00:00:00'
2026-11-06T01:09:27.549950Z [info     ] Export cancelled by user       job_id=job-1 records_kept=4
2026-11-06T01:09:27.560655Z [info     ] OpenSearch export cancelled    exported=0 job_id=job-1 messages=4 skipped=0
2026-11-06T01:09:27.560978Z [info     ] Completion notification skipped — run was cancelled job_id=job-1
PASSED
tests/test_export_cancel_paths.py::test_cancel_during_phase_a_count_loop_is_a_cancel_not_a_failure 2026-11-06T01:09:27.877752Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-06T01:09:27.878011Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-06T01:09:27.878161Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-06T01:09:27.878285Z [info     ] Skipping active write index    index=graylog_write
2026-11-06T01:09:27.878643Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-06T01:09:27.893791Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-06T01:09:27.894283Z [info     ] Export cancelled by user       job_id=job-1 records_kept=0
2026-11-06T01:09:27.905071Z [info     ] OpenSearch export cancelled    exported=0 job_id=job-1 messages=0 skipped=0
2026-11-06T01:09:27.905371Z [info     ] Completion notification skipped — run was cancelled job_id=job-1
PASSED
tests/test_export_cancel_paths.py::test_a_normal_run_is_unaffected 2026-11-06T01:09:28.311012Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-06T01:09:28.311393Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-06T01:09:28.311552Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-06T01:09:28.311671Z [info     ] Skipping active write index    index=graylog_write
2026-11-06T01:09:28.312055Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-06T01:09:28.322588Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-06T01:09:28.323090Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-06T01:09:28.337156Z [info     ] Archive written (streaming)    messages=4 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_a_normal_run_is_unaffecte0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:09:28.345385Z [info     ] Chunk exported                 index=graylog_0 messages=4 time_from='2026-07-01 00:00:00'
2026-11-06T01:09:28.370603Z [info     ] Archive written (streaming)    messages=6 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_a_normal_run_is_unaffecte0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T010000Z_20260701T020000Z_001.json.gz size_mb=0.00
2026-11-06T01:09:28.381606Z [info     ] Chunk exported                 index=graylog_0 messages=6 time_from='2026-07-01 01:00:00'
2026-11-06T01:09:28.401120Z [info     ] Archive written (streaming)    messages=2 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_a_normal_run_is_unaffecte0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T020000Z_20260701T030000Z_001.json.gz size_mb=0.00
2026-11-06T01:09:28.411734Z [info     ] Chunk exported                 index=graylog_0 messages=2 time_from='2026-07-01 02:00:00'
2026-11-06T01:09:28.420624Z [info     ] OpenSearch export completed    exported=1 job_id=job-1 messages=12 skipped=0
PASSED
tests/test_export_cancel_paths.py::test_api_flag_cancel_inside_a_chunk_stops_and_ends_cancelled 2026-11-06T01:09:31.092112Z [info     ] Export started                 chunks=1 job_id=job-api time_from='2026-07-01 00:00:00' time_to='2026-07-01 01:00:00'
2026-11-06T01:09:31.107723Z [info     ] Total records to export        streams=None time_from='2026-07-01 00:00:00' time_to='2026-07-01 01:00:00' total=6
2026-11-06T01:09:31.123864Z [info     ] Export cancelled by user       job_id=job-api records_kept=0
2026-11-06T01:09:31.140284Z [info     ] Export cancelled               chunks_exported=0 chunks_skipped=0 job_id=job-api messages_total=0
2026-11-06T01:09:31.140560Z [info     ] Completion notification skipped — run was cancelled job_id=job-api
PASSED
tests/test_export_cancel_paths.py::test_backpressure_pause_honours_cancel 2026-11-06T01:09:31.152064Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 99%']
2026-11-06T01:09:31.162904Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
2026-11-06T01:09:31.174967Z [info     ] export cancelled during backpressure pause waited_sec=0.02
PASSED
tests/test_export_cancel_paths.py::test_backpressure_emit_reraises_a_cancel_from_the_callback PASSED
tests/test_export_cancel_registry.py::test_registry_round_trip PASSED
tests/test_export_cancel_registry.py::test_unknown_job_is_none_not_an_error PASSED
tests/test_export_cancel_registry.py::test_empty_job_id_is_never_registered PASSED
tests/test_export_cancel_registry.py::test_both_exporters_register_and_release[glogarch.export.exporter-_export_lock] PASSED
tests/test_export_cancel_registry.py::test_both_exporters_register_and_release[glogarch.opensearch.exporter-_os_export_lock] PASSED
tests/test_export_cancel_registry.py::test_cancel_endpoint_signals_the_exporter PASSED
tests/test_export_cancel_registry.py::test_skip_streak_escalates_and_resets PASSED
tests/test_export_cancel_registry.py::test_skip_branch_escalates_and_notifies PASSED
tests/test_export_cancel_registry.py::test_stuck_notification_never_breaks_the_scheduler PASSED
tests/test_export_cancel_reporting.py::test_cancellation_is_told_apart_from_a_failure PASSED
tests/test_export_cancel_reporting.py::test_result_carries_the_partial_count_and_the_cancel_flag PASSED
tests/test_export_cancel_reporting.py::test_a_cancelled_run_is_not_written_as_completed PASSED
tests/test_export_cancel_reporting.py::test_a_normal_run_still_completes_at_100 PASSED
tests/test_export_cancel_reporting.py::test_records_written_before_the_cancel_are_kept_in_the_count PASSED
tests/test_export_cancel_reporting.py::test_the_partial_counter_is_reset_between_indices PASSED
tests/test_export_cancel_reporting.py::test_both_export_modes_apply_the_same_rule[opensearch] PASSED
tests/test_export_cancel_reporting.py::test_both_export_modes_apply_the_same_rule[api] PASSED
tests/test_export_pagination.py::test_deep_pagination_no_same_ms_loss_or_dup 2026-11-06T01:09:31.272929Z [info     ] Total messages to fetch        total=6
2026-11-06T01:09:31.273774Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=4 new_from='2024-01-01 00:00:00.003000' old_from='2024-01-01 00:00:00'
PASSED
tests/test_export_pagination.py::test_deep_pagination_multiple_windows 2026-11-06T01:09:31.279234Z [info     ] Total messages to fetch        total=30
2026-11-06T01:09:31.281018Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=6 new_from='2024-01-01 00:00:00.005000' old_from='2024-01-01 00:00:00'
2026-11-06T01:09:31.282651Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=11 new_from='2024-01-01 00:00:00.010000' old_from='2024-01-01 00:00:00.005000'
2026-11-06T01:09:31.284577Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=16 new_from='2024-01-01 00:00:00.015000' old_from='2024-01-01 00:00:00.010000'
2026-11-06T01:09:31.286235Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=21 new_from='2024-01-01 00:00:00.020000' old_from='2024-01-01 00:00:00.015000'
2026-11-06T01:09:31.287773Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=26 new_from='2024-01-01 00:00:00.025000' old_from='2024-01-01 00:00:00.020000'
PASSED
tests/test_export_pagination.py::test_pagination_raises_on_unsplittable_ms 2026-11-06T01:09:31.293572Z [info     ] Total messages to fetch        total=10
2026-11-06T01:09:31.294722Z [warning  ] Single-millisecond overflow during API export: more than 4 messages share 2024-01-01T00:00:00.000Z; Graylog's REST API cannot page past it. Kept the first 4, skipping the rest of this millisecond and continuing. Re-run this window in OpenSearch Direct mode to capture them all.
PASSED
tests/test_export_pagination.py::test_overflow_ms_does_not_lose_messages_after_it 2026-11-06T01:09:31.299005Z [info     ] Total messages to fetch        total=12
2026-11-06T01:09:31.300298Z [warning  ] Single-millisecond overflow during API export: more than 4 messages share 2024-01-01T00:00:00.000Z; Graylog's REST API cannot page past it. Kept the first 4, skipping the rest of this millisecond and continuing. Re-run this window in OpenSearch Direct mode to capture them all.
PASSED
tests/test_export_pagination.py::test_fmt_ts_millisecond_precision PASSED
tests/test_export_pagination.py::test_parse_timestamp_robust_fallback PASSED
tests/test_export_pagination.py::test_transient_5xx_fails_over_to_next_host 2026-11-06T01:09:31.317991Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=1 status=503 wait=1
2026-11-06T01:09:31.323375Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=2 status=503 wait=2
2026-11-06T01:09:31.325981Z [warning  ] Transient errors exhausted, failing over to next host host=http://host0:9200 status=503
2026-11-06T01:09:31.328556Z [info     ] Failover to host               host=http://host1:9200
PASSED
tests/test_export_pagination.py::test_all_hosts_transient_raises 2026-11-06T01:09:31.340724Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=1 status=503 wait=1
2026-11-06T01:09:31.342582Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=2 status=503 wait=2
2026-11-06T01:09:31.342917Z [warning  ] Transient errors exhausted, failing over to next host host=http://host0:9200 status=503
2026-11-06T01:09:31.343132Z [warning  ] Transient error, retrying      host=http://host1:9200 retry=1 status=503 wait=1
2026-11-06T01:09:31.343380Z [warning  ] Transient error, retrying      host=http://host1:9200 retry=2 status=503 wait=2
2026-11-06T01:09:31.343609Z [warning  ] Transient errors exhausted, failing over to next host host=http://host1:9200 status=503
PASSED
tests/test_export_pagination.py::test_non_transient_4xx_raises_immediately PASSED
tests/test_export_pagination.py::test_scan_never_terminates_on_a_stale_count PASSED
tests/test_export_pagination.py::test_rate_limiter_does_not_hold_lock_across_sleep PASSED
tests/test_export_pagination.py::test_rate_limiter_acquire_allows_burst PASSED
tests/test_export_progress_denominator.py::test_export_index_never_rebinds_the_jobwide_denominator PASSED
tests/test_export_progress_denominator.py::test_plan_phase_sets_the_denominator_exactly_once PASSED
tests/test_export_progress_denominator.py::test_progress_pct_is_derived_from_the_same_pair PASSED
tests/test_export_skip_archived.py::test_contiguous_ranges_are_merged PASSED
tests/test_export_skip_archived.py::test_gaps_are_preserved PASSED
tests/test_export_skip_archived.py::test_sister_index_of_same_prefix_does_not_cover PASSED
tests/test_export_skip_archived.py::test_api_all_streams_archive_covers PASSED
tests/test_export_skip_archived.py::test_stream_filtered_archive_does_not_cover PASSED
tests/test_export_skip_archived.py::test_other_server_is_not_counted PASSED
tests/test_export_skip_archived.py::test_exporter_filters_at_query_level PASSED
tests/test_export_skip_archived.py::test_range_filter_declares_the_graylog_date_format PASSED
tests/test_export_skip_archived.py::test_zero_remaining_skips_the_scan PASSED
tests/test_export_skip_archived.py::test_new_index_set_is_cycled_so_graylog_provisions_it PASSED
tests/test_export_skip_archived.py::test_bulk_waits_for_the_deflector_instead_of_failing_instantly PASSED
tests/test_export_skip_archived.py::test_no_fuzzy_coverage_threshold_skips_a_whole_index PASSED
tests/test_export_skip_archived.py::test_chunk_dedup_and_query_filter_use_the_same_ranges PASSED
tests/test_fast_paths_equivalence.py::test_fixed_parser_never_disagrees_with_strptime[formats0] PASSED
tests/test_fast_paths_equivalence.py::test_fixed_parser_never_disagrees_with_strptime[formats1] PASSED
tests/test_fast_paths_equivalence.py::test_fixed_parser_takes_the_two_real_archive_shapes PASSED
tests/test_fast_paths_equivalence.py::test_gelf_timestamp_identical_to_the_old_parser PASSED
tests/test_fast_paths_equivalence.py::test_os_parse_ts_identical_to_the_old_parser PASSED
tests/test_fast_paths_equivalence.py::test_field_types_identical_to_isinstance_chain PASSED
tests/test_fast_paths_equivalence.py::test_reused_encoder_writes_the_same_bytes PASSED
tests/test_fast_paths_equivalence.py::test_gelf_send_delivers_every_message 2026-11-06T01:09:37.344067Z [info     ] GELF TCP connected             host=127.0.0.1 port=38431
2026-11-06T01:09:37.632681Z [info     ] GELF TCP disconnected          messages_sent=5000
PASSED
tests/test_fast_paths_equivalence.py::test_gelf_closed_connection_is_detected_not_silently_dropped 2026-11-06T01:09:37.841388Z [info     ] GELF TCP connected             host=127.0.0.1 port=42289
PASSED
tests/test_fast_paths_equivalence.py::test_gelf_reset_by_the_target_is_noticed_and_counted 2026-11-06T01:09:37.880703Z [info     ] GELF TCP connected             host=127.0.0.1 port=35973
2026-11-06T01:09:38.335404Z [error    ] Failed to send GELF message    error='[Errno 104] Connection reset by peer' sent=3000
2026-11-06T01:09:38.335693Z [info     ] GELF TCP disconnected          messages_sent=3000
2026-11-06T01:09:38.336810Z [info     ] GELF TCP connected             host=127.0.0.1 port=35973
2026-11-06T01:09:38.337154Z [warning  ] GELF connection lost and re-established; messages in transit at that moment may not have reached the target reconnects=1 sent=3001
2026-11-06T01:09:39.645436Z [info     ] GELF TCP disconnected          messages_sent=12000
PASSED
tests/test_fast_paths_equivalence.py::test_import_without_reconnect_is_verified 2026-11-06T01:09:40.713693Z [info     ] Import started                 archives=1 job_id=j1 total_messages=40
2026-11-06T01:09:40.714037Z [info     ] Preflight passed               duration=0.0s fields=0 fixed=0 rotated=False
2026-11-06T01:09:40.780746Z [info     ] Reconciliation OK: 0 indexer failures — all messages verified at destination failures_after=0 failures_before=0 indexed=40 sent=40
2026-11-06T01:09:40.794039Z [info     ] Import completed               archives=1 job_id=j1 messages=40
PASSED
tests/test_fast_paths_equivalence.py::test_import_with_a_gelf_reconnect_is_not_called_verified 2026-11-06T01:09:41.207839Z [info     ] Import started                 archives=1 job_id=j1 total_messages=40
2026-11-06T01:09:41.208232Z [info     ] Preflight passed               duration=0.0s fields=0 fixed=0 rotated=False
2026-11-06T01:09:41.270623Z [warning  ] The GELF connection to the target was lost 1 time(s) and re-established during this import. Messages that were in transit at that moment may not have reached Graylog, and TCP cannot tell which, so this run is NOT verified even with 0 indexer failures. Check the message count in Graylog for this time range, or re-import with Bulk mode (it de-duplicates by message id). reconnects=1
2026-11-06T01:09:41.281377Z [info     ] Import completed               archives=1 job_id=j1 messages=40
PASSED
tests/test_field_schema.py::test_plain_json_passthrough PASSED
tests/test_field_schema.py::test_zlib_roundtrip PASSED
tests/test_field_schema.py::test_decompress_none PASSED
tests/test_field_schema.py::test_decompress_corrupted PASSED
tests/test_field_schema.py::test_decompress_plain_json PASSED
tests/test_field_schema.py::test_db_field_schema_store_and_read PASSED
tests/test_gelf_cancel_midbatch.py::test_send_batch_stops_mid_batch_on_cancel PASSED
tests/test_gelf_cancel_midbatch.py::test_send_batch_cancel_after_some_messages PASSED
tests/test_gelf_cancel_midbatch.py::test_send_batch_without_cancel_check_sends_all PASSED
tests/test_gelf_cancel_midbatch.py::test_importer_passes_cancel_check_to_sender PASSED
tests/test_graylog_error_detail.py::test_error_detail_extracts_graylog_message PASSED
tests/test_graylog_error_detail.py::test_error_detail_falls_back_to_text_body PASSED
tests/test_graylog_error_detail.py::test_error_detail_handles_empty_body PASSED
tests/test_graylog_flush.py::test_flush_cycles_and_rebuilds_never_deletes 2026-11-06T01:09:41.801921Z [info     ] graylog flush done             actions=['cycle_deflector:ok', 'rebuild_index_ranges:ok'] ok=True
PASSED
tests/test_graylog_flush.py::test_flush_global_deflector_fallback_when_no_index_set 2026-11-06T01:09:41.812645Z [info     ] graylog flush done             actions=['cycle_deflector:ok', 'rebuild_index_ranges:ok'] ok=True
PASSED
tests/test_graylog_flush.py::test_flush_reports_action_error_without_raising 2026-11-06T01:09:41.823161Z [info     ] graylog flush done             actions=['cycle_deflector:error', 'rebuild_index_ranges:ok'] ok=False
PASSED
tests/test_graylog_flush.py::test_snapshot_unreachable_returns_empty_not_raise 2026-11-06T01:09:41.833024Z [warning  ] flush snapshot failed          error=unreachable
PASSED
tests/test_health_endpoint.py::test_health_response_structure PASSED
tests/test_health_endpoint.py::test_health_not_behind_auth PASSED
tests/test_health_guard.py::test_rising_tracker_detects_sustained_climb PASSED
tests/test_health_guard.py::test_rising_tracker_ignores_flat_and_falling PASSED
tests/test_health_guard.py::test_rising_tracker_respects_min_delta PASSED
tests/test_health_guard.py::test_tripped_failsafe_on_unreachable PASSED
tests/test_health_guard.py::test_heap_hard_tier_trips_immediately 2026-11-06T01:09:41.859275Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard.py::test_heap_soft_tier_needs_sustained 2026-11-06T01:09:41.862250Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard.py::test_heap_soft_streak_resets_on_dip 2026-11-06T01:09:41.865098Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard.py::test_tripped_on_rising_journal 2026-11-06T01:09:41.867921Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard.py::test_pause_then_resume 2026-11-06T01:09:41.871638Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
2026-11-06T01:09:41.871885Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 95% (over the hard limit 90%)']
2026-11-06T01:09:41.872139Z [info     ] export resumed — backpressure cleared waited_sec=1
PASSED
tests/test_health_guard.py::test_pause_times_out_and_raises 2026-11-06T01:09:41.876545Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
2026-11-06T01:09:41.876813Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 99% (over the hard limit 90%)']
2026-11-06T01:09:41.877019Z [error    ] export stopped — backpressure did not clear signals=['JVM heap 99% (over the hard limit 90%)'] waited_sec=60
PASSED
tests/test_health_guard_gc.py::test_healthy_sawtooth_never_pauses_on_gc_signal 2026-11-06T01:09:41.884172Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_same_sawtooth_did_pause_on_used_percent 2026-11-06T01:09:41.890813Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard_gc.py::test_full_gc_trips_immediately 2026-11-06T01:09:41.895091Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_heap_full_right_after_gc_trips_on_first_reading 2026-11-06T01:09:41.898807Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_heap_exhausting_load_trips 2026-11-06T01:09:41.902465Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_gc_time_share_must_be_sustained 2026-11-06T01:09:41.906021Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_graylog_restart_resets_counters_without_tripping 2026-11-06T01:09:41.909710Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_missing_gc_metrics_fall_back_to_used_percent 2026-11-06T01:09:41.913128Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard_gc.py::test_gc_mode_still_watches_journal_and_buffers 2026-11-06T01:09:41.916665Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_pause_on_full_gc_resumes_once_collections_stop 2026-11-06T01:09:41.921123Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-06T01:09:41.922373Z [warning  ] export paused — Graylog backpressure signals=['1 full garbage collection(s) in the last 15s (Graylog heap exhausted)']
2026-11-06T01:09:41.922720Z [info     ] export resumed — backpressure cleared waited_sec=15
PASSED
tests/test_health_guard_gc.py::test_gc_signals_from_a_real_g1_response PASSED
tests/test_health_guard_gc.py::test_gc_signals_parallel_gc_uses_the_old_pool_max PASSED
tests/test_health_guard_gc.py::test_gc_signals_absent_means_none PASSED
tests/test_health_guard_gc.py::test_get_health_requests_the_gc_metrics PASSED
tests/test_health_guard_gc.py::test_pace_delay_rises_with_heap_after_gc[40-0.0] 2026-11-06T01:09:41.940370Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_pace_delay_rises_with_heap_after_gc[70-0.0] 2026-11-06T01:09:41.944933Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_pace_delay_rises_with_heap_after_gc[80-2.5] 2026-11-06T01:09:41.949625Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-06T01:09:41.949880Z [info     ] export pacing adjusted         delay_per_page_sec=2.5 heap_after_gc_pct=80
PASSED
tests/test_health_guard_gc.py::test_pace_delay_rises_with_heap_after_gc[85-3.75] 2026-11-06T01:09:41.953644Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-06T01:09:41.953884Z [info     ] export pacing adjusted         delay_per_page_sec=3.75 heap_after_gc_pct=85
PASSED
tests/test_health_guard_gc.py::test_pace_delay_rises_with_heap_after_gc[95-5.0] 2026-11-06T01:09:41.957613Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-06T01:09:41.957916Z [info     ] export pacing adjusted         delay_per_page_sec=5.0 heap_after_gc_pct=95
PASSED
tests/test_health_guard_gc.py::test_no_pacing_without_gc_metrics_or_for_opensearch_direct 2026-11-06T01:09:41.960784Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard_gc.py::test_pacing_relaxes_when_heap_recovers 2026-11-06T01:09:41.963979Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-06T01:09:41.964689Z [info     ] export pacing adjusted         delay_per_page_sec=4.0 heap_after_gc_pct=86
2026-11-06T01:09:41.964967Z [info     ] export pacing adjusted         delay_per_page_sec=0.0 heap_after_gc_pct=60
PASSED
tests/test_health_guard_gc.py::test_checkpoint_applies_the_pace_between_pages 2026-11-06T01:09:41.968612Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-06T01:09:41.968865Z [info     ] export pacing adjusted         delay_per_page_sec=2.5 heap_after_gc_pct=80
PASSED
tests/test_health_guard_gc.py::test_heap_bound_pause_releases_expired_searches_and_resumes 2026-11-06T01:09:41.974503Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-06T01:09:41.974882Z [info     ] export pacing adjusted         delay_per_page_sec=5.0 heap_after_gc_pct=92.0
2026-11-06T01:09:41.975049Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 92% still in use right after garbage collection (limit 90%)']
2026-11-06T01:09:41.976502Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=315
2026-11-06T01:09:41.976783Z [info     ] export resumed — backpressure cleared waited_sec=315
PASSED
tests/test_health_guard_gc.py::test_release_is_repeated_at_most_once_a_minute 2026-11-06T01:09:41.983603Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-06T01:09:41.983937Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 92% still in use right after garbage collection (limit 90%)']
2026-11-06T01:09:41.985214Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=315
2026-11-06T01:09:41.985614Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=375
2026-11-06T01:09:41.985947Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=435
2026-11-06T01:09:41.986279Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=495
2026-11-06T01:09:41.986574Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=555
2026-11-06T01:09:41.986857Z [error    ] export stopped — backpressure did not clear signals=['JVM heap 92% still in use right after garbage collection (limit 90%)'] waited_sec=600
PASSED
tests/test_health_guard_gc.py::test_journal_pause_does_not_send_searches 2026-11-06T01:09:41.990277Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-06T01:09:41.991329Z [warning  ] export paused — Graylog backpressure signals=['disk journal backlog rising (1,000)']
2026-11-06T01:09:41.993870Z [error    ] export stopped — backpressure did not clear signals=['disk journal backlog rising (1,000)'] waited_sec=600
PASSED
tests/test_health_guard_gc.py::test_release_expired_searches_sends_small_searches PASSED
tests/test_health_guard_gc.py::test_release_expired_searches_stops_on_error 2026-11-06T01:09:42.002653Z [warning  ] Search to release Graylog's expired search results failed error='connection refused'
PASSED
tests/test_health_guard_gc.py::test_api_exporter_paces_and_opensearch_exporter_does_not PASSED
tests/test_health_schedule_registration.py::test_health_compares_enabled_schedules_against_registered_jobs PASSED
tests/test_health_schedule_registration.py::test_unregistered_schedule_makes_health_unhealthy PASSED
tests/test_health_schedule_registration.py::test_upgrade_script_fails_when_schedules_are_not_registered PASSED
tests/test_i18n_ja.py::test_ja_has_exactly_the_english_keys PASSED
tests/test_i18n_ja.py::test_ja_keeps_every_placeholder PASSED
tests/test_i18n_ja.py::test_ja_keeps_html_markup PASSED
tests/test_i18n_ja.py::test_ja_is_japanese_not_copied_chinese PASSED
tests/test_i18n_ja.py::test_ja_uses_fullwidth_punctuation PASSED
tests/test_i18n_ja.py::test_every_page_switcher_offers_every_language PASSED
tests/test_i18n_ja.py::test_notification_language_offers_japanese PASSED
tests/test_i18n_ja.py::test_cron_label_in_japanese[*/15 * * * *-15\u5206\u3054\u3068] PASSED
tests/test_i18n_ja.py::test_cron_label_in_japanese[0 */6 * * *-6\u6642\u9593\u3054\u3068] PASSED
tests/test_i18n_ja.py::test_cron_label_in_japanese[0 3 * * *-\u6bce\u65e5 03:00] PASSED
tests/test_i18n_ja.py::test_cron_label_in_japanese[0 3 * * 6-\u6bce\u9031\u571f\u66dc 03:00] PASSED
tests/test_i18n_ja.py::test_cron_label_in_japanese[0 5 * * 1-5-\u6bce\u9031\u6708\u66dc\u301c\u91d1\u66dc 05:00] PASSED
tests/test_i18n_ja.py::test_cron_label_in_japanese[0 5 1 * *-\u6bce\u67081\u65e5 05:00] PASSED
tests/test_i18n_ja.py::test_cron_label_in_japanese[0 3 1-7 * 6-\u6bce\u67081\u301c7\u65e5\u304b\u3064\u571f\u66dc 03:00] PASSED
tests/test_import_batch_flow.py::test_web_ui_flow_control_batch_and_rate_are_preserved 2026-11-06T01:09:43.306574Z [info     ] No archives to import         
PASSED
tests/test_import_batch_flow.py::test_no_flow_control_captures_config_defaults 2026-11-06T01:09:43.722866Z [info     ] No archives to import         
PASSED
tests/test_import_batch_flow.py::test_seeding_is_guarded_in_source PASSED
tests/test_import_jvm_throttle.py::test_ring_buffer_is_the_early_signal PASSED
tests/test_import_jvm_throttle.py::test_buffer_pause_beats_low_journal PASSED
tests/test_import_jvm_throttle.py::test_heap_alone_triggers_slow_then_pause PASSED
tests/test_import_jvm_throttle.py::test_journal_alone_still_works PASSED
tests/test_import_jvm_throttle.py::test_most_severe_signal_wins PASSED
tests/test_import_jvm_throttle.py::test_unknown_heap_is_ignored PASSED
tests/test_import_jvm_throttle.py::test_monitoring_disabled_is_normal PASSED
tests/test_import_jvm_throttle.py::test_failed_check_before_ever_working_does_not_deadlock 2026-11-06T01:09:43.782560Z [warning  ] Journal endpoint unreachable; import proceeds at user rate without journal throttling error=404
PASSED
tests/test_import_jvm_throttle.py::test_failed_check_after_working_is_failsafe_pause 2026-11-06T01:09:43.785386Z [warning  ] Journal check failed mid-import (target unreachable/stuck) — pausing until it recovers error=timeout
PASSED
tests/test_import_jvm_throttle.py::test_elevated_backlog_not_draining_escalates_to_pause PASSED
tests/test_import_jvm_throttle.py::test_elevated_backlog_that_is_draining_stays_slow PASSED
tests/test_import_lock.py::test_claim_success PASSED
tests/test_import_lock.py::test_claim_conflict PASSED
tests/test_import_lock.py::test_release PASSED
tests/test_import_lock.py::test_release_wrong_owner PASSED
tests/test_import_lock.py::test_same_job_reclaim PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_internal_sets_are_protected[gl-events] PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_internal_sets_are_protected[gl-system-events] PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_internal_sets_are_protected[gl_system_events] PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_internal_sets_are_protected[gl-events-2] PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_internal_sets_are_protected[gl-system-events-archive] PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_user_sets_are_clearable[graylog] PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_user_sets_are_clearable[jt_restored] PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_user_sets_are_clearable[filesrv] PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_user_sets_are_clearable[custom_idx] PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_empty_prefix_is_protected[] PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_empty_prefix_is_protected[   ] PASSED
tests/test_index_cleaner.py::TestProtectedIndexSets::test_empty_prefix_is_protected[None] PASSED
tests/test_index_cleaner.py::TestIndicesListParsing::test_reads_dict_wrapped_indices PASSED
tests/test_index_cleaner.py::TestIndicesListParsing::test_sizes_come_from_all_shards PASSED
tests/test_index_cleaner.py::TestIndicesListParsing::test_closed_indices_are_counted PASSED
tests/test_index_cleaner.py::TestIndicesListParsing::test_an_index_listed_twice_is_counted_once PASSED
tests/test_index_cleaner.py::TestIndicesListParsing::test_bare_list_shape_still_works PASSED
tests/test_index_cleaner.py::TestIndicesListParsing::test_empty_and_malformed_payloads_yield_nothing PASSED
tests/test_index_cleaner.py::TestIndicesListParsing::test_missing_size_is_zero_not_an_error PASSED
tests/test_index_cleaner.py::test_rotates_before_deleting_and_keeps_the_new_write_index 2026-11-06T01:09:46.869143Z [warning  ] Cleared index set before import deleted=2 failed=0 index_set=graylog kept_write_index=graylog_9
PASSED
tests/test_index_cleaner.py::test_refuses_to_clear_a_graylog_internal_index_set PASSED
tests/test_index_cleaner.py::test_unknown_write_index_aborts_without_deleting PASSED
tests/test_index_cleaner.py::test_list_index_sets_reports_count_and_size PASSED
tests/test_index_cleaner.py::test_list_index_sets_hides_internal_sets PASSED
tests/test_index_set_coverage.py::test_empty_or_none_means_all PASSED
tests/test_index_set_coverage.py::test_star_means_all_even_over_config PASSED
tests/test_index_set_coverage.py::test_single_string_backward_compatible PASSED
tests/test_index_set_coverage.py::test_list_value PASSED
tests/test_index_set_coverage.py::test_empty_falls_back_to_global_config PASSED
tests/test_index_set_coverage.py::test_explicit_value_overrides_global_config PASSED
tests/test_index_set_coverage.py::test_none_covers_all_index_sets PASSED
tests/test_index_set_coverage.py::test_restricting_reports_skipped_index_sets 2026-11-06T01:09:50.151261Z [warning  ] Index sets NOT covered by this OpenSearch export — their logs will NOT be archived and will be lost when Graylog retention deletes them covered=['graylog'] skipped=['PVE Hosts', 'Wazuh']
PASSED
tests/test_index_set_coverage.py::test_explicit_prefix_skips_api_lookup PASSED
tests/test_index_set_coverage.py::test_index_sets_without_prefix_are_ignored PASSED
tests/test_index_set_coverage.py::test_graylog_internal_event_sets_are_not_a_coverage_gap 2026-11-06T01:09:50.190529Z [info     ] Graylog-internal event index sets not selected (no ingested logs) internal=['Graylog Events', 'Graylog System Events']
PASSED
tests/test_index_set_coverage.py::test_a_real_log_set_left_out_still_warns_beside_internal_ones 2026-11-06T01:09:50.207700Z [info     ] Graylog-internal event index sets not selected (no ingested logs) internal=['Graylog Events', 'Graylog System Events']
2026-11-06T01:09:50.207923Z [warning  ] Index sets NOT covered by this OpenSearch export — their logs will NOT be archived and will be lost when Graylog retention deletes them covered=['graylog'] skipped=['PVE Hosts', 'Wazuh']
PASSED
tests/test_index_set_coverage.py::test_internal_prefix_rule_matches_the_clear_guard PASSED
tests/test_index_set_coverage.py::test_job_note_and_result_for_internal_only_omission PASSED
tests/test_index_set_coverage.py::test_coverage_chip_is_green_when_only_internal_sets_are_left_out PASSED
tests/test_index_set_coverage.py::test_job_result_json_round_trips PASSED
tests/test_indexer_failure_autofix.py::test_parse_failure_message_extracts_field_and_reason PASSED
tests/test_indexer_failure_autofix.py::test_parse_failure_rejects_log_prefix_tokens PASSED
tests/test_indexer_failure_autofix.py::test_get_indexer_failure_details_aggregates_fields PASSED
tests/test_indexer_failure_autofix.py::test_remediate_pins_fields_and_cycles_never_deletes 2026-11-06T01:09:50.762734Z [info     ] Custom mappings applied        failed=0 ok=2 total=2
2026-11-06T01:09:50.766521Z [info     ] Auto-remediated indexer-failure fields as string fields=['Keywords', 'foo'] index_set=idx1
PASSED
tests/test_indexer_failure_autofix.py::test_iterator_metadata_fallback_degrades_not_crashes PASSED
tests/test_indexer_failure_autofix.py::test_long_overflow_numeric_tracked_as_string PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_pins_new_fields_on_rise 2026-11-06T01:09:50.801336Z [warning  ] Mid-import auto-remediation applied failures_delta=5 fields=['Keywords']
PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_noop_when_no_rise PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_skips_already_pinned_field PASSED
tests/test_inline_remediation.py::test_bulk_inline_remediation_resends_failed_docs 2026-11-06T01:09:50.837004Z [info     ] Bulk import starting           archives=1 batch_docs=10000 indices_to_create=1 target_pattern=jt_restored total_messages=2
2026-11-06T01:09:50.837507Z [info     ] Bulk re-sent failed docs after remediation fields=['Keywords'] reindexed=1 resent=1 still_failed=0
2026-11-06T01:09:50.837804Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-11-06T01:09:50.837947Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.0s failed=0 indexed=2 sent=2
PASSED
tests/test_inline_remediation.py::test_check_capacity_uses_measured_override PASSED
tests/test_inline_remediation.py::test_capacity_abort_is_overridable PASSED
tests/test_inline_remediation.py::test_import_job_persists_retry_config 2026-11-06T01:09:51.360284Z [info     ] No archives to import         
PASSED
tests/test_integration.py::test_cross_conflict_actual_os_mapping PASSED
tests/test_integration.py::test_field_schema_zlib_in_preflight PASSED
tests/test_integration.py::test_timezone_dedup_correctness PASSED
tests/test_integration.py::test_timezone_retention_correctness PASSED
tests/test_integration.py::test_archive_write_read_integrity 2026-11-06T01:09:53.549422Z [info     ] Archive written                messages=50 path=/tmp/tmp1bocgkkz/test/stream1/2026/01/01/test_stream1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
PASSED
tests/test_integration.py::test_coverage_ratio_timezone PASSED
tests/test_integrity.py::test_key_gen_and_load_roundtrip PASSED
tests/test_integrity.py::test_env_key_overrides_file PASSED
tests/test_integrity.py::test_hmac_depends_on_key PASSED
tests/test_integrity.py::test_seal_noop_when_disabled PASSED
tests/test_integrity.py::test_seal_writes_hmac_and_ledger PASSED
tests/test_integrity.py::test_verify_ok_when_untouched PASSED
tests/test_integrity.py::test_tamper_detected_even_if_db_checksum_rewritten PASSED
tests/test_integrity.py::test_verify_skip_when_not_sealed PASSED
tests/test_integrity.py::test_verifier_flags_tampered 2026-11-06T01:09:56.063733Z [info     ] Verification started           total_archives=1
2026-11-06T01:09:56.065225Z [error    ] TAMPERED archive (HMAC mismatch) archive_id=1 path=/tmp/pytest-of-root/pytest-70/test_verifier_flags_tampered0/a.json.gz
2026-11-06T01:09:56.072796Z [info     ] Verification completed         corrupted=0 missing=0 orphans=0 tampered=1 total=1 valid=0
PASSED
tests/test_integrity.py::test_notify_tampered_line_is_distinct PASSED
tests/test_job_cancel_stale_view.py::test_cancelling_an_ended_job_is_refused_and_changes_nothing PASSED
tests/test_job_cancel_stale_view.py::test_cancelling_a_running_job_still_works PASSED
tests/test_job_cancel_stale_view.py::test_unknown_job_is_404_and_leaves_no_flag PASSED
tests/test_job_cancel_stale_view.py::test_job_lists_refresh_and_cancel_confirms_against_live_state PASSED
tests/test_job_eta.py::test_the_real_site_reports_about_53_days PASSED
tests/test_job_eta.py::test_no_estimate_before_there_is_signal PASSED
tests/test_job_eta.py::test_finished_and_non_running_jobs_have_no_estimate PASSED
tests/test_job_eta.py::test_a_malformed_start_time_does_not_raise PASSED
tests/test_job_eta.py::test_naive_start_times_are_treated_as_utc PASSED
tests/test_job_notes.py::test_a_clean_import_still_gets_a_note PASSED
tests/test_job_notes.py::test_the_summary_keeps_whatever_note_already_existed PASSED
tests/test_job_notes.py::test_a_shortfall_at_the_destination_is_stated PASSED
tests/test_job_notes.py::test_no_shortfall_is_not_mentioned PASSED
tests/test_job_notes.py::test_both_exporters_lead_with_a_summary PASSED
tests/test_local_admin.py::test_default_hash_is_empty PASSED
tests/test_local_admin.py::test_hash_generation PASSED
tests/test_local_admin.py::test_backward_compatible_config PASSED
tests/test_local_admin.py::test_localadmin_logs_in_even_when_graylog_configured PASSED
tests/test_local_admin.py::test_localadmin_wrong_password_rejected_without_graylog PASSED
tests/test_local_admin.py::test_no_hash_means_no_local_login PASSED
tests/test_login_roles.py::test_reader_is_refused_and_gets_no_session 2026-11-06T01:10:14.990953Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-06T01:10:15.042413Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-06T01:10:15.067753Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-06T01:10:15.068892Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-06T01:10:15.069539Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-06T01:10:15.073619Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-06T01:10:15.087022Z [info     ] Scheduler started             
2026-11-06T01:10:15.093684Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-06T01:10:15.315940Z [warning  ] Graylog login refused: no role allowed to use jt-glogarch allowed=['Admin'] reason='no allowed role' roles=['Reader'] server=a user=reader1
2026-11-06T01:10:15.337060Z [info     ] API Audit listener stopped    
2026-11-06T01:10:15.369834Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_admin_role_signs_in 2026-11-06T01:10:16.557035Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-06T01:10:16.580630Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-06T01:10:16.609752Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-06T01:10:16.612728Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-06T01:10:16.613380Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-06T01:10:16.613837Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-06T01:10:16.618764Z [info     ] Scheduler started             
2026-11-06T01:10:16.622249Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-06T01:10:17.132898Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=a
2026-11-06T01:10:17.203605Z [info     ] API Audit listener stopped    
2026-11-06T01:10:17.220994Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_star_permission_signs_in_without_the_admin_role 2026-11-06T01:10:18.237654Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-06T01:10:18.265683Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-06T01:10:18.294783Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-06T01:10:18.295638Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-06T01:10:18.297786Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-06T01:10:18.298610Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-06T01:10:18.303612Z [info     ] Scheduler started             
2026-11-06T01:10:18.316647Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-06T01:10:18.424067Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=a
2026-11-06T01:10:18.505085Z [info     ] API Audit listener stopped    
2026-11-06T01:10:18.531046Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_a_role_added_in_config_signs_in 2026-11-06T01:10:20.117216Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-06T01:10:20.134574Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-06T01:10:20.157267Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-06T01:10:20.158018Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-06T01:10:20.158807Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-06T01:10:20.159509Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-06T01:10:20.161671Z [info     ] Scheduler started             
2026-11-06T01:10:20.167125Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-06T01:10:20.274706Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=a
2026-11-06T01:10:20.320642Z [info     ] API Audit listener stopped    
2026-11-06T01:10:20.349926Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_star_in_config_restores_the_old_behaviour 2026-11-06T01:10:21.166737Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-06T01:10:21.177508Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-06T01:10:21.185457Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-06T01:10:21.186137Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-06T01:10:21.186640Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-06T01:10:21.187055Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-06T01:10:21.188581Z [info     ] Scheduler started             
2026-11-06T01:10:21.190479Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-06T01:10:21.220312Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=a
2026-11-06T01:10:21.254243Z [info     ] API Audit listener stopped    
2026-11-06T01:10:21.279768Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_token_login_is_checked_and_shows_the_owner 2026-11-06T01:10:22.386653Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-06T01:10:22.401308Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-06T01:10:22.412684Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-06T01:10:22.414165Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-06T01:10:22.415362Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-06T01:10:22.415950Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-06T01:10:22.417776Z [info     ] Scheduler started             
2026-11-06T01:10:22.420101Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-06T01:10:22.461755Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=a
2026-11-06T01:10:22.496749Z [info     ] API Audit listener stopped    
2026-11-06T01:10:22.518024Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_roles_that_cannot_be_read_refuse_the_login 2026-11-06T01:10:23.505150Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-06T01:10:23.523215Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-06T01:10:23.536524Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-06T01:10:23.537299Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-06T01:10:23.539064Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-06T01:10:23.540891Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-06T01:10:23.543621Z [info     ] Scheduler started             
2026-11-06T01:10:23.548105Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-06T01:10:23.605975Z [warning  ] Graylog login refused: no role allowed to use jt-glogarch allowed=['Admin'] reason='user name not readable (sessions HTTP 500)' roles=[] server=a user=admin
2026-11-06T01:10:23.614713Z [info     ] API Audit listener stopped    
2026-11-06T01:10:23.637360Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_admin_on_a_second_server_signs_in 2026-11-06T01:10:24.512920Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-06T01:10:24.550335Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-06T01:10:24.564986Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-06T01:10:24.565872Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-06T01:10:24.566568Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-06T01:10:24.566970Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-06T01:10:24.569562Z [info     ] Scheduler started             
2026-11-06T01:10:24.572689Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a', 'gl-b'] port=8991
2026-11-06T01:10:24.621409Z [warning  ] Graylog login refused: no role allowed to use jt-glogarch allowed=['Admin'] reason='no allowed role' roles=['Reader'] server=a user=reader1
2026-11-06T01:10:24.624202Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=b
2026-11-06T01:10:24.643986Z [info     ] API Audit listener stopped    
2026-11-06T01:10:24.661444Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_localadmin_still_signs_in 2026-11-06T01:10:25.310693Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-06T01:10:25.331938Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-06T01:10:25.351645Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-06T01:10:25.354580Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-06T01:10:25.355171Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-06T01:10:25.355637Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-06T01:10:25.360894Z [info     ] Scheduler started             
2026-11-06T01:10:25.371176Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-06T01:10:25.507127Z [info     ] API Audit listener stopped    
2026-11-06T01:10:25.557524Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_a_session_from_before_the_check_counts_as_signed_out PASSED
tests/test_login_roles.py::test_role_rule[roles0-perms0-allowed0-False] PASSED
tests/test_login_roles.py::test_role_rule[roles1-perms1-allowed1-True] PASSED
tests/test_login_roles.py::test_role_rule[roles2-perms2-allowed2-True] PASSED
tests/test_login_roles.py::test_role_rule[roles3-perms3-allowed3-True] PASSED
tests/test_login_roles.py::test_role_rule[roles4-perms4-allowed4-False] PASSED
tests/test_memguard.py::test_mem_action_tiers PASSED
tests/test_memguard.py::test_fail_open_when_unreadable PASSED
tests/test_memguard.py::test_reads_real_meminfo_on_linux PASSED
tests/test_multi_admin_guards.py::test_editing_a_schedule_keeps_it_disabled_and_keeps_its_server PASSED
tests/test_multi_admin_guards.py::test_schedule_with_unknown_server_is_refused PASSED
tests/test_multi_admin_guards.py::test_clearing_keep_indices_on_edit_actually_clears_it 2026-11-06T01:10:28.438275Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=os type=export
2026-11-06T01:10:28.511777Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=os type=export
PASSED
tests/test_multi_admin_guards.py::test_run_now_export_is_refused_while_an_export_of_that_server_runs 2026-11-06T01:10:29.425118Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=exp type=export
PASSED
tests/test_multi_admin_guards.py::test_run_now_cleanup_runs_in_background_with_the_schedules_retention 2026-11-06T01:10:30.181769Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-06T01:10:30.201856Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-06T01:10:30.218647Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-06T01:10:30.219372Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-06T01:10:30.220283Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-06T01:10:30.221528Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-06T01:10:30.222845Z [info     ] Scheduler started             
2026-11-06T01:10:30.222981Z [info     ] API Audit disabled            
2026-11-06T01:10:30.291147Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=cln type=cleanup
2026-11-06T01:10:30.342023Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=1500 retention_source=schedule
2026-11-06T01:10:30.399352Z [info     ] API Audit listener stopped    
2026-11-06T01:10:30.411915Z [info     ] Scheduler stopped             
PASSED
tests/test_multi_admin_guards.py::test_audit_toggle_with_a_stale_desired_state_changes_nothing PASSED
tests/test_multi_admin_guards.py::test_deleting_a_server_still_used_by_a_schedule_is_refused 2026-11-06T01:10:31.730653Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=exp-b type=export
PASSED
tests/test_multi_admin_guards.py::test_deleting_an_archive_that_is_being_imported_is_refused PASSED
tests/test_multi_admin_guards.py::test_clearing_an_index_set_while_an_import_writes_there_is_refused PASSED
tests/test_multi_admin_guards.py::test_cancelling_an_ended_in_memory_only_job_is_refused PASSED
tests/test_multi_admin_guards.py::test_scheduled_exports_publish_live_progress PASSED
tests/test_multi_server.py::test_config_supports_multiple_servers PASSED
tests/test_multi_server.py::test_get_server_by_name PASSED
tests/test_multi_server.py::test_get_opensearch_per_server_block PASSED
tests/test_multi_server.py::test_get_opensearch_empty_block_falls_back PASSED
tests/test_multi_server.py::test_get_opensearch_backward_compatible PASSED
tests/test_multi_server.py::test_scheduler_reads_server_from_config PASSED
tests/test_multi_server.py::test_schedule_ui_has_server_selector PASSED
tests/test_multi_server.py::test_schedule_js_saves_server PASSED
tests/test_multi_server.py::test_schedule_js_loads_server_on_edit PASSED
tests/test_notify_cancelled.py::test_cancelled_import_notifies_as_cancelled PASSED
tests/test_notify_cancelled.py::test_real_errors_before_a_cancel_are_still_shown PASSED
tests/test_notify_cancelled.py::test_uncancelled_errors_still_report_as_errors PASSED
tests/test_notify_format.py::test_export_ok_has_emoji PASSED
tests/test_notify_format.py::test_export_err_has_warning_emoji PASSED
tests/test_notify_format.py::test_verify_fail_has_x_emoji PASSED
tests/test_notify_format.py::test_error_title_has_x_emoji PASSED
tests/test_notify_format.py::test_export_body_per_line PASSED
tests/test_notify_format.py::test_url_shortening_in_errors PASSED
tests/test_notify_format.py::test_all_langs_have_same_keys PASSED
tests/test_notify_format.py::test_overflow_only_run_is_not_titled_as_error PASSED
tests/test_notify_format.py::test_real_error_still_outranks_overflow PASSED
tests/test_notify_format.py::test_clean_run_stays_success PASSED
tests/test_notify_format.py::test_notification_values_line_up_in_one_column[export_body-en] PASSED
tests/test_notify_format.py::test_notification_values_line_up_in_one_column[export_body-zh-TW] PASSED
tests/test_notify_format.py::test_notification_values_line_up_in_one_column[import_body-en] PASSED
tests/test_notify_format.py::test_notification_values_line_up_in_one_column[import_body-zh-TW] PASSED
tests/test_notify_format.py::test_notification_values_line_up_in_one_column[cleanup_body-en] PASSED
tests/test_notify_format.py::test_notification_values_line_up_in_one_column[cleanup_body-zh-TW] PASSED
tests/test_notify_format.py::test_notification_values_line_up_in_one_column[verify_body-en] PASSED
tests/test_notify_format.py::test_notification_values_line_up_in_one_column[verify_body-zh-TW] PASSED
tests/test_notify_format.py::test_zh_bodies_use_fullwidth_colons[en] PASSED
tests/test_notify_format.py::test_zh_bodies_use_fullwidth_colons[zh-TW] PASSED
tests/test_notify_format.py::test_overflow_timestamps_show_local_time_not_only_utc PASSED
tests/test_notify_format.py::test_overflow_timestamp_formatting_never_raises_on_junk PASSED
tests/test_notify_format.py::test_telegram_body_escapes_html_and_is_monospace PASSED
tests/test_notify_format.py::test_overflow_notice_states_how_many_were_not_read PASSED
tests/test_notify_ja.py::test_ja_has_exactly_the_english_keys PASSED
tests/test_notify_ja.py::test_ja_placeholders_match_english PASSED
tests/test_notify_ja.py::test_ja_has_no_traditional_chinese_characters PASSED
tests/test_notify_ja.py::test_ja_uses_fullwidth_punctuation_next_to_japanese PASSED
tests/test_notify_ja.py::test_ja_keeps_the_status_emoji PASSED
tests/test_notify_ja.py::test_ja_values_line_up_in_one_column[export_body] PASSED
tests/test_notify_ja.py::test_ja_values_line_up_in_one_column[import_body] PASSED
tests/test_notify_ja.py::test_ja_values_line_up_in_one_column[cleanup_body] PASSED
tests/test_notify_ja.py::test_ja_values_line_up_in_one_column[verify_body] PASSED
tests/test_notify_ja.py::test_lookup_returns_japanese_when_language_is_ja PASSED
tests/test_notify_ja.py::test_real_import_notification_is_japanese PASSED
tests/test_notify_ja.py::test_test_notification_endpoint_has_a_japanese_branch PASSED
tests/test_notify_test_endpoint.py::test_send_discord_params PASSED
tests/test_notify_test_endpoint.py::test_send_slack_params PASSED
tests/test_notify_test_endpoint.py::test_send_teams_params PASSED
tests/test_notify_test_endpoint.py::test_send_telegram_params PASSED
tests/test_notify_test_endpoint.py::test_send_nextcloud_talk_params PASSED
tests/test_notify_test_endpoint.py::test_send_zulip_params PASSED
tests/test_notify_test_endpoint.py::test_send_email_params PASSED
tests/test_notify_test_endpoint.py::test_test_endpoint_calls_match_signatures PASSED
tests/test_notify_zulip.py::test_zulip_posts_a_stream_message_with_basic_auth PASSED
tests/test_notify_zulip.py::test_zulip_uses_the_configured_topic PASSED
tests/test_notify_zulip.py::test_zulip_error_says_what_zulip_said PASSED
tests/test_notify_zulip.py::test_zulip_with_missing_settings_fails_without_sending PASSED
tests/test_notify_zulip.py::test_zulip_code_fence_cannot_be_closed_by_the_message PASSED
tests/test_notify_zulip.py::test_every_path_goes_through_one_channel_list 2026-11-06T01:10:35.797881Z [info     ] Notification sent              channel=zulip notify_event=error
PASSED
tests/test_notify_zulip.py::test_settings_api_masks_the_key_and_keeps_it_when_saved_masked PASSED
tests/test_notify_zulip.py::test_settings_api_refuses_a_link_local_zulip_url PASSED
tests/test_opensearch_client.py::test_search_sort_uses_doc_not_id PASSED
tests/test_opensearch_multicluster.py::test_status_reports_per_server_vs_global PASSED
tests/test_opensearch_multicluster.py::test_reorder_is_server_aware PASSED
tests/test_opensearch_multicluster.py::test_reorder_without_server_touches_global PASSED
tests/test_os_export_multiprefix.py::test_denominator_is_grand_total_across_prefixes 2026-11-06T01:10:43.185263Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-11-06T01:10:43.185647Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-06T01:10:43.185837Z [info     ] Found indices                  count=3 prefix=graylog
2026-11-06T01:10:43.185967Z [info     ] Skipping active write index    index=graylog_write
2026-11-06T01:10:43.186499Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-11-06T01:10:43.187668Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-11-06T01:10:43.188127Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-11-06T01:10:43.188287Z [info     ] Found indices                  count=2 prefix=noise_38
2026-11-06T01:10:43.188404Z [info     ] Skipping active write index    index=noise_38_write
2026-11-06T01:10:43.189074Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-11-06T01:10:43.217771Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-11-06T01:10:43.218339Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-06T01:10:43.242687Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_denominator_is_grand_tota0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:10:43.268265Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-11-06T01:10:43.268993Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-11-06T01:10:43.292130Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_denominator_is_grand_tota0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:10:43.343805Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-11-06T01:10:43.344540Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-11-06T01:10:43.375942Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_denominator_is_grand_tota0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:10:43.446032Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-11-06T01:10:43.487351Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_multiprefix.py::test_progress_never_exceeds_total 2026-11-06T01:10:44.693348Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-11-06T01:10:44.693810Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-06T01:10:44.693998Z [info     ] Found indices                  count=3 prefix=graylog
2026-11-06T01:10:44.694124Z [info     ] Skipping active write index    index=graylog_write
2026-11-06T01:10:44.708450Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-11-06T01:10:44.709885Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-11-06T01:10:44.710397Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-11-06T01:10:44.710615Z [info     ] Found indices                  count=2 prefix=noise_38
2026-11-06T01:10:44.710741Z [info     ] Skipping active write index    index=noise_38_write
2026-11-06T01:10:44.711129Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-11-06T01:10:44.777867Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-11-06T01:10:44.793193Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-06T01:10:44.829636Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_progress_never_exceeds_to0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:10:44.852439Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-11-06T01:10:44.853343Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-11-06T01:10:44.871882Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_progress_never_exceeds_to0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:10:44.887799Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-11-06T01:10:44.888443Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-11-06T01:10:44.903195Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_progress_never_exceeds_to0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:10:44.915093Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-11-06T01:10:44.938109Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_multiprefix.py::test_denominator_is_stable_no_regression 2026-11-06T01:10:45.620944Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-11-06T01:10:45.622467Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-06T01:10:45.622957Z [info     ] Found indices                  count=3 prefix=graylog
2026-11-06T01:10:45.623101Z [info     ] Skipping active write index    index=graylog_write
2026-11-06T01:10:45.625064Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-11-06T01:10:45.629086Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-11-06T01:10:45.630902Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-11-06T01:10:45.631166Z [info     ] Found indices                  count=2 prefix=noise_38
2026-11-06T01:10:45.632130Z [info     ] Skipping active write index    index=noise_38_write
2026-11-06T01:10:45.633899Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-11-06T01:10:45.651321Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-11-06T01:10:45.651939Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-06T01:10:45.668514Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_denominator_is_stable_no_0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:10:45.697989Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-11-06T01:10:45.700202Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-11-06T01:10:45.744265Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_denominator_is_stable_no_0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:10:45.786684Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-11-06T01:10:45.787832Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-11-06T01:10:45.804658Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-70/test_denominator_is_stable_no_0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-11-06T01:10:45.826126Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-11-06T01:10:45.842191Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_progress.py::test_denominator_is_accumulated_not_reset_per_prefix PASSED
tests/test_os_export_progress.py::test_update_job_uses_grand_total_not_prefix_total PASSED
tests/test_os_export_progress.py::test_denominator_is_stable_two_phase PASSED
tests/test_os_export_progress.py::test_grand_total_initialised_before_prefix_loop PASSED
tests/test_os_page_sizing.py::test_wide_docs_shrink_the_page 2026-11-06T01:10:45.917333Z [info     ] Fetching from index            index=idx shards=1 total=25000
2026-11-06T01:10:48.334777Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9130 index=idx page_size=1837 was=10000
2026-11-06T01:10:51.501296Z [info     ] Index fetch completed          fetched=25000 index=idx shards=1
PASSED
tests/test_os_page_sizing.py::test_typical_docs_keep_full_page 2026-11-06T01:10:51.510826Z [info     ] Fetching from index            index=idx shards=1 total=25000
2026-11-06T01:10:52.649897Z [info     ] Index fetch completed          fetched=25000 index=idx shards=1
PASSED
tests/test_os_page_sizing.py::test_adaptation_never_below_floor 2026-11-06T01:10:52.666601Z [info     ] Fetching from index            index=idx shards=1 total=3000
2026-11-06T01:10:59.628620Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=120130 index=idx page_size=500 was=10000
2026-11-06T01:10:59.637700Z [info     ] Index fetch completed          fetched=3000 index=idx shards=1
PASSED
tests/test_os_page_sizing.py::test_adaptation_does_not_raise 2026-11-06T01:10:59.695777Z [info     ] Fetching from index            index=idx shards=1 total=12000
2026-11-06T01:11:02.594613Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9130 index=idx page_size=1837 was=10000
2026-11-06T01:11:03.092834Z [info     ] Index fetch completed          fetched=12000 index=idx shards=1
PASSED
tests/test_os_scan_reconcile.py::test_short_scan_raises_instead_of_reporting_success 2026-11-06T01:11:03.098672Z [info     ] Fetching from index            index=idx shards=1 total=8
2026-11-06T01:11:03.099070Z [error    ] Index scan returned fewer documents than the index reported. The chunks already written are valid, but this index is NOT completely archived for this run. expected=8 fetched=5 index=idx missing=3 per_shard=None shards=1
PASSED
tests/test_os_scan_reconcile.py::test_the_error_names_the_shard_count_when_it_can 2026-11-06T01:11:03.104952Z [info     ] Fetching from index            index=idx shards=4 total=8
2026-11-06T01:11:03.105925Z [error    ] Index scan returned fewer documents than the index reported. The chunks already written are valid, but this index is NOT completely archived for this run. expected=8 fetched=5 index=idx missing=3 per_shard={0: 5} shards=4
PASSED
tests/test_os_scan_reconcile.py::test_a_complete_scan_does_not_raise 2026-11-06T01:11:03.111370Z [info     ] Fetching from index            index=idx shards=1 total=16
2026-11-06T01:11:03.111857Z [info     ] Index fetch completed          fetched=16 index=idx shards=1
PASSED
tests/test_os_scan_reconcile.py::test_reading_more_than_counted_is_not_an_error 2026-11-06T01:11:03.117252Z [info     ] Fetching from index            index=idx shards=1 total=11
2026-11-06T01:11:03.117768Z [info     ] Index held more documents than the pre-scan count counted=11 fetched=14 index=idx
2026-11-06T01:11:03.117954Z [info     ] Index fetch completed          fetched=14 index=idx shards=1
PASSED
tests/test_os_scan_reconcile.py::test_an_intentional_early_stop_is_never_reported_as_loss 2026-11-06T01:11:03.123043Z [info     ] Fetching from index            index=idx shards=1 total=30
PASSED
tests/test_os_scan_reconcile.py::test_an_empty_index_is_not_a_short_scan PASSED
tests/test_os_shard_scan.py::test_the_old_single_cursor_really_did_drop_records 2026-11-06T01:11:03.140518Z [info     ] Fetching from index            index=idx shards=1 total=24
2026-11-06T01:11:03.141325Z [error    ] Index scan returned fewer documents than the index reported. The chunks already written are valid, but this index is NOT completely archived for this run. expected=24 fetched=22 index=idx missing=2 per_shard=None shards=1
PASSED
tests/test_os_shard_scan.py::test_per_shard_scan_returns_every_document 2026-11-06T01:11:03.156526Z [info     ] Fetching from index            index=idx shards=4 total=24
2026-11-06T01:11:03.161046Z [info     ] Index fetch completed          fetched=24 index=idx shards=4
PASSED
tests/test_os_shard_scan.py::test_merged_output_is_in_global_timestamp_order 2026-11-06T01:11:03.200061Z [info     ] Fetching from index            index=idx shards=4 total=24
2026-11-06T01:11:03.214380Z [info     ] Index fetch completed          fetched=24 index=idx shards=4
PASSED
tests/test_os_shard_scan.py::test_every_shard_request_pins_the_primary_copy 2026-11-06T01:11:03.236628Z [info     ] Fetching from index            index=idx shards=4 total=24
2026-11-06T01:11:03.241250Z [info     ] Index fetch completed          fetched=24 index=idx shards=4
PASSED
tests/test_os_shard_scan.py::test_bytes_in_flight_stay_within_the_single_page_budget 2026-11-06T01:11:03.260478Z [info     ] Fetching from index            index=idx shards=4 total=1600
2026-11-06T01:11:03.272586Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9068 index=idx page_size=231 was=2500
2026-11-06T01:11:03.275049Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9068 index=idx page_size=231 was=2500
2026-11-06T01:11:03.276873Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9068 index=idx page_size=231 was=2500
2026-11-06T01:11:03.279160Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9068 index=idx page_size=231 was=2500
2026-11-06T01:11:03.303023Z [info     ] Index fetch completed          fetched=1600 index=idx shards=4
PASSED
tests/test_os_shard_scan.py::test_no_prefetch_outlives_a_cancelled_scan 2026-11-06T01:11:03.312967Z [info     ] Fetching from index            index=idx shards=4 total=800
PASSED
tests/test_os_shard_scan.py::test_a_single_shard_index_is_scanned_exactly_as_before 2026-11-06T01:11:03.376434Z [info     ] Fetching from index            index=idx shards=1 total=9
2026-11-06T01:11:03.376990Z [info     ] Index fetch completed          fetched=9 index=idx shards=1
PASSED
tests/test_os_shard_scan.py::test_an_intentional_early_stop_is_never_reported_as_loss 2026-11-06T01:11:03.383768Z [info     ] Fetching from index            index=idx shards=4 total=24
PASSED
tests/test_os_upgrade_paths.py::test_upgrade_says_when_python_changed PASSED
tests/test_os_upgrade_paths.py::test_backup_does_not_need_the_installed_package PASSED
tests/test_os_upgrade_paths.py::test_version_probe_does_not_read_the_source_tree PASSED
tests/test_os_upgrade_paths.py::test_setuptools_is_ensured_before_building PASSED
tests/test_os_upgrade_paths.py::test_offline_upgrade_refuses_a_bundle_for_another_python_before_changing_anything PASSED
tests/test_os_upgrade_paths.py::test_fallback_backup_snippet_really_backs_up PASSED
tests/test_os_upgrade_paths.py::test_scripts_are_valid_bash PASSED
tests/test_overflow_holes.py::test_migration_adds_the_column_and_round_trips PASSED
tests/test_overflow_holes.py::test_coverage_has_a_one_millisecond_hole_at_the_overflow PASSED
tests/test_overflow_holes.py::test_without_an_overflow_the_hour_is_fully_covered PASSED
tests/test_overflow_holes.py::test_the_hole_reaches_both_dedup_rules_from_one_place 2026-11-06T01:11:07.158309Z [warning  ] Could not read archived ids for an overflow hole — that millisecond will be refilled whole error="[Errno 2] No such file or directory: 'a.json.gz'" ms=2026-09-09T08:25:02.000Z path=a.json.gz
PASSED
tests/test_overflow_holes.py::test_an_os_archive_of_the_hour_closes_the_hole PASSED
tests/test_overflow_holes.py::test_multiple_and_out_of_range_overflows PASSED
tests/test_overflow_holes.py::test_truncation_record_carries_the_count 2026-11-06T01:11:08.094410Z [info     ] Total messages to fetch        total=14
2026-11-06T01:11:08.097392Z [info     ] Advancing time window for deep pagination carry=4 fetched_so_far=4 new_from='2026-09-09 08:25:02' old_from='2026-09-09 08:25:00'
2026-11-06T01:11:08.101570Z [warning  ] Single-millisecond overflow during API export: more than 4 messages share 2026-09-09T08:25:02.000Z; Graylog's REST API cannot page past it. Kept the first 4, skipping the rest of this millisecond and continuing. Re-run this window in OpenSearch Direct mode to capture them all.
PASSED
tests/test_overflow_holes.py::test_the_refill_excludes_ids_the_api_archive_already_holds 2026-11-06T01:11:08.540373Z [info     ] Overflow hole: excluding already-archived ids ids=3 ms=2026-09-09T08:25:02.000Z
PASSED
tests/test_overflow_holes.py::test_an_unreadable_archive_degrades_to_the_range_refill 2026-11-06T01:11:08.849067Z [warning  ] Could not read archived ids for an overflow hole — that millisecond will be refilled whole error="[Errno 2] No such file or directory: '/tmp/pytest-of-root/pytest-70/test_an_unreadable_archive_deg0/missing.json.gz'" ms=2026-09-09T08:25:02.000Z path=/tmp/pytest-of-root/pytest-70/test_an_unreadable_archive_deg0/missing.json.gz
PASSED
tests/test_pack_guide.py::test_every_language_has_the_same_keys_and_placeholders PASSED
tests/test_pack_guide.py::test_japanese_is_not_copied_chinese PASSED
tests/test_pack_guide.py::test_cjk_uses_fullwidth_punctuation[zh-TW] PASSED
tests/test_pack_guide.py::test_cjk_uses_fullwidth_punctuation[ja] PASSED
tests/test_pack_guide.py::test_chinese_uses_taiwan_terms PASSED
tests/test_pack_guide.py::test_sop_has_all_three_procedures_in_the_asked_language[en-heads0] PASSED
tests/test_pack_guide.py::test_sop_has_all_three_procedures_in_the_asked_language[zh-TW-heads1] PASSED
tests/test_pack_guide.py::test_sop_has_all_three_procedures_in_the_asked_language[ja-heads2] PASSED
tests/test_pack_guide.py::test_only_the_other_languages_are_absent PASSED
tests/test_pack_guide.py::test_unknown_language_falls_back_to_english PASSED
tests/test_pack_guide.py::test_a_paused_stream_is_named_as_a_step PASSED
tests/test_pack_guide.py::test_no_stream_means_no_start_step PASSED
tests/test_pack_guide.py::test_a_stream_rule_on_a_hostname_must_be_changed PASSED
tests/test_pack_guide.py::test_pipeline_connection_steps_follow_the_pack PASSED
tests/test_pack_guide.py::test_missing_lookup_table_is_listed PASSED
tests/test_pack_guide.py::test_alert_notification_facts PASSED
tests/test_pack_guide.py::test_required_version_comes_from_the_pack PASSED
tests/test_pack_guide.py::test_a_false_version_claim_is_not_repeated PASSED
tests/test_pack_guide.py::test_a_converted_file_names_only_its_own_version PASSED
tests/test_pack_guide.py::test_values_cannot_become_markup PASSED
tests/test_pack_guide.py::test_code_span_survives_backticks_in_the_value PASSED
tests/test_pack_guide.py::test_notes_replace_the_untranslated_description PASSED
tests/test_pack_guide.py::test_without_notes_the_description_is_labelled_as_original PASSED
tests/test_pack_guide.py::test_no_input_note_drops_the_create_input_step PASSED
tests/test_pack_guide.py::test_upgrade_and_uninstall_name_what_this_pack_leaves_behind PASSED
tests/test_pack_guide.py::test_rules_without_a_shared_prefix_are_listed PASSED
tests/test_pack_guide.py::test_a_long_list_is_named_by_its_prefix PASSED
tests/test_pack_guide.py::test_no_pipelines_means_no_extractor_step PASSED
tests/test_pack_guide.py::test_upgrade_notes_from_the_library_come_before_the_steps PASSED
tests/test_pack_guide.py::test_zip_holds_the_pack_and_the_guide[en-SOP-install-upgrade-uninstall.md] PASSED
tests/test_pack_guide.py::test_zip_holds_the_pack_and_the_guide[zh-TW-SOP-\u5b89\u88dd-\u5347\u7d1a-\u89e3\u9664\u5b89\u88dd.md] PASSED
tests/test_pack_guide.py::test_zip_holds_the_pack_and_the_guide[ja-SOP-\u30a4\u30f3\u30b9\u30c8\u30fc\u30eb-\u30a2\u30c3\u30d7\u30b0\u30ec\u30fc\u30c9-\u30a2\u30f3\u30a4\u30f3\u30b9\u30c8\u30fc\u30eb.md] PASSED
tests/test_pack_guide.py::test_a_converted_download_says_so PASSED
tests/test_pack_guide.py::test_library_notes_are_found_and_bad_ones_are_harmless 2026-11-06T01:11:08.982746Z [warning  ] Unreadable guide notes in the library error='Expecting value: line 1 column 1 (char 0)' path=/tmp/pytest-of-root/pytest-70/test_library_notes_are_found_a0/guide-notes.i18n
PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[apache] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[aruba] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[check-point] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[cisco-switch] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[crowdstrike] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[data-retention] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[eagle-api] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[f5-bigip] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[fortiadc] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[fortigate] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[fortiwan] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[hyper-v] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[iis] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[imperva-waf] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[linux-login] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[ms-dns] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[nextcloud] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[nginx] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[nutanix] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[palo-alto] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[pcap] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[proxmox] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[qnap] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[sophos] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[sql-server] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[suricata] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[synology] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[trend-apex] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[unifi] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[vcenter] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[wazuh] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[windows-ad] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[windows-fileserver] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[windows-logon] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[mail_zimbra_pmg] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[netflow] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[pfsense_opnsense] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[samba] PASSED
tests/test_packs.py::test_real_packs_are_understood[mail_zimbra_pmg-119-98-1-1-1-18] PASSED
tests/test_packs.py::test_real_packs_are_understood[pfsense_opnsense-58-53-3-0-2-0] PASSED
tests/test_packs.py::test_real_packs_are_understood[samba-41-33-1-1-1-5] PASSED
tests/test_packs.py::test_real_packs_are_understood[netflow-1-0-0-0-1-0] PASSED
tests/test_packs.py::test_notes_on_pfsense_are_reported_before_install PASSED
tests/test_packs.py::test_taken_rule_or_pipeline_title_blocks_because_graylog_rolls_back PASSED
tests/test_packs.py::test_a_stream_is_flagged_as_starting_paused PASSED
tests/test_packs.py::test_a_check_it_could_not_make_is_never_reported_as_clean PASSED
tests/test_packs.py::test_version_constraint PASSED
tests/test_packs.py::test_references_outside_the_pack PASSED
tests/test_packs.py::test_rule_renamed_only_in_title_is_flagged PASSED
tests/test_packs.py::test_validate_refuses[change0-UUID] PASSED
tests/test_packs.py::test_validate_refuses[change1-rev] PASSED
tests/test_packs.py::test_validate_refuses[change2-rev] PASSED
tests/test_packs.py::test_validate_refuses[change3-name] PASSED
tests/test_packs.py::test_validate_refuses[change4-entity list] PASSED
tests/test_packs.py::test_validate_refuses[change5-malformed] PASSED
tests/test_packs.py::test_validate_refuses_repeated_entity_ids PASSED
tests/test_packs.py::test_diff_names_what_changed PASSED
tests/test_packs.py::test_a_number_the_browser_rewrites_is_not_a_change PASSED
tests/test_packs.py::test_new_revision_keeps_the_id_whatever_the_edit_says PASSED
tests/test_packs.py::test_library_keeps_revisions_and_refuses_overwrite PASSED
tests/test_packs.py::test_library_files_are_not_world_readable PASSED
tests/test_packs.py::test_a_published_pack_can_be_edited_but_not_deleted PASSED
tests/test_packs.py::test_junk_in_the_library_is_ignored 2026-11-06T01:11:12.879261Z [warning  ] Unreadable file in the content pack library error='Expecting property name enclosed in double quotes: line 1 column 2 (char 1)' path=/tmp/pytest-of-root/pytest-70/test_junk_in_the_library_is_ig0/local/bad.json
2026-11-06T01:11:12.879768Z [warning  ] Not a valid content pack, ignored path=/tmp/pytest-of-root/pytest-70/test_junk_in_the_library_is_ig0/local/notpack.json
PASSED
tests/test_packs.py::test_the_published_library_holds_only_packs_the_owner_agreed_to_publish PASSED
tests/test_packs.py::test_the_local_library_is_outside_everything_that_gets_shipped PASSED
tests/test_packs.py::test_the_code_of_this_feature_gets_through_the_gate PASSED
tests/test_packs.py::test_the_wheel_would_carry_a_published_pack PASSED
tests/test_packs.py::test_graylog_calls_need_a_graylog_signin PASSED
tests/test_packs.py::test_the_library_works_without_any_graylog_signin PASSED
tests/test_packs.py::test_install_from_library_uploads_then_installs_and_lists_paused_streams PASSED
tests/test_packs.py::test_install_is_rechecked_on_the_server_not_trusted_from_the_page PASSED
tests/test_packs.py::test_failed_install_leaves_no_uploaded_revision_behind PASSED
tests/test_packs.py::test_failed_install_does_not_delete_a_revision_that_was_already_there PASSED
tests/test_packs.py::test_same_revision_with_other_content_is_not_silently_installed PASSED
tests/test_packs.py::test_editing_on_graylog_adds_a_revision_and_keeps_the_old_one PASSED
tests/test_packs.py::test_edit_based_on_an_old_revision_is_refused PASSED
tests/test_packs.py::test_editing_in_the_library_adds_a_revision PASSED
tests/test_packs.py::test_edit_cannot_save_an_invalid_pack PASSED
tests/test_packs.py::test_view_and_check_of_an_unsaved_file_store_nothing PASSED
tests/test_packs.py::test_delete_all_refuses_while_installed_and_says_why PASSED
tests/test_packs.py::test_uninstall_flow PASSED
tests/test_packs.py::test_library_ids_cannot_walk_out_of_the_library PASSED
tests/test_packs.py::test_download_is_the_pack_itself PASSED
tests/test_packs.py::test_parse_reports_graylogs_errors PASSED
tests/test_packs.py::test_start_streams_takes_only_real_ids PASSED
tests/test_packs.py::test_sensitive_values_are_found_and_can_be_removed[recipient] PASSED
tests/test_packs.py::test_sensitive_values_are_found_and_can_be_removed[http url] PASSED
tests/test_packs.py::test_sensitive_values_are_found_and_can_be_removed[api key] PASSED
tests/test_packs.py::test_sensitive_values_are_found_and_can_be_removed[wrapped password] PASSED
tests/test_packs.py::test_sensitive_values_are_found_and_can_be_removed[webhook] PASSED
tests/test_packs.py::test_sensitive_values_are_found_and_can_be_removed[mail in a widget query] PASSED
tests/test_packs.py::test_sensitive_values_are_found_and_can_be_removed[password in rule source] PASSED
tests/test_packs.py::test_sensitive_values_are_found_and_can_be_removed[user:pass in a url] PASSED
tests/test_packs.py::test_sensitive_values_are_found_and_can_be_removed[bearer token] PASSED
tests/test_packs.py::test_a_mask_never_shows_the_secret PASSED
tests/test_packs.py::test_things_that_only_look_sensitive_do_not_block[grok pattern after password=-data0] PASSED
tests/test_packs.py::test_things_that_only_look_sensitive_do_not_block[off is not a credential-data1] PASSED
tests/test_packs.py::test_things_that_only_look_sensitive_do_not_block[a parameter reference-data2] PASSED
tests/test_packs.py::test_things_that_only_look_sensitive_do_not_block[a field named token in a list-data3] PASSED
tests/test_packs.py::test_graylogs_own_default_packs_are_not_flagged PASSED
tests/test_packs.py::test_a_lookalike_of_a_public_host_is_still_flagged PASSED
tests/test_packs.py::test_removing_a_notification_also_unhooks_event_definitions PASSED
tests/test_packs.py::test_nothing_sensitive_leaves_without_a_decision PASSED
tests/test_packs.py::test_the_list_flags_a_sensitive_pack PASSED
tests/test_packs.py::test_63_download_loses_exactly_what_63_rejects PASSED
tests/test_packs.py::test_70_download_loses_what_70_rejects_and_keeps_the_rest PASSED
tests/test_packs.py::test_the_newest_target_changes_only_the_version_claims PASSED
tests/test_packs.py::test_no_target_older_than_63 PASSED
tests/test_packs.py::test_srv_catalog_covers_this_features_messages PASSED
tests/test_packs.py::test_dashboard_preview_shows_queries_in_our_own_box_not_the_browser_tooltip PASSED
tests/test_password_autocomplete.py::test_login_and_main_page_password_fields_disable_autocomplete PASSED
tests/test_password_autocomplete.py::test_login_form_itself_disables_autocomplete PASSED
tests/test_perf_covered_ranges.py::test_null_spans_cache_gives_identical_results PASSED
tests/test_perf_covered_ranges.py::test_string_merge_equals_datetime_merge_on_noncanonical_rows PASSED
tests/test_perf_covered_ranges.py::test_scheduled_run_pattern_stays_fast_at_scale PASSED
tests/test_perf_covered_ranges.py::test_zero_chunk_duration_cannot_hang_the_export PASSED
tests/test_perf_covered_ranges.py::test_jobs_table_has_a_polling_index_and_prune 2026-11-06T01:11:22.515292Z [info     ] Pruned old job-history rows    deleted=2 keep_days=365
PASSED
tests/test_posix_cron.py::test_dow_translation[0 0 * * 0-0 0 * * 6] PASSED
tests/test_posix_cron.py::test_dow_translation[0 0 * * 7-0 0 * * 6] PASSED
tests/test_posix_cron.py::test_dow_translation[0 3 1-7 * 6-0 3 1-7 * 5] PASSED
tests/test_posix_cron.py::test_dow_translation[0 0 * * 1-0 0 * * 0] PASSED
tests/test_posix_cron.py::test_dow_translation[0 0 * * 1-5-0 0 * * 0-4] PASSED
tests/test_posix_cron.py::test_dow_translation[0 0 * * 0,3,6-0 0 * * 6,2,5] PASSED
tests/test_posix_cron.py::test_dow_translation[0 0 * * 5-1-0 0 * * 4-6,0] PASSED
tests/test_posix_cron.py::test_dow_translation[0 0 * * 5-2-0 0 * * 4-6,0-1] PASSED
tests/test_posix_cron.py::test_dow_translation[0 0 * * 6-0-0 0 * * 5-6] PASSED
tests/test_posix_cron.py::test_dow_translation[0 0 * * sat-0 0 * * sat] PASSED
tests/test_posix_cron.py::test_dow_translation[0 0 * * mon-fri-0 0 * * mon-fri] PASSED
tests/test_posix_cron.py::test_dow_translation[0 0 * * *-0 0 * * *] PASSED
tests/test_posix_cron.py::test_dow_translation[0 */6 * * *-0 */6 * * *] PASSED
tests/test_posix_cron.py::test_dow_translation[0 3 * * *-0 3 * * *] PASSED
tests/test_posix_cron.py::test_non_5_field_passthrough PASSED
tests/test_posix_cron.py::test_real_dow_alignment PASSED
tests/test_posix_cron.py::test_weekly_sunday_midnight PASSED
tests/test_preflight_conflicts.py::test_intra_archive_conflict PASSED
tests/test_preflight_conflicts.py::test_cross_conflict_actual_mapping PASSED
tests/test_preflight_conflicts.py::test_string_only_no_target_mapping_not_pinned PASSED
tests/test_preflight_conflicts.py::test_mixed_scenario PASSED
tests/test_preflight_conflicts.py::TestFieldLimitAutoRaise::test_sizing_floor_and_headroom PASSED
tests/test_preflight_conflicts.py::TestFieldLimitAutoRaise::test_template_body_carries_the_computed_limit 2026-11-06T01:11:22.631095Z [info     ] Field limit applied to existing indices limit=30518 pattern=jt_restored_*
2026-11-06T01:11:22.632348Z [info     ] Bulk index template installed  pattern=jt_restored_* pinned_fields=1 template=jt_restored_template
PASSED
tests/test_preflight_conflicts.py::TestFieldLimitAutoRaise::test_rejected_limit_is_doubled_once_not_aborted 2026-11-06T01:11:22.644344Z [warning  ] Template rejected at field limit — retrying doubled limit=10000 retry=20000 template=jt_restored_template
2026-11-06T01:11:22.647180Z [info     ] Field limit applied to existing indices limit=20000 pattern=jt_restored_*
2026-11-06T01:11:22.647428Z [info     ] Bulk index template installed  pattern=jt_restored_* pinned_fields=1 template=jt_restored_template
PASSED
tests/test_recent_fixes.py::test_notification_timestamp_uses_local_tz PASSED
tests/test_recent_fixes.py::test_notification_test_endpoint_uses_local_tz PASSED
tests/test_recent_fixes.py::test_retention_default_is_3_years PASSED
tests/test_recent_fixes.py::test_datanode_detection_in_servers_endpoint PASSED
tests/test_recent_fixes.py::test_datanode_warning_i18n_in_files PASSED
tests/test_recent_fixes.py::test_schedule_opensearch_mode_display PASSED
tests/test_recent_fixes.py::test_import_modal_datanode_warning PASSED
tests/test_recent_fixes.py::test_export_mode_datanode_warning PASSED
tests/test_recent_fixes.py::test_config_example_retention_1095 PASSED
tests/test_recent_fixes.py::test_notify_discord_correct_args PASSED
tests/test_recent_fixes.py::test_notify_test_endpoint_correct_args PASSED
tests/test_repo_structure.py::test_pyproject_at_root PASSED
tests/test_repo_structure.py::test_glogarch_package_at_root PASSED
tests/test_repo_structure.py::test_deploy_files_exist PASSED
tests/test_repo_structure.py::test_readme_files_exist PASSED
tests/test_repo_structure.py::test_changelog_files_exist PASSED
tests/test_repo_structure.py::test_config_docs_exist PASSED
tests/test_repo_structure.py::test_no_src_directory PASSED
tests/test_repo_structure.py::test_github_glogarch_matches_source PASSED
tests/test_repo_structure.py::test_github_scripts_match_source PASSED
tests/test_report_adhoc_range.py::test_saved_settings_behave_as_before_without_a_one_off_range PASSED
tests/test_report_adhoc_range.py::test_a_one_off_range_overrides_widget_times_and_midnight_snap PASSED
tests/test_report_adhoc_range.py::test_naive_values_are_read_in_the_server_timezone_and_aware_values_kept PASSED
tests/test_report_adhoc_range.py::test_an_inverted_or_partial_range_is_ignored_not_applied PASSED
tests/test_report_adhoc_range.py::test_generate_passes_the_range_for_this_run_and_never_saves_it PASSED
tests/test_report_adhoc_range.py::test_generate_without_a_body_uses_the_saved_settings PASSED
tests/test_report_adhoc_range.py::test_invalid_one_off_ranges_are_rejected_before_anything_runs[body0-only one bound] PASSED
tests/test_report_adhoc_range.py::test_invalid_one_off_ranges_are_rejected_before_anything_runs[body1-inverted] PASSED
tests/test_report_adhoc_range.py::test_invalid_one_off_ranges_are_rejected_before_anything_runs[body2-unparseable] PASSED
tests/test_report_adhoc_range.py::test_invalid_one_off_ranges_are_rejected_before_anything_runs[body3-wider than 400 days] PASSED
tests/test_report_bigrange.py::TestCoarsening::test_exploding_fixed_interval_is_coarsened_and_recorded PASSED
tests/test_report_bigrange.py::TestCoarsening::test_widget_config_schema_is_also_understood PASSED
tests/test_report_bigrange.py::TestCoarsening::test_auto_interval_is_left_alone PASSED
tests/test_report_bigrange.py::TestCoarsening::test_interval_that_fits_is_untouched PASSED
tests/test_report_bigrange.py::TestCoarsening::test_input_is_not_mutated PASSED
tests/test_report_bigrange.py::TestCoarsening::test_zh_note_uses_taiwan_wording PASSED
tests/test_report_bigrange.py::TestMergeEligibility::test_search_definition_series_schema_is_understood PASSED
tests/test_report_bigrange.py::TestMergeEligibility::test_exact_functions_are_mergeable PASSED
tests/test_report_bigrange.py::TestMergeEligibility::test_any_inexact_function_refuses_the_whole_search_type PASSED
tests/test_report_bigrange.py::TestMergeEligibility::test_empty_series_is_not_mergeable PASSED
tests/test_report_bigrange.py::TestSliceWindows::test_covers_the_window_disjointly PASSED
tests/test_report_bigrange.py::TestSliceWindows::test_empty_window_yields_nothing PASSED
tests/test_report_bigrange.py::TestPivotMerge::test_time_rows_concatenate_chronologically PASSED
tests/test_report_bigrange.py::TestPivotMerge::test_same_term_key_sums_counts_exactly PASSED
tests/test_report_bigrange.py::TestPivotMerge::test_min_and_max_merge_by_their_own_semantics PASSED
tests/test_report_bigrange.py::TestPivotMerge::test_effective_timerange_spans_all_slices PASSED
tests/test_report_bigrange.py::TestPivotMerge::test_empty_slices_are_skipped PASSED
tests/test_report_bigrange.py::TestMessageMerge::test_newest_n_overall PASSED
tests/test_report_deps_browser_build.py::test_an_older_build_is_not_mistaken_for_the_needed_one PASSED
tests/test_report_deps_browser_build.py::test_the_needed_build_already_present_is_skipped PASSED
tests/test_report_deps_browser_build.py::test_nothing_is_removed_when_the_install_fails PASSED
tests/test_report_deps_browser_build.py::test_no_presence_check_by_directory_name_alone PASSED
tests/test_report_deps_browser_build.py::test_helpers_never_abort_a_set_e_caller PASSED
tests/test_report_incomplete_notice.py::test_note_section_actually_renders PASSED
tests/test_report_incomplete_notice.py::test_note_description_is_not_duplicated PASSED
tests/test_report_incomplete_notice.py::test_incomplete_text_names_the_cause_and_the_remedy PASSED
tests/test_report_incomplete_notice.py::test_search_wait_is_configurable_not_hardcoded PASSED
tests/test_report_incomplete_notice.py::test_timeout_marks_the_run_incomplete PASSED
tests/test_report_incomplete_notice.py::test_axis_clamp_still_protects_sparse_widgets PASSED
tests/test_report_ja.py::test_every_zh_branch_in_the_report_package_also_handles_japanese PASSED
tests/test_report_ja.py::test_string_tables_have_japanese_for_every_english_key[builder._I18N] PASSED
tests/test_report_ja.py::test_string_tables_have_japanese_for_every_english_key[generator._TXT] PASSED
tests/test_report_ja.py::test_archive_summary_labels_have_japanese_for_every_english_key PASSED
tests/test_report_ja.py::test_time_span_and_row_count_wording PASSED
tests/test_report_ja.py::test_range_label_states_the_requested_window_in_japanese PASSED
tests/test_report_ja.py::test_incomplete_warning_and_rebuild_description PASSED
tests/test_report_ja.py::test_interval_coarsening_note_in_japanese PASSED
tests/test_report_ja.py::test_japanese_report_html_uses_a_japanese_face_first PASSED
tests/test_report_ja.py::test_band_and_watermark_font_prefers_japanese_faces_when_present PASSED
tests/test_report_ja.py::test_toc_entry_points_at_the_heading_not_a_sentence_that_mentions_it PASSED
tests/test_report_ja.py::test_archive_summary_counts_archives PASSED
tests/test_report_ja.py::test_report_form_offers_japanese_and_new_reports_follow_the_ui PASSED
tests/test_report_progress.py::test_rebuild_accepts_a_progress_callback PASSED
tests/test_report_progress.py::test_slicing_loop_reports_each_finished_slice PASSED
tests/test_report_progress.py::test_generator_threads_the_callback_into_the_rebuild PASSED
tests/test_report_progress.py::test_progress_callback_writes_columns_update_job_accepts PASSED
tests/test_report_progress.py::test_progress_never_claims_100_before_the_pdf_is_written PASSED
tests/test_report_progress.py::test_both_callers_pass_job_id PASSED
tests/test_report_progress.py::test_progress_never_goes_backwards_across_dashboards 2026-11-06T01:11:36.666340Z [info     ] Report generated               by=manual bytes=42127 emailed=False report=p
PASSED
tests/test_report_progress.py::test_sidebar_does_not_force_reports_to_an_indeterminate_bar PASSED
tests/test_reports.py::test_build_html_contains_cover_and_charts PASSED
tests/test_reports.py::test_chart_helpers_shapes PASSED
tests/test_reports.py::test_report_db_crud PASSED
tests/test_reports.py::test_archive_summary_sections_from_db PASSED
tests/test_reports.py::test_render_pdf_if_engine_available PASSED
tests/test_reports.py::test_time_pivot_sorts_and_zero_fills_modest_range PASSED
tests/test_reports.py::test_time_pivot_first_bucket_rounds_before_eff_from PASSED
tests/test_reports.py::test_time_pivot_clamps_when_eff_far_wider_than_data PASSED
tests/test_reports.py::test_time_pivot_tz_mismatch_never_raises PASSED
tests/test_reports.py::test_empty_non_count_metric_is_no_data_not_phantom PASSED
tests/test_reports.py::test_empty_count_metric_uses_total PASSED
tests/test_reports.py::test_empty_table_renders_no_phantom_row PASSED
tests/test_reports.py::test_pie_caps_to_others_preserving_total PASSED
tests/test_reports.py::test_heatmap_reverse_scale_inverts PASSED
tests/test_reports.py::test_empty_column_pivot_value_labeled_not_blank PASSED
tests/test_reports.py::test_null_rowpivot_value_does_not_shift_columns PASSED
tests/test_reports.py::TestCategoryAxisLabels::test_terms_bar_labels_every_category PASSED
tests/test_reports.py::TestCategoryAxisLabels::test_time_bar_keeps_the_thinned_axis PASSED
tests/test_reports.py::TestCategoryAxisLabels::test_horizontal_terms_bar_labels_every_category PASSED
tests/test_reports.py::TestCategoryAxisLabels::test_categorical_line_and_scatter_label_every_point PASSED
tests/test_reports.py::TestCategoryAxisLabels::test_time_line_keeps_thinned_axis PASSED
tests/test_reports.py::TestReportHonestyCaptions::test_requested_window_is_stated_when_data_covers_less PASSED
tests/test_reports.py::TestReportHonestyCaptions::test_no_warning_when_requested_matches_data PASSED
tests/test_reports.py::TestReportHonestyCaptions::test_table_always_states_the_total_row_count PASSED
tests/test_retention_estimate.py::test_basic_estimate_months PASSED
tests/test_retention_estimate.py::test_trailing_z_and_micros_parse PASSED
tests/test_retention_estimate.py::test_span_too_short_not_available PASSED
tests/test_retention_estimate.py::test_no_data_not_available PASSED
tests/test_retention_estimate.py::test_alert_threshold_semantics PASSED
tests/test_retry_import_ui.py::test_import_dialog_lives_only_on_the_archives_page PASSED
tests/test_retry_import_ui.py::test_retry_from_job_history_goes_to_the_archives_page PASSED
tests/test_retry_import_ui.py::test_retry_prefills_the_job_target_before_the_autofill PASSED
tests/test_retry_import_ui.py::test_gelf_never_forwards_the_message_id PASSED
tests/test_retry_import_ui.py::test_retry_messages_exist_with_their_placeholders PASSED
tests/test_retry_import_ui.py::test_retry_mode_follows_what_reached_the_target PASSED
tests/test_sanitize.py::test_none_passthrough PASSED
tests/test_sanitize.py::test_password_url_style PASSED
tests/test_sanitize.py::test_password_json_style PASSED
tests/test_sanitize.py::test_token_redaction PASSED
tests/test_sanitize.py::test_basic_auth_header PASSED
tests/test_sanitize.py::test_bearer_token PASSED
tests/test_sanitize.py::test_url_with_credentials PASSED
tests/test_sanitize.py::test_truncation PASSED
tests/test_sanitize.py::test_no_false_positive PASSED
tests/test_sanitize.py::test_mixed_secrets PASSED
tests/test_schedule_lock_skip.py::test_a_long_export_that_is_advancing_never_alerts 2026-11-06T01:11:41.524247Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=518394098 records_total=11579254477 schedule=auto-export skipped_in_a_row=1
2026-11-06T01:11:41.524978Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=527094098 records_total=11579254477 schedule=auto-export skipped_in_a_row=2
2026-11-06T01:11:41.525500Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=535794098 records_total=11579254477 schedule=auto-export skipped_in_a_row=3
2026-11-06T01:11:41.526279Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=544494098 records_total=11579254477 schedule=auto-export skipped_in_a_row=4
2026-11-06T01:11:41.526993Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=553194098 records_total=11579254477 schedule=auto-export skipped_in_a_row=5
2026-11-06T01:11:41.527627Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=561894098 records_total=11579254477 schedule=auto-export skipped_in_a_row=6
2026-11-06T01:11:41.528211Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=570594098 records_total=11579254477 schedule=auto-export skipped_in_a_row=7
2026-11-06T01:11:41.528950Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=579294098 records_total=11579254477 schedule=auto-export skipped_in_a_row=8
2026-11-06T01:11:41.529504Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=587994098 records_total=11579254477 schedule=auto-export skipped_in_a_row=9
2026-11-06T01:11:41.530192Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=596694098 records_total=11579254477 schedule=auto-export skipped_in_a_row=10
PASSED
tests/test_schedule_lock_skip.py::test_stale_lock_with_no_running_export_alerts 2026-11-06T01:11:41.532792Z [error    ] Scheduled export skipped 1 run(s) in a row and NO export is running — the per-server lock is stale and this schedule has stopped archiving. Restart jt-glogarch to clear it. error='Export already running' schedule=auto-export
2026-11-06T01:11:41.533537Z [error    ] Scheduled export skipped 2 run(s) in a row and NO export is running — the per-server lock is stale and this schedule has stopped archiving. Restart jt-glogarch to clear it. error='Export already running' schedule=auto-export
PASSED
tests/test_schedule_lock_skip.py::test_a_running_export_that_stops_advancing_alerts_differently 2026-11-06T01:11:41.536346Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=509694098 records_total=11579254477 schedule=auto-export skipped_in_a_row=1
2026-11-06T01:11:41.537142Z [error    ] Scheduled export skipped 2 run(s) and the running export has not advanced across 1 of them (still 509,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
2026-11-06T01:11:41.538411Z [error    ] Scheduled export skipped 3 run(s) and the running export has not advanced across 2 of them (still 509,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
2026-11-06T01:11:41.539122Z [error    ] Scheduled export skipped 4 run(s) and the running export has not advanced across 3 of them (still 509,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
PASSED
tests/test_schedule_lock_skip.py::test_progress_resuming_clears_the_stalled_state 2026-11-06T01:11:41.541489Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=509694098 records_total=11579254477 schedule=auto-export skipped_in_a_row=1
2026-11-06T01:11:41.542172Z [error    ] Scheduled export skipped 2 run(s) and the running export has not advanced across 1 of them (still 509,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
2026-11-06T01:11:41.542902Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=514694098 records_total=11579254477 schedule=auto-export skipped_in_a_row=3
2026-11-06T01:11:41.543573Z [error    ] Scheduled export skipped 4 run(s) and the running export has not advanced across 1 of them (still 514,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
2026-11-06T01:11:41.544255Z [error    ] Scheduled export skipped 5 run(s) and the running export has not advanced across 2 of them (still 514,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
PASSED
tests/test_schedule_lock_skip.py::test_working_export_message_never_says_nothing_is_archived PASSED
tests/test_schedule_lock_skip.py::test_stale_lock_message_tells_the_operator_to_restart PASSED
tests/test_schedule_overlap_guard.py::test_a_second_schedule_is_not_blocked_by_the_first PASSED
tests/test_schedule_overlap_guard.py::test_the_same_schedule_still_does_not_overlap_itself 2026-11-06T01:11:41.614964Z [info     ] This export schedule is still running, skipping this run schedule=auto-export
PASSED
tests/test_schedule_running_visibility.py::test_list_running_jobs_finds_a_weeks_old_running_job PASSED
tests/test_schedule_running_visibility.py::test_schedule_dict_marks_running_and_drops_misleading_next_run PASSED
tests/test_schedule_running_visibility.py::test_source_without_schedule_name_is_ignored PASSED
tests/test_search_api.py::test_time_range_is_required PASSED
tests/test_search_api.py::test_time_range_must_be_ordered PASSED
tests/test_search_api.py::test_a_query_needs_a_term_or_a_filter PASSED
tests/test_search_api.py::test_terms_split_on_whitespace_and_are_anded PASSED
tests/test_search_api.py::test_field_filters_parse PASSED
tests/test_search_api.py::test_a_malformed_field_filter_is_rejected_not_ignored PASSED
tests/test_search_api.py::test_page_size_is_clamped_not_trusted PASSED
tests/test_search_api.py::test_a_non_numeric_limit_is_an_error PASSED
tests/test_search_api.py::test_plan_counts_without_opening_any_archive PASSED
tests/test_search_api.py::test_plan_rejects_a_bad_query_with_400 PASSED
tests/test_search_api.py::test_full_lifecycle_and_resume 2026-11-06T01:11:44.298847Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-06T01:11:44.301538Z [info     ] Archive search finished        cancelled=False examined=25 hits=7 parsed=1 scanned=0 seconds=0.0 truncated=True
2026-11-06T01:11:44.350126Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-06T01:11:44.355062Z [info     ] Archive search finished        cancelled=False examined=53 hits=7 parsed=2 scanned=1 seconds=0.0 truncated=True
2026-11-06T01:11:44.401679Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-06T01:11:44.406010Z [info     ] Archive search finished        cancelled=False examined=41 hits=7 parsed=2 scanned=2 seconds=0.0 truncated=True
2026-11-06T01:11:44.453020Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-06T01:11:44.455409Z [info     ] Archive search finished        cancelled=False examined=29 hits=7 parsed=1 scanned=2 seconds=0.0 truncated=True
2026-11-06T01:11:44.457630Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-06T01:11:44.460131Z [info     ] Archive search finished        cancelled=False examined=40 hits=2 parsed=1 scanned=3 seconds=0.0 truncated=False
PASSED
tests/test_search_api.py::test_more_is_refused_while_still_running PASSED
tests/test_search_api.py::test_more_is_refused_once_the_range_is_exhausted 2026-11-06T01:11:44.526754Z [info     ] Archive search starting        archives=1 filters=0 terms=1
2026-11-06T01:11:44.685911Z [info     ] Archive search finished        cancelled=False examined=10 hits=5 parsed=1 scanned=1 seconds=0.2 truncated=False
PASSED
tests/test_search_api.py::test_retained_hits_are_capped 2026-11-06T01:11:44.744244Z [info     ] Archive search starting        archives=1 filters=0 terms=1
2026-11-06T01:11:44.747006Z [info     ] Archive search finished        cancelled=False examined=10 hits=10 parsed=1 scanned=1 seconds=0.0 truncated=False
PASSED
tests/test_search_api.py::test_unknown_search_is_404_not_a_crash PASSED
tests/test_search_api.py::test_old_searches_are_pruned PASSED
tests/test_search_api.py::test_search_yields_to_a_running_export PASSED
tests/test_search_api.py::test_the_backend_refuses_a_rangeless_search_even_if_the_button_is_bypassed PASSED
tests/test_search_api.py::test_plan_also_refuses_without_a_range PASSED
tests/test_search_api.py::test_every_refusal_carries_a_translatable_code PASSED
tests/test_search_api.py::test_archive_total_is_known_before_the_first_poll 2026-11-06T01:11:44.834182Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-06T01:11:44.839531Z [info     ] Archive search finished        cancelled=False examined=40 hits=8 parsed=4 scanned=4 seconds=0.0 truncated=False
PASSED
tests/test_search_api.py::test_every_error_code_has_a_translation_in_both_languages PASSED
tests/test_search_api.py::test_a_quoted_phrase_is_one_term PASSED
tests/test_search_api.py::test_an_unbalanced_quote_is_not_an_error PASSED
tests/test_search_api.py::test_a_quoted_phrase_still_survives_the_byte_prefilter PASSED
tests/test_search_api.py::test_export_covers_every_page_not_just_the_first 2026-11-06T01:11:44.909279Z [info     ] Archive search (streaming) starting archives=3
2026-11-06T01:11:44.915041Z [info     ] Search export finished         fmt=csv rows=30 truncated=False
PASSED
tests/test_search_api.py::test_export_and_the_paged_screen_agree_on_what_matches 2026-11-06T01:11:44.923691Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-06T01:11:44.929223Z [info     ] Archive search finished        cancelled=False examined=120 hits=30 parsed=3 scanned=3 seconds=0.0 truncated=False
2026-11-06T01:11:44.929683Z [info     ] Archive search (streaming) starting archives=3
PASSED
tests/test_search_api.py::test_export_reads_each_archive_exactly_once 2026-11-06T01:11:44.947832Z [info     ] Archive search (streaming) starting archives=3
2026-11-06T01:11:44.953863Z [info     ] Search export finished         fmt=jsonl rows=30 truncated=False
PASSED
tests/test_search_api.py::test_export_streams_rather_than_building_the_file 2026-11-06T01:11:44.961894Z [info     ] Archive search (streaming) starting archives=3
2026-11-06T01:11:44.967640Z [info     ] Search export finished         fmt=jsonl rows=30 truncated=False
PASSED
tests/test_search_api.py::test_export_truncation_is_marked_in_the_file 2026-11-06T01:11:44.974888Z [info     ] Archive search (streaming) starting archives=3
2026-11-06T01:11:44.976613Z [warning  ] Search export hit the row ceiling rows=5
2026-11-06T01:11:44.976808Z [info     ] Search export finished         fmt=csv rows=5 truncated=True
2026-11-06T01:11:44.977064Z [info     ] Archive search (streaming) starting archives=3
2026-11-06T01:11:44.978885Z [warning  ] Search export hit the row ceiling rows=5
2026-11-06T01:11:44.979088Z [info     ] Search export finished         fmt=jsonl rows=5 truncated=True
PASSED
tests/test_search_api.py::test_csv_starts_with_a_bom_and_a_header 2026-11-06T01:11:44.984856Z [info     ] Archive search (streaming) starting archives=1
2026-11-06T01:11:44.986414Z [info     ] Search export finished         fmt=csv rows=2 truncated=False
PASSED
tests/test_search_api.py::test_jsonl_keeps_every_field_and_names_its_archive 2026-11-06T01:11:44.991950Z [info     ] Archive search (streaming) starting archives=1
2026-11-06T01:11:44.993838Z [info     ] Search export finished         fmt=jsonl rows=2 truncated=False
PASSED
tests/test_search_api.py::test_export_rejects_an_unknown_format PASSED
tests/test_search_api.py::test_export_still_requires_a_time_range PASSED
tests/test_search_api.py::test_export_is_audited PASSED
tests/test_search_api.py::test_export_route_is_declared_before_the_id_route PASSED
tests/test_search_engine.py::test_the_written_archive_really_has_no_newlines PASSED
tests/test_search_engine.py::test_prefilter_finds_a_term_and_rejects_an_absent_one PASSED
tests/test_search_engine.py::test_prefilter_requires_every_needle PASSED
tests/test_search_engine.py::test_prefilter_is_case_insensitive PASSED
tests/test_search_engine.py::test_prefilter_finds_a_term_straddling_the_chunk_boundary PASSED
tests/test_search_engine.py::test_prefilter_never_under_selects_on_a_json_escaped_term PASSED
tests/test_search_engine.py::test_prefilter_treats_an_unreadable_archive_as_a_candidate 2026-11-06T01:11:45.475228Z [warning  ] Search prefilter failed, parsing the archive anyway error="Not a gzipped file (b'th')" path=/tmp/pytest-of-root/pytest-70/test_prefilter_treats_an_unrea0/broken.json.gz
PASSED
tests/test_search_engine.py::test_terms_are_anded_and_match_any_field PASSED
tests/test_search_engine.py::test_field_filter_is_exact_not_substring PASSED
tests/test_search_engine.py::test_field_filter_on_a_missing_field_does_not_match PASSED
tests/test_search_engine.py::test_search_collects_only_matching_messages PASSED
tests/test_search_engine.py::test_a_non_matching_archive_is_never_parsed PASSED
tests/test_search_engine.py::test_missing_file_is_reported_not_silently_skipped PASSED
tests/test_search_engine.py::test_paging_returns_every_hit_exactly_once 2026-11-06T01:11:45.519714Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-06T01:11:45.521979Z [info     ] Archive search finished        cancelled=False examined=31 hits=7 parsed=1 scanned=0 seconds=0.0 truncated=True
2026-11-06T01:11:45.522304Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-06T01:11:45.525921Z [info     ] Archive search finished        cancelled=False examined=66 hits=7 parsed=2 scanned=1 seconds=0.0 truncated=True
2026-11-06T01:11:45.526209Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-06T01:11:45.529628Z [info     ] Archive search finished        cancelled=False examined=51 hits=7 parsed=2 scanned=2 seconds=0.0 truncated=True
2026-11-06T01:11:45.530035Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-06T01:11:45.532442Z [info     ] Archive search finished        cancelled=False examined=36 hits=7 parsed=1 scanned=2 seconds=0.0 truncated=True
2026-11-06T01:11:45.532760Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-06T01:11:45.536453Z [info     ] Archive search finished        cancelled=False examined=71 hits=7 parsed=2 scanned=3 seconds=0.0 truncated=True
2026-11-06T01:11:45.536713Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-06T01:11:45.538619Z [info     ] Archive search finished        cancelled=False examined=50 hits=5 parsed=1 scanned=4 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_an_exhausted_range_reports_no_next_page 2026-11-06T01:11:45.545803Z [info     ] Archive search starting        archives=2 filters=0 terms=1
2026-11-06T01:11:45.548389Z [info     ] Archive search finished        cancelled=False examined=20 hits=4 parsed=2 scanned=2 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_a_full_page_reports_a_next_page 2026-11-06T01:11:45.557034Z [info     ] Archive search starting        archives=2 filters=0 terms=1
2026-11-06T01:11:45.558996Z [info     ] Archive search finished        cancelled=False examined=21 hits=5 parsed=1 scanned=0 seconds=0.0 truncated=True
PASSED
tests/test_search_engine.py::test_resuming_does_not_rescan_earlier_archives 2026-11-06T01:11:45.570648Z [info     ] Archive search starting        archives=6 filters=0 terms=1
2026-11-06T01:11:45.574050Z [info     ] Archive search finished        cancelled=False examined=56 hits=12 parsed=2 scanned=1 seconds=0.0 truncated=True
2026-11-06T01:11:45.574255Z [info     ] Archive search starting        archives=6 filters=0 terms=1
2026-11-06T01:11:45.577319Z [info     ] Archive search finished        cancelled=False examined=66 hits=12 parsed=2 scanned=2 seconds=0.0 truncated=True
PASSED
tests/test_search_engine.py::test_cancel_stops_and_keeps_a_resume_point 2026-11-06T01:11:45.589179Z [info     ] Archive search starting        archives=5 filters=0 terms=1
2026-11-06T01:11:45.591403Z [info     ] Archive search finished        cancelled=True examined=50 hits=10 parsed=1 scanned=1 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_field_only_query_needs_no_terms 2026-11-06T01:11:45.599225Z [info     ] Archive search starting        archives=2 filters=1 terms=0
2026-11-06T01:11:45.601468Z [info     ] Archive search finished        cancelled=False examined=40 hits=40 parsed=2 scanned=2 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_progress_is_reported_per_archive 2026-11-06T01:11:45.611758Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-06T01:11:45.619547Z [info     ] Archive search finished        cancelled=False examined=80 hits=16 parsed=4 scanned=4 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_search_yields_between_archives 2026-11-06T01:11:45.628171Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-06T01:11:45.632552Z [info     ] Archive search finished        cancelled=False examined=30 hits=6 parsed=3 scanned=3 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_the_total_is_known_before_any_archive_is_opened 2026-11-06T01:11:45.642940Z [info     ] Archive search starting        archives=5 filters=0 terms=1
2026-11-06T01:11:45.651246Z [info     ] Archive search finished        cancelled=False examined=100 hits=20 parsed=5 scanned=5 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_hits_are_published_while_a_single_archive_is_still_being_parsed PASSED
tests/test_search_engine.py::test_intra_archive_reporting_is_time_throttled PASSED
tests/test_security.py::test_ssrf_blocks_cloud_metadata_and_link_local PASSED
tests/test_security.py::test_ssrf_allows_loopback_and_private PASSED
tests/test_security.py::test_ssrf_handles_bad_input PASSED
tests/test_security.py::test_docs_endpoints_disabled PASSED
tests/test_sensitive_notify_body.py::test_single_entry_renders_with_ip PASSED
tests/test_sensitive_notify_body.py::test_missing_ip_falls_back_to_user_only PASSED
tests/test_sensitive_notify_body.py::test_same_user_two_ips_does_not_merge PASSED
tests/test_sensitive_notify_body.py::test_same_user_same_ip_merges_with_count PASSED
tests/test_sensitive_notify_body.py::test_no_target_omits_brackets PASSED
tests/test_sensitive_notify_body.py::test_truncates_after_five_groups PASSED
tests/test_settings_api.py::test_fresh_install_redirects_to_setup PASSED
tests/test_settings_api.py::test_config_endpoints_require_auth PASSED
tests/test_settings_api.py::test_admin_password_requires_setup_session PASSED
tests/test_settings_api.py::test_setup_admin_password_short_rejected PASSED
tests/test_settings_api.py::test_setup_flow_then_gate_closes PASSED
tests/test_settings_api.py::test_wizard_reorder_config_written_before_admin_password PASSED
tests/test_settings_api.py::test_server_masking_and_secret_reconcile PASSED
tests/test_settings_api.py::test_server_delete_reassigns_default PASSED
tests/test_settings_api.py::test_opensearch_save_and_mask PASSED
tests/test_settings_api.py::test_login_with_empty_servers_does_not_500 PASSED
tests/test_settings_api.py::test_report_download_rejects_path_outside_reports_dir PASSED
tests/test_settings_api.py::test_login_iterates_all_servers_then_localadmin PASSED
tests/test_settings_api.py::test_upgrade_existing_servers_skip_wizard PASSED
tests/test_settings_api.py::test_upgrade_partial_edit_preserves_untouched_fields PASSED
tests/test_sizing_and_adaptive.py::test_xmx_parsing PASSED
tests/test_sizing_and_adaptive.py::test_colocated_heavy_matches_field_calibration PASSED
tests/test_sizing_and_adaptive.py::test_swap_in_use_is_critical PASSED
tests/test_sizing_and_adaptive.py::test_archive_only_node_is_modest PASSED
tests/test_sizing_and_adaptive.py::test_heaps_over_60pct_flagged PASSED
tests/test_sizing_and_adaptive.py::test_recommended_heaps_leave_room_for_page_cache PASSED
tests/test_sizing_and_adaptive.py::test_batch_shrinks_under_pressure_and_recovers PASSED
tests/test_sizing_and_adaptive.py::test_batch_never_below_floor PASSED
tests/test_sizing_and_adaptive.py::test_normal_memory_leaves_batch_alone PASSED
tests/test_sizing_and_adaptive.py::test_importer_iterates_archives_lazily PASSED
tests/test_sizing_and_adaptive.py::test_archive_disk_flags_retention_the_disk_cannot_hold PASSED
tests/test_sizing_and_adaptive.py::test_archive_disk_ok_when_retention_fits PASSED
tests/test_sizing_and_adaptive.py::test_archive_disk_absent_without_a_measured_rate PASSED
tests/test_srv_messages.py::test_catalog_is_present_in_every_language PASSED
tests/test_srv_messages.py::test_translations_keep_every_placeholder PASSED
tests/test_srv_messages.py::test_every_template_still_exists_in_the_backend PASSED
tests/test_srv_messages.py::test_every_template_translates_in_both_languages PASSED
tests/test_srv_messages.py::test_real_job_notes_translate PASSED
tests/test_srv_messages.py::test_unknown_text_and_english_are_left_alone PASSED
tests/test_srv_messages.py::test_ui_routes_server_text_through_the_translator PASSED
tests/test_startup_recovery.py::test_recover_stuck_importing PASSED
tests/test_startup_recovery.py::test_recover_stuck_importing_noop_when_clean PASSED
tests/test_static_sweeps.py::test_no_undefined_python_names PASSED
tests/test_static_sweeps.py::test_no_local_import_shadowing_module_imports PASSED
tests/test_static_sweeps.py::test_i18n_keys_exist_in_both_languages PASSED
tests/test_static_sweeps.py::test_every_data_act_handler_exists PASSED
tests/test_static_sweeps.py::test_silent_except_count_only_goes_down PASSED
tests/test_static_sweeps.py::test_remaining_silent_excepts_are_narrow PASSED
tests/test_static_sweeps.py::test_error_strings_are_escaped_in_innerhtml PASSED
tests/test_static_sweeps.py::test_zh_i18n_fullwidth_punctuation PASSED
tests/test_static_sweeps.py::test_zh_i18n_taiwan_terminology PASSED
tests/test_static_sweeps.py::test_zh_ui_says_guanxian_for_pipeline PASSED
tests/test_static_sweeps.py::test_no_inline_style_attributes_in_templates PASSED
tests/test_static_sweeps.py::test_search_button_is_disabled_without_a_time_range PASSED
tests/test_static_sweeps.py::test_search_range_is_watched_by_value_not_by_change_event PASSED
tests/test_static_sweeps.py::test_enter_runs_the_search_and_respects_the_disabled_rule PASSED
tests/test_static_sweeps.py::test_search_pane_re_renders_on_language_change PASSED
tests/test_static_sweeps.py::test_ui_strings_use_taiwan_terminology PASSED
tests/test_static_sweeps.py::test_no_css_variable_is_used_without_being_defined PASSED
tests/test_static_sweeps.py::test_theme_tokens_are_defined_for_both_themes PASSED
tests/test_static_sweeps.py::test_no_select_uses_the_browsers_own_dropdown PASSED
tests/test_static_sweeps.py::test_every_python_file_declares_its_licence PASSED
tests/test_static_sweeps.py::test_the_declared_licence_matches_pyproject_and_LICENSE PASSED
tests/test_static_sweeps.py::test_search_usage_is_shown_as_examples_not_prose PASSED
tests/test_static_sweeps.py::test_zh_docs_use_taiwanese_terminology PASSED
tests/test_static_sweeps.py::test_offline_bundle_can_do_a_first_install PASSED
tests/test_static_sweeps.py::test_report_engine_install_is_verified_not_assumed PASSED
tests/test_static_sweeps.py::test_installer_does_not_die_where_systemd_is_absent PASSED
tests/test_static_sweeps.py::test_release_scripts_capture_exit_codes_under_set_e PASSED
tests/test_static_sweeps.py::test_run_tests_fails_when_the_version_check_fails PASSED
tests/test_storage_ownership.py::test_fix_dir_ownership_as_root 2026-11-06T01:12:05.976746Z [warning  ] Fixing directory ownership     new_owner=jt-glogarch path=/tmp/tmp45x370uq/archives/log4
PASSED
tests/test_storage_ownership.py::test_fix_dir_ownership_not_root SKIPPED
tests/test_storage_ownership.py::test_fix_only_under_base_path PASSED
tests/test_streams_cleanup.py::test_matches_stream_by_index_set_not_just_title PASSED
tests/test_streams_cleanup.py::test_does_not_touch_unrelated_streams PASSED
tests/test_streams_cleanup.py::test_title_prefix_match_still_works PASSED
tests/test_streams_cleanup.py::test_command_source_matches_by_index_set_id PASSED
tests/test_streams_cleanup.py::test_streams_are_deleted_before_index_sets PASSED
tests/test_tls_trust.py::test_pyproject_requires_a_certifi_without_the_compromised_root PASSED
tests/test_tls_trust.py::test_the_bundle_httpx_uses_does_not_trust_the_compromised_root PASSED
tests/test_tls_verify.py::test_no_call_site_hardcodes_verify_false PASSED
tests/test_tls_verify.py::test_target_matching_a_configured_server_inherits_its_setting PASSED
tests/test_tls_verify.py::test_unknown_target_keeps_the_previous_behaviour PASSED
tests/test_tls_verify.py::test_default_ports_are_normalised PASSED
tests/test_tls_verify.py::test_broken_settings_object_never_raises PASSED
tests/test_upgrade.py::test_old_db_without_source_column PASSED
tests/test_upgrade.py::test_old_config_without_new_fields PASSED
tests/test_upgrade.py::test_existing_archives_survive PASSED
tests/test_upgrade.py::test_db_backup_before_upgrade PASSED
tests/test_upgrade_divergence.py::test_rewritten_upstream_is_recovered_not_abandoned PASSED
tests/test_upgrade_divergence.py::test_a_plain_behind_clone_is_left_for_the_normal_pull PASSED
tests/test_upgrade_divergence.py::test_upgrade_script_still_fails_loudly_when_it_cannot_recover PASSED
tests/test_upgrade_divergence.py::test_recovery_block_is_present_in_the_shipped_script[git rev-list --count "$_upstream..HEAD"] PASSED
tests/test_upgrade_divergence.py::test_recovery_block_is_present_in_the_shipped_script[git rev-list --count "HEAD..$_upstream"] PASSED
tests/test_upgrade_divergence.py::test_recovery_block_is_present_in_the_shipped_script[git reset --hard "$_upstream"] PASSED
tests/test_upgrade_script.py::test_upgrade_script_exists PASSED
tests/test_upgrade_script.py::test_upgrade_script_content PASSED
tests/test_upgrade_script.py::test_upgrade_script_checks_root PASSED
tests/test_upgrade_script.py::test_upgrade_script_shows_version_change PASSED
tests/test_upgrade_script.py::test_readme_mentions_upgrade_script PASSED
tests/test_upgrade_script.py::test_install_script_systemd_default_yes PASSED
tests/test_upgrade_script.py::test_upgrade_script_adds_retention_days PASSED
tests/test_upgrade_script.py::test_upgrade_script_op_audit_has_retention_days PASSED
tests/test_upgrade_script.py::test_readme_git_clone_has_sudo PASSED
tests/test_upgrade_script.py::test_memory_cap_is_soft_only PASSED
tests/test_upgrade_script.py::test_db_backup_probe_runs_inside_install_dir PASSED

================= 1134 passed, 1 skipped in 279.22s (0:04:39) ==================
```

## Version Check

```
Canonical version: 1.18.3
OK: version '1.18.3' has exactly one source of truth.
```
