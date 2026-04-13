# Test Results

| Item | Value |
|---|---|
| **Status** | ✅ ALL PASSED |
| **Version** | v1.5.5 |
| **Date** | 2026-04-13 13:23:41 UTC |
| **Platform** | Python 3.10.12 / Linux 5.15.0-171-generic x86_64 |
| **Results** | 109 passed  / 1 skipped in 3.36s |
| **Version Check** | ✅ OK |

## Test Output

```
============================= test session starts ==============================
platform linux -- Python 3.10.12, pytest-9.0.3, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /opt/jt-glogarch
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 110 items

tests/test_api_error_handling.py::test_index_sets_catches_401 PASSED
tests/test_api_error_handling.py::test_streams_catches_401 PASSED
tests/test_api_error_handling.py::test_index_sets_catches_connection_error PASSED
tests/test_api_error_handling.py::test_streams_catches_connection_error PASSED
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
tests/test_config.py::test_default_settings PASSED
tests/test_config.py::test_config_search_paths PASSED
tests/test_config.py::test_load_from_file PASSED
tests/test_config.py::test_web_config_local_admin PASSED
tests/test_database_datetime.py::test_naive_roundtrip PASSED
tests/test_database_datetime.py::test_utc_aware_roundtrip PASSED
tests/test_database_datetime.py::test_non_utc_aware_roundtrip PASSED
tests/test_database_datetime.py::test_none_passthrough PASSED
tests/test_database_datetime.py::test_str_to_dt_with_offset PASSED
tests/test_db_rebuild.py::test_rebuild_dry_run [2m2026-04-13T13:23:43.462272Z[0m [[32m[1minfo     [0m] [1mWould insert                  [0m [36mpath[0m=[35m/tmp/tmp_43tu09q/archives/server1/2026/01/test.json.gz[0m [36mserver[0m=[35mtest[0m [36mtime_from[0m=[35m2026-01-01T00:00:00Z[0m
PASSED
tests/test_db_rebuild.py::test_rebuild_actual PASSED
tests/test_db_rebuild.py::test_rebuild_skip_existing PASSED
tests/test_db_rebuild.py::test_backup_db PASSED
tests/test_db_rebuild.py::test_prune_backups PASSED
tests/test_field_schema.py::test_plain_json_passthrough PASSED
tests/test_field_schema.py::test_zlib_roundtrip PASSED
tests/test_field_schema.py::test_decompress_none PASSED
tests/test_field_schema.py::test_decompress_corrupted PASSED
tests/test_field_schema.py::test_decompress_plain_json PASSED
tests/test_field_schema.py::test_db_field_schema_store_and_read PASSED
tests/test_health_endpoint.py::test_health_response_structure PASSED
tests/test_health_endpoint.py::test_health_not_behind_auth PASSED
tests/test_import_lock.py::test_claim_success PASSED
tests/test_import_lock.py::test_claim_conflict PASSED
tests/test_import_lock.py::test_release PASSED
tests/test_import_lock.py::test_release_wrong_owner PASSED
tests/test_import_lock.py::test_same_job_reclaim PASSED
tests/test_integration.py::test_cross_conflict_actual_os_mapping PASSED
tests/test_integration.py::test_field_schema_zlib_in_preflight PASSED
tests/test_integration.py::test_timezone_dedup_correctness PASSED
tests/test_integration.py::test_timezone_retention_correctness PASSED
tests/test_integration.py::test_archive_write_read_integrity [2m2026-04-13T13:23:45.044821Z[0m [[32m[1minfo     [0m] [1mArchive written               [0m [36mmessages[0m=[35m50[0m [36mpath[0m=[35m/tmp/tmp158pzokj/test/stream1/2026/01/01/test_stream1_20260101T000000Z_20260101T010000Z_001.json.gz[0m [36msize_mb[0m=[35m0.00[0m
PASSED
tests/test_integration.py::test_coverage_ratio_timezone PASSED
tests/test_local_admin.py::test_default_hash_is_empty PASSED
tests/test_local_admin.py::test_hash_generation PASSED
tests/test_local_admin.py::test_hash_verification PASSED
tests/test_local_admin.py::test_empty_hash_disables_fallback PASSED
tests/test_local_admin.py::test_backward_compatible_config PASSED
tests/test_local_admin.py::test_login_logic_graylog_rejects_no_fallback PASSED
tests/test_local_admin.py::test_login_logic_graylog_down_with_hash PASSED
tests/test_local_admin.py::test_login_wrong_username_rejected PASSED
tests/test_local_admin.py::test_login_logic_graylog_down_no_hash PASSED
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
tests/test_preflight_conflicts.py::test_intra_archive_conflict PASSED
tests/test_preflight_conflicts.py::test_cross_conflict_actual_mapping PASSED
tests/test_preflight_conflicts.py::test_string_only_no_target_mapping_not_pinned PASSED
tests/test_preflight_conflicts.py::test_mixed_scenario PASSED
tests/test_repo_structure.py::test_pyproject_at_root PASSED
tests/test_repo_structure.py::test_glogarch_package_at_root PASSED
tests/test_repo_structure.py::test_deploy_files_exist PASSED
tests/test_repo_structure.py::test_readme_files_exist PASSED
tests/test_repo_structure.py::test_changelog_files_exist PASSED
tests/test_repo_structure.py::test_config_docs_exist PASSED
tests/test_repo_structure.py::test_no_src_directory PASSED
tests/test_repo_structure.py::test_github_glogarch_matches_source PASSED
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
tests/test_storage_ownership.py::test_fix_dir_ownership_as_root [2m2026-04-13T13:23:45.227424Z[0m [[33m[1mwarning  [0m] [1mFixing directory ownership    [0m [36mnew_owner[0m=[35mjt-glogarch[0m [36mpath[0m=[35m/tmp/tmpaaxbgal9/archives/log4[0m
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
tests/test_upgrade_script.py::test_readme_git_clone_has_sudo PASSED

======================== 109 passed, 1 skipped in 3.36s ========================
```

## Version Check

```
Canonical version: 1.5.5
OK: version '1.5.5' has exactly one source of truth.
```
