# Test Results

| Item | Value |
|---|---|
| **Status** | ✅ ALL PASSED |
| **Version** | v1.13.63 |
| **Date** | 2026-07-27 07:10:50 UTC |
| **Platform** | Python 3.10.12 / Linux 5.15.0-185-generic x86_64 |
| **Results** | 389 passed  / 1 skipped in 51.76s |
| **Version Check** | ✅ OK |

## Test Output

```
============================= test session starts ==============================
collecting ... collected 390 items

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
tests/test_archive_streaming.py::test_streaming_returns_all_messages_incl_tricky_content 2026-07-27T07:10:58.734760Z [info     ] Archive written                messages=1000 path=/tmp/pytest-of-root/pytest-185/test_streaming_returns_all_mes0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.01
PASSED
tests/test_archive_streaming.py::test_empty_and_single 2026-07-27T07:10:58.976917Z [info     ] Archive written                messages=0 path=/tmp/pytest-of-root/pytest-185/test_empty_and_single0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
2026-07-27T07:10:58.979834Z [info     ] Archive written                messages=1 path=/tmp/pytest-of-root/pytest-185/test_empty_and_single0/b/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
PASSED
tests/test_archive_streaming.py::test_batching_shape 2026-07-27T07:10:58.988062Z [info     ] Archive written                messages=105 path=/tmp/pytest-of-root/pytest-185/test_batching_shape0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
PASSED
tests/test_archive_streaming.py::test_memory_is_bounded_not_whole_file 2026-07-27T07:11:00.039146Z [info     ] Archive written                messages=20000 path=/tmp/pytest-of-root/pytest-185/test_memory_is_bounded_not_who0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.12
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
tests/test_audit.py::test_cleanup_uses_audit_retention 2026-07-27T07:11:01.305498Z [info     ] No archives to clean up        retention_days=1095
2026-07-27T07:11:01.313716Z [info     ] Cleaned audit records          deleted=1 retention_days=180
2026-07-27T07:11:01.313902Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
2026-07-27T07:11:01.322017Z [info     ] No archives to clean up        retention_days=1095
2026-07-27T07:11:01.322589Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
PASSED
tests/test_audit.py::test_cleanup_audit_no_config 2026-07-27T07:11:01.550175Z [info     ] No archives to clean up        retention_days=1095
2026-07-27T07:11:01.558049Z [info     ] Cleaned audit records          deleted=1 retention_days=180
2026-07-27T07:11:01.558285Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
PASSED
tests/test_bulk_import.py::test_reserved_fields_stripped PASSED
tests/test_bulk_import.py::test_index_name_is_deflector PASSED
tests/test_bulk_import.py::test_index_name_no_timestamp PASSED
tests/test_bulk_import.py::test_stream_rewrite PASSED
tests/test_bulk_import.py::test_marker_field_injected PASSED
tests/test_bulk_import.py::test_dedup_id_uses_gl2_message_id PASSED
tests/test_bulk_import.py::test_dedup_none_no_id PASSED
tests/test_bulk_streaming.py::test_iter_batches_streams_in_batch_sized_chunks PASSED
tests/test_bulk_streaming.py::test_count_messages_uses_header_not_full_read PASSED
tests/test_bulk_streaming.py::test_import_path_never_calls_whole_file_loader 2026-07-27T07:11:01.615510Z [info     ] Bulk import starting           archives=1 batch_docs=50 indices_to_create=1 target_pattern=graylog total_messages=120
2026-07-27T07:11:01.620165Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-07-27T07:11:01.620377Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.0s failed=0 indexed=120 sent=120
PASSED
tests/test_bulk_streaming.py::test_corrupt_archive_does_not_abort_whole_run 2026-07-27T07:11:01.628896Z [info     ] Bulk import starting           archives=2 batch_docs=5 indices_to_create=1 target_pattern=graylog total_messages=11
2026-07-27T07:11:01.631413Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-07-27T07:11:01.631625Z [info     ] Bulk import completed          archives=2 at_destination=-1 duration=0.0s failed=0 indexed=11 sent=11
PASSED
tests/test_bulk_streaming.py::test_bulk_body_capped_by_bytes_not_just_doc_count PASSED
tests/test_bulk_streaming.py::test_single_oversized_doc_still_sent PASSED
tests/test_bulk_streaming.py::test_byte_cap_loses_no_documents 2026-07-27T07:11:02.411514Z [info     ] Bulk import starting           archives=1 batch_docs=10000 indices_to_create=1 target_pattern=graylog total_messages=400
2026-07-27T07:11:02.661080Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-07-27T07:11:02.661313Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.3s failed=0 indexed=400 sent=400
PASSED
tests/test_cleanup_race.py::test_grace_seconds_defined PASSED
tests/test_cleanup_race.py::test_recent_file_skipped PASSED
tests/test_cleanup_race.py::test_old_file_not_skipped PASSED
tests/test_cleanup_schedule_retention.py::test_schedule_retention_days_is_used 2026-07-27T07:11:02.678592Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=200 retention_source=schedule
PASSED
tests/test_cleanup_schedule_retention.py::test_falls_back_to_config_when_schedule_has_none 2026-07-27T07:11:02.686899Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=1095 retention_source=config.yaml
PASSED
tests/test_cleanup_schedule_retention.py::test_bad_config_json_does_not_break_cleanup 2026-07-27T07:11:02.695660Z [warning  ] Could not read the schedule's retention setting; falling back to config.yaml error='Expecting property name enclosed in double quotes: line 1 column 2 (char 1)' schedule=auto-cleanup
2026-07-27T07:11:02.696019Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=1095 retention_source=config.yaml
PASSED
tests/test_cleanup_schedule_retention.py::test_upgrade_does_not_shorten_retention_and_delete_data 2026-07-27T07:11:02.702650Z [warning  ] Cleanup schedule retention reconciled on upgrade — the value shown in the UI was never actually applied, and honouring it now would have deleted archives this version was keeping. Set it again in the Schedules page if the shorter retention is what you want. now_in_force=1095 schedule=auto-cleanup was_shown=200
PASSED
tests/test_cleanup_schedule_retention.py::test_longer_stored_retention_is_kept_it_only_retains_more PASSED
tests/test_cleanup_schedule_retention.py::test_equal_values_are_untouched PASSED
tests/test_cleanup_schedule_retention.py::test_schedule_without_retention_is_untouched PASSED
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
tests/test_db_rebuild.py::test_rebuild_dry_run 2026-07-27T07:11:07.950672Z [info     ] Would insert                   path=/tmp/tmp9_qyzo7z/archives/server1/2026/01/test.json.gz server=test time_from=2026-01-01T00:00:00Z
PASSED
tests/test_db_rebuild.py::test_rebuild_actual PASSED
tests/test_db_rebuild.py::test_rebuild_skip_existing PASSED
tests/test_db_rebuild.py::test_backup_db PASSED
tests/test_db_rebuild.py::test_prune_backups PASSED
tests/test_export_pagination.py::test_deep_pagination_no_same_ms_loss_or_dup 2026-07-27T07:11:08.790991Z [info     ] Total messages to fetch        total=6
2026-07-27T07:11:08.793714Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=4 new_from='2024-01-01 00:00:00.003000' old_from='2024-01-01 00:00:00'
PASSED
tests/test_export_pagination.py::test_deep_pagination_multiple_windows 2026-07-27T07:11:08.804053Z [info     ] Total messages to fetch        total=30
2026-07-27T07:11:08.807513Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=6 new_from='2024-01-01 00:00:00.005000' old_from='2024-01-01 00:00:00'
2026-07-27T07:11:08.811952Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=11 new_from='2024-01-01 00:00:00.010000' old_from='2024-01-01 00:00:00.005000'
2026-07-27T07:11:08.814916Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=16 new_from='2024-01-01 00:00:00.015000' old_from='2024-01-01 00:00:00.010000'
2026-07-27T07:11:08.817655Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=21 new_from='2024-01-01 00:00:00.020000' old_from='2024-01-01 00:00:00.015000'
2026-07-27T07:11:08.820303Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=26 new_from='2024-01-01 00:00:00.025000' old_from='2024-01-01 00:00:00.020000'
PASSED
tests/test_export_pagination.py::test_pagination_raises_on_unsplittable_ms 2026-07-27T07:11:08.828173Z [info     ] Total messages to fetch        total=10
PASSED
tests/test_export_pagination.py::test_fmt_ts_millisecond_precision PASSED
tests/test_export_pagination.py::test_parse_timestamp_robust_fallback PASSED
tests/test_export_pagination.py::test_transient_5xx_fails_over_to_next_host 2026-07-27T07:11:08.848371Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=1 status=503 wait=1
2026-07-27T07:11:08.852398Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=2 status=503 wait=2
2026-07-27T07:11:08.854035Z [warning  ] Transient errors exhausted, failing over to next host host=http://host0:9200 status=503
2026-07-27T07:11:08.855556Z [info     ] Failover to host               host=http://host1:9200
PASSED
tests/test_export_pagination.py::test_all_hosts_transient_raises 2026-07-27T07:11:08.868501Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=1 status=503 wait=1
2026-07-27T07:11:08.870452Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=2 status=503 wait=2
2026-07-27T07:11:08.870871Z [warning  ] Transient errors exhausted, failing over to next host host=http://host0:9200 status=503
2026-07-27T07:11:08.871119Z [warning  ] Transient error, retrying      host=http://host1:9200 retry=1 status=503 wait=1
2026-07-27T07:11:08.871386Z [warning  ] Transient error, retrying      host=http://host1:9200 retry=2 status=503 wait=2
2026-07-27T07:11:08.871583Z [warning  ] Transient errors exhausted, failing over to next host host=http://host1:9200 status=503
PASSED
tests/test_export_pagination.py::test_non_transient_4xx_raises_immediately PASSED
tests/test_export_pagination.py::test_iter_index_docs_no_stale_total_early_stop PASSED
tests/test_export_pagination.py::test_rate_limiter_does_not_hold_lock_across_sleep PASSED
tests/test_export_pagination.py::test_rate_limiter_acquire_allows_burst PASSED
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
tests/test_graylog_flush.py::test_flush_cycles_and_rebuilds_never_deletes 2026-07-27T07:11:10.486604Z [info     ] graylog flush done             actions=['cycle_deflector:ok', 'rebuild_index_ranges:ok'] ok=True
PASSED
tests/test_graylog_flush.py::test_flush_global_deflector_fallback_when_no_index_set 2026-07-27T07:11:10.493841Z [info     ] graylog flush done             actions=['cycle_deflector:ok', 'rebuild_index_ranges:ok'] ok=True
PASSED
tests/test_graylog_flush.py::test_flush_reports_action_error_without_raising 2026-07-27T07:11:10.500588Z [info     ] graylog flush done             actions=['cycle_deflector:error', 'rebuild_index_ranges:ok'] ok=False
PASSED
tests/test_graylog_flush.py::test_snapshot_unreachable_returns_empty_not_raise 2026-07-27T07:11:10.504990Z [warning  ] flush snapshot failed          error=unreachable
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
tests/test_health_guard.py::test_pause_then_resume 2026-07-27T07:11:10.526965Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 95% (over the hard limit 90%)']
2026-07-27T07:11:10.527156Z [info     ] export resumed — backpressure cleared waited_sec=1
PASSED
tests/test_health_guard.py::test_pause_times_out_and_raises 2026-07-27T07:11:10.529732Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 99% (over the hard limit 90%)']
2026-07-27T07:11:10.529924Z [error    ] export stopped — backpressure did not clear signals=['JVM heap 99% (over the hard limit 90%)'] waited_sec=60
PASSED
tests/test_health_schedule_registration.py::test_health_compares_enabled_schedules_against_registered_jobs PASSED
tests/test_health_schedule_registration.py::test_unregistered_schedule_makes_health_unhealthy PASSED
tests/test_health_schedule_registration.py::test_upgrade_script_fails_when_schedules_are_not_registered PASSED
tests/test_import_batch_flow.py::test_web_ui_flow_control_batch_and_rate_are_preserved 2026-07-27T07:11:10.787326Z [info     ] No archives to import         
PASSED
tests/test_import_batch_flow.py::test_no_flow_control_captures_config_defaults 2026-07-27T07:11:11.047848Z [info     ] No archives to import         
PASSED
tests/test_import_batch_flow.py::test_seeding_is_guarded_in_source PASSED
tests/test_import_jvm_throttle.py::test_ring_buffer_is_the_early_signal PASSED
tests/test_import_jvm_throttle.py::test_buffer_pause_beats_low_journal PASSED
tests/test_import_jvm_throttle.py::test_heap_alone_triggers_slow_then_pause PASSED
tests/test_import_jvm_throttle.py::test_journal_alone_still_works PASSED
tests/test_import_jvm_throttle.py::test_most_severe_signal_wins PASSED
tests/test_import_jvm_throttle.py::test_unknown_heap_is_ignored PASSED
tests/test_import_jvm_throttle.py::test_monitoring_disabled_is_normal PASSED
tests/test_import_jvm_throttle.py::test_failed_check_before_ever_working_does_not_deadlock 2026-07-27T07:11:11.078146Z [warning  ] Journal endpoint unreachable; import proceeds at user rate without journal throttling error=404
PASSED
tests/test_import_jvm_throttle.py::test_failed_check_after_working_is_failsafe_pause 2026-07-27T07:11:11.079757Z [warning  ] Journal check failed mid-import (target unreachable/stuck) — pausing until it recovers error=timeout
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
tests/test_index_set_coverage.py::test_restricting_reports_skipped_index_sets 2026-07-27T07:11:11.116667Z [warning  ] Index sets NOT covered by this OpenSearch export — their logs will NOT be archived and will be lost when Graylog retention deletes them covered=['graylog'] skipped=['PVE Hosts', 'Wazuh']
PASSED
tests/test_index_set_coverage.py::test_explicit_prefix_skips_api_lookup PASSED
tests/test_index_set_coverage.py::test_index_sets_without_prefix_are_ignored PASSED
tests/test_index_set_coverage.py::test_job_result_json_round_trips PASSED
tests/test_indexer_failure_autofix.py::test_parse_failure_message_extracts_field_and_reason PASSED
tests/test_indexer_failure_autofix.py::test_parse_failure_rejects_log_prefix_tokens PASSED
tests/test_indexer_failure_autofix.py::test_get_indexer_failure_details_aggregates_fields PASSED
tests/test_indexer_failure_autofix.py::test_remediate_pins_fields_and_cycles_never_deletes 2026-07-27T07:11:11.410754Z [info     ] Custom mappings applied        failed=0 ok=2 total=2
2026-07-27T07:11:11.412304Z [info     ] Auto-remediated indexer-failure fields as string fields=['Keywords', 'foo'] index_set=idx1
PASSED
tests/test_indexer_failure_autofix.py::test_iterator_metadata_fallback_degrades_not_crashes PASSED
tests/test_indexer_failure_autofix.py::test_long_overflow_numeric_tracked_as_string PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_pins_new_fields_on_rise 2026-07-27T07:11:11.432257Z [warning  ] Mid-import auto-remediation applied failures_delta=5 fields=['Keywords']
PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_noop_when_no_rise PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_skips_already_pinned_field PASSED
tests/test_inline_remediation.py::test_bulk_inline_remediation_resends_failed_docs 2026-07-27T07:11:11.462261Z [info     ] Bulk import starting           archives=1 batch_docs=10000 indices_to_create=1 target_pattern=jt_restored total_messages=2
2026-07-27T07:11:11.462803Z [info     ] Bulk re-sent failed docs after remediation fields=['Keywords'] reindexed=1 resent=1 still_failed=0
2026-07-27T07:11:11.462964Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-07-27T07:11:11.463077Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.0s failed=0 indexed=2 sent=2
PASSED
tests/test_inline_remediation.py::test_check_capacity_uses_measured_override PASSED
tests/test_inline_remediation.py::test_capacity_abort_is_overridable PASSED
tests/test_inline_remediation.py::test_import_job_persists_retry_config 2026-07-27T07:11:11.718994Z [info     ] No archives to import         
PASSED
tests/test_integration.py::test_cross_conflict_actual_os_mapping PASSED
tests/test_integration.py::test_field_schema_zlib_in_preflight PASSED
tests/test_integration.py::test_timezone_dedup_correctness PASSED
tests/test_integration.py::test_timezone_retention_correctness PASSED
tests/test_integration.py::test_archive_write_read_integrity 2026-07-27T07:11:13.027547Z [info     ] Archive written                messages=50 path=/tmp/tmplp_vkto8/test/stream1/2026/01/01/test_stream1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
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
tests/test_integrity.py::test_verifier_flags_tampered 2026-07-27T07:11:14.146384Z [info     ] Verification started           total_archives=1
2026-07-27T07:11:14.147314Z [error    ] TAMPERED archive (HMAC mismatch) archive_id=1 path=/tmp/pytest-of-root/pytest-185/test_verifier_flags_tampered0/a.json.gz
2026-07-27T07:11:14.153504Z [info     ] Verification completed         corrupted=0 missing=0 orphans=0 tampered=1 total=1 valid=0
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
tests/test_os_export_multiprefix.py::test_denominator_is_grand_total_across_prefixes 2026-07-27T07:11:26.592275Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-07-27T07:11:26.592540Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-07-27T07:11:26.592670Z [info     ] Found indices                  count=3 prefix=graylog
2026-07-27T07:11:26.592934Z [info     ] Skipping active write index    index=graylog_write
2026-07-27T07:11:26.593683Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-07-27T07:11:26.594323Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-07-27T07:11:26.594727Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-07-27T07:11:26.594867Z [info     ] Found indices                  count=2 prefix=noise_38
2026-07-27T07:11:26.595012Z [info     ] Skipping active write index    index=noise_38_write
2026-07-27T07:11:26.595538Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-07-27T07:11:26.604020Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-07-27T07:11:26.604521Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-07-27T07:11:26.618609Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-185/test_denominator_is_grand_tota0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-27T07:11:26.627609Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-07-27T07:11:26.628003Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-07-27T07:11:26.638129Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-185/test_denominator_is_grand_tota0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-27T07:11:26.646292Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-07-27T07:11:26.646609Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-07-27T07:11:26.660347Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-185/test_denominator_is_grand_tota0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-07-27T07:11:26.668439Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-07-27T07:11:26.674926Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_multiprefix.py::test_progress_never_exceeds_total 2026-07-27T07:11:26.852353Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-07-27T07:11:26.852836Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-07-27T07:11:26.853078Z [info     ] Found indices                  count=3 prefix=graylog
2026-07-27T07:11:26.853300Z [info     ] Skipping active write index    index=graylog_write
2026-07-27T07:11:26.854119Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-07-27T07:11:26.854830Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-07-27T07:11:26.855114Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-07-27T07:11:26.855226Z [info     ] Found indices                  count=2 prefix=noise_38
2026-07-27T07:11:26.855339Z [info     ] Skipping active write index    index=noise_38_write
2026-07-27T07:11:26.855765Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-07-27T07:11:26.862656Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-07-27T07:11:26.863025Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-07-27T07:11:26.873535Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-185/test_progress_never_exceeds_to0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-27T07:11:26.884286Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-07-27T07:11:26.884717Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-07-27T07:11:26.897265Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-185/test_progress_never_exceeds_to0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-27T07:11:26.907350Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-07-27T07:11:26.907809Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-07-27T07:11:26.918484Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-185/test_progress_never_exceeds_to0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-07-27T07:11:26.928363Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-07-27T07:11:26.934920Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_multiprefix.py::test_denominator_is_stable_no_regression 2026-07-27T07:11:27.141096Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-07-27T07:11:27.141502Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-07-27T07:11:27.141740Z [info     ] Found indices                  count=3 prefix=graylog
2026-07-27T07:11:27.141940Z [info     ] Skipping active write index    index=graylog_write
2026-07-27T07:11:27.142693Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-07-27T07:11:27.143421Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-07-27T07:11:27.143834Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-07-27T07:11:27.144097Z [info     ] Found indices                  count=2 prefix=noise_38
2026-07-27T07:11:27.144262Z [info     ] Skipping active write index    index=noise_38_write
2026-07-27T07:11:27.144704Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-07-27T07:11:27.151988Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-07-27T07:11:27.152488Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-07-27T07:11:27.167003Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-185/test_denominator_is_stable_no_0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-27T07:11:27.175286Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-07-27T07:11:27.175845Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-07-27T07:11:27.185979Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-185/test_denominator_is_stable_no_0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-07-27T07:11:27.195558Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-07-27T07:11:27.196111Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-07-27T07:11:27.205389Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-185/test_denominator_is_stable_no_0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-07-27T07:11:27.215320Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-07-27T07:11:27.226860Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_progress.py::test_denominator_is_accumulated_not_reset_per_prefix PASSED
tests/test_os_export_progress.py::test_update_job_uses_grand_total_not_prefix_total PASSED
tests/test_os_export_progress.py::test_denominator_is_stable_two_phase PASSED
tests/test_os_export_progress.py::test_grand_total_initialised_before_prefix_loop PASSED
tests/test_os_page_sizing.py::test_wide_docs_shrink_the_page 2026-07-27T07:11:27.249993Z [info     ] Fetching from index            index=idx total=25000
2026-07-27T07:11:28.437039Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9130 index=idx page_size=1837 was=10000
2026-07-27T07:11:29.889719Z [info     ] Index fetch completed          fetched=25000 index=idx
PASSED
tests/test_os_page_sizing.py::test_typical_docs_keep_full_page 2026-07-27T07:11:29.893743Z [info     ] Fetching from index            index=idx total=25000
2026-07-27T07:11:30.480218Z [info     ] Index fetch completed          fetched=25000 index=idx
PASSED
tests/test_os_page_sizing.py::test_adaptation_never_below_floor 2026-07-27T07:11:30.486225Z [info     ] Fetching from index            index=idx total=3000
2026-07-27T07:11:34.757572Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=120130 index=idx page_size=500 was=10000
2026-07-27T07:11:34.764047Z [info     ] Index fetch completed          fetched=3000 index=idx
PASSED
tests/test_os_page_sizing.py::test_adaptation_does_not_raise 2026-07-27T07:11:34.793356Z [info     ] Fetching from index            index=idx total=12000
2026-07-27T07:11:35.918207Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9130 index=idx page_size=1837 was=10000
2026-07-27T07:11:36.135028Z [info     ] Index fetch completed          fetched=12000 index=idx
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
tests/test_schedule_overlap_guard.py::test_the_same_schedule_still_does_not_overlap_itself 2026-07-27T07:11:39.788438Z [info     ] This export schedule is still running, skipping this run schedule=auto-export
PASSED
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
tests/test_storage_ownership.py::test_fix_dir_ownership_as_root 2026-07-27T07:11:45.511994Z [warning  ] Fixing directory ownership     new_owner=jt-glogarch path=/tmp/tmptwk_fbfy/archives/log4
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

======================= 389 passed, 1 skipped in 51.76s ========================
```

## Version Check

```
Canonical version: 1.13.63
OK: version '1.13.63' has exactly one source of truth.
```
