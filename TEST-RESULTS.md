# Test Results

| Item | Value |
|---|---|
| **Status** | ✅ ALL PASSED |
| **Version** | v1.13.31 |
| **Date** | 2026-07-23 15:52:19 UTC |
| **Platform** | Python 3.10.12 / Linux 5.15.0-185-generic x86_64 |
| **Results** | 317 passed  / 1 skipped in 29.24s |
| **Version Check** | ✅ OK |

## Test Output

```
============================= test session starts ==============================
collecting ... collected 318 items

tests/test_api_error_handling.py::test_index_sets_catches_401 PASSED
tests/test_api_error_handling.py::test_streams_catches_401 PASSED
tests/test_api_error_handling.py::test_index_sets_catches_connection_error PASSED
tests/test_api_error_handling.py::test_streams_catches_connection_error PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_scoped_to_time_filter PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_scoped_to_server_and_stream PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_status_completed_excludes_others PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_requires_auth PASSED
tests/test_archive_streaming.py::test_streaming_returns_all_messages_incl_tricky_content 2026-07-23T15:52:26.420023Z [info     ] Archive written                messages=1000 path=/tmp/pytest-of-root/pytest-75/test_streaming_returns_all_mes0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.01
PASSED
tests/test_archive_streaming.py::test_empty_and_single 2026-07-23T15:52:26.489019Z [info     ] Archive written                messages=0 path=/tmp/pytest-of-root/pytest-75/test_empty_and_single0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
2026-07-23T15:52:26.492268Z [info     ] Archive written                messages=1 path=/tmp/pytest-of-root/pytest-75/test_empty_and_single0/b/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
PASSED
tests/test_archive_streaming.py::test_batching_shape 2026-07-23T15:52:26.500422Z [info     ] Archive written                messages=105 path=/tmp/pytest-of-root/pytest-75/test_batching_shape0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
PASSED
tests/test_archive_streaming.py::test_memory_is_bounded_not_whole_file 2026-07-23T15:52:27.506276Z [info     ] Archive written                messages=20000 path=/tmp/pytest-of-root/pytest-75/test_memory_is_bounded_not_who0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.12
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
tests/test_audit.py::test_cleanup_uses_audit_retention 2026-07-23T15:52:28.864260Z [info     ] No archives to clean up        retention_days=1095
2026-07-23T15:52:28.876355Z [info     ] Cleaned audit records          deleted=1 retention_days=180
2026-07-23T15:52:28.876689Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
2026-07-23T15:52:28.883954Z [info     ] No archives to clean up        retention_days=1095
2026-07-23T15:52:28.884584Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
PASSED
tests/test_audit.py::test_cleanup_audit_no_config 2026-07-23T15:52:29.103416Z [info     ] No archives to clean up        retention_days=1095
2026-07-23T15:52:29.112516Z [info     ] Cleaned audit records          deleted=1 retention_days=180
2026-07-23T15:52:29.112743Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
PASSED
tests/test_bulk_import.py::test_reserved_fields_stripped PASSED
tests/test_bulk_import.py::test_index_name_is_deflector PASSED
tests/test_bulk_import.py::test_index_name_no_timestamp PASSED
tests/test_bulk_import.py::test_stream_rewrite PASSED
tests/test_bulk_import.py::test_marker_field_injected PASSED
tests/test_bulk_import.py::test_dedup_id_uses_gl2_message_id PASSED
tests/test_bulk_import.py::test_dedup_none_no_id PASSED
tests/test_cleanup_race.py::test_grace_seconds_defined PASSED
tests/test_cleanup_race.py::test_recent_file_skipped PASSED
tests/test_cleanup_race.py::test_old_file_not_skipped PASSED
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
tests/test_database_datetime.py::test_naive_roundtrip PASSED
tests/test_database_datetime.py::test_utc_aware_roundtrip PASSED
tests/test_database_datetime.py::test_non_utc_aware_roundtrip PASSED
tests/test_database_datetime.py::test_none_passthrough PASSED
tests/test_database_datetime.py::test_str_to_dt_with_offset PASSED
tests/test_db_rebuild.py::test_rebuild_dry_run 2026-07-23T15:52:32.980134Z [info     ] Would insert                   path=/tmp/tmpq959c4ve/archives/server1/2026/01/test.json.gz server=test time_from=2026-01-01T00:00:00Z
PASSED
tests/test_db_rebuild.py::test_rebuild_actual PASSED
tests/test_db_rebuild.py::test_rebuild_skip_existing PASSED
tests/test_db_rebuild.py::test_backup_db PASSED
tests/test_db_rebuild.py::test_prune_backups PASSED
tests/test_export_pagination.py::test_deep_pagination_no_same_ms_loss_or_dup 2026-07-23T15:52:34.046165Z [info     ] Total messages to fetch        total=6
2026-07-23T15:52:34.047080Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=4 new_from='2024-01-01 00:00:00.003000' old_from='2024-01-01 00:00:00'
PASSED
tests/test_export_pagination.py::test_deep_pagination_multiple_windows 2026-07-23T15:52:34.051140Z [info     ] Total messages to fetch        total=30
2026-07-23T15:52:34.052766Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=6 new_from='2024-01-01 00:00:00.005000' old_from='2024-01-01 00:00:00'
2026-07-23T15:52:34.054368Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=11 new_from='2024-01-01 00:00:00.010000' old_from='2024-01-01 00:00:00.005000'
2026-07-23T15:52:34.055393Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=16 new_from='2024-01-01 00:00:00.015000' old_from='2024-01-01 00:00:00.010000'
2026-07-23T15:52:34.056367Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=21 new_from='2024-01-01 00:00:00.020000' old_from='2024-01-01 00:00:00.015000'
2026-07-23T15:52:34.057795Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=26 new_from='2024-01-01 00:00:00.025000' old_from='2024-01-01 00:00:00.020000'
PASSED
tests/test_export_pagination.py::test_pagination_raises_on_unsplittable_ms 2026-07-23T15:52:34.062001Z [info     ] Total messages to fetch        total=10
PASSED
tests/test_export_pagination.py::test_fmt_ts_millisecond_precision PASSED
tests/test_export_pagination.py::test_parse_timestamp_robust_fallback PASSED
tests/test_export_pagination.py::test_transient_5xx_fails_over_to_next_host 2026-07-23T15:52:34.076875Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=1 status=503 wait=1
2026-07-23T15:52:34.079739Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=2 status=503 wait=2
2026-07-23T15:52:34.081789Z [warning  ] Transient errors exhausted, failing over to next host host=http://host0:9200 status=503
2026-07-23T15:52:34.083821Z [info     ] Failover to host               host=http://host1:9200
PASSED
tests/test_export_pagination.py::test_all_hosts_transient_raises 2026-07-23T15:52:34.093984Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=1 status=503 wait=1
2026-07-23T15:52:34.095659Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=2 status=503 wait=2
2026-07-23T15:52:34.095957Z [warning  ] Transient errors exhausted, failing over to next host host=http://host0:9200 status=503
2026-07-23T15:52:34.096220Z [warning  ] Transient error, retrying      host=http://host1:9200 retry=1 status=503 wait=1
2026-07-23T15:52:34.096374Z [warning  ] Transient error, retrying      host=http://host1:9200 retry=2 status=503 wait=2
2026-07-23T15:52:34.096500Z [warning  ] Transient errors exhausted, failing over to next host host=http://host1:9200 status=503
PASSED
tests/test_export_pagination.py::test_non_transient_4xx_raises_immediately PASSED
tests/test_export_pagination.py::test_iter_index_docs_no_stale_total_early_stop PASSED
tests/test_export_pagination.py::test_rate_limiter_does_not_hold_lock_across_sleep PASSED
tests/test_export_pagination.py::test_rate_limiter_acquire_allows_burst PASSED
tests/test_field_schema.py::test_plain_json_passthrough PASSED
tests/test_field_schema.py::test_zlib_roundtrip PASSED
tests/test_field_schema.py::test_decompress_none PASSED
tests/test_field_schema.py::test_decompress_corrupted PASSED
tests/test_field_schema.py::test_decompress_plain_json PASSED
tests/test_field_schema.py::test_db_field_schema_store_and_read PASSED
tests/test_graylog_error_detail.py::test_error_detail_extracts_graylog_message PASSED
tests/test_graylog_error_detail.py::test_error_detail_falls_back_to_text_body PASSED
tests/test_graylog_error_detail.py::test_error_detail_handles_empty_body PASSED
tests/test_graylog_flush.py::test_flush_cycles_and_rebuilds_never_deletes 2026-07-23T15:52:34.602316Z [info     ] graylog flush done             actions=['cycle_deflector:ok', 'rebuild_index_ranges:ok'] ok=True
PASSED
tests/test_graylog_flush.py::test_flush_global_deflector_fallback_when_no_index_set 2026-07-23T15:52:34.611835Z [info     ] graylog flush done             actions=['cycle_deflector:ok', 'rebuild_index_ranges:ok'] ok=True
PASSED
tests/test_graylog_flush.py::test_flush_reports_action_error_without_raising 2026-07-23T15:52:34.620071Z [info     ] graylog flush done             actions=['cycle_deflector:error', 'rebuild_index_ranges:ok'] ok=False
PASSED
tests/test_graylog_flush.py::test_snapshot_unreachable_returns_empty_not_raise 2026-07-23T15:52:34.626593Z [warning  ] flush snapshot failed          error=unreachable
PASSED
tests/test_health_endpoint.py::test_health_response_structure PASSED
tests/test_health_endpoint.py::test_health_not_behind_auth PASSED
tests/test_health_guard.py::test_rising_tracker_detects_sustained_climb PASSED
tests/test_health_guard.py::test_rising_tracker_ignores_flat_and_falling PASSED
tests/test_health_guard.py::test_rising_tracker_respects_min_delta PASSED
tests/test_health_guard.py::test_tripped_failsafe_on_unreachable PASSED
tests/test_health_guard.py::test_heap_hard_tier_trips_immediately PASSED
tests/test_health_guard.py::test_heap_soft_tier_needs_sustained PASSED
tests/test_health_guard.py::test_heap_soft_streak_resets_on_dip PASSED
tests/test_health_guard.py::test_tripped_on_rising_journal PASSED
tests/test_health_guard.py::test_pause_then_resume 2026-07-23T15:52:34.654219Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 95%（超過硬上限 90%）']
2026-07-23T15:52:34.654465Z [info     ] export resumed — backpressure cleared waited_sec=1
PASSED
tests/test_health_guard.py::test_pause_times_out_and_raises 2026-07-23T15:52:34.657491Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 99%（超過硬上限 90%）']
2026-07-23T15:52:34.657712Z [error    ] export stopped — backpressure did not clear signals=['JVM heap 99%（超過硬上限 90%）'] waited_sec=60
PASSED
tests/test_import_batch_flow.py::test_web_ui_flow_control_batch_and_rate_are_preserved 2026-07-23T15:52:34.973478Z [info     ] No archives to import         
PASSED
tests/test_import_batch_flow.py::test_no_flow_control_captures_config_defaults 2026-07-23T15:52:35.171880Z [info     ] No archives to import         
PASSED
tests/test_import_batch_flow.py::test_seeding_is_guarded_in_source PASSED
tests/test_import_jvm_throttle.py::test_ring_buffer_is_the_early_signal PASSED
tests/test_import_jvm_throttle.py::test_buffer_pause_beats_low_journal PASSED
tests/test_import_jvm_throttle.py::test_heap_alone_triggers_slow_then_pause PASSED
tests/test_import_jvm_throttle.py::test_journal_alone_still_works PASSED
tests/test_import_jvm_throttle.py::test_most_severe_signal_wins PASSED
tests/test_import_jvm_throttle.py::test_unknown_heap_is_ignored PASSED
tests/test_import_jvm_throttle.py::test_monitoring_disabled_is_normal PASSED
tests/test_import_jvm_throttle.py::test_failed_check_before_ever_working_does_not_deadlock 2026-07-23T15:52:35.204876Z [warning  ] Journal endpoint unreachable; import proceeds at user rate without journal throttling error=404
PASSED
tests/test_import_jvm_throttle.py::test_failed_check_after_working_is_failsafe_pause 2026-07-23T15:52:35.206983Z [warning  ] Journal check failed mid-import (target unreachable/stuck) — pausing until it recovers error=timeout
PASSED
tests/test_import_jvm_throttle.py::test_elevated_backlog_not_draining_escalates_to_pause PASSED
tests/test_import_jvm_throttle.py::test_elevated_backlog_that_is_draining_stays_slow PASSED
tests/test_import_lock.py::test_claim_success PASSED
tests/test_import_lock.py::test_claim_conflict PASSED
tests/test_import_lock.py::test_release PASSED
tests/test_import_lock.py::test_release_wrong_owner PASSED
tests/test_import_lock.py::test_same_job_reclaim PASSED
tests/test_index_set_coverage.py::test_empty_or_none_means_all PASSED
tests/test_index_set_coverage.py::test_star_means_all_even_over_config PASSED
tests/test_index_set_coverage.py::test_single_string_backward_compatible PASSED
tests/test_index_set_coverage.py::test_list_value PASSED
tests/test_index_set_coverage.py::test_empty_falls_back_to_global_config PASSED
tests/test_index_set_coverage.py::test_explicit_value_overrides_global_config PASSED
tests/test_index_set_coverage.py::test_none_covers_all_index_sets PASSED
tests/test_index_set_coverage.py::test_restricting_reports_skipped_index_sets 2026-07-23T15:52:35.255904Z [warning  ] Index sets NOT covered by this OpenSearch export — their logs will NOT be archived and will be lost when Graylog retention deletes them covered=['graylog'] skipped=['PVE Hosts', 'Wazuh']
PASSED
tests/test_index_set_coverage.py::test_explicit_prefix_skips_api_lookup PASSED
tests/test_index_set_coverage.py::test_index_sets_without_prefix_are_ignored PASSED
tests/test_index_set_coverage.py::test_job_result_json_round_trips PASSED
tests/test_indexer_failure_autofix.py::test_parse_failure_message_extracts_field_and_reason PASSED
tests/test_indexer_failure_autofix.py::test_parse_failure_rejects_log_prefix_tokens PASSED
tests/test_indexer_failure_autofix.py::test_get_indexer_failure_details_aggregates_fields PASSED
tests/test_indexer_failure_autofix.py::test_remediate_pins_fields_and_cycles_never_deletes 2026-07-23T15:52:35.512665Z [info     ] Custom mappings applied        failed=0 ok=2 total=2
2026-07-23T15:52:35.513393Z [info     ] Auto-remediated indexer-failure fields as string fields=['Keywords', 'foo'] index_set=idx1
PASSED
tests/test_indexer_failure_autofix.py::test_iterator_metadata_fallback_degrades_not_crashes PASSED
tests/test_indexer_failure_autofix.py::test_long_overflow_numeric_tracked_as_string PASSED
tests/test_integration.py::test_cross_conflict_actual_os_mapping PASSED
tests/test_integration.py::test_field_schema_zlib_in_preflight PASSED
tests/test_integration.py::test_timezone_dedup_correctness PASSED
tests/test_integration.py::test_timezone_retention_correctness PASSED
tests/test_integration.py::test_archive_write_read_integrity 2026-07-23T15:52:36.791137Z [info     ] Archive written                messages=50 path=/tmp/tmpyqixlbzt/test/stream1/2026/01/01/test_stream1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
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
tests/test_integrity.py::test_verifier_flags_tampered 2026-07-23T15:52:38.035552Z [info     ] Verification started           total_archives=1
2026-07-23T15:52:38.037076Z [error    ] TAMPERED archive (HMAC mismatch) archive_id=1 path=/tmp/pytest-of-root/pytest-75/test_verifier_flags_tampered0/a.json.gz
2026-07-23T15:52:38.044308Z [info     ] Verification completed         corrupted=0 missing=0 orphans=0 tampered=1 total=1 valid=0
PASSED
tests/test_integrity.py::test_notify_tampered_line_is_distinct PASSED
tests/test_local_admin.py::test_default_hash_is_empty PASSED
tests/test_local_admin.py::test_hash_generation PASSED
tests/test_local_admin.py::test_backward_compatible_config PASSED
tests/test_local_admin.py::test_localadmin_logs_in_even_when_graylog_configured PASSED
tests/test_local_admin.py::test_localadmin_wrong_password_rejected_without_graylog PASSED
tests/test_local_admin.py::test_no_hash_means_no_local_login PASSED
tests/test_memguard.py::test_mem_action_tiers PASSED
tests/test_memguard.py::test_fail_open_when_unreadable PASSED
tests/test_memguard.py::test_reads_real_meminfo_on_linux PASSED
tests/test_multi_server.py::test_config_supports_multiple_servers PASSED
tests/test_multi_server.py::test_get_server_by_name PASSED
tests/test_multi_server.py::test_get_opensearch_per_server_block PASSED
tests/test_multi_server.py::test_get_opensearch_empty_block_falls_back PASSED
tests/test_multi_server.py::test_get_opensearch_backward_compatible PASSED
tests/test_multi_server.py::test_scheduler_reads_server_from_config PASSED
tests/test_multi_server.py::test_schedule_ui_has_server_selector PASSED
tests/test_multi_server.py::test_schedule_js_saves_server PASSED
tests/test_multi_server.py::test_schedule_js_loads_server_on_edit PASSED
tests/test_notify_format.py::test_export_ok_has_emoji PASSED
tests/test_notify_format.py::test_export_err_has_warning_emoji PASSED
tests/test_notify_format.py::test_verify_fail_has_x_emoji PASSED
tests/test_notify_format.py::test_error_title_has_x_emoji PASSED
tests/test_notify_format.py::test_export_body_per_line PASSED
tests/test_notify_format.py::test_url_shortening_in_errors PASSED
tests/test_notify_format.py::test_all_langs_have_same_keys PASSED
tests/test_notify_test_endpoint.py::test_send_discord_params PASSED
tests/test_notify_test_endpoint.py::test_send_slack_params PASSED
tests/test_notify_test_endpoint.py::test_send_teams_params PASSED
tests/test_notify_test_endpoint.py::test_send_telegram_params PASSED
tests/test_notify_test_endpoint.py::test_send_nextcloud_talk_params PASSED
tests/test_notify_test_endpoint.py::test_send_email_params PASSED
tests/test_notify_test_endpoint.py::test_test_endpoint_calls_match_signatures PASSED
tests/test_opensearch_client.py::test_search_sort_uses_doc_not_id PASSED
tests/test_opensearch_multicluster.py::test_status_reports_per_server_vs_global PASSED
tests/test_opensearch_multicluster.py::test_reorder_is_server_aware PASSED
tests/test_opensearch_multicluster.py::test_reorder_without_server_touches_global PASSED
tests/test_os_export_multiprefix.py::test_denominator_is_grand_total_across_prefixes 2026-07-23T15:52:40.925831Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-07-23T15:52:40.926102Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-07-23T15:52:40.926260Z [info     ] Found indices                  count=3 prefix=graylog
2026-07-23T15:52:40.926363Z [info     ] Skipping active write index    index=graylog_write
2026-07-23T15:52:40.926907Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-07-23T15:52:40.927603Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-07-23T15:52:40.927853Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-07-23T15:52:40.927956Z [info     ] Found indices                  count=2 prefix=noise_38
2026-07-23T15:52:40.928033Z [info     ] Skipping active write index    index=noise_38_write
2026-07-23T15:52:40.928375Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-07-23T15:52:40.936602Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-07-23T15:52:40.937021Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-07-23T15:52:40.949844Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-75/test_denominator_is_grand_tota0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-23T15:52:40.959860Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-07-23T15:52:40.960437Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-07-23T15:52:40.973811Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-75/test_denominator_is_grand_tota0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-23T15:52:40.982879Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-07-23T15:52:40.983286Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-07-23T15:52:40.991397Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-75/test_denominator_is_grand_tota0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-07-23T15:52:41.006984Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-07-23T15:52:41.015426Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_multiprefix.py::test_progress_never_exceeds_total 2026-07-23T15:52:41.368788Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-07-23T15:52:41.369262Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-07-23T15:52:41.369563Z [info     ] Found indices                  count=3 prefix=graylog
2026-07-23T15:52:41.369710Z [info     ] Skipping active write index    index=graylog_write
2026-07-23T15:52:41.370398Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-07-23T15:52:41.370900Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-07-23T15:52:41.371122Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-07-23T15:52:41.371297Z [info     ] Found indices                  count=2 prefix=noise_38
2026-07-23T15:52:41.371404Z [info     ] Skipping active write index    index=noise_38_write
2026-07-23T15:52:41.371789Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-07-23T15:52:41.390347Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-07-23T15:52:41.390857Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-07-23T15:52:41.407259Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-75/test_progress_never_exceeds_to0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-23T15:52:41.424245Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-07-23T15:52:41.424681Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-07-23T15:52:41.437835Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-75/test_progress_never_exceeds_to0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-23T15:52:41.454138Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-07-23T15:52:41.454603Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-07-23T15:52:41.473678Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-75/test_progress_never_exceeds_to0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-07-23T15:52:41.485572Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-07-23T15:52:41.505559Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_multiprefix.py::test_denominator_is_stable_no_regression 2026-07-23T15:52:41.741455Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-07-23T15:52:41.741780Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-07-23T15:52:41.741987Z [info     ] Found indices                  count=3 prefix=graylog
2026-07-23T15:52:41.742168Z [info     ] Skipping active write index    index=graylog_write
2026-07-23T15:52:41.742838Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-07-23T15:52:41.743644Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-07-23T15:52:41.744064Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-07-23T15:52:41.744266Z [info     ] Found indices                  count=2 prefix=noise_38
2026-07-23T15:52:41.744368Z [info     ] Skipping active write index    index=noise_38_write
2026-07-23T15:52:41.744769Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-07-23T15:52:41.752057Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-07-23T15:52:41.752479Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-07-23T15:52:41.762680Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-75/test_denominator_is_stable_no_0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-23T15:52:41.771363Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-07-23T15:52:41.771809Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-07-23T15:52:41.784599Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-75/test_denominator_is_stable_no_0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-23T15:52:41.791477Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-07-23T15:52:41.791898Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-07-23T15:52:41.801894Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-75/test_denominator_is_stable_no_0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-07-23T15:52:41.808935Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-07-23T15:52:41.815715Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_progress.py::test_denominator_is_accumulated_not_reset_per_prefix PASSED
tests/test_os_export_progress.py::test_update_job_uses_grand_total_not_prefix_total PASSED
tests/test_os_export_progress.py::test_denominator_is_stable_two_phase PASSED
tests/test_os_export_progress.py::test_grand_total_initialised_before_prefix_loop PASSED
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
tests/test_startup_recovery.py::test_recover_stuck_importing PASSED
tests/test_startup_recovery.py::test_recover_stuck_importing_noop_when_clean PASSED
tests/test_storage_ownership.py::test_fix_dir_ownership_as_root 2026-07-23T15:52:51.905896Z [warning  ] Fixing directory ownership     new_owner=jt-glogarch path=/tmp/tmpsee7p1k1/archives/log4
PASSED
tests/test_storage_ownership.py::test_fix_dir_ownership_not_root SKIPPED
tests/test_storage_ownership.py::test_fix_only_under_base_path PASSED
tests/test_upgrade.py::test_old_db_without_source_column PASSED
tests/test_upgrade.py::test_old_config_without_new_fields PASSED
tests/test_upgrade.py::test_existing_archives_survive PASSED
tests/test_upgrade.py::test_db_backup_before_upgrade PASSED
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

======================= 317 passed, 1 skipped in 29.24s ========================
```

## Version Check

```
Canonical version: 1.13.31
OK: version '1.13.31' has exactly one source of truth.
```
