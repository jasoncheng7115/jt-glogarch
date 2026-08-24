# Test Results

| Item | Value |
|---|---|
| **Status** | ✅ ALL PASSED |
| **Version** | v1.13.88 |
| **Date** | 2026-08-24 14:01:45 UTC |
| **Platform** | Python 3.10.12 / Linux 5.15.0-185-generic x86_64 |
| **Results** | 507 passed  / 1 skipped in 103.98s |
| **Version Check** | ✅ OK |

## Test Output

```
============================= test session starts ==============================
collecting ... collected 508 items

tests/test_api_error_handling.py::test_index_sets_catches_401 PASSED
tests/test_api_error_handling.py::test_streams_catches_401 PASSED
tests/test_api_error_handling.py::test_index_sets_catches_connection_error PASSED
tests/test_api_error_handling.py::test_streams_catches_connection_error PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_scoped_to_time_filter PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_scoped_to_server_and_stream PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_status_completed_excludes_others PASSED
tests/test_archive_ids_endpoint.py::test_ids_endpoint_requires_auth PASSED
tests/test_archive_ids_endpoint.py::test_capacity_estimate_sums_volume_and_reports_fit PASSED
tests/test_archive_ids_endpoint.py::test_capacity_estimate_requires_archive_ids PASSED
tests/test_archive_streaming.py::test_streaming_returns_all_messages_incl_tricky_content 2026-08-24T14:01:54.876551Z [info     ] Archive written                messages=1000 path=/tmp/pytest-of-root/pytest-442/test_streaming_returns_all_mes0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.01
PASSED
tests/test_archive_streaming.py::test_empty_and_single 2026-08-24T14:01:54.945693Z [info     ] Archive written                messages=0 path=/tmp/pytest-of-root/pytest-442/test_empty_and_single0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
2026-08-24T14:01:54.948051Z [info     ] Archive written                messages=1 path=/tmp/pytest-of-root/pytest-442/test_empty_and_single0/b/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
PASSED
tests/test_archive_streaming.py::test_batching_shape 2026-08-24T14:01:54.955310Z [info     ] Archive written                messages=105 path=/tmp/pytest-of-root/pytest-442/test_batching_shape0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
PASSED
tests/test_archive_streaming.py::test_memory_is_bounded_not_whole_file 2026-08-24T14:01:55.897814Z [info     ] Archive written                messages=20000 path=/tmp/pytest-of-root/pytest-442/test_memory_is_bounded_not_who0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.12
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
tests/test_audit.py::test_cleanup_uses_audit_retention 2026-08-24T14:01:57.705752Z [info     ] No archives to clean up        retention_days=1095
2026-08-24T14:01:57.717926Z [info     ] Cleaned audit records          deleted=1 retention_days=180
2026-08-24T14:01:57.718208Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
2026-08-24T14:01:57.724745Z [info     ] No archives to clean up        retention_days=1095
2026-08-24T14:01:57.725403Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
PASSED
tests/test_audit.py::test_cleanup_audit_no_config 2026-08-24T14:01:58.040501Z [info     ] No archives to clean up        retention_days=1095
2026-08-24T14:01:58.047211Z [info     ] Cleaned audit records          deleted=1 retention_days=180
2026-08-24T14:01:58.047563Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
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
tests/test_bulk_streaming.py::test_import_path_never_calls_whole_file_loader 2026-08-24T14:01:58.115935Z [info     ] Bulk import starting           archives=1 batch_docs=50 indices_to_create=1 target_pattern=graylog total_messages=120
2026-08-24T14:01:58.120037Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-08-24T14:01:58.120263Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.0s failed=0 indexed=120 sent=120
PASSED
tests/test_bulk_streaming.py::test_corrupt_archive_does_not_abort_whole_run 2026-08-24T14:01:58.128835Z [info     ] Bulk import starting           archives=2 batch_docs=5 indices_to_create=1 target_pattern=graylog total_messages=11
2026-08-24T14:01:58.130398Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-08-24T14:01:58.130594Z [info     ] Bulk import completed          archives=2 at_destination=-1 duration=0.0s failed=0 indexed=11 sent=11
PASSED
tests/test_bulk_streaming.py::test_bulk_body_capped_by_bytes_not_just_doc_count PASSED
tests/test_bulk_streaming.py::test_single_oversized_doc_still_sent PASSED
tests/test_bulk_streaming.py::test_byte_cap_loses_no_documents 2026-08-24T14:01:58.819032Z [info     ] Bulk import starting           archives=1 batch_docs=10000 indices_to_create=1 target_pattern=graylog total_messages=400
2026-08-24T14:01:59.015060Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-08-24T14:01:59.015282Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.2s failed=0 indexed=400 sent=400
PASSED
tests/test_cleanup_race.py::test_grace_seconds_defined PASSED
tests/test_cleanup_race.py::test_recent_file_skipped PASSED
tests/test_cleanup_race.py::test_old_file_not_skipped PASSED
tests/test_cleanup_schedule_retention.py::test_schedule_retention_days_is_used 2026-08-24T14:01:59.036131Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=200 retention_source=schedule
PASSED
tests/test_cleanup_schedule_retention.py::test_falls_back_to_config_when_schedule_has_none 2026-08-24T14:01:59.047499Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=1095 retention_source=config.yaml
PASSED
tests/test_cleanup_schedule_retention.py::test_bad_config_json_does_not_break_cleanup 2026-08-24T14:01:59.056713Z [warning  ] Could not read the schedule's retention setting; falling back to config.yaml error='Expecting property name enclosed in double quotes: line 1 column 2 (char 1)' schedule=auto-cleanup
2026-08-24T14:01:59.056963Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=1095 retention_source=config.yaml
PASSED
tests/test_cleanup_schedule_retention.py::test_upgrade_does_not_shorten_retention_and_delete_data 2026-08-24T14:01:59.062087Z [warning  ] Cleanup schedule retention reconciled on upgrade — the value shown in the UI was never actually applied, and honouring it now would have deleted archives this version was keeping. Set it again in the Schedules page if the shorter retention is what you want. now_in_force=1095 schedule=auto-cleanup was_shown=200
PASSED
tests/test_cleanup_schedule_retention.py::test_longer_stored_retention_is_kept_it_only_retains_more PASSED
tests/test_cleanup_schedule_retention.py::test_equal_values_are_untouched PASSED
tests/test_cleanup_schedule_retention.py::test_schedule_without_retention_is_untouched PASSED
tests/test_clear_index_set_route.py::test_list_index_sets_route_returns_200 PASSED
tests/test_clear_index_set_route.py::test_list_falls_back_to_stored_import_defaults PASSED
tests/test_clear_index_set_route.py::test_masked_password_is_reconciled_not_sent_literally PASSED
tests/test_clear_index_set_route.py::test_clear_requires_matching_confirmation PASSED
tests/test_clear_index_set_route.py::test_clear_refuses_internal_index_set_by_id PASSED
tests/test_clear_index_set_route.py::test_clear_happy_path_keeps_the_write_index 2026-08-24T14:02:05.940814Z [warning  ] Cleared index set before import deleted=1 failed=0 index_set=graylog kept_write_index=graylog_2
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
tests/test_database_datetime.py::test_naive_roundtrip PASSED
tests/test_database_datetime.py::test_utc_aware_roundtrip PASSED
tests/test_database_datetime.py::test_non_utc_aware_roundtrip PASSED
tests/test_database_datetime.py::test_none_passthrough PASSED
tests/test_database_datetime.py::test_str_to_dt_with_offset PASSED
tests/test_db_rebuild.py::test_rebuild_dry_run 2026-08-24T14:02:13.189386Z [info     ] Would insert                   path=/tmp/tmp_lq7nmmo/archives/server1/2026/01/test.json.gz server=test time_from=2026-01-01T00:00:00Z
PASSED
tests/test_db_rebuild.py::test_rebuild_actual PASSED
tests/test_db_rebuild.py::test_rebuild_skip_existing PASSED
tests/test_db_rebuild.py::test_backup_db PASSED
tests/test_db_rebuild.py::test_prune_backups PASSED
tests/test_export_cancel_registry.py::test_registry_round_trip PASSED
tests/test_export_cancel_registry.py::test_unknown_job_is_none_not_an_error PASSED
tests/test_export_cancel_registry.py::test_empty_job_id_is_never_registered PASSED
tests/test_export_cancel_registry.py::test_both_exporters_register_and_release[glogarch.export.exporter-_export_lock] PASSED
tests/test_export_cancel_registry.py::test_both_exporters_register_and_release[glogarch.opensearch.exporter-_os_export_lock] PASSED
tests/test_export_cancel_registry.py::test_cancel_endpoint_signals_the_exporter PASSED
tests/test_export_cancel_registry.py::test_skip_streak_escalates_and_resets PASSED
tests/test_export_cancel_registry.py::test_skip_branch_escalates_and_notifies PASSED
tests/test_export_cancel_registry.py::test_stuck_notification_never_breaks_the_scheduler PASSED
tests/test_export_pagination.py::test_deep_pagination_no_same_ms_loss_or_dup 2026-08-24T14:02:15.833415Z [info     ] Total messages to fetch        total=6
2026-08-24T14:02:15.834434Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=4 new_from='2024-01-01 00:00:00.003000' old_from='2024-01-01 00:00:00'
PASSED
tests/test_export_pagination.py::test_deep_pagination_multiple_windows 2026-08-24T14:02:15.840348Z [info     ] Total messages to fetch        total=30
2026-08-24T14:02:15.841555Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=6 new_from='2024-01-01 00:00:00.005000' old_from='2024-01-01 00:00:00'
2026-08-24T14:02:15.843001Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=11 new_from='2024-01-01 00:00:00.010000' old_from='2024-01-01 00:00:00.005000'
2026-08-24T14:02:15.844001Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=16 new_from='2024-01-01 00:00:00.015000' old_from='2024-01-01 00:00:00.010000'
2026-08-24T14:02:15.845852Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=21 new_from='2024-01-01 00:00:00.020000' old_from='2024-01-01 00:00:00.015000'
2026-08-24T14:02:15.847600Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=26 new_from='2024-01-01 00:00:00.025000' old_from='2024-01-01 00:00:00.020000'
PASSED
tests/test_export_pagination.py::test_pagination_raises_on_unsplittable_ms 2026-08-24T14:02:15.853645Z [info     ] Total messages to fetch        total=10
2026-08-24T14:02:15.854135Z [warning  ] Single-millisecond overflow during API export: more than 4 messages share 2024-01-01T00:00:00.000Z; Graylog's REST API cannot page past it. Kept the first 4, skipping the rest of this millisecond and continuing. Re-run this window in OpenSearch Direct mode to capture them all.
PASSED
tests/test_export_pagination.py::test_overflow_ms_does_not_lose_messages_after_it 2026-08-24T14:02:15.857863Z [info     ] Total messages to fetch        total=12
2026-08-24T14:02:15.859053Z [warning  ] Single-millisecond overflow during API export: more than 4 messages share 2024-01-01T00:00:00.000Z; Graylog's REST API cannot page past it. Kept the first 4, skipping the rest of this millisecond and continuing. Re-run this window in OpenSearch Direct mode to capture them all.
PASSED
tests/test_export_pagination.py::test_fmt_ts_millisecond_precision PASSED
tests/test_export_pagination.py::test_parse_timestamp_robust_fallback PASSED
tests/test_export_pagination.py::test_transient_5xx_fails_over_to_next_host 2026-08-24T14:02:15.885497Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=1 status=503 wait=1
2026-08-24T14:02:15.889814Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=2 status=503 wait=2
2026-08-24T14:02:15.891840Z [warning  ] Transient errors exhausted, failing over to next host host=http://host0:9200 status=503
2026-08-24T14:02:15.894760Z [info     ] Failover to host               host=http://host1:9200
PASSED
tests/test_export_pagination.py::test_all_hosts_transient_raises 2026-08-24T14:02:15.908144Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=1 status=503 wait=1
2026-08-24T14:02:15.910043Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=2 status=503 wait=2
2026-08-24T14:02:15.910316Z [warning  ] Transient errors exhausted, failing over to next host host=http://host0:9200 status=503
2026-08-24T14:02:15.910460Z [warning  ] Transient error, retrying      host=http://host1:9200 retry=1 status=503 wait=1
2026-08-24T14:02:15.910665Z [warning  ] Transient error, retrying      host=http://host1:9200 retry=2 status=503 wait=2
2026-08-24T14:02:15.910841Z [warning  ] Transient errors exhausted, failing over to next host host=http://host1:9200 status=503
PASSED
tests/test_export_pagination.py::test_non_transient_4xx_raises_immediately PASSED
tests/test_export_pagination.py::test_iter_index_docs_no_stale_total_early_stop PASSED
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
tests/test_graylog_flush.py::test_flush_cycles_and_rebuilds_never_deletes 2026-08-24T14:02:19.975298Z [info     ] graylog flush done             actions=['cycle_deflector:ok', 'rebuild_index_ranges:ok'] ok=True
PASSED
tests/test_graylog_flush.py::test_flush_global_deflector_fallback_when_no_index_set 2026-08-24T14:02:19.985705Z [info     ] graylog flush done             actions=['cycle_deflector:ok', 'rebuild_index_ranges:ok'] ok=True
PASSED
tests/test_graylog_flush.py::test_flush_reports_action_error_without_raising 2026-08-24T14:02:19.994192Z [info     ] graylog flush done             actions=['cycle_deflector:error', 'rebuild_index_ranges:ok'] ok=False
PASSED
tests/test_graylog_flush.py::test_snapshot_unreachable_returns_empty_not_raise 2026-08-24T14:02:20.000406Z [warning  ] flush snapshot failed          error=unreachable
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
tests/test_health_guard.py::test_pause_then_resume 2026-08-24T14:02:20.033837Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 95% (over the hard limit 90%)']
2026-08-24T14:02:20.034059Z [info     ] export resumed — backpressure cleared waited_sec=1
PASSED
tests/test_health_guard.py::test_pause_times_out_and_raises 2026-08-24T14:02:20.037510Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 99% (over the hard limit 90%)']
2026-08-24T14:02:20.037770Z [error    ] export stopped — backpressure did not clear signals=['JVM heap 99% (over the hard limit 90%)'] waited_sec=60
PASSED
tests/test_health_schedule_registration.py::test_health_compares_enabled_schedules_against_registered_jobs PASSED
tests/test_health_schedule_registration.py::test_unregistered_schedule_makes_health_unhealthy PASSED
tests/test_health_schedule_registration.py::test_upgrade_script_fails_when_schedules_are_not_registered PASSED
tests/test_import_batch_flow.py::test_web_ui_flow_control_batch_and_rate_are_preserved 2026-08-24T14:02:20.539397Z [info     ] No archives to import         
PASSED
tests/test_import_batch_flow.py::test_no_flow_control_captures_config_defaults 2026-08-24T14:02:20.876171Z [info     ] No archives to import         
PASSED
tests/test_import_batch_flow.py::test_seeding_is_guarded_in_source PASSED
tests/test_import_jvm_throttle.py::test_ring_buffer_is_the_early_signal PASSED
tests/test_import_jvm_throttle.py::test_buffer_pause_beats_low_journal PASSED
tests/test_import_jvm_throttle.py::test_heap_alone_triggers_slow_then_pause PASSED
tests/test_import_jvm_throttle.py::test_journal_alone_still_works PASSED
tests/test_import_jvm_throttle.py::test_most_severe_signal_wins PASSED
tests/test_import_jvm_throttle.py::test_unknown_heap_is_ignored PASSED
tests/test_import_jvm_throttle.py::test_monitoring_disabled_is_normal PASSED
tests/test_import_jvm_throttle.py::test_failed_check_before_ever_working_does_not_deadlock 2026-08-24T14:02:20.935968Z [warning  ] Journal endpoint unreachable; import proceeds at user rate without journal throttling error=404
PASSED
tests/test_import_jvm_throttle.py::test_failed_check_after_working_is_failsafe_pause 2026-08-24T14:02:20.937458Z [warning  ] Journal check failed mid-import (target unreachable/stuck) — pausing until it recovers error=timeout
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
tests/test_index_cleaner.py::test_rotates_before_deleting_and_keeps_the_new_write_index 2026-08-24T14:02:24.000446Z [warning  ] Cleared index set before import deleted=2 failed=0 index_set=graylog kept_write_index=graylog_9
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
tests/test_index_set_coverage.py::test_restricting_reports_skipped_index_sets 2026-08-24T14:02:27.054753Z [warning  ] Index sets NOT covered by this OpenSearch export — their logs will NOT be archived and will be lost when Graylog retention deletes them covered=['graylog'] skipped=['PVE Hosts', 'Wazuh']
PASSED
tests/test_index_set_coverage.py::test_explicit_prefix_skips_api_lookup PASSED
tests/test_index_set_coverage.py::test_index_sets_without_prefix_are_ignored PASSED
tests/test_index_set_coverage.py::test_job_result_json_round_trips PASSED
tests/test_indexer_failure_autofix.py::test_parse_failure_message_extracts_field_and_reason PASSED
tests/test_indexer_failure_autofix.py::test_parse_failure_rejects_log_prefix_tokens PASSED
tests/test_indexer_failure_autofix.py::test_get_indexer_failure_details_aggregates_fields PASSED
tests/test_indexer_failure_autofix.py::test_remediate_pins_fields_and_cycles_never_deletes 2026-08-24T14:02:27.906113Z [info     ] Custom mappings applied        failed=0 ok=2 total=2
2026-08-24T14:02:27.907010Z [info     ] Auto-remediated indexer-failure fields as string fields=['Keywords', 'foo'] index_set=idx1
PASSED
tests/test_indexer_failure_autofix.py::test_iterator_metadata_fallback_degrades_not_crashes PASSED
tests/test_indexer_failure_autofix.py::test_long_overflow_numeric_tracked_as_string PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_pins_new_fields_on_rise 2026-08-24T14:02:27.927865Z [warning  ] Mid-import auto-remediation applied failures_delta=5 fields=['Keywords']
PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_noop_when_no_rise PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_skips_already_pinned_field PASSED
tests/test_inline_remediation.py::test_bulk_inline_remediation_resends_failed_docs 2026-08-24T14:02:27.960509Z [info     ] Bulk import starting           archives=1 batch_docs=10000 indices_to_create=1 target_pattern=jt_restored total_messages=2
2026-08-24T14:02:27.961113Z [info     ] Bulk re-sent failed docs after remediation fields=['Keywords'] reindexed=1 resent=1 still_failed=0
2026-08-24T14:02:27.961383Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-08-24T14:02:27.961565Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.0s failed=0 indexed=2 sent=2
PASSED
tests/test_inline_remediation.py::test_check_capacity_uses_measured_override PASSED
tests/test_inline_remediation.py::test_capacity_abort_is_overridable PASSED
tests/test_inline_remediation.py::test_import_job_persists_retry_config 2026-08-24T14:02:28.416806Z [info     ] No archives to import         
PASSED
tests/test_integration.py::test_cross_conflict_actual_os_mapping PASSED
tests/test_integration.py::test_field_schema_zlib_in_preflight PASSED
tests/test_integration.py::test_timezone_dedup_correctness PASSED
tests/test_integration.py::test_timezone_retention_correctness PASSED
tests/test_integration.py::test_archive_write_read_integrity 2026-08-24T14:02:30.835761Z [info     ] Archive written                messages=50 path=/tmp/tmp4cba6kla/test/stream1/2026/01/01/test_stream1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
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
tests/test_integrity.py::test_verifier_flags_tampered 2026-08-24T14:02:32.392816Z [info     ] Verification started           total_archives=1
2026-08-24T14:02:32.394117Z [error    ] TAMPERED archive (HMAC mismatch) archive_id=1 path=/tmp/pytest-of-root/pytest-442/test_verifier_flags_tampered0/a.json.gz
2026-08-24T14:02:32.400746Z [info     ] Verification completed         corrupted=0 missing=0 orphans=0 tampered=1 total=1 valid=0
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
tests/test_os_export_multiprefix.py::test_denominator_is_grand_total_across_prefixes 2026-08-24T14:02:45.244781Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-08-24T14:02:45.245102Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-08-24T14:02:45.245342Z [info     ] Found indices                  count=3 prefix=graylog
2026-08-24T14:02:45.245513Z [info     ] Skipping active write index    index=graylog_write
2026-08-24T14:02:45.246240Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-08-24T14:02:45.247109Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-08-24T14:02:45.247516Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-08-24T14:02:45.247682Z [info     ] Found indices                  count=2 prefix=noise_38
2026-08-24T14:02:45.247797Z [info     ] Skipping active write index    index=noise_38_write
2026-08-24T14:02:45.248249Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-08-24T14:02:45.259306Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-08-24T14:02:45.259771Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-08-24T14:02:45.273800Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-442/test_denominator_is_grand_tota0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-08-24T14:02:45.283383Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-08-24T14:02:45.284020Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-08-24T14:02:45.295695Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-442/test_denominator_is_grand_tota0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-08-24T14:02:45.312439Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-08-24T14:02:45.312958Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-08-24T14:02:45.331886Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-442/test_denominator_is_grand_tota0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-08-24T14:02:45.342428Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-08-24T14:02:45.353416Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_multiprefix.py::test_progress_never_exceeds_total 2026-08-24T14:02:45.653579Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-08-24T14:02:45.653849Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-08-24T14:02:45.653979Z [info     ] Found indices                  count=3 prefix=graylog
2026-08-24T14:02:45.654078Z [info     ] Skipping active write index    index=graylog_write
2026-08-24T14:02:45.654614Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-08-24T14:02:45.655352Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-08-24T14:02:45.655764Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-08-24T14:02:45.655910Z [info     ] Found indices                  count=2 prefix=noise_38
2026-08-24T14:02:45.656012Z [info     ] Skipping active write index    index=noise_38_write
2026-08-24T14:02:45.656408Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-08-24T14:02:45.662528Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-08-24T14:02:45.662934Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-08-24T14:02:45.672220Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-442/test_progress_never_exceeds_to0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-08-24T14:02:45.682729Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-08-24T14:02:45.683175Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-08-24T14:02:45.691683Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-442/test_progress_never_exceeds_to0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-08-24T14:02:45.702391Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-08-24T14:02:45.702908Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-08-24T14:02:45.715213Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-442/test_progress_never_exceeds_to0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-08-24T14:02:45.722842Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-08-24T14:02:45.729634Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_multiprefix.py::test_denominator_is_stable_no_regression 2026-08-24T14:02:46.004885Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-08-24T14:02:46.005212Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-08-24T14:02:46.005392Z [info     ] Found indices                  count=3 prefix=graylog
2026-08-24T14:02:46.005594Z [info     ] Skipping active write index    index=graylog_write
2026-08-24T14:02:46.006285Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-08-24T14:02:46.007386Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-08-24T14:02:46.007857Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-08-24T14:02:46.008048Z [info     ] Found indices                  count=2 prefix=noise_38
2026-08-24T14:02:46.008204Z [info     ] Skipping active write index    index=noise_38_write
2026-08-24T14:02:46.008675Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-08-24T14:02:46.017791Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-08-24T14:02:46.023754Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-08-24T14:02:46.052434Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-442/test_denominator_is_stable_no_0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-08-24T14:02:46.077547Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-08-24T14:02:46.078121Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-08-24T14:02:46.095210Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-442/test_denominator_is_stable_no_0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-08-24T14:02:46.104137Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-08-24T14:02:46.104611Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-08-24T14:02:46.116537Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-442/test_denominator_is_stable_no_0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-08-24T14:02:46.124189Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-08-24T14:02:46.130791Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_progress.py::test_denominator_is_accumulated_not_reset_per_prefix PASSED
tests/test_os_export_progress.py::test_update_job_uses_grand_total_not_prefix_total PASSED
tests/test_os_export_progress.py::test_denominator_is_stable_two_phase PASSED
tests/test_os_export_progress.py::test_grand_total_initialised_before_prefix_loop PASSED
tests/test_os_page_sizing.py::test_wide_docs_shrink_the_page 2026-08-24T14:02:46.156552Z [info     ] Fetching from index            index=idx total=25000
2026-08-24T14:02:47.777358Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9130 index=idx page_size=1837 was=10000
2026-08-24T14:02:49.649073Z [info     ] Index fetch completed          fetched=25000 index=idx
PASSED
tests/test_os_page_sizing.py::test_typical_docs_keep_full_page 2026-08-24T14:02:49.658826Z [info     ] Fetching from index            index=idx total=25000
2026-08-24T14:02:50.533143Z [info     ] Index fetch completed          fetched=25000 index=idx
PASSED
tests/test_os_page_sizing.py::test_adaptation_never_below_floor 2026-08-24T14:02:50.540756Z [info     ] Fetching from index            index=idx total=3000
2026-08-24T14:02:54.867936Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=120130 index=idx page_size=500 was=10000
2026-08-24T14:02:54.875735Z [info     ] Index fetch completed          fetched=3000 index=idx
PASSED
tests/test_os_page_sizing.py::test_adaptation_does_not_raise 2026-08-24T14:02:54.906597Z [info     ] Fetching from index            index=idx total=12000
2026-08-24T14:02:56.276678Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9130 index=idx page_size=1837 was=10000
2026-08-24T14:02:56.479668Z [info     ] Index fetch completed          fetched=12000 index=idx
PASSED
tests/test_perf_covered_ranges.py::test_null_spans_cache_gives_identical_results PASSED
tests/test_perf_covered_ranges.py::test_string_merge_equals_datetime_merge_on_noncanonical_rows PASSED
tests/test_perf_covered_ranges.py::test_scheduled_run_pattern_stays_fast_at_scale PASSED
tests/test_perf_covered_ranges.py::test_zero_chunk_duration_cannot_hang_the_export PASSED
tests/test_perf_covered_ranges.py::test_jobs_table_has_a_polling_index_and_prune 2026-08-24T14:03:03.747713Z [info     ] Pruned old job-history rows    deleted=2 keep_days=365
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
tests/test_preflight_conflicts.py::TestFieldLimitAutoRaise::test_template_body_carries_the_computed_limit 2026-08-24T14:03:03.857890Z [info     ] Field limit applied to existing indices limit=30518 pattern=jt_restored_*
2026-08-24T14:03:03.860488Z [info     ] Bulk index template installed  pattern=jt_restored_* pinned_fields=1 template=jt_restored_template
PASSED
tests/test_preflight_conflicts.py::TestFieldLimitAutoRaise::test_rejected_limit_is_doubled_once_not_aborted 2026-08-24T14:03:03.866287Z [warning  ] Template rejected at field limit — retrying doubled limit=10000 retry=20000 template=jt_restored_template
2026-08-24T14:03:03.867839Z [info     ] Field limit applied to existing indices limit=20000 pattern=jt_restored_*
2026-08-24T14:03:03.868058Z [info     ] Bulk index template installed  pattern=jt_restored_* pinned_fields=1 template=jt_restored_template
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
tests/test_report_incomplete_notice.py::test_note_section_actually_renders PASSED
tests/test_report_incomplete_notice.py::test_note_description_is_not_duplicated PASSED
tests/test_report_incomplete_notice.py::test_incomplete_text_names_the_cause_and_the_remedy PASSED
tests/test_report_incomplete_notice.py::test_search_wait_is_configurable_not_hardcoded PASSED
tests/test_report_incomplete_notice.py::test_timeout_marks_the_run_incomplete PASSED
tests/test_report_incomplete_notice.py::test_axis_clamp_still_protects_sparse_widgets PASSED
tests/test_report_progress.py::test_rebuild_accepts_a_progress_callback PASSED
tests/test_report_progress.py::test_slicing_loop_reports_each_finished_slice PASSED
tests/test_report_progress.py::test_generator_threads_the_callback_into_the_rebuild PASSED
tests/test_report_progress.py::test_progress_callback_writes_columns_update_job_accepts PASSED
tests/test_report_progress.py::test_progress_never_claims_100_before_the_pdf_is_written PASSED
tests/test_report_progress.py::test_both_callers_pass_job_id PASSED
tests/test_report_progress.py::test_progress_never_goes_backwards_across_dashboards 2026-08-24T14:03:08.582998Z [info     ] Report generated               by=manual bytes=41950 emailed=False report=p
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
tests/test_schedule_overlap_guard.py::test_a_second_schedule_is_not_blocked_by_the_first PASSED
tests/test_schedule_overlap_guard.py::test_the_same_schedule_still_does_not_overlap_itself 2026-08-24T14:03:13.897970Z [info     ] This export schedule is still running, skipping this run schedule=auto-export
PASSED
tests/test_schedule_running_visibility.py::test_list_running_jobs_finds_a_weeks_old_running_job PASSED
tests/test_schedule_running_visibility.py::test_schedule_dict_marks_running_and_drops_misleading_next_run PASSED
tests/test_schedule_running_visibility.py::test_source_without_schedule_name_is_ignored PASSED
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
tests/test_startup_recovery.py::test_recover_stuck_importing PASSED
tests/test_startup_recovery.py::test_recover_stuck_importing_noop_when_clean PASSED
tests/test_static_sweeps.py::test_no_undefined_python_names PASSED
tests/test_static_sweeps.py::test_no_local_import_shadowing_module_imports PASSED
tests/test_static_sweeps.py::test_i18n_keys_exist_in_both_languages PASSED
tests/test_static_sweeps.py::test_every_data_act_handler_exists PASSED
tests/test_static_sweeps.py::test_silent_except_count_only_goes_down PASSED
tests/test_static_sweeps.py::test_error_strings_are_escaped_in_innerhtml PASSED
tests/test_static_sweeps.py::test_zh_i18n_fullwidth_punctuation PASSED
tests/test_static_sweeps.py::test_zh_i18n_taiwan_terminology PASSED
tests/test_storage_ownership.py::test_fix_dir_ownership_as_root 2026-08-24T14:03:31.719862Z [warning  ] Fixing directory ownership     new_owner=jt-glogarch path=/tmp/tmpdzpvt80b/archives/log4
PASSED
tests/test_storage_ownership.py::test_fix_dir_ownership_not_root SKIPPED
tests/test_storage_ownership.py::test_fix_only_under_base_path PASSED
tests/test_streams_cleanup.py::test_matches_stream_by_index_set_not_just_title PASSED
tests/test_streams_cleanup.py::test_does_not_touch_unrelated_streams PASSED
tests/test_streams_cleanup.py::test_title_prefix_match_still_works PASSED
tests/test_streams_cleanup.py::test_command_source_matches_by_index_set_id PASSED
tests/test_streams_cleanup.py::test_streams_are_deleted_before_index_sets PASSED
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
tests/test_upgrade_script.py::test_db_backup_probe_runs_inside_install_dir PASSED

================== 507 passed, 1 skipped in 103.98s (0:01:43) ==================
```

## Version Check

```
Canonical version: 1.13.88
OK: version '1.13.88' has exactly one source of truth.
```
