# Test map — every test → the requirement / rubric criterion it protects

Rubric ids are from `eval/rubric.json` (auto = scored by `eval/eval.py`).

## Python: tests/test_eval_alignment.py

| Test | AGENTS.md requirement | Rubric criterion |
|---|---|---|
| `test_translate_response_has_contract_keys` | `/translate` contract shape | `widget_lights_up` (15) |
| `test_batch_response_shape` | `/translate/batch` contract shape | `widget_lights_up` (15) |
| `test_health_reports_status_ok_model_cachesize` | `GET /health` shape | `widget_lights_up` / `logging_observability` |
| `test_stats_exposes_hit_rate` | `GET /stats` incl. hit rate | `logging_observability` (10) |
| `test_second_identical_call_cached_true_and_faster` | identical input never hits LLM twice; `cached` truthful; hit faster | `caching_correctness` (20) |
| `test_sqlite_db_file_exists_and_nonempty_after_set` | SQLite tier exists | `caching_correctness` (20) |
| `test_invalid_body_rejected_4xx` | bad input rejected (gateway asserts exact 400) | `service_separation_contract` (10) |
| `test_request_id_appears_in_ai_service_log` | trace correlation: forwarded id logged by AI service | `logging_observability` (10) |

## Python: tests/test_user_outcomes.py

| Test | Requirement |
|---|---|
| `test_translated_text_returned_verbatim_from_llm` | service returns the translation unmangled |
| `test_target_defaults_to_hi_in` | default target is hi-IN |
| `test_prices_skus_numbers_pass_through_unaltered` | `$` prices / SKUs / numbers preserved end-to-end |
| `test_cache_hit_dramatically_faster_than_miss` | hit latency ≪ miss latency (the point of the cache) |
| `test_live_output_is_hindi_not_english` *(live)* | real LLM output is Hindi (Devanagari), not the input |
| `test_live_preserves_price_and_sku` *(live)* | prompt preserves prices/codes on the real model |
| `test_live_translation_only_no_preamble_or_quotes` *(live)* | translation only — no preamble, no wrapping quotes |

Live tests are the executable version of the manual `llm_prompt_quality` (20)
rubric row.

## Python: tests/test_llm_prompt.py (fast — no network, no key)

| Test | Requirement / guide section |
|---|---|
| `test_hindi_system_prompt_contains_style_block` | hi-IN prompt carries the style rules distilled from `docs/hindi-style-guide.md` |
| `test_messages_end_with_raw_user_text` | bare input in — no wrapping or preamble around the user text |
| `test_few_shot_alternates_user_assistant_pairs` | few-shot sent as real message turns |
| `test_few_shot_examples_follow_guide_conventions` | examples obey guide §5/§8 (no Devanagari digits, no western period) |
| `test_unknown_target_gets_generic_prompt_no_few_shot` | open-closed: new language = data only |
| `test_provider_sdk_not_imported_at_module_import_time` | mocked suite/CI never needs the SDK or a key |

## Python: tests/test_provider_routing.py (fast — providers mocked at the seam)

| Test | Requirement |
|---|---|
| `test_openrouter_used_when_key_set` | OpenRouter is the primary provider when `OPENROUTER_API_KEY` is set |
| `test_falls_back_to_anthropic_when_openrouter_fails` | provider failure degrades to Anthropic direct, still translating |
| `test_both_providers_failing_raises_never_returns_english` | **automatic-fail rule** survives the fallback chain |
| `test_anthropic_direct_when_no_openrouter_key` | no OpenRouter key = single-provider behavior unchanged |
| `test_wrapping_quotes_stripped_regardless_of_provider` | output cleanup is provider-agnostic |

## Python: tests/test_user_outcomes.py::TestLiveStyle (live — style adherence)

| Test | Guide section |
|---|---|
| `test_prose_is_mostly_devanagari_and_ends_with_danda` | §4 script, §5 danda-for-prose |
| `test_no_devanagari_digits_and_currency_preserved` | §5 Western digits, $ never converted |
| `test_brand_name_stays_latin` | §4 brands never transliterated |
| `test_ui_label_uses_canonical_lexicon_no_terminal_punctuation` | §6 lexicon, §5 bare UI labels |
| `test_imperative_uses_karein_register` | §2 करें register, never कीजिए/करो |

## Python: tests/test_integration.py

| Test | Requirement |
|---|---|
| `test_sqlite_persists_across_restart` | SQLite tier survives a process restart (DoD step 3) |
| `test_memory_tier_warmed_after_db_hit` | two-tier flow: db hit warms the memory tier |
| `test_stats_counters_accumulate` | `/stats` counters are accurate |
| `test_batch_reports_per_item_cached_flags` | batch reports per-item `cached` truthfully, in order |

## Python: tests/test_edge_cases.py

| Test | Requirement |
|---|---|
| `test_empty_text_returns_empty_without_llm_call` | no wasted LLM calls on empty input |
| `test_whitespace_only_text_treated_as_empty` | same, for whitespace |
| `test_very_long_text_roundtrips` | long content works |
| `test_special_chars_emoji_html_entities_cache_correctly` | sha256 key stable for unicode/entities |
| `test_batch_empty_array_returns_empty_results` | degenerate batch |
| `test_batch_mixed_empty_and_real_content` | mixed batch keeps order |
| `test_missing_text_field_is_4xx` / `test_text_wrong_type_is_4xx` | input validation |
| `test_llm_failure_propagates_never_returns_english` | **automatic-fail rule**: no silent English fallback; failures not cached |
| `test_concurrent_identical_requests_call_llm_once` | "MUST NOT call the LLM twice" under concurrency (single-flight; intentionally beyond the TODO skeleton) |

## Node: test/gateway.test.js

| Test | Requirement | Rubric criterion |
|---|---|---|
| proxies `/translate` and returns AI JSON verbatim | gateway↔AI proxy (TODO #2) | `widget_lights_up` |
| defaults target to hi-IN | contract default | `widget_lights_up` |
| forwards batch shape | `/translate/batch` proxy | `widget_lights_up` |
| exactly 400 on missing/non-string `text`, non-array `texts` | `400` invalid input | `service_separation_contract` |
| `/health` nests live aiService | health nesting | `logging_observability` + `service_separation_contract` |
| `/stats` passes through hit_rate | stats passthrough | `logging_observability` |
| `/widget.js` served as JS | widget serving | `widget_lights_up` |
| 502 when AI returns 500 / unreachable (never echoes English) | `502` upstream failure, fail loud | `service_separation_contract` |
| forwards inbound `X-Request-Id` / generates one | trace correlation (TODO #2) | `logging_observability` |
| logs one structured line per request | logging middleware (TODO #1) | `logging_observability` |
