# Test Results

| Item | Value |
|---|---|
| **Status** | ✅ ALL PASSED |
| **Version** | v1.36.0 |
| **Date** | 2026-11-27 01:24:03 UTC |
| **Platform** | Python 3.10.12 / Linux 5.15.0-202-generic x86_64 |
| **Results** | 1756 passed  / 1 skipped in 524.12s |
| **Version Check** | ✅ OK |
| **Bandit (source security)** | Bandit: OK (HIGH 0, MEDIUM 0, gated LOW 8/8; 9 LOW total, 1 owned by the except-ratchet sweep) |
| **SBOM** | ✅ 60 components (CycloneDX 1.5, sbom.cdx.json) |
| **Vendored mcp_graylog** | mcp_graylog: OK - vendored 1.12.0 is the published version. |

## Test Output

```
============================= test session starts ==============================
collecting ... collected 1757 items

tests/test_ai.py::test_vendored_file_is_the_manifest_version PASSED
tests/test_ai.py::test_it_loads_on_this_python PASSED
tests/test_ai.py::test_status_says_why_when_it_cannot_load 2026-11-27 09:24:32 [warning  ] mcp_graylog could not be loaded; its tools are unavailable error='mcp_graylog could not be loaded on Python 3.10: SyntaxError: f-string expression part cannot include a backslash'
PASSED
tests/test_ai.py::test_wildcard_queries_never_reach_mcp_graylog PASSED
tests/test_ai.py::test_heavy_mcp_graylog_tools_are_opt_in PASSED
tests/test_ai.py::test_event_tools_are_offered_and_search_events_gets_the_long_range PASSED
tests/test_ai.py::test_lookback_is_capped PASSED
tests/test_ai.py::test_own_tools_work_without_mcp_graylog PASSED
tests/test_ai.py::test_mcp_graylog_import_is_contained PASSED
tests/test_ai.py::test_stand_in_is_not_installed_when_the_sdk_exists PASSED
tests/test_ai.py::test_range_hours[now-15m-now-0.25] PASSED
tests/test_ai.py::test_range_hours[now-24h-now-24] PASSED
tests/test_ai.py::test_range_hours[2 hours ago-now-2] PASSED
tests/test_ai.py::test_range_hours[2026-11-19T00:00:00Z-2026-11-19T06:00:00Z-6] PASSED
tests/test_ai.py::test_range_hours[now-1w-now-168] PASSED
tests/test_ai.py::test_range_hours[yesterday-now-None] PASSED
tests/test_ai.py::test_range_hours[now-5x-now-None] PASSED
tests/test_ai.py::test_call_tool_refuses_unknown_tool_args_and_long_ranges PASSED
tests/test_ai.py::test_top_values_is_exact_and_validates_the_field 2026-11-27 09:24:34 [info     ] AI tool failed                 channel=chat error='field: a Graylog field name, e.g. source_ip' tool=top_values
PASSED
tests/test_ai.py::test_results_too_big_are_kept_and_paged_not_cut 2026-11-27 09:24:35 [info     ] AI tool failed                 channel=chat error='result_id: unknown or expired (results are kept 30 minutes); run the tool again' tool=read_result
PASSED
tests/test_ai.py::test_parse_reply_native_text_and_think PASSED
tests/test_ai.py::test_check_url_private_first PASSED
tests/test_ai.py::test_budget PASSED
tests/test_ai.py::test_tool_round_then_answer_and_audit PASSED
tests/test_ai.py::test_rounds_run_out_then_a_forced_answer PASSED
tests/test_ai.py::test_empty_answer_is_asked_again_then_reported PASSED
tests/test_ai.py::test_data_block_cannot_be_closed_from_inside PASSED
tests/test_ai.py::test_budget_stops_the_chat PASSED
tests/test_ai.py::test_a_cut_off_answer_is_continued PASSED
tests/test_ai.py::test_an_answer_still_cut_off_says_so PASSED
tests/test_ai.py::test_an_answer_goes_on_after_the_page_is_left PASSED
tests/test_ai.py::test_stop_ends_an_answer_left_running PASSED
tests/test_ai.py::test_chat_page_wiring PASSED
tests/test_ai.py::test_mcp_methods PASSED
tests/test_ai.py::test_token_headers_and_rate PASSED
tests/test_ai.py::test_mcp_endpoint_gates PASSED
tests/test_ai.py::test_settings_secret_and_locality PASSED
tests/test_ai.py::test_chat_needs_graylog_signin_and_conversations_are_private PASSED
tests/test_ai.py::test_markdown_renderer_escapes_before_formatting PASSED
tests/test_ai.py::test_streamed_text_resets_when_a_round_turns_into_tool_calls PASSED
tests/test_ai.py::test_a_continuation_streams_onto_the_text_already_shown PASSED
tests/test_ai.py::test_stream_client_assembles_text_tool_calls_and_usage PASSED
tests/test_ai.py::test_stream_falls_back_to_a_plain_request_when_refused 2026-11-27T01:24:50.952684Z [info     ] LLM server refused a streamed request; using plain requests error='stream not supported'
PASSED
tests/test_ai.py::test_stream_dropped_mid_reply_is_an_llm_error PASSED
tests/test_ai.py::test_live_text_hides_unfinished_think_and_text_tool_calls PASSED
tests/test_ai.py::test_each_query_is_kept_with_the_range_it_ran_with PASSED
tests/test_ai.py::test_a_recorded_query_holds_no_log_text PASSED
tests/test_ai.py::test_stored_queries_link_to_the_same_search_in_graylog PASSED
tests/test_ai.py::test_rename_and_search_conversations PASSED
tests/test_ai.py::test_a_question_left_unanswered_can_be_answered_once PASSED
tests/test_ai.py::test_an_old_database_gets_the_calls_column PASSED
tests/test_ai.py::test_chat_page_wiring_134 PASSED
tests/test_ai.py::test_conversation_markdown_and_day_groups PASSED
tests/test_ai.py::test_a_page_that_comes_back_reads_the_answer_written_so_far PASSED
tests/test_ai.py::test_number_columns_are_right_aligned_and_do_not_wrap PASSED
tests/test_ai.py::test_a_tool_that_does_not_report_its_range_gets_it_from_its_arguments PASSED
tests/test_ai.py::test_another_users_running_conversation_reads_as_not_found PASSED
tests/test_ai.py::test_stop_and_delete_cancel_on_the_event_loop PASSED
tests/test_ai.py::test_an_answer_that_cannot_be_stored_ends_the_run 2026-11-27T01:25:00.019977Z [warning  ] AI answer could not be stored  conversation=1 error='database is locked'
PASSED
tests/test_ai.py::test_an_absurd_range_from_the_model_does_not_end_the_answer PASSED
tests/test_ai.py::test_stream_assembly_survives_odd_servers PASSED
tests/test_ai.py::test_a_400_that_plain_requests_also_get_keeps_streaming_on PASSED
tests/test_ai.py::test_chat_page_review_fixes_wiring PASSED
tests/test_ai.py::test_tool_numbers_are_kept_within_the_schema PASSED
tests/test_ai.py::test_mcp_limits_batches_bodies_unknown_servers_and_refused_tokens PASSED
tests/test_ai.py::test_stream_client_sends_reasoning_as_it_grows_and_all_of_it_before_the_answer PASSED
tests/test_ai.py::test_reasoning_inside_think_tags_in_content_is_shown_too PASSED
tests/test_ai.py::test_run_chat_streams_each_requests_reasoning_and_replaces_the_last_one PASSED
tests/test_ai.py::test_a_page_that_comes_back_gets_the_reasoning_so_far PASSED
tests/test_ai.py::test_split_followups[24 \u5c0f\u6642\u5167 3 \u500b IP\u3002\n\n| ip | n |\n|---|---|\n| a | 2 |\n\n[[follow-up]]\n- \u9019\u4e9b IP \u8a66\u4e86\u54ea\u4e9b\u5e33\u865f\uff1f\n2. \u904e\u53bb 7 \u5929\u7684\u8da8\u52e2\u5462\uff1f\n\u300c\u54ea\u500b\u4e3b\u6a5f\u88ab\u8a66\u6700\u591a\u6b21\uff1f\u300d\n-24 \u5c0f\u6642\u5167 3 \u500b IP\u3002\n\n| ip | n |\n|---|---|\n| a | 2 |-qs0] PASSED
tests/test_ai.py::test_split_followups[A.\n**[[Follow-ups]]**\n1) q1?\n1) q1?\n\n2) q2?\n3) q3?\n4) q4?-A.-qs1] PASSED
tests/test_ai.py::test_split_followups[A.\n### [[ follow up ]]\uff1a\n* xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n* ok?-A.-qs2] PASSED
tests/test_ai.py::test_split_followups[No marker, a [[link]] in text.\n- not a suggestion-No marker, a [[link]] in text.\n- not a suggestion-qs3] PASSED
tests/test_ai.py::test_split_followups[A.\n[[follow-up]]-A.-qs4] PASSED
tests/test_ai.py::test_the_marker_never_shows_while_the_answer_streams PASSED
tests/test_ai.py::test_rule_asks_for_suggestions_in_the_page_language PASSED
tests/test_ai.py::test_run_chat_returns_suggestions_apart_from_the_answer PASSED
tests/test_ai.py::test_a_cut_off_answer_offers_no_suggestions PASSED
tests/test_ai.py::test_suggestions_are_stored_and_read_back PASSED
tests/test_ai.py::test_an_old_database_gets_the_followups_column PASSED
tests/test_ai.py::test_page_offers_the_suggestions_under_the_last_answer_only PASSED
tests/test_ai.py::test_a_silent_model_server_is_reported_and_then_cleared[headers] PASSED
tests/test_ai.py::test_a_silent_model_server_is_reported_and_then_cleared[body] PASSED
tests/test_ai.py::test_a_server_that_answers_at_once_gives_no_wait_notice PASSED
tests/test_ai.py::test_a_failing_wait_notice_never_fails_the_request 2026-11-27T01:25:08.278276Z [warning  ] LLM wait notice failed         error='page gone'
PASSED
tests/test_ai.py::test_run_chat_shows_the_wait_and_gives_the_phase_line_back PASSED
tests/test_ai.py::test_the_page_names_the_wait PASSED
tests/test_ai.py::test_the_chat_never_makes_the_page_scroll PASSED
tests/test_ai.py::test_opening_the_query_list_brings_it_to_the_top PASSED
tests/test_ai.py::test_the_chat_draws_its_blocks_apart PASSED
tests/test_ai.py::test_static_files_are_revalidated PASSED
tests/test_ai.py::test_a_notice_colours_only_its_own_icon PASSED
tests/test_ai.py::test_the_settings_are_framed_sections PASSED
tests/test_ai_136.py::test_reasoning_loops_are_caught PASSED
tests/test_ai_136.py::test_tables_html_and_lists_are_not_loops PASSED
tests/test_ai_136.py::test_a_looping_answer_is_cut_to_its_first_copy PASSED
tests/test_ai_136.py::test_the_watch_checks_only_every_few_hundred_characters PASSED
tests/test_ai_136.py::test_same_call_whatever_the_key_order PASSED
tests/test_ai_136.py::test_a_small_result_is_unchanged PASSED
tests/test_ai_136.py::test_a_big_result_becomes_a_valid_view_with_a_summary PASSED
tests/test_ai_136.py::test_text_results_come_in_pages PASSED
tests/test_ai_136.py::test_kept_results_expire PASSED
tests/test_ai_136.py::test_aggregate_builds_the_graylog_request PASSED
tests/test_ai_136.py::test_aggregate_coarsens_time_buckets_and_caps_rows 2026-11-27T01:25:10.547663Z [info     ] AI tool failed                 channel=chat error='group_by: up to 1,000,000 rows; at most 10,000 (fewer rows per field, a coarser time step or a shorter range)' tool=aggregate
2026-11-27T01:25:10.554987Z [info     ] AI tool failed                 channel=chat error='group_by: 1 to 3 fields, e.g. ["user_name", "source_ip:5"] or ["timestamp:1h", "event_outcome"]' tool=aggregate
2026-11-27T01:25:10.563196Z [info     ] AI tool failed                 channel=chat error="metrics: 'median:x' is not one of count, count:<field>, card:<field>, min:<field>, max:<field>, sum:<field>, avg:<field>, latest:<field>, stddev:<field>, p95:<field>" tool=aggregate
PASSED
tests/test_ai_136.py::test_aggregate_says_when_a_metric_field_is_missing PASSED
tests/test_ai_136.py::test_summarize_reads_pages_and_merges_patterns PASSED
tests/test_ai_136.py::test_paging_past_graylogs_window_is_refused PASSED
tests/test_ai_136.py::test_profile_reads_the_server_and_honours_the_setting PASSED
tests/test_ai_136.py::test_unknown_context_is_assumed_not_fatal PASSED
tests/test_ai_136.py::test_token_estimate_counts_cjk_heavier PASSED
tests/test_ai_136.py::test_a_small_context_gets_fewer_tools_and_smaller_results PASSED
tests/test_ai_136.py::test_repeated_tool_calls_are_not_run_again PASSED
tests/test_ai_136.py::test_a_reasoning_loop_is_stopped_and_asked_again_once PASSED
tests/test_ai_136.py::test_a_looping_answer_is_kept_up_to_the_repeat PASSED
tests/test_ai_136.py::test_history_keeps_the_newest_turns_and_lists_older_questions PASSED
tests/test_ai_136.py::test_a_single_server_config_becomes_the_first_server_and_is_written_back PASSED
tests/test_ai_136.py::test_limits_site_server_and_user PASSED
tests/test_ai_136.py::test_pins_are_capped_listed_first_and_kept_by_the_prune PASSED
tests/test_ai_136.py::test_messages_convert_to_the_claude_shape PASSED
tests/test_ai_136.py::test_claude_request_choices PASSED
tests/test_ai_136.py::test_a_claude_tool_round_through_the_real_sdk PASSED
tests/test_ai_136.py::test_private_keys_never_reach_an_openai_server PASSED
tests/test_ai_136.py::test_several_llm_servers_are_saved_with_their_keys PASSED
tests/test_ai_136.py::test_chat_refuses_an_unknown_llm_and_pins_are_capped PASSED
tests/test_ai_136.py::test_preview_is_sandboxed_and_only_the_owners PASSED
tests/test_ai_136.py::test_bundled_mermaid_matches_its_manifest PASSED
tests/test_ai_136.py::test_a_stopped_question_is_marked_for_the_model_until_it_is_answered PASSED
tests/test_ai_136.py::test_stopped_at_is_stored_and_read_back PASSED
tests/test_ai_136.py::test_the_dashboard_follows_the_page_theme PASSED
tests/test_ai_136.py::test_the_answer_may_use_a_quarter_of_the_reported_context PASSED
tests/test_ai_136.py::test_preview_blocks_while_the_answer_is_written PASSED
tests/test_ai_136.py::test_live_preview_is_the_owners_running_answer_only PASSED
tests/test_ai_136.py::test_page_side_of_folding_live_preview_and_the_splitter PASSED
tests/test_ai_136.py::test_markdown_preview_is_escaped_and_follows_the_theme PASSED
tests/test_ai_136.py::test_the_conversation_list_shows_more_on_request PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[*error*-starts with] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[not source:mail-upper case] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[source:$host$-Enterprise] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[source:(mail mg1)-operator inside] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[source:*mail-starts with] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[source:/.*mail.*/i-no flags] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[source:mail AND not user_name:root-upper case] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[source:mg1 and source:mail2-upper case] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[source:mg1 or source:mail2-upper case] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[source_ip:192.0.2.0/24-CIDR] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[user_name:$u$ AND source:mail-Enterprise] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[user_name:(root jason)-operator inside] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[user_name:*ROOT*-starts with] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[user_name:/ROOT/i-no flags] PASSED
tests/test_ai_query_syntax.py::test_measured_wrong_forms_are_refused_with_the_fix[user_name:root OR NOT source:mail-OR NOT] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[*] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[*:*] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[  ] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source:mail] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source:"mail"] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source:mail*] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source:mail.jason.tools] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source:/mail.*/] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[message:/fail.*/] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[user_name:roo?] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source:(mail OR mg1)] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[user_name:(root OR jason)] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source:mail OR source:mg1] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source:mail AND NOT user_name:root] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source:mail -user_name:root] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[user_name:root OR (*:* AND NOT source:mail)] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[_exists_:user_name] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[NOT _exists_:user_name] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[user_name:*] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[http_response_code:[400 TO 499]] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[http_response_code:>=400] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[http_response_code:{200 TO 403]] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source_ip:"192.0.2.68"] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source_ip:192.0.2.*] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source_ip:"10.0.0.0/8"] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[message:"session opened"] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[message:"session opened"~3] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[source:mail~] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[message:"could not and should not"] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[message:"a/b/i"] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[resource:\\/posts\\/45326] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[event_category:authentication AND event_outcome:failure] PASSED
tests/test_ai_query_syntax.py::test_measured_right_forms_pass[user_name:/.*[$]/] PASSED
tests/test_ai_query_syntax.py::test_the_prompt_carries_the_rules_and_the_open_enterprise_difference PASSED
tests/test_ai_query_syntax.py::test_call_tool_refuses_before_graylog_is_asked PASSED
tests/test_alerting.py::test_schedule_value_is_the_current_state PASSED
tests/test_alerting.py::test_add_remove_replace_keep_other_entries_untouched PASSED
tests/test_alerting.py::test_action_validation PASSED
tests/test_alerting.py::test_plan_splits_change_unchanged_skipped PASSED
tests/test_alerting.py::test_title_tags PASSED
tests/test_alerting.py::test_disabled_definitions_stay_disabled PASSED
tests/test_alerting.py::test_a_definition_edited_after_the_preview_is_not_overwritten PASSED
tests/test_alerting.py::test_other_fields_edited_meanwhile_are_kept PASSED
tests/test_alerting.py::test_one_failure_does_not_stop_the_rest_and_is_logged 2026-11-27T01:25:35.393036Z [warning  ] Alerting change failed         definition=b error='Graylog HTTP 500: boom'
PASSED
tests/test_alerting.py::test_expired_signin_stops_the_batch PASSED
tests/test_alerting.py::test_cancel_stops_between_definitions PASSED
tests/test_alerting.py::test_graylog_storing_a_different_state_is_a_failure_not_a_success 2026-11-27T01:25:37.220525Z [warning  ] Graylog changed an event definition's state; putting it back definition=off now=ENABLED was=DISABLED
2026-11-27T01:25:37.227518Z [warning  ] Alerting change failed         definition=off error='Graylog stored something else: state changed DISABLED -> ENABLED'
PASSED
tests/test_alerting.py::test_undo_restores_and_skips_what_was_changed_since PASSED
tests/test_alerting.py::test_a_change_sent_but_never_confirmed_can_still_be_undone PASSED
tests/test_alerting.py::test_client_sends_schedule_matching_state_and_the_whole_body PASSED
tests/test_alerting.py::test_client_maps_401_and_403 PASSED
tests/test_alerting.py::test_paging_reads_every_definition PASSED
tests/test_alerting.py::test_identity_secret_never_goes_into_the_cookie_session PASSED
tests/test_alerting.py::test_expired_identity_is_not_used PASSED
tests/test_alerting.py::test_valid_until_parsing PASSED
tests/test_alerting.py::test_login_keeps_a_graylog_session_not_the_password PASSED
tests/test_alerting.py::test_token_login_keeps_the_token 2026-11-27T01:25:38.741224Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error=no server=log4
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
tests/test_alerting.py::test_a_state_flipped_by_graylog_is_put_back_once 2026-11-27T01:25:42.134450Z [warning  ] Graylog changed an event definition's state; putting it back definition=off now=ENABLED was=DISABLED
PASSED
tests/test_alerting.py::test_an_unknown_state_is_skipped_before_anything_is_written PASSED
tests/test_alerting.py::test_a_failed_row_can_be_undone PASSED
tests/test_alerting.py::test_the_page_offers_undo_for_failed_rows_and_the_routes_check_ids PASSED
tests/test_api_error_handling.py::test_index_sets_catches_401 PASSED
tests/test_api_error_handling.py::test_streams_catches_401 PASSED
tests/test_api_error_handling.py::test_index_sets_catches_connection_error PASSED
tests/test_api_error_handling.py::test_streams_catches_connection_error PASSED
tests/test_api_heap_hint.py::test_estimate_is_about_200_per_second_per_gb[1-200-True] PASSED
tests/test_api_heap_hint.py::test_estimate_is_about_200_per_second_per_gb[1.5-300-True] PASSED
tests/test_api_heap_hint.py::test_estimate_is_about_200_per_second_per_gb[3-600-True] PASSED
tests/test_api_heap_hint.py::test_estimate_is_about_200_per_second_per_gb[3.9-780-True] PASSED
tests/test_api_heap_hint.py::test_estimate_is_about_200_per_second_per_gb[4-800-False] PASSED
tests/test_api_heap_hint.py::test_estimate_is_about_200_per_second_per_gb[8-1600-False] PASSED
tests/test_api_heap_hint.py::test_unknown_heap_gives_no_estimate PASSED
tests/test_api_heap_hint.py::test_a_small_heap_is_reported_with_its_speed PASSED
tests/test_api_heap_hint.py::test_unknown_server_and_unreadable_graylog_show_nothing PASSED
tests/test_api_heap_hint.py::test_api_in_use_follows_the_default_mode_and_api_schedules PASSED
tests/test_api_heap_hint.py::test_dialogs_and_sizing_card_use_the_hint PASSED
tests/test_api_heap_hint.py::test_hint_text_in_every_language PASSED
tests/test_api_heap_hint.py::test_the_sizing_card_is_actually_shown PASSED
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
tests/test_archive_status.py::test_gaps_merge_overlaps_and_skip_short_holes PASSED
tests/test_archive_status.py::test_status_reports_totals_gaps_problems_and_disk PASSED
tests/test_archive_status.py::test_gap_list_is_newest_first_and_capped PASSED
tests/test_archive_status.py::test_jobs_schedules_and_running_eta PASSED
tests/test_archive_status.py::test_empty_db PASSED
tests/test_archive_status.py::test_the_ai_tool_returns_it PASSED
tests/test_archive_status.py::test_eta_matches_the_old_rule PASSED
tests/test_archive_streaming.py::test_streaming_returns_all_messages_incl_tricky_content 2026-11-27T01:25:58.172098Z [info     ] Archive written                messages=1000 path=/tmp/pytest-of-root/pytest-419/test_streaming_returns_all_mes0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.01
PASSED
tests/test_archive_streaming.py::test_empty_and_single 2026-11-27T01:25:58.234548Z [info     ] Archive written                messages=0 path=/tmp/pytest-of-root/pytest-419/test_empty_and_single0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:25:58.237283Z [info     ] Archive written                messages=1 path=/tmp/pytest-of-root/pytest-419/test_empty_and_single0/b/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
PASSED
tests/test_archive_streaming.py::test_batching_shape 2026-11-27T01:25:58.243814Z [info     ] Archive written                messages=105 path=/tmp/pytest-of-root/pytest-419/test_batching_shape0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
PASSED
tests/test_archive_streaming.py::test_memory_is_bounded_not_whole_file 2026-11-27T01:25:59.209934Z [info     ] Archive written                messages=20000 path=/tmp/pytest-of-root/pytest-419/test_memory_is_bounded_not_who0/test/s1/2026/01/01/test_s1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.12
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
tests/test_audit.py::test_cleanup_uses_audit_retention 2026-11-27T01:26:02.089875Z [info     ] No archives to clean up        retention_days=1095
2026-11-27T01:26:02.096742Z [info     ] Cleaned audit records          deleted=1 retention_days=180
2026-11-27T01:26:02.097005Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
2026-11-27T01:26:02.104292Z [info     ] No archives to clean up        retention_days=1095
2026-11-27T01:26:02.104853Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
PASSED
tests/test_audit.py::test_cleanup_audit_no_config 2026-11-27T01:26:02.874225Z [info     ] No archives to clean up        retention_days=1095
2026-11-27T01:26:02.892873Z [info     ] Cleaned audit records          deleted=1 retention_days=180
2026-11-27T01:26:02.893112Z [info     ] Cleanup completed              bytes_freed=0 files_deleted=0
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
tests/test_backpressure_stop.py::test_guard_raises_backpressure_stop_and_does_not_notify 2026-11-27T01:26:52.076710Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
2026-11-27T01:26:52.076871Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 99% (over the hard limit 90%)']
2026-11-27T01:26:52.076979Z [error    ] export stopped — backpressure did not clear signals=['JVM heap 99% (over the hard limit 90%)'] waited_sec=60
PASSED
tests/test_backpressure_stop.py::test_api_stop_ends_the_run_not_the_chunk[manual:api-1] 2026-11-27T01:26:52.555379Z [info     ] Export started                 chunks=3 job_id=j1 time_from='2026-07-01 00:00:00' time_to='2026-07-01 03:00:00'
2026-11-27T01:26:52.564476Z [info     ] Total records to export        streams=None time_from='2026-07-01 00:00:00' time_to='2026-07-01 03:00:00' total=3
2026-11-27T01:26:52.573843Z [info     ] Archive written (streaming)    messages=1 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_api_stop_ends_the_run_not0/arch/s1/all/2026/07/01/s1_all_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:26:52.595559Z [error    ] Export failed                  error='Source load did not drain for over 30 minutes (JVM heap 92%) 1 record(s) were archived in this run before the stop and stay archived; the next run continues from there.' job_id=j1
PASSED
tests/test_backpressure_stop.py::test_api_stop_ends_the_run_not_the_chunk[scheduled:api:auto-export-0] 2026-11-27T01:26:53.222353Z [info     ] Export started                 chunks=3 job_id=j1 time_from='2026-07-01 00:00:00' time_to='2026-07-01 03:00:00'
2026-11-27T01:26:53.234944Z [info     ] Total records to export        streams=None time_from='2026-07-01 00:00:00' time_to='2026-07-01 03:00:00' total=3
2026-11-27T01:26:53.253375Z [info     ] Archive written (streaming)    messages=1 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_api_stop_ends_the_run_not1/arch/s1/all/2026/07/01/s1_all_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:26:53.281713Z [error    ] Export failed                  error='Source load did not drain for over 30 minutes (JVM heap 92%) 1 record(s) were archived in this run before the stop and stay archived; the next run continues from there.' job_id=j1
PASSED
tests/test_backpressure_stop.py::test_os_stop_ends_the_run_not_the_index[manual:opensearch-1] 2026-11-27T01:26:54.110840Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-27T01:26:54.111153Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-27T01:26:54.111322Z [info     ] Found indices                  count=3 prefix=graylog
2026-11-27T01:26:54.111440Z [info     ] Skipping active write index    index=graylog_write
2026-11-27T01:26:54.111937Z [info     ] Index time range               docs=6 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-27T01:26:54.113045Z [info     ] Index time range               docs=6 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 02:59:59' index=graylog_1
2026-11-27T01:26:54.124412Z [info     ] Export plan built              grand_total_docs=12 indices=2 prefixes=1
2026-11-27T01:26:54.125377Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-27T01:26:54.143865Z [error    ] OpenSearch export failed       error='Source load did not drain for over 30 minutes (output buffer rising) 0 record(s) were archived in this run before the stop and stay archived; the next run continues from there.'
PASSED
tests/test_backpressure_stop.py::test_os_stop_ends_the_run_not_the_index[scheduled:opensearch:x-0] 2026-11-27T01:26:54.931186Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-27T01:26:54.931741Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-27T01:26:54.931974Z [info     ] Found indices                  count=3 prefix=graylog
2026-11-27T01:26:54.932207Z [info     ] Skipping active write index    index=graylog_write
2026-11-27T01:26:54.932748Z [info     ] Index time range               docs=6 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-27T01:26:54.933957Z [info     ] Index time range               docs=6 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 02:59:59' index=graylog_1
2026-11-27T01:26:54.942953Z [info     ] Export plan built              grand_total_docs=12 indices=2 prefixes=1
2026-11-27T01:26:54.943490Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-27T01:26:54.963707Z [error    ] OpenSearch export failed       error='Source load did not drain for over 30 minutes (output buffer rising) 0 record(s) were archived in this run before the stop and stay archived; the next run continues from there.'
PASSED
tests/test_backpressure_stop.py::test_scheduler_retries_a_stop_once_after_an_hour_then_notifies_once 2026-11-27T01:26:54.970214Z [warning  ] Scheduled export stopped because the source stayed under load; trying once more later retry_in_min=60 schedule=auto-export
2026-11-27T01:26:54.970428Z [error    ] Scheduled export stopped by backpressure; the next scheduled run continues retried=True schedule=auto-export
PASSED
tests/test_backpressure_stop.py::test_scheduler_late_retry_that_succeeds_sends_nothing 2026-11-27T01:26:54.974172Z [warning  ] Scheduled export stopped because the source stayed under load; trying once more later retry_in_min=60 schedule=auto-export
PASSED
tests/test_backpressure_stop.py::test_scheduler_with_late_retry_disabled_stops_at_once 2026-11-27T01:26:54.977987Z [error    ] Scheduled export stopped by backpressure; the next scheduled run continues retried=False schedule=auto-export
PASSED
tests/test_backpressure_stop.py::test_other_failures_keep_the_quick_retries 2026-11-27T01:26:54.981906Z [warning  ] Scheduled export failed, retrying attempt=1 error='database is locked' max=3 retry_in=60
2026-11-27T01:26:54.982186Z [warning  ] Scheduled export failed, retrying attempt=2 error='database is locked' max=3 retry_in=60
2026-11-27T01:26:54.982339Z [error    ] Scheduled export failed after all retries attempts=3 error='database is locked'
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
tests/test_bulk_streaming.py::test_import_path_never_calls_whole_file_loader 2026-11-27T01:26:55.061214Z [info     ] Bulk import starting           archives=1 batch_docs=50 indices_to_create=1 target_pattern=graylog total_messages=120
2026-11-27T01:26:55.066693Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-11-27T01:26:55.066960Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.0s failed=0 indexed=120 sent=120
PASSED
tests/test_bulk_streaming.py::test_corrupt_archive_does_not_abort_whole_run 2026-11-27T01:26:55.090806Z [info     ] Bulk import starting           archives=2 batch_docs=5 indices_to_create=1 target_pattern=graylog total_messages=11
2026-11-27T01:26:55.093447Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-11-27T01:26:55.093690Z [info     ] Bulk import completed          archives=2 at_destination=-1 duration=0.0s failed=0 indexed=11 sent=11
PASSED
tests/test_bulk_streaming.py::test_bulk_body_capped_by_bytes_not_just_doc_count PASSED
tests/test_bulk_streaming.py::test_single_oversized_doc_still_sent PASSED
tests/test_bulk_streaming.py::test_byte_cap_loses_no_documents 2026-11-27T01:26:55.812792Z [info     ] Bulk import starting           archives=1 batch_docs=10000 indices_to_create=1 target_pattern=graylog total_messages=400
2026-11-27T01:26:56.011729Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-11-27T01:26:56.011933Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.2s failed=0 indexed=400 sent=400
PASSED
tests/test_cleanup_race.py::test_grace_seconds_defined PASSED
tests/test_cleanup_race.py::test_recent_file_skipped PASSED
tests/test_cleanup_race.py::test_old_file_not_skipped PASSED
tests/test_cleanup_schedule_retention.py::test_schedule_retention_days_is_used 2026-11-27T01:26:56.025723Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=200 retention_source=schedule
PASSED
tests/test_cleanup_schedule_retention.py::test_falls_back_to_config_when_schedule_has_none 2026-11-27T01:26:56.034014Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=1095 retention_source=config.yaml
PASSED
tests/test_cleanup_schedule_retention.py::test_bad_config_json_does_not_break_cleanup 2026-11-27T01:26:56.043090Z [warning  ] Could not read the schedule's retention setting; falling back to config.yaml error='Expecting property name enclosed in double quotes: line 1 column 2 (char 1)' schedule=auto-cleanup
2026-11-27T01:26:56.043480Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=1095 retention_source=config.yaml
PASSED
tests/test_cleanup_schedule_retention.py::test_upgrade_does_not_shorten_retention_and_delete_data 2026-11-27T01:26:56.050839Z [warning  ] Cleanup schedule retention set back to retention.retention_days — it is shorter and was not saved by this version, so it may date from before cleanup schedules honoured their own value, and honouring it now could delete archives that version was keeping. Set it again in the Schedules page if the shorter retention is what you want; from then on it is kept. now_in_force=1095 schedule=auto-cleanup was_shown=200
PASSED
tests/test_cleanup_schedule_retention.py::test_longer_stored_retention_is_kept_it_only_retains_more PASSED
tests/test_cleanup_schedule_retention.py::test_equal_values_are_untouched PASSED
tests/test_cleanup_schedule_retention.py::test_schedule_without_retention_is_untouched PASSED
tests/test_cleanup_schedule_retention.py::test_retention_saved_from_the_ui_survives_a_restart 2026-11-27T01:26:56.063982Z [warning  ] Cleanup schedule retention set back to retention.retention_days — it is shorter and was not saved by this version, so it may date from before cleanup schedules honoured their own value, and honouring it now could delete archives that version was keeping. Set it again in the Schedules page if the shorter retention is what you want; from then on it is kept. now_in_force=1095 schedule=auto-cleanup was_shown=150
PASSED
tests/test_cleanup_schedule_retention.py::test_retention_saved_through_the_api_survives_the_startup_reconciliation 2026-11-27T01:26:57.224678Z [info     ] Schedule registered            cron='0 4 1 * *' cron_aps=None name=auto-cleanup type=cleanup
PASSED
tests/test_clear_index_set_route.py::test_list_index_sets_route_returns_200 PASSED
tests/test_clear_index_set_route.py::test_list_falls_back_to_stored_import_defaults PASSED
tests/test_clear_index_set_route.py::test_masked_password_is_reconciled_not_sent_literally PASSED
tests/test_clear_index_set_route.py::test_clear_requires_matching_confirmation PASSED
tests/test_clear_index_set_route.py::test_clear_refuses_internal_index_set_by_id PASSED
tests/test_clear_index_set_route.py::test_clear_happy_path_keeps_the_write_index 2026-11-27T01:27:10.915220Z [warning  ] Cleared index set before import deleted=1 failed=0 index_set=graylog kept_write_index=graylog_2
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
tests/test_contentpack_guard.py::test_consent_is_for_this_mcp_graylog_version PASSED
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
tests/test_datanode.py::test_hosts_come_from_transport_address_and_skip_nodes_not_serving PASSED
tests/test_datanode.py::test_graylog_63_status_field_is_read_too PASSED
tests/test_datanode.py::test_listing_uses_the_endpoint_that_exists PASSED
tests/test_datanode.py::test_principal_is_unique_per_server PASSED
tests/test_datanode.py::test_plain_config_keeps_its_old_behaviour PASSED
tests/test_datanode.py::test_client_cert_sends_no_basic_auth_and_pins_the_ca PASSED
tests/test_datanode.py::test_missing_cert_file_is_a_clear_error PASSED
tests/test_datanode.py::test_cert_expiry_is_read_with_the_stdlib PASSED
tests/test_datanode.py::test_bundle_is_written_private_and_replaced_atomically PASSED
tests/test_datanode.py::test_renewal_starts_a_third_of_the_lifetime_before_expiry PASSED
tests/test_datanode.py::test_a_failed_renewal_keeps_the_working_certificate 2026-11-27T01:27:49.352205Z [warning  ] Data Node client certificate renewal failed error='Graylog down' server=g
PASSED
tests/test_datanode.py::test_only_refusals_a_new_certificate_can_cure_trigger_a_reissue PASSED
tests/test_datanode.py::test_only_certificate_blocks_are_picked_up_for_an_import_target PASSED
tests/test_datanode.py::test_bulk_and_preflight_route_opensearch_calls_through_the_config PASSED
tests/test_datanode.py::test_scheduled_os_run_falls_back_to_the_api_when_the_certificate_fails 2026-11-27T01:27:51.053218Z [info     ] Scheduled export config        days=180 index_set=None initial_from='2026-05-31 01:27:51.053103' mode=opensearch server=g streams=None to='2026-11-27 01:27:51.053103'
2026-11-27T01:27:51.053562Z [error    ] Data Node OpenSearch unusable — this scheduled run uses the Graylog API instead attempts=1 problem="Client error '403 Forbidden'" schedule=nightly server=g waited_sec=0
2026-11-27T01:27:51.053760Z [info     ] No resume point found (API), using full range stream=None
2026-11-27T01:27:51.053865Z [info     ] Scheduled export starting (API) streams=None time_from='2026-05-31 01:27:51.053103' time_to='2026-11-27 01:27:51.053103'
2026-11-27T01:27:51.053986Z [info     ] Scheduled export completed     chunks=0 index_sets_skipped=[] messages=0 skipped=0
PASSED
tests/test_datanode.py::test_daily_renewal_job_is_registered PASSED
tests/test_datanode.py::test_editing_a_server_keeps_its_data_node_certificate PASSED
tests/test_datanode.py::test_connect_refuses_plain_http_and_unknown_servers PASSED
tests/test_datanode.py::test_disconnect_asks_before_turning_os_schedules_into_api_runs 2026-11-27T01:27:54.275666Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=os-a type=export
2026-11-27T01:27:54.332482Z [info     ] Data Node OpenSearch access removed errors=[] server=a
PASSED
tests/test_datanode.py::test_ui_unlocks_os_direct_and_bulk_only_with_data_node_access PASSED
tests/test_datanode.py::test_connection_test_and_capacity_probes_keep_the_certificate PASSED
tests/test_datanode.py::test_issue_falls_back_to_a_single_role_on_graylog_63 PASSED
tests/test_datanode.py::test_two_connects_at_once_do_not_freeze_the_service PASSED
tests/test_datanode.py::test_server_names_that_would_share_a_certificate_are_refused PASSED
tests/test_datanode.py::test_a_replaced_ca_is_cured_by_a_new_certificate_but_a_wrong_hostname_is_not PASSED
tests/test_datanode.py::test_deleting_a_server_with_a_connected_data_node_is_refused PASSED
tests/test_datanode.py::test_a_scheduled_run_whose_block_vanished_uses_the_api PASSED
tests/test_datanode.py::test_an_unreachable_data_node_is_tried_again_after_1_2_and_5_minutes 2026-11-27T01:27:56.352963Z [warning  ] Data Node OpenSearch not reachable — trying again attempt=1 problem='All connection attempts failed' server=g wait_sec=60
2026-11-27T01:27:56.353318Z [warning  ] Data Node OpenSearch not reachable — trying again attempt=2 problem='All connection attempts failed' server=g wait_sec=120
2026-11-27T01:27:56.353559Z [warning  ] Data Node OpenSearch not reachable — trying again attempt=3 problem='All connection attempts failed' server=g wait_sec=300
PASSED
tests/test_datanode.py::test_the_first_success_ends_the_wait 2026-11-27T01:27:56.359264Z [warning  ] Data Node OpenSearch not reachable — trying again attempt=1 problem=ConnectTimeout server=g wait_sec=60
2026-11-27T01:27:56.359489Z [info     ] Data Node OpenSearch reachable again attempts=2 server=g waited_sec=60
PASSED
tests/test_datanode.py::test_a_refused_certificate_is_not_waited_for PASSED
tests/test_datanode.py::test_manual_runs_do_not_wait PASSED
tests/test_datanode.py::test_the_fallback_notification_says_how_long_it_waited PASSED
tests/test_db_rebuild.py::test_rebuild_dry_run 2026-11-27T01:27:57.034599Z [info     ] Would insert                   path=/tmp/tmpx_hoo_ny/archives/server1/2026/01/test.json.gz server=test time_from=2026-01-01T00:00:00Z
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
tests/test_export_busy_visibility.py::test_the_safety_net_never_raises 2026-11-27T01:28:07.328307Z [warning  ] Could not record an unstarted export job error='db down' job=x
PASSED
tests/test_export_cancel_paths.py::test_flag_cancel_mid_index_never_records_a_partial_hour 2026-11-27T01:28:08.711301Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-27T01:28:08.711754Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-27T01:28:08.711946Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-27T01:28:08.713220Z [info     ] Skipping active write index    index=graylog_write
2026-11-27T01:28:08.713707Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-27T01:28:08.743548Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-27T01:28:08.744146Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-27T01:28:08.793199Z [info     ] Archive written (streaming)    messages=4 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_flag_cancel_mid_index_nev0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:08.846692Z [info     ] Chunk exported                 index=graylog_0 messages=4 time_from='2026-07-01 00:00:00'
2026-11-27T01:28:08.870387Z [info     ] Export cancelled by user       job_id=job-1 records_kept=4
2026-11-27T01:28:08.884537Z [info     ] OpenSearch export cancelled    exported=0 job_id=job-1 messages=4 skipped=0
2026-11-27T01:28:08.884932Z [info     ] Completion notification skipped — run was cancelled job_id=job-1
PASSED
tests/test_export_cancel_paths.py::test_the_next_run_resumes_from_the_discarded_hour 2026-11-27T01:28:10.055103Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-27T01:28:10.055450Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-27T01:28:10.055599Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-27T01:28:10.055693Z [info     ] Skipping active write index    index=graylog_write
2026-11-27T01:28:10.056231Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-27T01:28:10.071632Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-27T01:28:10.072389Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-27T01:28:10.089981Z [info     ] Archive written (streaming)    messages=4 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_the_next_run_resumes_from0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:10.108635Z [info     ] Chunk exported                 index=graylog_0 messages=4 time_from='2026-07-01 00:00:00'
2026-11-27T01:28:10.122852Z [info     ] Export cancelled by user       job_id=job-1 records_kept=4
2026-11-27T01:28:10.134360Z [info     ] OpenSearch export cancelled    exported=0 job_id=job-1 messages=4 skipped=0
2026-11-27T01:28:10.134674Z [info     ] Completion notification skipped — run was cancelled job_id=job-1
2026-11-27T01:28:10.147479Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-27T01:28:10.147922Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-27T01:28:10.148190Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-27T01:28:10.148313Z [info     ] Skipping active write index    index=graylog_write
2026-11-27T01:28:10.148813Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-27T01:28:10.165338Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-27T01:28:10.165881Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-27T01:28:10.166458Z [info     ] Excluding already-archived ranges from the scan docs_to_export=12 index=graylog_0 ranges_excluded=1
2026-11-27T01:28:10.190820Z [info     ] Archive written (streaming)    messages=6 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_the_next_run_resumes_from0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T010000Z_20260701T020000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:10.203665Z [info     ] Chunk exported                 index=graylog_0 messages=6 time_from='2026-07-01 01:00:00'
2026-11-27T01:28:10.218319Z [info     ] Archive written (streaming)    messages=2 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_the_next_run_resumes_from0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T020000Z_20260701T030000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:10.225790Z [info     ] Chunk exported                 index=graylog_0 messages=2 time_from='2026-07-01 02:00:00'
2026-11-27T01:28:10.239119Z [info     ] OpenSearch export completed    exported=1 job_id=job-2 messages=8 skipped=0
PASSED
tests/test_export_cancel_paths.py::test_callback_cancel_mid_index_ends_cancelled 2026-11-27T01:28:11.434799Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-27T01:28:11.435243Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-27T01:28:11.435907Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-27T01:28:11.436147Z [info     ] Skipping active write index    index=graylog_write
2026-11-27T01:28:11.437237Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-27T01:28:11.496790Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-27T01:28:11.497543Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-27T01:28:11.515868Z [info     ] Archive written (streaming)    messages=4 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_callback_cancel_mid_index0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:11.528669Z [info     ] Chunk exported                 index=graylog_0 messages=4 time_from='2026-07-01 00:00:00'
2026-11-27T01:28:11.546342Z [info     ] Export cancelled by user       job_id=job-1 records_kept=4
2026-11-27T01:28:11.566385Z [info     ] OpenSearch export cancelled    exported=0 job_id=job-1 messages=4 skipped=0
2026-11-27T01:28:11.566756Z [info     ] Completion notification skipped — run was cancelled job_id=job-1
PASSED
tests/test_export_cancel_paths.py::test_cancel_during_phase_a_count_loop_is_a_cancel_not_a_failure 2026-11-27T01:28:12.470921Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-27T01:28:12.471238Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-27T01:28:12.471393Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-27T01:28:12.471494Z [info     ] Skipping active write index    index=graylog_write
2026-11-27T01:28:12.471894Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-27T01:28:12.481159Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-27T01:28:12.481435Z [info     ] Export cancelled by user       job_id=job-1 records_kept=0
2026-11-27T01:28:12.505634Z [info     ] OpenSearch export cancelled    exported=0 job_id=job-1 messages=0 skipped=0
2026-11-27T01:28:12.506077Z [info     ] Completion notification skipped — run was cancelled job_id=job-1
PASSED
tests/test_export_cancel_paths.py::test_a_normal_run_is_unaffected 2026-11-27T01:28:13.844549Z [info     ] Index sets resolved for export covered=1 prefixes=['graylog'] skipped=[]
2026-11-27T01:28:13.844920Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-27T01:28:13.845171Z [info     ] Found indices                  count=2 prefix=graylog
2026-11-27T01:28:13.845311Z [info     ] Skipping active write index    index=graylog_write
2026-11-27T01:28:13.845697Z [info     ] Index time range               docs=12 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 02:59:59' index=graylog_0
2026-11-27T01:28:13.862390Z [info     ] Export plan built              grand_total_docs=12 indices=1 prefixes=1
2026-11-27T01:28:13.862892Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-27T01:28:13.893480Z [info     ] Archive written (streaming)    messages=4 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_a_normal_run_is_unaffecte0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:13.910876Z [info     ] Chunk exported                 index=graylog_0 messages=4 time_from='2026-07-01 00:00:00'
2026-11-27T01:28:13.968523Z [info     ] Archive written (streaming)    messages=6 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_a_normal_run_is_unaffecte0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T010000Z_20260701T020000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:14.003517Z [info     ] Chunk exported                 index=graylog_0 messages=6 time_from='2026-07-01 01:00:00'
2026-11-27T01:28:14.023435Z [info     ] Archive written (streaming)    messages=2 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_a_normal_run_is_unaffecte0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T020000Z_20260701T030000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:14.053632Z [info     ] Chunk exported                 index=graylog_0 messages=2 time_from='2026-07-01 02:00:00'
2026-11-27T01:28:14.129661Z [info     ] OpenSearch export completed    exported=1 job_id=job-1 messages=12 skipped=0
PASSED
tests/test_export_cancel_paths.py::test_api_flag_cancel_inside_a_chunk_stops_and_ends_cancelled 2026-11-27T01:28:15.668355Z [info     ] Export started                 chunks=1 job_id=job-api time_from='2026-07-01 00:00:00' time_to='2026-07-01 01:00:00'
2026-11-27T01:28:15.689712Z [info     ] Total records to export        streams=None time_from='2026-07-01 00:00:00' time_to='2026-07-01 01:00:00' total=6
2026-11-27T01:28:15.719632Z [info     ] Export cancelled by user       job_id=job-api records_kept=0
2026-11-27T01:28:15.735959Z [info     ] Export cancelled               chunks_exported=0 chunks_skipped=0 job_id=job-api messages_total=0
2026-11-27T01:28:15.736486Z [info     ] Completion notification skipped — run was cancelled job_id=job-api
PASSED
tests/test_export_cancel_paths.py::test_backpressure_pause_honours_cancel 2026-11-27T01:28:15.743198Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 99%']
2026-11-27T01:28:15.755753Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
2026-11-27T01:28:15.766685Z [info     ] export cancelled during backpressure pause waited_sec=0.02
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
tests/test_export_gap_refill.py::test_find_gaps_returns_only_holes_between_archives PASSED
tests/test_export_gap_refill.py::test_find_gaps_ignores_time_before_the_first_archive_and_clips PASSED
tests/test_export_gap_refill.py::test_find_gaps_counts_archives_of_any_stream_and_only_this_server PASSED
tests/test_export_gap_refill.py::test_refill_windows_are_exported_first_in_the_same_job 2026-11-27T01:28:21.470848Z [info     ] Export started                 chunks=3 job_id=j1 time_from='2026-07-01 05:00:00' time_to='2026-07-01 07:00:00'
2026-11-27T01:28:21.500882Z [info     ] Total records to export        streams=None time_from='2026-07-01 05:00:00' time_to='2026-07-01 07:00:00' total=3
2026-11-27T01:28:21.525859Z [info     ] Archive written (streaming)    messages=1 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_refill_windows_are_export0/arch/s1/all/2026/07/01/s1_all_20260701T020000Z_20260701T030000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:21.563258Z [info     ] Archive written (streaming)    messages=1 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_refill_windows_are_export0/arch/s1/all/2026/07/01/s1_all_20260701T050000Z_20260701T060000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:21.585857Z [info     ] Archive written (streaming)    messages=1 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_refill_windows_are_export0/arch/s1/all/2026/07/01/s1_all_20260701T060000Z_20260701T070000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:21.607903Z [info     ] Export completed               chunks_exported=3 chunks_skipped=0 job_id=j1 messages_total=3
PASSED
tests/test_export_gap_refill.py::test_refill_with_no_new_range_still_runs 2026-11-27T01:28:22.352833Z [info     ] Export started                 chunks=1 job_id=j2 time_from='2026-07-01 05:00:00' time_to='2026-07-01 05:00:00'
2026-11-27T01:28:22.362103Z [info     ] Total records to export        streams=None time_from='2026-07-01 05:00:00' time_to='2026-07-01 05:00:00' total=1
2026-11-27T01:28:22.373069Z [info     ] Archive written (streaming)    messages=1 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_refill_with_no_new_range_0/arch/s1/all/2026/07/01/s1_all_20260701T020000Z_20260701T030000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:22.389752Z [info     ] Export completed               chunks_exported=1 chunks_skipped=0 job_id=j2 messages_total=1
PASSED
tests/test_export_gap_refill.py::test_a_failed_chunk_says_what_failed_and_is_refilled_by_the_next_run 2026-11-27T01:28:23.159651Z [info     ] Export started                 chunks=3 job_id=j3 time_from='2026-07-01 00:00:00' time_to='2026-07-01 03:00:00'
2026-11-27T01:28:23.172663Z [info     ] Total records to export        streams=None time_from='2026-07-01 00:00:00' time_to='2026-07-01 03:00:00' total=3
2026-11-27T01:28:23.186083Z [info     ] Archive written (streaming)    messages=1 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_a_failed_chunk_says_what_0/arch/s1/all/2026/07/01/s1_all_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:23.196168Z [error    ] Chunk 2 failed: ReadTimeout    chunk_from='2026-07-01 01:00:00'
2026-11-27T01:28:23.220626Z [info     ] Archive written (streaming)    messages=1 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_a_failed_chunk_says_what_0/arch/s1/all/2026/07/01/s1_all_20260701T020000Z_20260701T030000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:23.261972Z [info     ] Export completed               chunks_exported=2 chunks_skipped=0 job_id=j3 messages_total=2
2026-11-27T01:28:23.315818Z [info     ] Export started                 chunks=1 job_id=j4 time_from='2026-07-01 03:00:00' time_to='2026-07-01 03:00:00'
2026-11-27T01:28:23.367155Z [info     ] Total records to export        streams=None time_from='2026-07-01 03:00:00' time_to='2026-07-01 03:00:00' total=1
2026-11-27T01:28:23.387412Z [info     ] Archive written (streaming)    messages=1 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_a_failed_chunk_says_what_0/arch/s1/all/2026/07/01/s1_all_20260701T010000Z_20260701T020000Z_001.json.gz size_mb=0.00
2026-11-27T01:28:23.430613Z [info     ] Export completed               chunks_exported=1 chunks_skipped=0 job_id=j4 messages_total=1
PASSED
tests/test_export_gap_refill.py::test_exc_text_never_empty PASSED
tests/test_export_gap_refill.py::test_scheduled_api_run_passes_the_holes_behind_the_resume_point 2026-11-27T01:28:24.293746Z [info     ] Scheduled export config        days=180 index_set=None initial_from='2026-05-31 01:28:24.293639' mode=api server=s1 streams=None to='2026-11-27 01:28:24.293639'
2026-11-27T01:28:24.294967Z [info     ] Resume point (API)             resume='2026-11-26 23:00:00' stream=None
2026-11-27T01:28:24.295205Z [info     ] Refilling gaps left by earlier runs gaps=1 windows=['2026-11-26 05:00:00..2026-11-26 06:00:00']
2026-11-27T01:28:24.295304Z [info     ] Scheduled export starting (API) streams=None time_from='2026-11-26 23:00:00' time_to='2026-11-27 01:28:24.293639'
2026-11-27T01:28:24.295403Z [info     ] Scheduled export completed     chunks=0 index_sets_skipped=[] messages=0 skipped=0
PASSED
tests/test_export_gap_refill.py::test_a_hole_reaching_back_past_the_lookback_is_cut_at_its_edge 2026-11-27T01:28:25.084430Z [info     ] Scheduled export config        days=180 index_set=None initial_from='2026-05-31 01:28:25.084315' mode=api server=s1 streams=None to='2026-11-27 01:28:25.084315'
2026-11-27T01:28:25.085969Z [info     ] Resume point (API)             resume='2026-11-26 23:00:00' stream=None
2026-11-27T01:28:25.086185Z [info     ] Refilling gaps left by earlier runs gaps=1 windows=['2026-11-20 01:28:25.084315..2026-11-25 19:00:00']
2026-11-27T01:28:25.086303Z [info     ] Scheduled export starting (API) streams=None time_from='2026-11-26 23:00:00' time_to='2026-11-27 01:28:25.084315'
2026-11-27T01:28:25.086440Z [info     ] Scheduled export completed     chunks=0 index_sets_skipped=[] messages=0 skipped=0
PASSED
tests/test_export_gap_refill.py::test_the_schedule_window_bounds_the_lookback_too 2026-11-27T01:28:25.589751Z [info     ] Scheduled export config        days=1 index_set=None initial_from='2026-11-26 01:28:25.589633' mode=api server=s1 streams=None to='2026-11-27 01:28:25.589633'
2026-11-27T01:28:25.591307Z [info     ] Resume point (API)             resume='2026-11-26 23:00:00' stream=None
2026-11-27T01:28:25.591516Z [info     ] Refilling gaps left by earlier runs gaps=1 windows=['2026-11-26 01:28:25.589633..2026-11-26 15:00:00']
2026-11-27T01:28:25.591643Z [info     ] Scheduled export starting (API) streams=None time_from='2026-11-26 23:00:00' time_to='2026-11-27 01:28:25.589633'
2026-11-27T01:28:25.591791Z [info     ] Scheduled export completed     chunks=0 index_sets_skipped=[] messages=0 skipped=0
PASSED
tests/test_export_gap_refill.py::test_scheduled_api_run_refills_even_when_nothing_new 2026-11-27T01:28:26.409457Z [info     ] Scheduled export config        days=180 index_set=None initial_from='2026-05-31 01:28:26.409308' mode=api server=s1 streams=None to='2026-11-27 01:28:26.409308'
2026-11-27T01:28:26.411364Z [info     ] Resume point (API)             resume='2026-11-27 02:28:26' stream=None
2026-11-27T01:28:26.411675Z [info     ] Refilling gaps left by earlier runs gaps=1 windows=['2026-11-26 20:28:26..2026-11-26 21:28:26']
2026-11-27T01:28:26.411891Z [info     ] Scheduled export starting (API) streams=None time_from='2026-11-27 02:28:26' time_to='2026-11-27 01:28:26.409308'
2026-11-27T01:28:26.412129Z [info     ] Scheduled export completed     chunks=0 index_sets_skipped=[] messages=0 skipped=0
PASSED
tests/test_export_gap_refill.py::test_gap_refill_off_keeps_the_old_behaviour 2026-11-27T01:28:26.939217Z [info     ] Scheduled export config        days=180 index_set=None initial_from='2026-05-31 01:28:26.938995' mode=api server=s1 streams=None to='2026-11-27 01:28:26.938995'
2026-11-27T01:28:26.940652Z [info     ] Resume point (API)             resume='2026-11-26 23:00:00' stream=None
2026-11-27T01:28:26.940886Z [info     ] Scheduled export starting (API) streams=None time_from='2026-11-26 23:00:00' time_to='2026-11-27 01:28:26.938995'
2026-11-27T01:28:26.941105Z [info     ] Scheduled export completed     chunks=0 index_sets_skipped=[] messages=0 skipped=0
PASSED
tests/test_export_gap_refill.py::test_no_holes_means_the_same_call_as_before 2026-11-27T01:28:27.515486Z [info     ] Scheduled export config        days=180 index_set=None initial_from='2026-05-31 01:28:27.515359' mode=api server=s1 streams=None to='2026-11-27 01:28:27.515359'
2026-11-27T01:28:27.517566Z [info     ] Resume point (API)             resume='2026-11-26 23:00:00' stream=None
2026-11-27T01:28:27.517780Z [info     ] Scheduled export starting (API) streams=None time_from='2026-11-26 23:00:00' time_to='2026-11-27 01:28:27.515359'
2026-11-27T01:28:27.517934Z [info     ] Scheduled export completed     chunks=0 index_sets_skipped=[] messages=0 skipped=0
PASSED
tests/test_export_gap_refill.py::test_run_now_uses_the_same_plan_and_refills 2026-11-27T01:28:28.305165Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:28:28.312419Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:28:28.323175Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:28:28.323878Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:28:28.324643Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:28:28.325262Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:28:28.328968Z [info     ] Scheduler started             
2026-11-27T01:28:28.409913Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1'] port=8991
2026-11-27T01:28:28.507633Z [warning  ] Resource cache refresh failed - audit target names will be stale error='All connection attempts failed'
2026-11-27T01:28:28.598837Z [warning  ] Token cache refresh failed - token users will fall back to IP resolution error='All connection attempts failed'
2026-11-27T01:28:28.733770Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=exp type=export
2026-11-27T01:28:28.767574Z [info     ] API Audit listener stopped    
2026-11-27T01:28:28.775082Z [info     ] Scheduler stopped             
PASSED
tests/test_export_pagination.py::test_deep_pagination_no_same_ms_loss_or_dup 2026-11-27T01:28:28.800567Z [info     ] Total messages to fetch        total=6
2026-11-27T01:28:28.801290Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=4 new_from='2024-01-01 00:00:00.003000' old_from='2024-01-01 00:00:00'
PASSED
tests/test_export_pagination.py::test_deep_pagination_multiple_windows 2026-11-27T01:28:28.806834Z [info     ] Total messages to fetch        total=30
2026-11-27T01:28:28.808857Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=6 new_from='2024-01-01 00:00:00.005000' old_from='2024-01-01 00:00:00'
2026-11-27T01:28:28.810815Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=11 new_from='2024-01-01 00:00:00.010000' old_from='2024-01-01 00:00:00.005000'
2026-11-27T01:28:28.812843Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=16 new_from='2024-01-01 00:00:00.015000' old_from='2024-01-01 00:00:00.010000'
2026-11-27T01:28:28.814770Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=21 new_from='2024-01-01 00:00:00.020000' old_from='2024-01-01 00:00:00.015000'
2026-11-27T01:28:28.816807Z [info     ] Advancing time window for deep pagination carry=1 fetched_so_far=26 new_from='2024-01-01 00:00:00.025000' old_from='2024-01-01 00:00:00.020000'
PASSED
tests/test_export_pagination.py::test_pagination_raises_on_unsplittable_ms 2026-11-27T01:28:28.824628Z [info     ] Total messages to fetch        total=10
2026-11-27T01:28:28.826140Z [warning  ] Single-millisecond overflow during API export: more than 4 messages share 2024-01-01T00:00:00.000Z; Graylog's REST API cannot page past it. Kept the first 4, skipping the rest of this millisecond and continuing. Re-run this window in OpenSearch Direct mode to capture them all.
PASSED
tests/test_export_pagination.py::test_overflow_ms_does_not_lose_messages_after_it 2026-11-27T01:28:28.831691Z [info     ] Total messages to fetch        total=12
2026-11-27T01:28:28.833452Z [warning  ] Single-millisecond overflow during API export: more than 4 messages share 2024-01-01T00:00:00.000Z; Graylog's REST API cannot page past it. Kept the first 4, skipping the rest of this millisecond and continuing. Re-run this window in OpenSearch Direct mode to capture them all.
PASSED
tests/test_export_pagination.py::test_fmt_ts_millisecond_precision PASSED
tests/test_export_pagination.py::test_parse_timestamp_robust_fallback PASSED
tests/test_export_pagination.py::test_transient_5xx_fails_over_to_next_host 2026-11-27T01:28:28.856827Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=1 status=503 wait=1
2026-11-27T01:28:28.862213Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=2 status=503 wait=2
2026-11-27T01:28:28.863928Z [warning  ] Transient errors exhausted, failing over to next host host=http://host0:9200 status=503
2026-11-27T01:28:28.866413Z [info     ] Failover to host               host=http://host1:9200
PASSED
tests/test_export_pagination.py::test_all_hosts_transient_raises 2026-11-27T01:28:28.876610Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=1 status=503 wait=1
2026-11-27T01:28:28.878424Z [warning  ] Transient error, retrying      host=http://host0:9200 retry=2 status=503 wait=2
2026-11-27T01:28:28.878642Z [warning  ] Transient errors exhausted, failing over to next host host=http://host0:9200 status=503
2026-11-27T01:28:28.878764Z [warning  ] Transient error, retrying      host=http://host1:9200 retry=1 status=503 wait=1
2026-11-27T01:28:28.878894Z [warning  ] Transient error, retrying      host=http://host1:9200 retry=2 status=503 wait=2
2026-11-27T01:28:28.879021Z [warning  ] Transient errors exhausted, failing over to next host host=http://host1:9200 status=503
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
tests/test_fast_paths_equivalence.py::test_gelf_send_delivers_every_message 2026-11-27T01:28:35.524142Z [info     ] GELF TCP connected             host=127.0.0.1 port=42565
2026-11-27T01:28:35.764945Z [info     ] GELF TCP disconnected          messages_sent=5000
PASSED
tests/test_fast_paths_equivalence.py::test_gelf_closed_connection_is_detected_not_silently_dropped 2026-11-27T01:28:35.972361Z [info     ] GELF TCP connected             host=127.0.0.1 port=40911
PASSED
tests/test_fast_paths_equivalence.py::test_gelf_reset_by_the_target_is_noticed_and_counted 2026-11-27T01:28:35.992797Z [info     ] GELF TCP connected             host=127.0.0.1 port=34325
2026-11-27T01:28:36.418090Z [error    ] Failed to send GELF message    error='[Errno 104] Connection reset by peer' sent=3002
2026-11-27T01:28:36.418407Z [info     ] GELF TCP disconnected          messages_sent=3002
2026-11-27T01:28:36.419930Z [info     ] GELF TCP connected             host=127.0.0.1 port=34325
2026-11-27T01:28:36.420383Z [warning  ] GELF connection lost and re-established; messages in transit at that moment may not have reached the target reconnects=1 sent=3003
2026-11-27T01:28:37.866117Z [info     ] GELF TCP disconnected          messages_sent=12000
PASSED
tests/test_fast_paths_equivalence.py::test_import_without_reconnect_is_verified 2026-11-27T01:28:38.910246Z [info     ] Import started                 archives=1 job_id=j1 total_messages=40
2026-11-27T01:28:38.910599Z [info     ] Preflight passed               duration=0.0s fields=0 fixed=0 rotated=False
2026-11-27T01:28:38.958418Z [info     ] Reconciliation OK: 0 indexer failures — all messages verified at destination failures_after=0 failures_before=0 indexed=40 sent=40
2026-11-27T01:28:38.969251Z [info     ] Import completed               archives=1 job_id=j1 messages=40
PASSED
tests/test_fast_paths_equivalence.py::test_import_with_a_gelf_reconnect_is_not_called_verified 2026-11-27T01:28:39.647965Z [info     ] Import started                 archives=1 job_id=j1 total_messages=40
2026-11-27T01:28:39.648389Z [info     ] Preflight passed               duration=0.0s fields=0 fixed=0 rotated=False
2026-11-27T01:28:39.685234Z [warning  ] The GELF connection to the target was lost 1 time(s) and re-established during this import. Messages that were in transit at that moment may not have reached Graylog, and TCP cannot tell which, so this run is NOT verified even with 0 indexer failures. Check the message count in Graylog for this time range, or re-import with Bulk mode (it de-duplicates by message id). reconnects=1
2026-11-27T01:28:39.693006Z [info     ] Import completed               archives=1 job_id=j1 messages=40
PASSED
tests/test_field_schema.py::test_plain_json_passthrough PASSED
tests/test_field_schema.py::test_zlib_roundtrip PASSED
tests/test_field_schema.py::test_decompress_none PASSED
tests/test_field_schema.py::test_decompress_corrupted PASSED
tests/test_field_schema.py::test_decompress_plain_json PASSED
tests/test_field_schema.py::test_db_field_schema_store_and_read PASSED
tests/test_form_fields.py::test_the_setup_wizard_can_set_a_custom_archive_path PASSED
tests/test_form_fields.py::test_switching_a_server_to_username_and_password_drops_the_token PASSED
tests/test_form_fields.py::test_a_schedule_can_go_back_to_the_default_server 2026-11-27T01:28:43.528487Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=nightly type=export
2026-11-27T01:28:43.558557Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=nightly type=export
2026-11-27T01:28:43.592296Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=nightly type=export
PASSED
tests/test_form_fields.py::test_typed_import_credentials_win_over_the_saved_token PASSED
tests/test_form_fields.py::test_stored_import_secrets_go_only_to_the_stored_url PASSED
tests/test_form_fields.py::test_saving_import_defaults_follows_the_same_rule PASSED
tests/test_form_fields.py::test_every_target_endpoint_uses_the_one_rule PASSED
tests/test_form_fields.py::test_the_security_notification_switch_is_on_the_form PASSED
tests/test_form_fields.py::test_manual_os_export_sends_recent_n_only_when_lowered PASSED
tests/test_form_fields.py::test_an_empty_security_number_box_keeps_the_stored_value PASSED
tests/test_form_fields.py::test_a_manual_export_of_an_unknown_server_is_refused PASSED
tests/test_gelf_cancel_midbatch.py::test_send_batch_stops_mid_batch_on_cancel PASSED
tests/test_gelf_cancel_midbatch.py::test_send_batch_cancel_after_some_messages PASSED
tests/test_gelf_cancel_midbatch.py::test_send_batch_without_cancel_check_sends_all PASSED
tests/test_gelf_cancel_midbatch.py::test_importer_passes_cancel_check_to_sender PASSED
tests/test_graylog_error_detail.py::test_error_detail_extracts_graylog_message PASSED
tests/test_graylog_error_detail.py::test_error_detail_falls_back_to_text_body PASSED
tests/test_graylog_error_detail.py::test_error_detail_handles_empty_body PASSED
tests/test_graylog_flush.py::test_flush_cycles_and_rebuilds_never_deletes 2026-11-27T01:28:47.342357Z [info     ] graylog flush done             actions=['cycle_deflector:ok', 'rebuild_index_ranges:ok'] ok=True
PASSED
tests/test_graylog_flush.py::test_flush_global_deflector_fallback_when_no_index_set 2026-11-27T01:28:47.351203Z [info     ] graylog flush done             actions=['cycle_deflector:ok', 'rebuild_index_ranges:ok'] ok=True
PASSED
tests/test_graylog_flush.py::test_flush_reports_action_error_without_raising 2026-11-27T01:28:47.359902Z [info     ] graylog flush done             actions=['cycle_deflector:error', 'rebuild_index_ranges:ok'] ok=False
PASSED
tests/test_graylog_flush.py::test_snapshot_unreachable_returns_empty_not_raise 2026-11-27T01:28:47.365481Z [warning  ] flush snapshot failed          error=unreachable
PASSED
tests/test_health_endpoint.py::test_health_response_structure PASSED
tests/test_health_endpoint.py::test_health_not_behind_auth PASSED
tests/test_health_guard.py::test_rising_tracker_detects_sustained_climb PASSED
tests/test_health_guard.py::test_rising_tracker_ignores_flat_and_falling PASSED
tests/test_health_guard.py::test_rising_tracker_respects_min_delta PASSED
tests/test_health_guard.py::test_tripped_failsafe_on_unreachable PASSED
tests/test_health_guard.py::test_heap_hard_tier_trips_immediately 2026-11-27T01:28:47.386440Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard.py::test_heap_soft_tier_needs_sustained 2026-11-27T01:28:47.388727Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard.py::test_heap_soft_streak_resets_on_dip 2026-11-27T01:28:47.391260Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard.py::test_tripped_on_rising_journal 2026-11-27T01:28:47.393553Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard.py::test_pause_then_resume 2026-11-27T01:28:47.396418Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
2026-11-27T01:28:47.396622Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 95% (over the hard limit 90%)']
2026-11-27T01:28:47.396783Z [info     ] export resumed — backpressure cleared waited_sec=1
PASSED
tests/test_health_guard.py::test_pause_times_out_and_raises 2026-11-27T01:28:47.400404Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
2026-11-27T01:28:47.400796Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 99% (over the hard limit 90%)']
2026-11-27T01:28:47.401038Z [error    ] export stopped — backpressure did not clear signals=['JVM heap 99% (over the hard limit 90%)'] waited_sec=60
PASSED
tests/test_health_guard_gc.py::test_healthy_sawtooth_never_pauses_on_gc_signal 2026-11-27T01:28:47.404507Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_same_sawtooth_did_pause_on_used_percent 2026-11-27T01:28:47.407639Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard_gc.py::test_full_gc_trips_immediately 2026-11-27T01:28:47.410673Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_heap_full_right_after_gc_trips_on_first_reading 2026-11-27T01:28:47.413205Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_heap_exhausting_load_trips 2026-11-27T01:28:47.415516Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_gc_time_share_must_be_sustained 2026-11-27T01:28:47.417857Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_graylog_restart_resets_counters_without_tripping 2026-11-27T01:28:47.420559Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_missing_gc_metrics_fall_back_to_used_percent 2026-11-27T01:28:47.423193Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard_gc.py::test_gc_mode_still_watches_journal_and_buffers 2026-11-27T01:28:47.425681Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_pause_on_full_gc_resumes_once_collections_stop 2026-11-27T01:28:47.428722Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-27T01:28:47.430007Z [warning  ] export paused — Graylog backpressure signals=['1 full garbage collection(s) in the last 15s (Graylog heap exhausted)']
2026-11-27T01:28:47.430319Z [info     ] export resumed — backpressure cleared waited_sec=15
PASSED
tests/test_health_guard_gc.py::test_gc_signals_from_a_real_g1_response PASSED
tests/test_health_guard_gc.py::test_gc_signals_parallel_gc_uses_the_old_pool_max PASSED
tests/test_health_guard_gc.py::test_gc_signals_absent_means_none PASSED
tests/test_health_guard_gc.py::test_get_health_requests_the_gc_metrics PASSED
tests/test_health_guard_gc.py::test_pace_delay_rises_with_heap_after_gc[40-0.0] 2026-11-27T01:28:47.444635Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_pace_delay_rises_with_heap_after_gc[70-0.0] 2026-11-27T01:28:47.447657Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
PASSED
tests/test_health_guard_gc.py::test_pace_delay_rises_with_heap_after_gc[80-2.5] 2026-11-27T01:28:47.450758Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-27T01:28:47.450974Z [info     ] export pacing adjusted         delay_per_page_sec=2.5 heap_after_gc_pct=80
PASSED
tests/test_health_guard_gc.py::test_pace_delay_rises_with_heap_after_gc[85-3.75] 2026-11-27T01:28:47.453875Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-27T01:28:47.454114Z [info     ] export pacing adjusted         delay_per_page_sec=3.75 heap_after_gc_pct=85
PASSED
tests/test_health_guard_gc.py::test_pace_delay_rises_with_heap_after_gc[95-5.0] 2026-11-27T01:28:47.457032Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-27T01:28:47.457231Z [info     ] export pacing adjusted         delay_per_page_sec=5.0 heap_after_gc_pct=95
PASSED
tests/test_health_guard_gc.py::test_no_pacing_without_gc_metrics_or_for_opensearch_direct 2026-11-27T01:28:47.459550Z [info     ] Graylog heap pressure judged from heap used % heap_signal=used
PASSED
tests/test_health_guard_gc.py::test_pacing_relaxes_when_heap_recovers 2026-11-27T01:28:47.461918Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-27T01:28:47.462131Z [info     ] export pacing adjusted         delay_per_page_sec=4.0 heap_after_gc_pct=86
2026-11-27T01:28:47.462278Z [info     ] export pacing adjusted         delay_per_page_sec=0.0 heap_after_gc_pct=60
PASSED
tests/test_health_guard_gc.py::test_checkpoint_applies_the_pace_between_pages 2026-11-27T01:28:47.465202Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-27T01:28:47.465899Z [info     ] export pacing adjusted         delay_per_page_sec=2.5 heap_after_gc_pct=80
PASSED
tests/test_health_guard_gc.py::test_heap_bound_pause_releases_expired_searches_and_resumes 2026-11-27T01:28:47.471119Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-27T01:28:47.471384Z [info     ] export pacing adjusted         delay_per_page_sec=5.0 heap_after_gc_pct=92.0
2026-11-27T01:28:47.471519Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 92% still in use right after garbage collection (limit 90%)']
2026-11-27T01:28:47.472479Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=315
2026-11-27T01:28:47.472682Z [info     ] export resumed — backpressure cleared waited_sec=315
PASSED
tests/test_health_guard_gc.py::test_release_is_repeated_at_most_once_a_minute 2026-11-27T01:28:47.476734Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-27T01:28:47.476947Z [warning  ] export paused — Graylog backpressure signals=['JVM heap 92% still in use right after garbage collection (limit 90%)']
2026-11-27T01:28:47.477829Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=315
2026-11-27T01:28:47.478147Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=375
2026-11-27T01:28:47.478438Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=435
2026-11-27T01:28:47.478715Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=495
2026-11-27T01:28:47.478987Z [info     ] asked Graylog to release expired search results searches=8 waited_sec=555
2026-11-27T01:28:47.479324Z [error    ] export stopped — backpressure did not clear signals=['JVM heap 92% still in use right after garbage collection (limit 90%)'] waited_sec=600
PASSED
tests/test_health_guard_gc.py::test_journal_pause_does_not_send_searches 2026-11-27T01:28:47.483210Z [info     ] Graylog heap pressure judged from garbage-collector metrics heap_signal=gc
2026-11-27T01:28:47.483948Z [warning  ] export paused — Graylog backpressure signals=['disk journal backlog rising (1,000)']
2026-11-27T01:28:47.485624Z [error    ] export stopped — backpressure did not clear signals=['disk journal backlog rising (1,000)'] waited_sec=600
PASSED
tests/test_health_guard_gc.py::test_release_expired_searches_sends_small_searches PASSED
tests/test_health_guard_gc.py::test_release_expired_searches_stops_on_error 2026-11-27T01:28:47.492659Z [warning  ] Search to release Graylog's expired search results failed error='connection refused'
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
tests/test_import_batch_flow.py::test_web_ui_flow_control_batch_and_rate_are_preserved 2026-11-27T01:28:48.847642Z [info     ] No archives to import         
PASSED
tests/test_import_batch_flow.py::test_no_flow_control_captures_config_defaults 2026-11-27T01:28:49.413336Z [info     ] No archives to import         
PASSED
tests/test_import_batch_flow.py::test_seeding_is_guarded_in_source PASSED
tests/test_import_jvm_throttle.py::test_ring_buffer_is_the_early_signal PASSED
tests/test_import_jvm_throttle.py::test_buffer_pause_beats_low_journal PASSED
tests/test_import_jvm_throttle.py::test_heap_alone_triggers_slow_then_pause PASSED
tests/test_import_jvm_throttle.py::test_journal_alone_still_works PASSED
tests/test_import_jvm_throttle.py::test_most_severe_signal_wins PASSED
tests/test_import_jvm_throttle.py::test_unknown_heap_is_ignored PASSED
tests/test_import_jvm_throttle.py::test_monitoring_disabled_is_normal PASSED
tests/test_import_jvm_throttle.py::test_failed_check_before_ever_working_does_not_deadlock 2026-11-27T01:28:49.450094Z [warning  ] Journal endpoint unreachable; import proceeds at user rate without journal throttling error=404
PASSED
tests/test_import_jvm_throttle.py::test_failed_check_after_working_is_failsafe_pause 2026-11-27T01:28:49.451564Z [warning  ] Journal check failed mid-import (target unreachable/stuck) — pausing until it recovers error=timeout
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
tests/test_index_cleaner.py::test_rotates_before_deleting_and_keeps_the_new_write_index 2026-11-27T01:28:52.508402Z [warning  ] Cleared index set before import deleted=2 failed=0 index_set=graylog kept_write_index=graylog_9
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
tests/test_index_set_coverage.py::test_restricting_reports_skipped_index_sets 2026-11-27T01:28:55.585428Z [warning  ] Index sets NOT covered by this OpenSearch export — their logs will NOT be archived and will be lost when Graylog retention deletes them covered=['graylog'] skipped=['PVE Hosts', 'Wazuh']
PASSED
tests/test_index_set_coverage.py::test_explicit_prefix_skips_api_lookup PASSED
tests/test_index_set_coverage.py::test_index_sets_without_prefix_are_ignored PASSED
tests/test_index_set_coverage.py::test_graylog_internal_event_sets_are_not_a_coverage_gap 2026-11-27T01:28:55.629691Z [info     ] Graylog-internal event index sets not selected (no ingested logs) internal=['Graylog Events', 'Graylog System Events']
PASSED
tests/test_index_set_coverage.py::test_a_real_log_set_left_out_still_warns_beside_internal_ones 2026-11-27T01:28:55.648879Z [info     ] Graylog-internal event index sets not selected (no ingested logs) internal=['Graylog Events', 'Graylog System Events']
2026-11-27T01:28:55.649171Z [warning  ] Index sets NOT covered by this OpenSearch export — their logs will NOT be archived and will be lost when Graylog retention deletes them covered=['graylog'] skipped=['PVE Hosts', 'Wazuh']
PASSED
tests/test_index_set_coverage.py::test_internal_prefix_rule_matches_the_clear_guard PASSED
tests/test_index_set_coverage.py::test_job_note_and_result_for_internal_only_omission PASSED
tests/test_index_set_coverage.py::test_coverage_chip_is_green_when_only_internal_sets_are_left_out PASSED
tests/test_index_set_coverage.py::test_job_result_json_round_trips PASSED
tests/test_indexer_failure_autofix.py::test_parse_failure_message_extracts_field_and_reason PASSED
tests/test_indexer_failure_autofix.py::test_parse_failure_rejects_log_prefix_tokens PASSED
tests/test_indexer_failure_autofix.py::test_get_indexer_failure_details_aggregates_fields PASSED
tests/test_indexer_failure_autofix.py::test_remediate_pins_fields_and_cycles_never_deletes 2026-11-27T01:28:56.619933Z [info     ] Custom mappings applied        failed=0 ok=2 total=2
2026-11-27T01:28:56.620942Z [info     ] Auto-remediated indexer-failure fields as string fields=['Keywords', 'foo'] index_set=idx1
PASSED
tests/test_indexer_failure_autofix.py::test_iterator_metadata_fallback_degrades_not_crashes PASSED
tests/test_indexer_failure_autofix.py::test_long_overflow_numeric_tracked_as_string PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_pins_new_fields_on_rise 2026-11-27T01:28:56.658354Z [warning  ] Mid-import auto-remediation applied failures_delta=5 fields=['Keywords']
PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_noop_when_no_rise PASSED
tests/test_inline_remediation.py::test_mid_import_remediate_skips_already_pinned_field PASSED
tests/test_inline_remediation.py::test_bulk_inline_remediation_resends_failed_docs 2026-11-27T01:28:56.701689Z [info     ] Bulk import starting           archives=1 batch_docs=10000 indices_to_create=1 target_pattern=jt_restored total_messages=2
2026-11-27T01:28:56.702378Z [info     ] Bulk re-sent failed docs after remediation fields=['Keywords'] reindexed=1 resent=1 still_failed=0
2026-11-27T01:28:56.702825Z [warning  ] Could not verify documents at the destination error="'_C' object has no attribute 'post'"
2026-11-27T01:28:56.702976Z [info     ] Bulk import completed          archives=1 at_destination=-1 duration=0.0s failed=0 indexed=2 sent=2
PASSED
tests/test_inline_remediation.py::test_check_capacity_uses_measured_override PASSED
tests/test_inline_remediation.py::test_capacity_abort_is_overridable PASSED
tests/test_inline_remediation.py::test_import_job_persists_retry_config 2026-11-27T01:28:57.535601Z [info     ] No archives to import         
PASSED
tests/test_integration.py::test_cross_conflict_actual_os_mapping PASSED
tests/test_integration.py::test_field_schema_zlib_in_preflight PASSED
tests/test_integration.py::test_timezone_dedup_correctness PASSED
tests/test_integration.py::test_timezone_retention_correctness PASSED
tests/test_integration.py::test_archive_write_read_integrity 2026-11-27T01:29:00.281509Z [info     ] Archive written                messages=50 path=/tmp/tmprbu8rj1f/test/stream1/2026/01/01/test_stream1_20260101T000000Z_20260101T010000Z_001.json.gz size_mb=0.00
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
tests/test_integrity.py::test_verifier_flags_tampered 2026-11-27T01:29:04.068996Z [info     ] Verification started           total_archives=1
2026-11-27T01:29:04.070263Z [error    ] TAMPERED archive (HMAC mismatch) archive_id=1 path=/tmp/pytest-of-root/pytest-419/test_verifier_flags_tampered0/a.json.gz
2026-11-27T01:29:04.080948Z [info     ] Verification completed         corrupted=0 missing=0 orphans=0 tampered=1 total=1 valid=0
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
tests/test_login_identity.py::test_a_restart_signs_out_a_graylog_login_only PASSED
tests/test_login_identity.py::test_login_signs_in_on_every_server_that_knows_the_account 2026-11-27T01:29:21.155628Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:21.161640Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:21.168692Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:21.169548Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:21.170144Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:21.170925Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:21.173240Z [info     ] Scheduler started             
2026-11-27T01:29:21.177141Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a', 'gl-b', 'gl-c'] port=8991
2026-11-27T01:29:21.211929Z [info     ] This account is not signed in on another Graylog server error='Graylog rejected the username or password' server=c
2026-11-27T01:29:21.262179Z [info     ] API Audit listener stopped    
2026-11-27T01:29:21.276355Z [info     ] Scheduler stopped             
PASSED
tests/test_login_identity.py::test_after_a_restart_the_login_page_comes_back 2026-11-27T01:29:22.549847Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:22.555729Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:22.562014Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:22.563074Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:22.564070Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:22.564896Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:22.567224Z [info     ] Scheduler started             
2026-11-27T01:29:22.570366Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a', 'gl-b', 'gl-c'] port=8991
2026-11-27T01:29:22.692643Z [info     ] API Audit listener stopped    
2026-11-27T01:29:22.710005Z [info     ] Scheduler stopped             
PASSED
tests/test_login_identity.py::test_ai_models_lists_from_the_form_without_leaking_the_key 2026-11-27T01:29:23.616713Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:23.624723Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:23.634545Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:23.635391Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:23.636518Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:23.637142Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:23.639671Z [info     ] Scheduler started             
2026-11-27T01:29:23.643635Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a', 'gl-b', 'gl-c'] port=8991
2026-11-27T01:29:23.811280Z [info     ] API Audit listener stopped    
2026-11-27T01:29:23.824640Z [info     ] Scheduler stopped             
PASSED
tests/test_login_identity.py::test_the_model_is_picked_from_a_list PASSED
tests/test_login_roles.py::test_reader_is_refused_and_gets_no_session 2026-11-27T01:29:24.539933Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:24.547509Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:24.554613Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:24.555633Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:24.559288Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:24.560055Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:24.562492Z [info     ] Scheduler started             
2026-11-27T01:29:24.565183Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-27T01:29:24.614332Z [warning  ] Graylog login refused: no role allowed to use jt-glogarch allowed=['Admin'] reason='no allowed role' roles=['Reader'] server=a user=reader1
2026-11-27T01:29:24.635761Z [info     ] API Audit listener stopped    
2026-11-27T01:29:24.653284Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_admin_role_signs_in 2026-11-27T01:29:25.498159Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:25.521229Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:25.575533Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:25.576494Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:25.577152Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:25.577691Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:25.579707Z [info     ] Scheduler started             
2026-11-27T01:29:25.581901Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-27T01:29:25.618695Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=a
2026-11-27T01:29:25.652448Z [info     ] API Audit listener stopped    
2026-11-27T01:29:25.680481Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_star_permission_signs_in_without_the_admin_role 2026-11-27T01:29:26.675361Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:26.694335Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:26.714899Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:26.716298Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:26.717460Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:26.718432Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:26.721496Z [info     ] Scheduler started             
2026-11-27T01:29:26.724041Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-27T01:29:26.764953Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=a
2026-11-27T01:29:26.788794Z [info     ] API Audit listener stopped    
2026-11-27T01:29:26.802298Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_a_role_added_in_config_signs_in 2026-11-27T01:29:27.750026Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:27.763433Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:27.772359Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:27.773212Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:27.773846Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:27.774430Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:27.776969Z [info     ] Scheduler started             
2026-11-27T01:29:27.779102Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-27T01:29:27.806163Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=a
2026-11-27T01:29:27.827839Z [info     ] API Audit listener stopped    
2026-11-27T01:29:27.839599Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_star_in_config_restores_the_old_behaviour 2026-11-27T01:29:29.065909Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:29.073425Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:29.079709Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:29.080520Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:29.081062Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:29.081466Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:29.083507Z [info     ] Scheduler started             
2026-11-27T01:29:29.085492Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-27T01:29:29.113843Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=a
2026-11-27T01:29:29.134920Z [info     ] API Audit listener stopped    
2026-11-27T01:29:29.150756Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_token_login_is_checked_and_shows_the_owner 2026-11-27T01:29:29.949847Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:29.959578Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:29.968893Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:29.969754Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:29.970452Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:29.970889Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:29.973109Z [info     ] Scheduler started             
2026-11-27T01:29:29.974999Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-27T01:29:30.009038Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=a
2026-11-27T01:29:30.030261Z [info     ] API Audit listener stopped    
2026-11-27T01:29:30.043592Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_roles_that_cannot_be_read_refuse_the_login 2026-11-27T01:29:30.912880Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:30.924990Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:30.935865Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:30.936734Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:30.937337Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:30.937782Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:30.939682Z [info     ] Scheduler started             
2026-11-27T01:29:30.941851Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-27T01:29:30.979438Z [warning  ] Graylog login refused: no role allowed to use jt-glogarch allowed=['Admin'] reason='user name not readable (sessions HTTP 500)' roles=[] server=a user=admin
2026-11-27T01:29:30.987743Z [info     ] API Audit listener stopped    
2026-11-27T01:29:31.002914Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_admin_on_a_second_server_signs_in 2026-11-27T01:29:31.797067Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:31.815670Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:31.827439Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:31.829081Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:31.830045Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:31.830735Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:31.833914Z [info     ] Scheduler started             
2026-11-27T01:29:31.837431Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a', 'gl-b'] port=8991
2026-11-27T01:29:31.887539Z [warning  ] Graylog login refused: no role allowed to use jt-glogarch allowed=['Admin'] reason='no allowed role' roles=['Reader'] server=a user=reader1
2026-11-27T01:29:31.893215Z [info     ] No Graylog session for this login (token login, or sessions unavailable) error='not in this test' server=b
2026-11-27T01:29:31.894516Z [info     ] This account is not signed in on another Graylog server error='not in this test' server=a
2026-11-27T01:29:31.959214Z [info     ] API Audit listener stopped    
2026-11-27T01:29:31.978465Z [info     ] Scheduler stopped             
PASSED
tests/test_login_roles.py::test_localadmin_still_signs_in 2026-11-27T01:29:32.799564Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:32.811018Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:32.825090Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:32.826025Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:32.827090Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:32.827721Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:32.830032Z [info     ] Scheduler started             
2026-11-27T01:29:32.832215Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1', 'gl-a'] port=8991
2026-11-27T01:29:32.882757Z [info     ] API Audit listener stopped    
2026-11-27T01:29:32.897264Z [info     ] Scheduler stopped             
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
tests/test_multi_admin_guards.py::test_clearing_keep_indices_on_edit_actually_clears_it 2026-11-27T01:29:36.347686Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=os type=export
2026-11-27T01:29:36.381641Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=os type=export
PASSED
tests/test_multi_admin_guards.py::test_run_now_export_is_refused_while_an_export_of_that_server_runs 2026-11-27T01:29:37.524877Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=exp type=export
PASSED
tests/test_multi_admin_guards.py::test_run_now_cleanup_runs_in_background_with_the_schedules_retention 2026-11-27T01:29:38.357163Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:29:38.364057Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:29:38.369833Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:29:38.370707Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:29:38.371389Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:29:38.371956Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:29:38.374470Z [info     ] Scheduler started             
2026-11-27T01:29:38.374631Z [info     ] API Audit disabled            
2026-11-27T01:29:38.430443Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=cln type=cleanup
2026-11-27T01:29:38.532262Z [info     ] Scheduled cleanup completed    bytes_freed=0 files_deleted=0 retention_days=1500 retention_source=schedule
2026-11-27T01:29:38.593484Z [info     ] API Audit listener stopped    
2026-11-27T01:29:38.603826Z [info     ] Scheduler stopped             
PASSED
tests/test_multi_admin_guards.py::test_audit_toggle_with_a_stale_desired_state_changes_nothing PASSED
tests/test_multi_admin_guards.py::test_deleting_a_server_still_used_by_a_schedule_is_refused 2026-11-27T01:29:40.393080Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=exp-b type=export
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
tests/test_notify_links.py::test_the_address_is_a_bare_origin[-] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://192.0.2.10:8990/-https://192.0.2.10:8990] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[http://jt.example-http://jt.example] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[ftp://x-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://u:p@h-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://h/x-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://h?a=1-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[javascript:alert(1)-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://h x-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://h#-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://h?-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://h:abc-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://h:99999-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://h"x-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://h<x-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://h|x-None] PASSED
tests/test_notify_links.py::test_the_address_is_a_bare_origin[https://[2001:db8::1]:8990-https://[2001:db8::1]:8990] PASSED
tests/test_notify_links.py::test_each_incident_links_to_itself_when_an_address_is_set PASSED
tests/test_notify_links.py::test_no_address_no_links PASSED
tests/test_notify_links.py::test_email_turns_only_our_own_links_into_links PASSED
tests/test_notify_links.py::test_link_reads_the_saved_address PASSED
tests/test_notify_links.py::test_settings_store_the_language_and_the_address PASSED
tests/test_notify_links.py::test_the_runner_passes_the_incident_id_and_the_page_opens_it PASSED
tests/test_notify_links.py::test_a_link_opened_while_signed_out_comes_back_after_login PASSED
tests/test_notify_links.py::test_after_login_only_goes_to_a_page_of_this_site[/security?incident=7-/security?incident=7] PASSED
tests/test_notify_links.py::test_after_login_only_goes_to_a_page_of_this_site[//evil.example/x-/] PASSED
tests/test_notify_links.py::test_after_login_only_goes_to_a_page_of_this_site[https://evil.example-/] PASSED
tests/test_notify_links.py::test_after_login_only_goes_to_a_page_of_this_site[/\\evil.example-/] PASSED
tests/test_notify_links.py::test_after_login_only_goes_to_a_page_of_this_site[/logout-/] PASSED
tests/test_notify_links.py::test_after_login_only_goes_to_a_page_of_this_site[/x\ny-/] PASSED
tests/test_notify_links.py::test_after_login_only_goes_to_a_page_of_this_site[-/] PASSED
tests/test_notify_links.py::test_after_login_only_goes_to_a_page_of_this_site[None-/] PASSED
tests/test_notify_links.py::test_after_login_only_goes_to_a_page_of_this_site[/a"onfocus=x-/a"onfocus=x] PASSED
tests/test_notify_links.py::test_the_next_field_is_escaped_in_the_form PASSED
tests/test_notify_links.py::test_a_new_login_starts_without_the_previous_users_graylog_identities PASSED
tests/test_notify_rich.py::test_telegram_rich_escapes_and_formats PASSED
tests/test_notify_rich.py::test_non_rich_messages_keep_the_aligned_block PASSED
tests/test_notify_rich.py::test_security_notifications_are_rich_and_unindented PASSED
tests/test_notify_rich.py::test_incident_says_who_reported_it_where_and_what_the_waf_did PASSED
tests/test_notify_rich.py::test_rich_renderers_bold_only_our_headings_and_labels PASSED
tests/test_notify_rich.py::test_email_rich_body_is_paragraphs PASSED
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
tests/test_notify_zulip.py::test_zulip_text_cannot_format_mention_or_link PASSED
tests/test_notify_zulip.py::test_zulip_long_line_and_full_width_labels PASSED
tests/test_notify_zulip.py::test_zulip_rich_keeps_code_spans_and_escapes_the_rest PASSED
tests/test_notify_zulip.py::test_zulip_gets_rich_from_the_channel_list PASSED
tests/test_notify_zulip.py::test_every_path_goes_through_one_channel_list 2026-11-27T01:29:48.142016Z [info     ] Notification sent              channel=zulip notify_event=error
PASSED
tests/test_notify_zulip.py::test_settings_api_masks_the_key_and_keeps_it_when_saved_masked PASSED
tests/test_notify_zulip.py::test_settings_api_refuses_a_link_local_zulip_url PASSED
tests/test_opensearch_client.py::test_search_sort_uses_doc_not_id PASSED
tests/test_opensearch_multicluster.py::test_status_reports_per_server_vs_global PASSED
tests/test_opensearch_multicluster.py::test_reorder_is_server_aware PASSED
tests/test_opensearch_multicluster.py::test_reorder_without_server_touches_global PASSED
tests/test_os_export_multiprefix.py::test_denominator_is_grand_total_across_prefixes 2026-11-27T01:29:53.856734Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-11-27T01:29:53.857086Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-27T01:29:53.857283Z [info     ] Found indices                  count=3 prefix=graylog
2026-11-27T01:29:53.857408Z [info     ] Skipping active write index    index=graylog_write
2026-11-27T01:29:53.857877Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-11-27T01:29:53.858927Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-11-27T01:29:53.859358Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-11-27T01:29:53.859504Z [info     ] Found indices                  count=2 prefix=noise_38
2026-11-27T01:29:53.859612Z [info     ] Skipping active write index    index=noise_38_write
2026-11-27T01:29:53.860059Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-11-27T01:29:53.867061Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-11-27T01:29:53.867626Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-27T01:29:53.879478Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_denominator_is_grand_tota0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:29:53.893102Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-11-27T01:29:53.893620Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-11-27T01:29:53.906393Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_denominator_is_grand_tota0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:29:53.913477Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-11-27T01:29:53.914129Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-11-27T01:29:53.924421Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_denominator_is_grand_tota0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:29:53.932290Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-11-27T01:29:53.941056Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_multiprefix.py::test_progress_never_exceeds_total 2026-11-27T01:29:54.577900Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-11-27T01:29:54.578354Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-27T01:29:54.578586Z [info     ] Found indices                  count=3 prefix=graylog
2026-11-27T01:29:54.578758Z [info     ] Skipping active write index    index=graylog_write
2026-11-27T01:29:54.579418Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-11-27T01:29:54.580654Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-11-27T01:29:54.581201Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-11-27T01:29:54.581407Z [info     ] Found indices                  count=2 prefix=noise_38
2026-11-27T01:29:54.581530Z [info     ] Skipping active write index    index=noise_38_write
2026-11-27T01:29:54.581912Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-11-27T01:29:54.588260Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-11-27T01:29:54.588797Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-27T01:29:54.602056Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_progress_never_exceeds_to0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:29:54.612462Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-11-27T01:29:54.613117Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-11-27T01:29:54.623226Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_progress_never_exceeds_to0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:29:54.634335Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-11-27T01:29:54.634896Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-11-27T01:29:54.644359Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_progress_never_exceeds_to0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:29:54.654977Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-11-27T01:29:54.661134Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_multiprefix.py::test_denominator_is_stable_no_regression 2026-11-27T01:29:55.270530Z [info     ] Index sets resolved for export covered=2 prefixes=['graylog', 'noise_38'] skipped=[]
2026-11-27T01:29:55.270917Z [info     ] Active write index             active=graylog_write prefix=graylog
2026-11-27T01:29:55.271211Z [info     ] Found indices                  count=3 prefix=graylog
2026-11-27T01:29:55.271446Z [info     ] Skipping active write index    index=graylog_write
2026-11-27T01:29:55.272297Z [info     ] Index time range               docs=20 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_0
2026-11-27T01:29:55.273650Z [info     ] Index time range               docs=10 idx_from='2026-07-01 00:00:00' idx_to='2026-07-01 00:59:59' index=graylog_1
2026-11-27T01:29:55.274148Z [info     ] Active write index             active=noise_38_write prefix=noise_38
2026-11-27T01:29:55.274327Z [info     ] Found indices                  count=2 prefix=noise_38
2026-11-27T01:29:55.274466Z [info     ] Skipping active write index    index=noise_38_write
2026-11-27T01:29:55.274853Z [info     ] Index time range               docs=5 idx_from='2026-07-02 00:00:00' idx_to='2026-07-02 00:59:59' index=noise_38_0
2026-11-27T01:29:55.282675Z [info     ] Export plan built              grand_total_docs=35 indices=3 prefixes=2
2026-11-27T01:29:55.283257Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_0
2026-11-27T01:29:55.301032Z [info     ] Archive written (streaming)    messages=20 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_denominator_is_stable_no_0/arch/s1/graylog_0/2026/07/01/s1_graylog_0_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:29:55.310448Z [info     ] Chunk exported                 index=graylog_0 messages=20 time_from='2026-07-01 00:00:00'
2026-11-27T01:29:55.311130Z [info     ] Single-scan export starting    batch_size=10000 index=graylog_1
2026-11-27T01:29:55.323968Z [info     ] Archive written (streaming)    messages=10 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_denominator_is_stable_no_0/arch/s1/graylog_1/2026/07/01/s1_graylog_1_20260701T000000Z_20260701T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:29:55.331583Z [info     ] Chunk exported                 index=graylog_1 messages=10 time_from='2026-07-01 00:00:00'
2026-11-27T01:29:55.332185Z [info     ] Single-scan export starting    batch_size=10000 index=noise_38_0
2026-11-27T01:29:55.342050Z [info     ] Archive written (streaming)    messages=5 original_mb=0.00 path=/tmp/pytest-of-root/pytest-419/test_denominator_is_stable_no_0/arch/s1/noise_38_0/2026/07/02/s1_noise_38_0_20260702T000000Z_20260702T010000Z_001.json.gz size_mb=0.00
2026-11-27T01:29:55.350653Z [info     ] Chunk exported                 index=noise_38_0 messages=5 time_from='2026-07-02 00:00:00'
2026-11-27T01:29:55.358229Z [info     ] OpenSearch export completed    exported=3 job_id=job-mp-1 messages=35 skipped=0
PASSED
tests/test_os_export_progress.py::test_denominator_is_accumulated_not_reset_per_prefix PASSED
tests/test_os_export_progress.py::test_update_job_uses_grand_total_not_prefix_total PASSED
tests/test_os_export_progress.py::test_denominator_is_stable_two_phase PASSED
tests/test_os_export_progress.py::test_grand_total_initialised_before_prefix_loop PASSED
tests/test_os_page_sizing.py::test_wide_docs_shrink_the_page 2026-11-27T01:29:55.388363Z [info     ] Fetching from index            index=idx shards=1 total=25000
2026-11-27T01:29:56.800690Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9130 index=idx page_size=1837 was=10000
2026-11-27T01:29:58.372816Z [info     ] Index fetch completed          fetched=25000 index=idx shards=1
PASSED
tests/test_os_page_sizing.py::test_typical_docs_keep_full_page 2026-11-27T01:29:58.379031Z [info     ] Fetching from index            index=idx shards=1 total=25000
2026-11-27T01:29:59.252079Z [info     ] Index fetch completed          fetched=25000 index=idx shards=1
PASSED
tests/test_os_page_sizing.py::test_adaptation_never_below_floor 2026-11-27T01:29:59.264813Z [info     ] Fetching from index            index=idx shards=1 total=3000
2026-11-27T01:30:06.356563Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=120130 index=idx page_size=500 was=10000
2026-11-27T01:30:06.373767Z [info     ] Index fetch completed          fetched=3000 index=idx shards=1
PASSED
tests/test_os_page_sizing.py::test_adaptation_does_not_raise 2026-11-27T01:30:06.418858Z [info     ] Fetching from index            index=idx shards=1 total=12000
2026-11-27T01:30:08.013255Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9130 index=idx page_size=1837 was=10000
2026-11-27T01:30:08.414349Z [info     ] Index fetch completed          fetched=12000 index=idx shards=1
PASSED
tests/test_os_scan_reconcile.py::test_short_scan_raises_instead_of_reporting_success 2026-11-27T01:30:08.435692Z [info     ] Fetching from index            index=idx shards=1 total=8
2026-11-27T01:30:08.436910Z [error    ] Index scan returned fewer documents than the index reported. The chunks already written are valid, but this index is NOT completely archived for this run. expected=8 fetched=5 index=idx missing=3 per_shard=None shards=1
PASSED
tests/test_os_scan_reconcile.py::test_the_error_names_the_shard_count_when_it_can 2026-11-27T01:30:08.446770Z [info     ] Fetching from index            index=idx shards=4 total=8
2026-11-27T01:30:08.448419Z [error    ] Index scan returned fewer documents than the index reported. The chunks already written are valid, but this index is NOT completely archived for this run. expected=8 fetched=5 index=idx missing=3 per_shard={0: 5} shards=4
PASSED
tests/test_os_scan_reconcile.py::test_a_complete_scan_does_not_raise 2026-11-27T01:30:08.464642Z [info     ] Fetching from index            index=idx shards=1 total=16
2026-11-27T01:30:08.465487Z [info     ] Index fetch completed          fetched=16 index=idx shards=1
PASSED
tests/test_os_scan_reconcile.py::test_reading_more_than_counted_is_not_an_error 2026-11-27T01:30:08.474571Z [info     ] Fetching from index            index=idx shards=1 total=11
2026-11-27T01:30:08.475083Z [info     ] Index held more documents than the pre-scan count counted=11 fetched=14 index=idx
2026-11-27T01:30:08.475281Z [info     ] Index fetch completed          fetched=14 index=idx shards=1
PASSED
tests/test_os_scan_reconcile.py::test_an_intentional_early_stop_is_never_reported_as_loss 2026-11-27T01:30:08.482100Z [info     ] Fetching from index            index=idx shards=1 total=30
PASSED
tests/test_os_scan_reconcile.py::test_an_empty_index_is_not_a_short_scan PASSED
tests/test_os_shard_scan.py::test_the_old_single_cursor_really_did_drop_records 2026-11-27T01:30:08.497288Z [info     ] Fetching from index            index=idx shards=1 total=24
2026-11-27T01:30:08.498452Z [error    ] Index scan returned fewer documents than the index reported. The chunks already written are valid, but this index is NOT completely archived for this run. expected=24 fetched=22 index=idx missing=2 per_shard=None shards=1
PASSED
tests/test_os_shard_scan.py::test_per_shard_scan_returns_every_document 2026-11-27T01:30:08.505224Z [info     ] Fetching from index            index=idx shards=4 total=24
2026-11-27T01:30:08.508264Z [info     ] Index fetch completed          fetched=24 index=idx shards=4
PASSED
tests/test_os_shard_scan.py::test_merged_output_is_in_global_timestamp_order 2026-11-27T01:30:08.514491Z [info     ] Fetching from index            index=idx shards=4 total=24
2026-11-27T01:30:08.517240Z [info     ] Index fetch completed          fetched=24 index=idx shards=4
PASSED
tests/test_os_shard_scan.py::test_every_shard_request_pins_the_primary_copy 2026-11-27T01:30:08.523422Z [info     ] Fetching from index            index=idx shards=4 total=24
2026-11-27T01:30:08.525459Z [info     ] Index fetch completed          fetched=24 index=idx shards=4
PASSED
tests/test_os_shard_scan.py::test_bytes_in_flight_stay_within_the_single_page_budget 2026-11-27T01:30:08.532904Z [info     ] Fetching from index            index=idx shards=4 total=1600
2026-11-27T01:30:08.537549Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9068 index=idx page_size=231 was=2500
2026-11-27T01:30:08.539480Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9068 index=idx page_size=231 was=2500
2026-11-27T01:30:08.541374Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9068 index=idx page_size=231 was=2500
2026-11-27T01:30:08.543421Z [info     ] Reducing OpenSearch page size for wide documents avg_doc_bytes=9068 index=idx page_size=231 was=2500
2026-11-27T01:30:08.565407Z [info     ] Index fetch completed          fetched=1600 index=idx shards=4
PASSED
tests/test_os_shard_scan.py::test_no_prefetch_outlives_a_cancelled_scan 2026-11-27T01:30:08.574105Z [info     ] Fetching from index            index=idx shards=4 total=800
PASSED
tests/test_os_shard_scan.py::test_a_single_shard_index_is_scanned_exactly_as_before 2026-11-27T01:30:08.636821Z [info     ] Fetching from index            index=idx shards=1 total=9
2026-11-27T01:30:08.637319Z [info     ] Index fetch completed          fetched=9 index=idx shards=1
PASSED
tests/test_os_shard_scan.py::test_an_intentional_early_stop_is_never_reported_as_loss 2026-11-27T01:30:08.643268Z [info     ] Fetching from index            index=idx shards=4 total=24
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
tests/test_overflow_holes.py::test_the_hole_reaches_both_dedup_rules_from_one_place 2026-11-27T01:30:14.316584Z [warning  ] Could not read archived ids for an overflow hole — that millisecond will be refilled whole error="[Errno 2] No such file or directory: 'a.json.gz'" ms=2026-09-09T08:25:02.000Z path=a.json.gz
PASSED
tests/test_overflow_holes.py::test_an_os_archive_of_the_hour_closes_the_hole PASSED
tests/test_overflow_holes.py::test_multiple_and_out_of_range_overflows PASSED
tests/test_overflow_holes.py::test_truncation_record_carries_the_count 2026-11-27T01:30:17.785340Z [info     ] Total messages to fetch        total=14
2026-11-27T01:30:17.787662Z [info     ] Advancing time window for deep pagination carry=4 fetched_so_far=4 new_from='2026-09-09 08:25:02' old_from='2026-09-09 08:25:00'
2026-11-27T01:30:17.791116Z [warning  ] Single-millisecond overflow during API export: more than 4 messages share 2026-09-09T08:25:02.000Z; Graylog's REST API cannot page past it. Kept the first 4, skipping the rest of this millisecond and continuing. Re-run this window in OpenSearch Direct mode to capture them all.
PASSED
tests/test_overflow_holes.py::test_the_refill_excludes_ids_the_api_archive_already_holds 2026-11-27T01:30:19.357372Z [info     ] Overflow hole: excluding already-archived ids ids=3 ms=2026-09-09T08:25:02.000Z
PASSED
tests/test_overflow_holes.py::test_an_unreadable_archive_degrades_to_the_range_refill 2026-11-27T01:30:21.489440Z [warning  ] Could not read archived ids for an overflow hole — that millisecond will be refilled whole error="[Errno 2] No such file or directory: '/tmp/pytest-of-root/pytest-419/test_an_unreadable_archive_deg0/missing.json.gz'" ms=2026-09-09T08:25:02.000Z path=/tmp/pytest-of-root/pytest-419/test_an_unreadable_archive_deg0/missing.json.gz
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
tests/test_pack_guide.py::test_library_notes_are_found_and_bad_ones_are_harmless 2026-11-27T01:30:21.713308Z [warning  ] Unreadable guide notes in the library error='Expecting value: line 1 column 1 (char 0)' path=/tmp/pytest-of-root/pytest-419/test_library_notes_are_found_a0/guide-notes.i18n
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
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[linux-auditd] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[mail_zimbra_pmg] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[netflow] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[pfsense_opnsense] PASSED
tests/test_pack_guide.py::test_every_real_pack_gets_a_complete_guide_in_every_language[samba] PASSED
tests/test_packs.py::test_real_packs_are_understood[mail_zimbra_pmg-119-98-1-1-1-18] PASSED
tests/test_packs.py::test_real_packs_are_understood[pfsense_opnsense-59-54-3-0-2-0] PASSED
tests/test_packs.py::test_real_packs_are_understood[samba-43-35-1-1-1-5] PASSED
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
tests/test_packs.py::test_junk_in_the_library_is_ignored 2026-11-27T01:30:25.464243Z [warning  ] Unreadable file in the content pack library error='Expecting property name enclosed in double quotes: line 1 column 2 (char 1)' path=/tmp/pytest-of-root/pytest-419/test_junk_in_the_library_is_ig0/local/bad.json
2026-11-27T01:30:25.464808Z [warning  ] Not a valid content pack, ignored path=/tmp/pytest-of-root/pytest-419/test_junk_in_the_library_is_ig0/local/notpack.json
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
tests/test_perf_covered_ranges.py::test_jobs_table_has_a_polling_index_and_prune 2026-11-27T01:30:38.774490Z [info     ] Pruned old job-history rows    deleted=2 keep_days=365
PASSED
tests/test_phone_layout.py::test_the_phone_block_is_last_in_the_stylesheet_loaded_last PASSED
tests/test_phone_layout.py::test_the_phone_check_is_in_the_repo_and_the_checklist PASSED
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
tests/test_preflight_conflicts.py::TestFieldLimitAutoRaise::test_template_body_carries_the_computed_limit 2026-11-27T01:30:38.903734Z [info     ] Field limit applied to existing indices limit=30518 pattern=jt_restored_*
2026-11-27T01:30:38.904176Z [info     ] Bulk index template installed  pattern=jt_restored_* pinned_fields=1 template=jt_restored_template
PASSED
tests/test_preflight_conflicts.py::TestFieldLimitAutoRaise::test_rejected_limit_is_doubled_once_not_aborted 2026-11-27T01:30:38.914184Z [warning  ] Template rejected at field limit — retrying doubled limit=10000 retry=20000 template=jt_restored_template
2026-11-27T01:30:38.916661Z [info     ] Field limit applied to existing indices limit=20000 pattern=jt_restored_*
2026-11-27T01:30:38.916979Z [info     ] Bulk index template installed  pattern=jt_restored_* pinned_fields=1 template=jt_restored_template
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
tests/test_report_progress.py::test_progress_never_goes_backwards_across_dashboards 2026-11-27T01:30:55.953897Z [info     ] Report generated               by=manual bytes=42220 emailed=False report=p
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
tests/test_reports_enabled.py::test_the_switch_turns_the_schedule_off_and_on PASSED
tests/test_reports_enabled.py::test_unknown_report_and_bad_value PASSED
tests/test_reports_enabled.py::test_a_save_without_the_state_keeps_it PASSED
tests/test_reports_enabled.py::test_the_list_has_the_switch_and_no_beta PASSED
tests/test_reports_poll.py::test_the_reports_page_polls_its_lists PASSED
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
tests/test_sbom.py::test_parse_requirement_extras_and_gate PASSED
tests/test_sbom.py::test_closure_follows_extras_skips_dev_and_absent PASSED
tests/test_sbom.py::test_closure_drops_requirements_whose_marker_does_not_hold PASSED
tests/test_sbom.py::test_missing_root_is_an_error_not_an_empty_sbom PASSED
tests/test_sbom.py::test_license_of[kw0-expected0] PASSED
tests/test_sbom.py::test_license_of[kw1-expected1] PASSED
tests/test_sbom.py::test_license_of[kw2-expected2] PASSED
tests/test_sbom.py::test_license_of[kw3-expected3] PASSED
tests/test_sbom.py::test_license_of[kw4-expected4] PASSED
tests/test_sbom.py::test_license_of[kw5-expected5] PASSED
tests/test_sbom.py::test_wheel_mode_lists_every_wheel_with_its_sha256_and_the_browser PASSED
tests/test_sbom.py::test_vendored_files_are_listed PASSED
tests/test_sbom.py::test_cyclonedx_shape_and_no_host_details PASSED
tests/test_sbom.py::test_cli_and_module_write_valid_json PASSED
tests/test_sbom.py::test_release_sbom_matches_this_version_and_lists_every_dependency PASSED
tests/test_sbom.py::test_offline_bundle_refuses_to_ship_without_an_sbom PASSED
tests/test_sbom.py::test_release_gate_generates_the_sbom PASSED
tests/test_schedule_lock_skip.py::test_a_long_export_that_is_advancing_never_alerts 2026-11-27T01:31:06.218802Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=518394098 records_total=11579254477 schedule=auto-export skipped_in_a_row=1
2026-11-27T01:31:06.220268Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=527094098 records_total=11579254477 schedule=auto-export skipped_in_a_row=2
2026-11-27T01:31:06.221209Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=535794098 records_total=11579254477 schedule=auto-export skipped_in_a_row=3
2026-11-27T01:31:06.221995Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=544494098 records_total=11579254477 schedule=auto-export skipped_in_a_row=4
2026-11-27T01:31:06.222733Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=553194098 records_total=11579254477 schedule=auto-export skipped_in_a_row=5
2026-11-27T01:31:06.223484Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=561894098 records_total=11579254477 schedule=auto-export skipped_in_a_row=6
2026-11-27T01:31:06.224358Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=570594098 records_total=11579254477 schedule=auto-export skipped_in_a_row=7
2026-11-27T01:31:06.225084Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=579294098 records_total=11579254477 schedule=auto-export skipped_in_a_row=8
2026-11-27T01:31:06.225782Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=587994098 records_total=11579254477 schedule=auto-export skipped_in_a_row=9
2026-11-27T01:31:06.226785Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=596694098 records_total=11579254477 schedule=auto-export skipped_in_a_row=10
PASSED
tests/test_schedule_lock_skip.py::test_stale_lock_with_no_running_export_alerts 2026-11-27T01:31:06.230122Z [error    ] Scheduled export skipped 1 run(s) in a row and NO export is running — the per-server lock is stale and this schedule has stopped archiving. Restart jt-glogarch to clear it. error='Export already running' schedule=auto-export
2026-11-27T01:31:06.231235Z [error    ] Scheduled export skipped 2 run(s) in a row and NO export is running — the per-server lock is stale and this schedule has stopped archiving. Restart jt-glogarch to clear it. error='Export already running' schedule=auto-export
PASSED
tests/test_schedule_lock_skip.py::test_a_running_export_that_stops_advancing_alerts_differently 2026-11-27T01:31:06.234062Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=509694098 records_total=11579254477 schedule=auto-export skipped_in_a_row=1
2026-11-27T01:31:06.235169Z [error    ] Scheduled export skipped 2 run(s) and the running export has not advanced across 1 of them (still 509,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
2026-11-27T01:31:06.236320Z [error    ] Scheduled export skipped 3 run(s) and the running export has not advanced across 2 of them (still 509,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
2026-11-27T01:31:06.237144Z [error    ] Scheduled export skipped 4 run(s) and the running export has not advanced across 3 of them (still 509,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
PASSED
tests/test_schedule_lock_skip.py::test_progress_resuming_clears_the_stalled_state 2026-11-27T01:31:06.240890Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=509694098 records_total=11579254477 schedule=auto-export skipped_in_a_row=1
2026-11-27T01:31:06.242163Z [error    ] Scheduled export skipped 2 run(s) and the running export has not advanced across 1 of them (still 509,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
2026-11-27T01:31:06.243276Z [info     ] Previous export still running and advancing, skipping this scheduled run job=54184933 records_done=514694098 records_total=11579254477 schedule=auto-export skipped_in_a_row=3
2026-11-27T01:31:06.244467Z [error    ] Scheduled export skipped 4 run(s) and the running export has not advanced across 1 of them (still 514,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
2026-11-27T01:31:06.245575Z [error    ] Scheduled export skipped 5 run(s) and the running export has not advanced across 2 of them (still 514,694,098 records) — it may be wedged. job=54184933 schedule=auto-export
PASSED
tests/test_schedule_lock_skip.py::test_working_export_message_never_says_nothing_is_archived PASSED
tests/test_schedule_lock_skip.py::test_stale_lock_message_tells_the_operator_to_restart PASSED
tests/test_schedule_overlap_guard.py::test_a_second_schedule_is_not_blocked_by_the_first PASSED
tests/test_schedule_overlap_guard.py::test_the_same_schedule_still_does_not_overlap_itself 2026-11-27T01:31:06.325004Z [info     ] This export schedule is still running, skipping this run schedule=auto-export
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
tests/test_search_api.py::test_full_lifecycle_and_resume 2026-11-27T01:31:09.295292Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-27T01:31:09.297640Z [info     ] Archive search finished        cancelled=False examined=25 hits=7 parsed=1 scanned=0 seconds=0.0 truncated=True
2026-11-27T01:31:09.347318Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-27T01:31:09.351769Z [info     ] Archive search finished        cancelled=False examined=53 hits=7 parsed=2 scanned=1 seconds=0.0 truncated=True
2026-11-27T01:31:09.398686Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-27T01:31:09.402127Z [info     ] Archive search finished        cancelled=False examined=41 hits=7 parsed=2 scanned=2 seconds=0.0 truncated=True
2026-11-27T01:31:09.452462Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-27T01:31:09.456343Z [info     ] Archive search finished        cancelled=False examined=29 hits=7 parsed=1 scanned=2 seconds=0.0 truncated=True
2026-11-27T01:31:09.506085Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-27T01:31:09.508794Z [info     ] Archive search finished        cancelled=False examined=40 hits=2 parsed=1 scanned=3 seconds=0.0 truncated=False
PASSED
tests/test_search_api.py::test_more_is_refused_while_still_running PASSED
tests/test_search_api.py::test_more_is_refused_once_the_range_is_exhausted 2026-11-27T01:31:09.577654Z [info     ] Archive search starting        archives=1 filters=0 terms=1
2026-11-27T01:31:09.580489Z [info     ] Archive search finished        cancelled=False examined=10 hits=5 parsed=1 scanned=1 seconds=0.0 truncated=False
PASSED
tests/test_search_api.py::test_retained_hits_are_capped 2026-11-27T01:31:09.641419Z [info     ] Archive search starting        archives=1 filters=0 terms=1
2026-11-27T01:31:09.644393Z [info     ] Archive search finished        cancelled=False examined=10 hits=10 parsed=1 scanned=1 seconds=0.0 truncated=False
PASSED
tests/test_search_api.py::test_unknown_search_is_404_not_a_crash PASSED
tests/test_search_api.py::test_old_searches_are_pruned PASSED
tests/test_search_api.py::test_search_yields_to_a_running_export PASSED
tests/test_search_api.py::test_the_backend_refuses_a_rangeless_search_even_if_the_button_is_bypassed PASSED
tests/test_search_api.py::test_plan_also_refuses_without_a_range PASSED
tests/test_search_api.py::test_every_refusal_carries_a_translatable_code PASSED
tests/test_search_api.py::test_archive_total_is_known_before_the_first_poll 2026-11-27T01:31:09.731006Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-27T01:31:09.739457Z [info     ] Archive search finished        cancelled=False examined=40 hits=8 parsed=4 scanned=4 seconds=0.0 truncated=False
PASSED
tests/test_search_api.py::test_every_error_code_has_a_translation_in_both_languages PASSED
tests/test_search_api.py::test_a_quoted_phrase_is_one_term PASSED
tests/test_search_api.py::test_an_unbalanced_quote_is_not_an_error PASSED
tests/test_search_api.py::test_a_quoted_phrase_still_survives_the_byte_prefilter PASSED
tests/test_search_api.py::test_export_covers_every_page_not_just_the_first 2026-11-27T01:31:09.808787Z [info     ] Archive search (streaming) starting archives=3
2026-11-27T01:31:09.814496Z [info     ] Search export finished         fmt=csv rows=30 truncated=False
PASSED
tests/test_search_api.py::test_export_and_the_paged_screen_agree_on_what_matches 2026-11-27T01:31:09.823686Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-27T01:31:09.828983Z [info     ] Archive search finished        cancelled=False examined=120 hits=30 parsed=3 scanned=3 seconds=0.0 truncated=False
2026-11-27T01:31:09.829414Z [info     ] Archive search (streaming) starting archives=3
PASSED
tests/test_search_api.py::test_export_reads_each_archive_exactly_once 2026-11-27T01:31:09.843553Z [info     ] Archive search (streaming) starting archives=3
2026-11-27T01:31:09.849364Z [info     ] Search export finished         fmt=jsonl rows=30 truncated=False
PASSED
tests/test_search_api.py::test_export_streams_rather_than_building_the_file 2026-11-27T01:31:09.859386Z [info     ] Archive search (streaming) starting archives=3
2026-11-27T01:31:09.865233Z [info     ] Search export finished         fmt=jsonl rows=30 truncated=False
PASSED
tests/test_search_api.py::test_export_truncation_is_marked_in_the_file 2026-11-27T01:31:09.874455Z [info     ] Archive search (streaming) starting archives=3
2026-11-27T01:31:09.876452Z [warning  ] Search export hit the row ceiling rows=5
2026-11-27T01:31:09.876702Z [info     ] Search export finished         fmt=csv rows=5 truncated=True
2026-11-27T01:31:09.877050Z [info     ] Archive search (streaming) starting archives=3
2026-11-27T01:31:09.878884Z [warning  ] Search export hit the row ceiling rows=5
2026-11-27T01:31:09.879096Z [info     ] Search export finished         fmt=jsonl rows=5 truncated=True
PASSED
tests/test_search_api.py::test_csv_starts_with_a_bom_and_a_header 2026-11-27T01:31:09.886268Z [info     ] Archive search (streaming) starting archives=1
2026-11-27T01:31:09.888204Z [info     ] Search export finished         fmt=csv rows=2 truncated=False
PASSED
tests/test_search_api.py::test_jsonl_keeps_every_field_and_names_its_archive 2026-11-27T01:31:09.895252Z [info     ] Archive search (streaming) starting archives=1
2026-11-27T01:31:09.897126Z [info     ] Search export finished         fmt=jsonl rows=2 truncated=False
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
tests/test_search_engine.py::test_prefilter_treats_an_unreadable_archive_as_a_candidate 2026-11-27T01:31:10.426711Z [warning  ] Search prefilter failed, parsing the archive anyway error="Not a gzipped file (b'th')" path=/tmp/pytest-of-root/pytest-419/test_prefilter_treats_an_unrea0/broken.json.gz
PASSED
tests/test_search_engine.py::test_terms_are_anded_and_match_any_field PASSED
tests/test_search_engine.py::test_field_filter_is_exact_not_substring PASSED
tests/test_search_engine.py::test_field_filter_on_a_missing_field_does_not_match PASSED
tests/test_search_engine.py::test_search_collects_only_matching_messages PASSED
tests/test_search_engine.py::test_a_non_matching_archive_is_never_parsed PASSED
tests/test_search_engine.py::test_missing_file_is_reported_not_silently_skipped PASSED
tests/test_search_engine.py::test_paging_returns_every_hit_exactly_once 2026-11-27T01:31:10.479246Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-27T01:31:10.481755Z [info     ] Archive search finished        cancelled=False examined=31 hits=7 parsed=1 scanned=0 seconds=0.0 truncated=True
2026-11-27T01:31:10.482217Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-27T01:31:10.486899Z [info     ] Archive search finished        cancelled=False examined=66 hits=7 parsed=2 scanned=1 seconds=0.0 truncated=True
2026-11-27T01:31:10.487533Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-27T01:31:10.491475Z [info     ] Archive search finished        cancelled=False examined=51 hits=7 parsed=2 scanned=2 seconds=0.0 truncated=True
2026-11-27T01:31:10.491753Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-27T01:31:10.493360Z [info     ] Archive search finished        cancelled=False examined=36 hits=7 parsed=1 scanned=2 seconds=0.0 truncated=True
2026-11-27T01:31:10.493617Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-27T01:31:10.496752Z [info     ] Archive search finished        cancelled=False examined=71 hits=7 parsed=2 scanned=3 seconds=0.0 truncated=True
2026-11-27T01:31:10.496973Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-27T01:31:10.498072Z [info     ] Archive search finished        cancelled=False examined=50 hits=5 parsed=1 scanned=4 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_an_exhausted_range_reports_no_next_page 2026-11-27T01:31:10.503745Z [info     ] Archive search starting        archives=2 filters=0 terms=1
2026-11-27T01:31:10.506238Z [info     ] Archive search finished        cancelled=False examined=20 hits=4 parsed=2 scanned=2 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_a_full_page_reports_a_next_page 2026-11-27T01:31:10.513667Z [info     ] Archive search starting        archives=2 filters=0 terms=1
2026-11-27T01:31:10.515671Z [info     ] Archive search finished        cancelled=False examined=21 hits=5 parsed=1 scanned=0 seconds=0.0 truncated=True
PASSED
tests/test_search_engine.py::test_resuming_does_not_rescan_earlier_archives 2026-11-27T01:31:10.528226Z [info     ] Archive search starting        archives=6 filters=0 terms=1
2026-11-27T01:31:10.531388Z [info     ] Archive search finished        cancelled=False examined=56 hits=12 parsed=2 scanned=1 seconds=0.0 truncated=True
2026-11-27T01:31:10.531669Z [info     ] Archive search starting        archives=6 filters=0 terms=1
2026-11-27T01:31:10.534601Z [info     ] Archive search finished        cancelled=False examined=66 hits=12 parsed=2 scanned=2 seconds=0.0 truncated=True
PASSED
tests/test_search_engine.py::test_cancel_stops_and_keeps_a_resume_point 2026-11-27T01:31:10.543210Z [info     ] Archive search starting        archives=5 filters=0 terms=1
2026-11-27T01:31:10.544648Z [info     ] Archive search finished        cancelled=True examined=50 hits=10 parsed=1 scanned=1 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_field_only_query_needs_no_terms 2026-11-27T01:31:10.550031Z [info     ] Archive search starting        archives=2 filters=1 terms=0
2026-11-27T01:31:10.551541Z [info     ] Archive search finished        cancelled=False examined=40 hits=40 parsed=2 scanned=2 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_progress_is_reported_per_archive 2026-11-27T01:31:10.557946Z [info     ] Archive search starting        archives=4 filters=0 terms=1
2026-11-27T01:31:10.563152Z [info     ] Archive search finished        cancelled=False examined=80 hits=16 parsed=4 scanned=4 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_search_yields_between_archives 2026-11-27T01:31:10.570264Z [info     ] Archive search starting        archives=3 filters=0 terms=1
2026-11-27T01:31:10.573190Z [info     ] Archive search finished        cancelled=False examined=30 hits=6 parsed=3 scanned=3 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_the_total_is_known_before_any_archive_is_opened 2026-11-27T01:31:10.580364Z [info     ] Archive search starting        archives=5 filters=0 terms=1
2026-11-27T01:31:10.585949Z [info     ] Archive search finished        cancelled=False examined=100 hits=20 parsed=5 scanned=5 seconds=0.0 truncated=False
PASSED
tests/test_search_engine.py::test_hits_are_published_while_a_single_archive_is_still_being_parsed PASSED
tests/test_search_engine.py::test_intra_archive_reporting_is_time_throttled PASSED
tests/test_security.py::test_ssrf_blocks_cloud_metadata_and_link_local PASSED
tests/test_security.py::test_ssrf_allows_loopback_and_private PASSED
tests/test_security.py::test_ssrf_handles_bad_input PASSED
tests/test_security.py::test_docs_endpoints_disabled PASSED
tests/test_security_ai.py::test_parse_analysis_validates_and_normalises PASSED
tests/test_security_ai.py::test_unverified_addresses_are_the_ones_the_evidence_never_names PASSED
tests/test_security_ai.py::test_incident_window_is_capped_to_a_day PASSED
tests/test_security_ai.py::test_auto_candidates_new_or_escalated_highest_first_capped PASSED
tests/test_security_ai.py::test_server_ctx_uses_the_detector_connection PASSED
tests/test_security_ai.py::test_evidence_queries_are_fixed_and_scoped PASSED
tests/test_security_ai.py::test_analysis_falls_back_through_response_formats_and_stores_no_messages 2026-11-27T01:31:12.736224Z [info     ] LLM refused a response format; trying the next error='HTTP 400' format=json_schema
PASSED
tests/test_security_ai.py::test_unusable_answer_is_asked_again_then_recorded_as_failed 2026-11-27T01:31:13.310621Z [warning  ] Incident AI analysis failed    error='The model did not return a usable analysis' incident=1
PASSED
tests/test_security_ai.py::test_llm_down_or_budget_used_records_an_error_row 2026-11-27T01:31:13.976823Z [warning  ] Incident AI analysis failed    error='LLM server unreachable (ConnectError)' incident=1
2026-11-27T01:31:13.996194Z [warning  ] Incident AI analysis failed    error='Daily AI token budget used up (500 of 100)' incident=1
PASSED
tests/test_security_ai.py::test_invented_address_is_flagged PASSED
tests/test_security_ai.py::test_analyses_go_with_their_incident PASSED
tests/test_security_ai.py::test_auto_analysis_needs_both_switches_and_stops_on_failure PASSED
tests/test_security_ai.py::test_defaults_are_off PASSED
tests/test_security_ai.py::test_api_gates_runs_and_lists 2026-11-27T01:31:17.706382Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:31:17.713597Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:31:17.720936Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:31:17.721963Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:31:17.722681Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:31:17.723269Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:31:17.725187Z [info     ] Scheduler started             
2026-11-27T01:31:17.806650Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1'] port=8991
2026-11-27T01:31:17.896713Z [warning  ] Resource cache refresh failed - audit target names will be stale error='All connection attempts failed'
2026-11-27T01:31:18.002219Z [warning  ] Token cache refresh failed - token users will fall back to IP resolution error='All connection attempts failed'
2026-11-27T01:31:18.234546Z [info     ] API Audit listener stopped    
2026-11-27T01:31:18.248346Z [info     ] Scheduler stopped             
PASSED
tests/test_security_ai.py::test_settings_validate_auto_analysis PASSED
tests/test_security_ai.py::test_page_escapes_what_the_model_wrote PASSED
tests/test_security_ai.py::test_i18n_keys_for_the_page_exist_in_every_language PASSED
tests/test_security_ai.py::test_verdict_notification_is_opt_in_and_lists_the_matches PASSED
tests/test_security_ai.py::test_verdict_notification_text PASSED
tests/test_security_ai.py::test_an_answer_cut_off_at_the_limit_is_asked_again_with_more_tokens 2026-11-27T01:31:21.055357Z [info     ] LLM answer cut off at the token limit; asking again with a larger one
PASSED
tests/test_security_anomaly.py::test_off_by_default_and_both_fields_are_collected PASSED
tests/test_security_anomaly.py::test_one_failing_field_does_not_stop_the_other PASSED
tests/test_security_anomaly.py::test_usual_rate_counts_quiet_hours_and_skips_days_without_runs PASSED
tests/test_security_anomaly.py::test_a_spike_against_a_learned_history PASSED
tests/test_security_anomaly.py::test_thresholds PASSED
tests/test_security_anomaly.py::test_learning_and_a_new_host PASSED
tests/test_security_anomaly.py::test_history_is_one_row_per_hour_and_pruned PASSED
tests/test_security_anomaly.py::test_runner_records_after_deciding 2026-11-27T01:31:28.945169Z [info     ] Security analysis finished     findings=0 notified=0 queries=0 server=s1 source=scheduled status=ok suppressed=0
PASSED
tests/test_security_anomaly.py::test_not_mapped_to_attack_labels_and_evidence PASSED
tests/test_security_anomaly.py::test_evidence_carries_the_explanation PASSED
tests/test_security_attack.py::test_every_detection_maps_to_known_techniques_and_tactics PASSED
tests/test_security_attack.py::test_urls_follow_mitre_paths PASSED
tests/test_security_attack.py::test_ids_signatures_by_keyword[ET SCAN NMAP -sS window 1024-want0] PASSED
tests/test_security_attack.py::test_ids_signatures_by_keyword[GPL EXPLOIT ntpdx overflow attempt-want1] PASSED
tests/test_security_attack.py::test_ids_signatures_by_keyword[ET WEB_SERVER Possible SQL Injection Attempt-want2] PASSED
tests/test_security_attack.py::test_ids_signatures_by_keyword[ET MALWARE Cobalt Strike Beacon Observed-want3] PASSED
tests/test_security_attack.py::test_ids_signatures_by_keyword[ET TROJAN Possible Win32 CnC Beacon-want4] PASSED
tests/test_security_attack.py::test_ids_signatures_by_keyword[ET DOS Possible NTP DDoS Inbound-want5] PASSED
tests/test_security_attack.py::test_ids_signatures_by_keyword[ET SCAN Possible SSH brute force-want6] PASSED
tests/test_security_attack.py::test_ids_signatures_by_keyword[ET INFO Observed DNS Query to .cloud TLD-want7] PASSED
tests/test_security_attack.py::test_ids_signatures_by_keyword[ET POLICY curl User-Agent Outbound-want8] PASSED
tests/test_security_attack.py::test_ids_signatures_by_keyword[-want9] PASSED
tests/test_security_attack.py::test_detections_without_a_signature PASSED
tests/test_security_attack.py::test_coverage_states PASSED
tests/test_security_attack.py::test_notification_names_the_techniques PASSED
tests/test_security_attack.py::test_evidence_and_chat_tool_carry_techniques PASSED
tests/test_security_attack.py::test_api_lists_techniques_and_coverage PASSED
tests/test_security_attack.py::test_page_chips_are_escaped_and_link_only_to_mitre PASSED
tests/test_security_attack.py::test_i18n_keys_exist_in_every_language PASSED
tests/test_security_cases.py::test_case_lifecycle_and_timeline PASSED
tests/test_security_cases.py::test_update_ignores_fields_outside_the_whitelist PASSED
tests/test_security_cases.py::test_retention_keeps_incidents_that_are_case_evidence PASSED
tests/test_security_cases.py::test_chat_tools_read_cases 2026-11-27T01:31:34.866407Z [info     ] AI tool failed                 channel=chat error='status: open, in_progress or closed' tool=list_security_cases
PASSED
tests/test_security_cases.py::test_api_flow_validation_and_audit PASSED
tests/test_security_cases.py::test_case_dialog_escapes_everything PASSED
tests/test_security_cases.py::test_markdown_report PASSED
tests/test_security_cases.py::test_i18n_keys_exist_in_every_language PASSED
tests/test_security_context.py::test_waf_scan_gets_reporter_site_paths_and_responses_from_its_own_query PASSED
tests/test_security_context.py::test_site_field_names_and_the_entity_field_itself_is_skipped PASSED
tests/test_security_context.py::test_a_failed_field_is_left_out_and_the_others_kept PASSED
tests/test_security_context.py::test_cost_is_capped_highest_first PASSED
tests/test_security_digest.py::test_build_digest PASSED
tests/test_security_digest.py::test_health PASSED
tests/test_security_digest.py::test_text PASSED
tests/test_security_digest.py::test_api PASSED
tests/test_security_digest.py::test_schedule 2026-11-27T01:31:40.666151Z [warning  ] Invalid security digest cron, using Monday 08:00 cron=bad error='use five fields: minute hour day month weekday'
PASSED
tests/test_security_digest.py::test_zh_text_uses_full_width_punctuation PASSED
tests/test_security_digest.py::test_labels PASSED
tests/test_security_digest.py::test_the_summary_cron_is_one_fixed_time_that_runs PASSED
tests/test_security_digest.py::test_a_bad_stored_summary_cron_does_not_stop_the_analysis_job 2026-11-27T01:31:42.746363Z [warning  ] Invalid security digest cron, using Monday 08:00 cron='0 8 * * 8' error='not a valid cron (KeyError)'
PASSED
tests/test_security_fieldmap.py::test_defaults_are_exactly_the_old_probes PASSED
tests/test_security_fieldmap.py::test_validate PASSED
tests/test_security_fieldmap.py::test_a_broken_stored_map_falls_back_key_by_key PASSED
tests/test_security_fieldmap.py::test_the_engine_reads_the_mapped_fields_and_keeps_gim_metric_names PASSED
tests/test_security_fieldmap.py::test_mapped_queries_and_the_other_probes PASSED
tests/test_security_fieldmap.py::test_success_after_fail_uses_the_mapped_success_query PASSED
tests/test_security_fieldmap.py::test_new_source_findings_query_uses_the_map PASSED
tests/test_security_fieldmap.py::test_detector_rows_show_the_mapped_query_fields_and_exclusion PASSED
tests/test_security_fieldmap.py::test_ai_evidence_breaks_down_by_the_mapped_fields PASSED
tests/test_security_fieldmap.py::test_candidates_pick_by_value_shape_and_name PASSED
tests/test_security_fieldmap.py::test_detect_on_a_log4_shaped_site PASSED
tests/test_security_fieldmap.py::test_detect_stops_at_a_query_that_matches_nothing PASSED
tests/test_security_fieldmap.py::test_api_save_and_detect PASSED
tests/test_security_incidents.py::test_bruteforce_threshold_and_external_severity PASSED
tests/test_security_incidents.py::test_spray_and_multi_host_use_cardinality PASSED
tests/test_security_incidents.py::test_empty_value_bucket_is_coverage_not_an_incident PASSED
tests/test_security_incidents.py::test_a_scan_the_waf_blocked_is_recorded_low_unless_it_is_a_flood PASSED
tests/test_security_incidents.py::test_blocked_count_failure_keeps_the_incident_as_before PASSED
tests/test_security_incidents.py::test_blocked_query_comes_from_the_field_map PASSED
tests/test_security_incidents.py::test_every_peer_field_is_tried_so_the_waf_client_ip_is_seen PASSED
tests/test_security_incidents.py::test_detectors_sharing_a_probe_share_one_search PASSED
tests/test_security_incidents.py::test_ids_severity_rules PASSED
tests/test_security_incidents.py::test_success_after_failures_needs_the_second_search PASSED
tests/test_security_incidents.py::test_a_failing_search_is_recorded_and_the_rest_still_run PASSED
tests/test_security_incidents.py::test_exclusions_and_settings PASSED
tests/test_security_incidents.py::test_entity_text_is_quoted_in_the_graylog_query PASSED
tests/test_security_incidents.py::test_is_external PASSED
tests/test_security_incidents.py::test_every_detector_has_a_known_probe_and_severity_rules PASSED
tests/test_security_incidents.py::test_aggregate_body_and_rows PASSED
tests/test_security_incidents.py::test_incident_lifecycle PASSED
tests/test_security_incidents.py::test_learning_period_suppresses_new PASSED
tests/test_security_incidents.py::test_list_filters_and_prune PASSED
tests/test_security_incidents.py::test_notify_decision[change0-None-high-high-True] PASSED
tests/test_security_incidents.py::test_notify_decision[change1-None-medium-high-False] PASSED
tests/test_security_incidents.py::test_notify_decision[change2-2026-11-19T09:55:00Z-high-medium-True] PASSED
tests/test_security_incidents.py::test_notify_decision[change3-2026-11-19T09:55:00Z-high-high-False] PASSED
tests/test_security_incidents.py::test_notify_decision[change4-2026-11-18T09:00:00Z-high-high-True] PASSED
tests/test_security_incidents.py::test_notify_decision[change5-None-high-high-True] PASSED
tests/test_security_incidents.py::test_notify_decision[change6-None-high-off-False] PASSED
tests/test_security_incidents.py::test_notification_text_is_neutralised PASSED
tests/test_security_incidents.py::test_email_and_slack_bodies_escape_log_text PASSED
tests/test_security_incidents.py::test_off_by_default_and_settings_register_the_job PASSED
tests/test_security_incidents.py::test_settings_validation PASSED
tests/test_security_incidents.py::test_incident_api PASSED
tests/test_security_incidents.py::test_unreachable_graylog_is_a_failed_run_and_alerts_once 2026-11-27T01:31:51.527445Z [warning  ] Security analysis failed       error='Graylog health could not be read' server=a
2026-11-27T01:31:51.629506Z [warning  ] Security analysis failed       error='Graylog health could not be read' server=a
2026-11-27T01:31:51.729620Z [warning  ] Security analysis failed       error='Graylog health could not be read' server=a
2026-11-27T01:31:51.820479Z [warning  ] Security analysis failed       error='Graylog health could not be read' server=a
2026-11-27T01:31:51.914075Z [warning  ] Security analysis failed       error='Graylog health could not be read' server=a
PASSED
tests/test_security_incidents.py::test_two_runs_notify_once_then_hold 2026-11-27T01:31:52.927820Z [info     ] Security analysis finished     findings=1 notified=1 queries=9 server=a source=scheduled status=ok suppressed=0
2026-11-27T01:31:53.135482Z [info     ] Security analysis finished     findings=1 notified=0 queries=9 server=a source=scheduled status=ok suppressed=0
PASSED
tests/test_security_incidents.py::test_runner_stores_the_context_and_notifies_with_it 2026-11-27T01:31:54.216446Z [info     ] Security analysis finished     findings=1 notified=1 queries=9 server=a source=scheduled status=ok suppressed=0
PASSED
tests/test_security_new_source.py::test_off_by_default_and_pairs_are_collected PASSED
tests/test_security_new_source.py::test_learning_memory_and_one_finding_per_account PASSED
tests/test_security_new_source.py::test_prune_forgets_old_pairs PASSED
tests/test_security_new_source.py::test_attack_and_labels PASSED
tests/test_security_overview.py::test_summary PASSED
tests/test_security_overview.py::test_chart_is_plain_svg_without_inline_style PASSED
tests/test_security_overview.py::test_i18n_keys_exist_in_every_language PASSED
tests/test_security_overview.py::test_attack_watched_uses_a_day_of_runs_not_the_last_quiet_one PASSED
tests/test_security_overview.py::test_incidents_csv_export PASSED
tests/test_security_review_fixes.py::test_an_empty_retention_box_cannot_delete_every_incident PASSED
tests/test_security_review_fixes.py::test_scheduled_and_manual_runs_share_one_lock 2026-11-27T01:31:59.819179Z [info     ] Security analysis skipped: a run (Run now) is still going
PASSED
tests/test_security_review_fixes.py::test_run_now_answers_before_the_ai_finishes 2026-11-27T01:32:00.683362Z [info     ] Bootstrapped auto-export from config.yaml cron='0 * * * *'
2026-11-27T01:32:00.712164Z [info     ] Bootstrapped auto-cleanup from config.yaml cron='0 3 * * *'
2026-11-27T01:32:00.733645Z [info     ] Bootstrapped auto-report-cleanup (720-day retention)
2026-11-27T01:32:00.735264Z [info     ] Schedule registered            cron='0 * * * *' cron_aps=None name=auto-export type=export
2026-11-27T01:32:00.736196Z [info     ] Schedule registered            cron='0 3 * * *' cron_aps=None name=auto-cleanup type=cleanup
2026-11-27T01:32:00.736980Z [info     ] Schedule registered            cron='0 4 * * *' cron_aps=None name=auto-report-cleanup type=report_cleanup
2026-11-27T01:32:00.739473Z [info     ] Scheduler started             
2026-11-27T01:32:00.839888Z [info     ] API Audit listener started     allowed_ips=['127.0.0.1', '::1'] port=8991
2026-11-27T01:32:00.961222Z [warning  ] Resource cache refresh failed - audit target names will be stale error='All connection attempts failed'
2026-11-27T01:32:01.096687Z [warning  ] Token cache refresh failed - token users will fall back to IP resolution error='All connection attempts failed'
2026-11-27T01:32:01.221730Z [info     ] API Audit listener stopped    
2026-11-27T01:32:01.239210Z [info     ] Scheduler stopped             
PASSED
tests/test_security_review_fixes.py::test_one_unparsable_network_asset_does_not_break_risk PASSED
tests/test_security_review_fixes.py::test_unverified_addresses_compare_whole_addresses_and_drop_ports PASSED
tests/test_security_review_fixes.py::test_no_leading_wildcard_term_reaches_mcp_graylog PASSED
tests/test_security_review_fixes.py::test_an_unexpected_llm_error_still_leaves_a_row 2026-11-27T01:32:01.778178Z [warning  ] Incident AI analysis failed    error='connection reset' incident=1
PASSED
tests/test_security_review_fixes.py::test_confirm_dialogs_escape_user_text PASSED
tests/test_security_review_fixes.py::test_case_report_cannot_carry_links_or_html PASSED
tests/test_security_risk.py::test_normalize_asset[ip- 10.0.0.5 -10.0.0.5] PASSED
tests/test_security_risk.py::test_normalize_asset[ip-2001:DB8::1-2001:db8::1] PASSED
tests/test_security_risk.py::test_normalize_asset[cidr-10.1.2.3/24-10.1.2.0/24] PASSED
tests/test_security_risk.py::test_normalize_asset[host-DC1-dc1] PASSED
tests/test_security_risk.py::test_normalize_asset[account-Administrator-administrator] PASSED
tests/test_security_risk.py::test_normalize_asset[ip-10.0.0.999-None] PASSED
tests/test_security_risk.py::test_normalize_asset[cidr-nope-None] PASSED
tests/test_security_risk.py::test_normalize_asset[host-two words-None] PASSED
tests/test_security_risk.py::test_normalize_asset[host-<script>-None] PASSED
tests/test_security_risk.py::test_normalize_asset[printer-x-None] PASSED
tests/test_security_risk.py::test_match_asset[10.0.5.10-3] PASSED
tests/test_security_risk.py::test_match_asset[10.0.5.11-2] PASSED
tests/test_security_risk.py::test_match_asset[10.9.9.9-1] PASSED
tests/test_security_risk.py::test_match_asset[192.168.9.9-None] PASSED
tests/test_security_risk.py::test_match_asset[Administrator-4] PASSED
tests/test_security_risk.py::test_match_asset[DC1-5] PASSED
tests/test_security_risk.py::test_match_asset[ET SCAN NMAP-None] PASSED
tests/test_security_risk.py::test_match_asset[2001:db8::1-None] PASSED
tests/test_security_risk.py::test_score_is_explained_and_ranked PASSED
tests/test_security_risk.py::test_assets_in_the_db PASSED
tests/test_security_risk.py::test_api_assets_risk_and_audit PASSED
tests/test_security_risk.py::test_evidence_and_tool_know_the_asset PASSED
tests/test_security_risk.py::test_page_escapes_assets_and_entities PASSED
tests/test_security_risk.py::test_i18n_keys_exist_in_every_language PASSED
tests/test_security_sigma.py::test_conversion[  s: {event_outcome: failure}\n  condition: s-event_outcome:"failure"] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a: x, b: 'y z'}\n  condition: s-(a:"x" AND b:"y z")] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a: [x, y]}\n  condition: s-(a:"x" OR a:"y")] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|all: [x, y]}\n  condition: s-(a:"x" AND a:"y")] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|startswith: adm}\n  condition: s-a:adm*] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|endswith: '.exe'}\n  condition: s-a:/.*\\.exe/] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|contains: 'x y'}\n  condition: s-a:/.*x y.*/] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a: 'ad*min'}\n  condition: s-a:ad*min] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a: '*min'}\n  condition: s-a:/.*min/] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a: 'C:\\\\Win dows\\\\x?'}\n  condition: s-a:C\\:\\\\Win\\ dows\\\\x?] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a: 'lit\\*eral'}\n  condition: s-a:"lit*eral"] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a: null}\n  condition: s-(*:* AND NOT _exists_:a)] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|exists: true}\n  condition: s-_exists_:a] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a: [null, x]}\n  condition: s-((*:* AND NOT _exists_:a) OR a:"x")] PASSED
tests/test_security_sigma.py::test_conversion[  sel: {a: 1}\n  f: {b: 2}\n  condition: not f or sel-((*:* AND NOT b:2) OR a:1)] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|exists: false}\n  condition: s-(*:* AND NOT _exists_:a)] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|re: mimikatz}\n  condition: s-a:/.*(mimikatz).*/] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|re: '^ab$'}\n  condition: s-a:/(ab)/] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|re: 'x\\/y'}\n  condition: s-a:/.*(x\\/y).*/] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|startswith: 'foo\\*bar'}\n  condition: s-a:foo\\*bar*] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|startswith: '>foo'}\n  condition: s-a:\\>foo*] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a: x}\n  _f: {b: y}\n  condition: all of them-a:"x"] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|gte: 5}\n  condition: s-a:>=5] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a: 4625}\n  condition: s-a:4625] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a|re: 'ab+c/d'}\n  condition: s-a:/.*(ab+c\\/d).*/] PASSED
tests/test_security_sigma.py::test_conversion[  s: ['Failed password', '*session opened*']\n  condition: s-(message:"Failed password" OR message:"session opened")] PASSED
tests/test_security_sigma.py::test_conversion[  s: [{a: x}, {b: y}]\n  condition: s-(a:"x" OR b:"y")] PASSED
tests/test_security_sigma.py::test_conversion[  sel: {a: x}\n  f: {b: y}\n  condition: sel and not f-(a:"x" AND (*:* AND NOT b:"y"))] PASSED
tests/test_security_sigma.py::test_conversion[  s1: {a: x}\n  s2: {b: y}\n  condition: 1 of s*-(a:"x" OR b:"y")] PASSED
tests/test_security_sigma.py::test_conversion[  s1: {a: x}\n  s2: {b: y}\n  condition: all of them-(a:"x" AND b:"y")] PASSED
tests/test_security_sigma.py::test_conversion[  s1: {a: x}\n  s2: {b: y}\n  s3: {c: z}\n  condition: (s1 or s2) and not s3-((a:"x" OR b:"y") AND (*:* AND NOT c:"z"))] PASSED
tests/test_security_sigma.py::test_conversion[  s: {a: x}\n  condition: [s, s]-(a:"x" OR a:"x")] PASSED
tests/test_security_sigma.py::test_message_is_text_not_a_keyword PASSED
tests/test_security_sigma.py::test_field_map_and_names PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a|base64: x}\n  condition: s-modifier 'base64'] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a|cidr: 10.0.0.0/8}\n  condition: s-modifier 'cidr'] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a|re|i: x}\n  condition: s-modifier 'i'] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a: x}\n  condition: s | count() > 5-aggregation] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a: x}\n  condition: s near t-cannot read the condition after] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a: x}\n  condition: t-not a selection] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a: x}\n  condition: 1 of x*-no selection matches] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a: x}\n  condition: (s-not closed] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: ['a*b']\n  condition: s-wildcards inside a keyword] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a|gt: x}\n  condition: s-takes a number] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {}\n  condition: s-empty selection] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a: x}-no condition] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[detection:\n  s: {a: x}\n  condition: s-no title] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\n-no detection] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: a\ndetection: {s: {a: x}, condition: s}\n---\ntitle: b\ndetection: {s: {a: x}, condition: s}-one Sigma rule] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[: : :-Not valid YAML] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a|re: '\\d+'}\n  condition: s-PCRE syntax] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a|re: '(?i)x'}\n  condition: s-PCRE syntax] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a|re: 'a^b'}\n  condition: s-anchors are only supported] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {'-x': 1}\n  condition: s-usable Graylog field] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a: x}\n  condition: 1 of-ends too early] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {a: ''}\n  condition: s-empty value] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {message|startswith: x}\n  condition: s-only |contains] PASSED
tests/test_security_sigma.py::test_refused_with_a_reason[title: t\ndetection:\n  s: {message: x}\n  condition: s-only |contains] PASSED
tests/test_security_sigma.py::test_rule_metadata_and_attack_tags PASSED
tests/test_security_sigma.py::test_engine_runs_enabled_rules_per_group PASSED
tests/test_security_sigma.py::test_db_rules_and_results PASSED
tests/test_security_sigma.py::test_notification_uses_the_rule_title PASSED
tests/test_security_sigma.py::test_api_flow PASSED
tests/test_security_sigma.py::test_incident_from_a_rule_shows_its_title_and_techniques PASSED
tests/test_security_sigma.py::test_page_escapes_rules PASSED
tests/test_security_sigma.py::test_i18n_keys_exist_in_every_language PASSED
tests/test_security_silent.py::test_off_by_default PASSED
tests/test_security_silent.py::test_silent_sources_two_windows_and_thresholds PASSED
tests/test_security_silent.py::test_min_count_is_configurable PASSED
tests/test_security_silent.py::test_a_truncated_recent_list_proves_nothing PASSED
tests/test_security_silent.py::test_a_failed_query_is_recorded_not_fatal PASSED
tests/test_security_silent.py::test_attack_and_labels PASSED
tests/test_security_suppress.py::test_normalize_entity PASSED
tests/test_security_suppress.py::test_matching PASSED
tests/test_security_suppress.py::test_apply_counts_hits PASSED
tests/test_security_suppress.py::test_api PASSED
tests/test_security_suppress.py::test_runner_drops_suppressed_findings_and_counts_them 2026-11-27T01:32:14.990559Z [info     ] Security analysis finished     findings=1 notified=1 queries=2 server=s1 source=scheduled status=ok suppressed=1
PASSED
tests/test_security_suppress.py::test_prune_keeps_live_and_recently_expired PASSED
tests/test_security_suppress.py::test_ui_wiring_and_labels PASSED
tests/test_security_suppress.py::test_addresses_compare_in_canonical_form PASSED
tests/test_security_suppress.py::test_mapped_ipv6_cannot_get_around_the_width_limit 2026-11-27T01:32:16.458304Z [warning  ] Too wide suppression network ignored entity=::ffff:0:0/96 id=9
PASSED
tests/test_security_suppress.py::test_an_entity_with_a_slash_that_is_not_a_network_is_exact PASSED
tests/test_security_suppress.py::test_closing_through_a_suppression_only_closes_what_it_covers PASSED
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
tests/test_sigma_library.py::test_read_package PASSED
tests/test_sigma_library.py::test_package_limits PASSED
tests/test_sigma_library.py::test_only_github_hosts PASSED
tests/test_sigma_library.py::test_refresh_then_current 2026-11-27T01:32:35.321981Z [warning  ] Sigma library refresh failed   error='release r2026-07-01 has no sigma_all_rules.zip'
PASSED
tests/test_sigma_library.py::test_redirect_elsewhere_is_refused_and_library_kept 2026-11-27T01:32:36.108525Z [warning  ] Sigma library refresh failed   error="refusing to download from '198.51.100.7'"
PASSED
tests/test_sigma_library.py::test_added_rules_follow_upstream 2026-11-27T01:32:36.941592Z [info     ] Sigma rules updated from the library rules=1
2026-11-27T01:32:36.982309Z [info     ] Sigma rules updated from the library rules=1
PASSED
tests/test_sigma_library.py::test_api PASSED
tests/test_sigma_library.py::test_schedule PASSED
tests/test_sigma_library.py::test_page_wiring PASSED
tests/test_sigma_library.py::test_version_txt_is_read_bounded PASSED
tests/test_sigma_library.py::test_yaml_aliases_are_refused_before_anything_expands PASSED
tests/test_sigma_library.py::test_one_odd_rule_does_not_stop_the_package PASSED
tests/test_sigma_library.py::test_regex_must_be_balanced[(-False] PASSED
tests/test_sigma_library.py::test_regex_must_be_balanced[a)-False] PASSED
tests/test_sigma_library.py::test_regex_must_be_balanced[[(]-True] PASSED
tests/test_sigma_library.py::test_regex_must_be_balanced[(a|b)-True] PASSED
tests/test_sigma_library.py::test_regex_must_be_balanced[[]x]-True] PASSED
tests/test_sigma_library.py::test_regex_must_be_balanced[[^]x]-True] PASSED
tests/test_sigma_library.py::test_regex_must_be_balanced[[ab-False] PASSED
tests/test_sigma_library.py::test_redirects_keep_to_port_443 PASSED
tests/test_sigma_library.py::test_a_download_has_an_overall_deadline PASSED
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
tests/test_static_sweeps.py::test_no_inline_style_attributes_in_generated_html PASSED
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
tests/test_static_sweeps.py::test_vendored_files_match_their_manifest PASSED
tests/test_storage_ownership.py::test_fix_dir_ownership_as_root 2026-11-27T01:32:59.898008Z [warning  ] Fixing directory ownership     new_owner=jt-glogarch path=/tmp/tmp9gyh1g0b/archives/log4
PASSED
tests/test_storage_ownership.py::test_fix_dir_ownership_not_root SKIPPED
tests/test_storage_ownership.py::test_fix_only_under_base_path PASSED
tests/test_streams_cleanup.py::test_matches_stream_by_index_set_not_just_title PASSED
tests/test_streams_cleanup.py::test_does_not_touch_unrelated_streams PASSED
tests/test_streams_cleanup.py::test_title_prefix_match_still_works PASSED
tests/test_streams_cleanup.py::test_command_source_matches_by_index_set_id PASSED
tests/test_streams_cleanup.py::test_streams_are_deleted_before_index_sets PASSED
tests/test_threat_intel.py::test_parse_feeds PASSED
tests/test_threat_intel.py::test_matcher PASSED
tests/test_threat_intel.py::test_refresh_replaces_and_a_failure_keeps_the_old_copy 2026-11-27T01:33:00.552589Z [warning  ] Threat-intel feed refresh failed error='no route' feed=feodo
2026-11-27T01:33:00.566168Z [warning  ] Threat-intel feed refresh failed error='no route' feed=tor_exit
PASSED
tests/test_threat_intel.py::test_download_refuses_an_empty_or_huge_feed PASSED
tests/test_threat_intel.py::test_a_feed_that_suddenly_shrinks_keeps_the_previous_list 2026-11-27T01:33:01.340110Z [warning  ] Threat-intel feed refresh failed error='the feed shrank from 400 to 1 entries; the previous list is kept' feed=tor_exit
PASSED
tests/test_threat_intel.py::test_a_download_has_an_overall_deadline PASSED
tests/test_threat_intel.py::test_matching_is_indexed_and_exact PASSED
tests/test_threat_intel.py::test_matcher_for_is_off_by_default_and_follows_settings PASSED
tests/test_threat_intel.py::test_risk_factor PASSED
tests/test_threat_intel.py::test_api_and_incident_marks PASSED
tests/test_threat_intel.py::test_evidence_mentions_the_listing PASSED
tests/test_threat_intel.py::test_scheduler_job_follows_the_switch PASSED
tests/test_threat_intel.py::test_i18n_keys_exist_in_every_language PASSED
tests/test_threat_intel.py::test_the_refresh_is_scheduled_from_the_last_one_not_from_each_restart PASSED
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

=============================== warnings summary ===============================
tests/test_ai.py::test_an_answer_goes_on_after_the_page_is_left
  /usr/local/lib/python3.10/dist-packages/websockets/legacy/__init__.py:6: DeprecationWarning: websockets.legacy is deprecated; see https://websockets.readthedocs.io/en/stable/howto/upgrade.html for upgrade instructions
    warnings.warn(  # deprecated in 14.0 - 2024-11-09

tests/test_ai.py::test_an_answer_goes_on_after_the_page_is_left
  /usr/local/lib/python3.10/dist-packages/uvicorn/protocols/websockets/websockets_impl.py:17: DeprecationWarning: websockets.server.WebSocketServerProtocol is deprecated
    from websockets.server import WebSocketServerProtocol

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========== 1756 passed, 1 skipped, 2 warnings in 524.12s (0:08:44) ============
```

## Version Check

```
Canonical version: 1.36.0
OK: version '1.36.0' has exactly one source of truth.
```
