"""The hub's public API: the one place a consumer imports from.

A consumer (any package built on the hub) never imports a hub module path such as
``hubofhubs.the_world.tools.deep``. It imports a name from here, or calls ``hubofhubs.run("<id>", input)`` for any part by its id,
or ``hubofhubs.run(Interface)`` for a typed handle. When a part moves inside the hub, the entry for its name in ``LOCATIONS`` changes
and no consumer file does.

    from hubofhubs.api import CardStore, Card, DeepRunner

Names are resolved on first use, so importing this module imports nothing else. ``__all__`` lists every public name. The entries
are grouped by the module that defines them today; a name that two modules both define is prefixed with its module (for example
``bm25_store_SOURCE_EXTS``). Every interface of the records is listed (``tests/test_public_api.py`` fails when one is missing).
"""
from __future__ import annotations

import importlib

from hubofhubs import (AssemblyConfig, AssemblyError, Assembly, Binding, Result, assemble, assembler, check, choice, evaluate,
                       evaluate_seats, metrics, names, needs, register, resolve, run)

MODULES = (
    "hubofhubs.the_body.internal_context.card_store.background_pacing", "hubofhubs.the_body.internal_context.card_store.card_limit",
    "hubofhubs.the_body.internal_context.card_store.card_limit_report", "hubofhubs.the_body.internal_context.card_store.card_origin",
    "hubofhubs.the_body.internal_context.card_store.card_store_hygiene",
    "hubofhubs.the_body.internal_context.card_store.card_store_identity", "hubofhubs.the_body.internal_context.card_store.card_store_merge",
    "hubofhubs.the_body.internal_context.card_store.card_store_mounts", "hubofhubs.the_body.internal_context.card_store.card_store_tidy",
    "hubofhubs.the_body.internal_context.card_store.card_vectors", "hubofhubs.the_body.internal_context.card_store.embedders",
    "hubofhubs.the_consciousness.terminal.render", "hubofhubs.the_consciousness.terminal.strings",
    "hubofhubs.the_consciousness.terminal.trail", "hubofhubs.the_intelligence.critical_thinking.goal_completion.sufficiency",
    "hubofhubs.the_intelligence.subconscious.context_retriever.assemblers.bm25_store",
    "hubofhubs.the_intelligence.subconscious.context_retriever.assemblers.hybrid_assembler",
    "hubofhubs.the_intelligence.subconscious.context_retriever.assemblers.vector_assembler",
    "hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.card_selection", "hubofhubs.the_self.assembler.arm_needs",
    "hubofhubs.the_self.integrity.cases", "hubofhubs.the_self.integrity.render_docs", "hubofhubs.the_self.integrity.scan",
    "hubofhubs.the_self.integrity.score", "hubofhubs.the_world.learning.research_freshness_reader.registry",
    "hubofhubs.the_world.model_plumbing.model_tier_chooser.tiers", "hubofhubs.the_world.model_plumbing.prompt_spec",
    "hubofhubs.the_world.model_plumbing.signature_probe", "hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli",
    "hubofhubs.the_world.model_plumbing.vendor_model_caller.outage", "hubofhubs.the_world.tools.connected_system_operations.mcp_client",
    "hubofhubs.the_world.tools.delegated_agent_sessions.acp_config", "hubofhubs.the_world.tools.delegated_agent_sessions.acp_runner",
    "hubofhubs.the_world.tools.delegated_agent_sessions.contract", "hubofhubs.the_world.tools.delegated_agent_sessions.session",
    "hubofhubs.the_world.tools.delegated_agent_sessions.stream_runner",
    "hubofhubs.the_world.tools.delegated_agent_sessions.subprocess_runner", "hubofhubs.the_world.tools.file_editing.editblock",
    "hubofhubs.the_world.tools.secret_redaction", "hubofhubs.the_world.tools.web_search.backends",
    "hubofhubs.the_world.tools.web_search.fetch", "hubofhubs.the_world.tools.web_search.link_access",
    "hubofhubs.the_world.tools.web_search.page_extract", "hubofhubs.the_world.tools.web_search.research"
)

# module -> the names it defines, each public under its own name
NAMES = {
    "hubofhubs": (
        "Binding", "check", "evaluate", "evaluate_seats",
    ),
    "hubofhubs.the_body.flow": (
        "BodyComposition",
    ),
    "hubofhubs.the_body.hands.interface": (
        "Connecting",
    ),
    "hubofhubs.the_body.intake_sources.interface": (
        "IntakeSourcing",
    ),
    "hubofhubs.the_body.interface": (
        "FormAndContext", "match_umask",
    ),
    "hubofhubs.the_body.internal_context.card_store.background_pacing": (
        "Pacer",
    ),
    "hubofhubs.the_body.internal_context.card_store.card": (
        "Card",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_limit": (
        "DEFAULT_MAX_CARDS", "parse_max_cards", "take_task_notes",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_limit_report": (
        "Breakdown", "KEPT_OVER_WHY", "REPORT_NAME", "Voice", "breakdown", "can_set_aside", "count_line", "write_report",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_origin": (
        "card_id_of_item", "compounding_evidence", "last_touched", "protection",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_repository": (
        "CardRepository", "FilesystemCardRepository", "QUARANTINE_DIR_NAME", "card_embed_text",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_store_hygiene": (
        "Move", "card_paths", "fold_card", "in_quarantine", "join_onto", "keeper_rank", "move_to", "name_match_score", "name_tokens",
        "plan_stray", "protection_reason", "read_card", "render_health_report", "settle_move",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_store_identity": (
        "EMBEDDED", "ORIGIN_FIELD", "SCHEME_QUALIFIED", "apply_move_root", "ensure_store_id", "is_merged", "read_meta", "update_identity",
        "write_meta", "writer_origins",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_store_lock": (
        "StoreLock", "TIDY_LOCK_FILE",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_store_merge": (
        "MergePlan", "item_id",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_store_mounts": (
        "MODE_MOUNT", "MOUNT_ID_SEP", "Mount", "MountedCardRepository", "NO_STORE", "Rebase", "copy_origin_root",
        "discover_ancestor_stores", "discover_nested_stores", "mounted_card_id", "parse_mount_mode", "rebase_path", "resolve_mounts",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_store_tidy": (
        "MANIFEST_SUFFIX", "RepositoryTidy", "StorePlan", "TidyRun", "is_local_folder", "split_steps",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_store_tidy_plan": (
        "DEFAULT_REASONS", "excluded_prefixes_from_review", "plan_cards", "strip_prefix", "under_any_prefix",
    ),
    "hubofhubs.the_body.internal_context.card_store.card_vectors": (
        "CONNECT_TIMEOUT_SECONDS", "Compatibility", "RETRY_AFTER_SECONDS", "ReaderFactory", "SCOPE_KEY", "STORE_KEY", "compatibility",
    ),
    "hubofhubs.the_body.internal_context.card_store.cardstore": (
        "LocalCardStore",
    ),
    "hubofhubs.the_body.internal_context.card_store.context_bootstrap_support": (
        "BOOTSTRAP_VERSION", "BOOTSTRAP_WORKERS_DEFAULT", "CHUNK_SIZE", "DISCOVERED_FILE", "MAX_ANCESTOR_WALK_LEVELS",
        "MAX_MERGED_KEYWORDS", "TFDFIDF_VERSION", "bootstrap_workers", "card_file_paths", "extract_json_array", "flag_enabled",
        "merge_card_group", "optional_positive_int", "read_bootstrap_meta", "run_parallel", "select_representative_files",
        "write_bootstrap_meta",
    ),
    "hubofhubs.the_body.internal_context.card_store.context_card_ceilings": (
        "FILE_SET_DEDUP_JACCARD", "MAX_CARDS_PER_FOLDER_DEFAULT", "MIN_FILES_PER_CARD", "apply_card_ceilings", "card_folder_key",
        "card_is_too_thin", "card_preference_key", "collapse_cards_by_file_set", "folders_for_room", "path_is_data_file", "positive_int",
    ),
    "hubofhubs.the_body.internal_context.card_store.context_card_extraction": (
        "LINKED_FOLDER_BOOST", "RECENCY_BOOST_HALF_LIFE_DAYS", "RECENCY_BOOST_MAX_DEFAULT", "RECENCY_BOOST_USAGE_CAP", "SOURCE_FILE_WEIGHT",
        "SOURCE_USAGE_MIN_INTERVAL_SECONDS", "TEST_FILE_WEIGHT", "build_rich_summary", "card_covered_paths", "card_display_title",
        "card_slug", "discover_areas", "extract_file_snippet", "extract_symbols", "extract_topic_cards", "is_test_path", "managed_names",
        "path_slug", "summarize_snippet", "trim_content_by_recency",
    ),
    "hubofhubs.the_body.internal_context.card_store.context_folder_review": (
        "FOLDER_REVIEW_FILE", "FOLDER_REVIEW_MIN_FILES", "FOLDER_REVIEW_START_DEPTH", "HARD_RISK_KINDS", "ai_instruction_files_in",
        "dir_file_counts", "drop_verdicts_under_final_exclusions", "duplicate_folders", "final_exclusion_covering", "folder_review",
        "has_kept_child", "is_excluded_folder", "load_verdicts", "nested_vcs_dirs", "review_corpus", "roll_up_to_depth", "verdict_is_final",
        "verdict_is_pinned",
    ),
    "hubofhubs.the_body.internal_context.card_store.embedders": (
        "EMBED_BATCH_DEFAULT", "EMBED_MAX_CHARS_DEFAULT", "FASTEMBED_EMBEDDER_ID",
    ),
    "hubofhubs.the_body.internal_context.card_store.interface": (
        "CardStore",
    ),
    "hubofhubs.the_body.internal_context.card_store.qdrant_store": (
        "QdrantVectorStore", "point_id", "scope_hash",
    ),
    "hubofhubs.the_body.internal_context.card_store.text_sampling": (
        "extract_terms", "keywords_from_text", "select_representatives",
    ),
    "hubofhubs.the_body.internal_context.card_store.vector_scopes": (
        "SeedItems",
    ),
    "hubofhubs.the_body.internal_context.card_store.walk": (
        "effective_skip_dirs", "is_claude_state_file", "prune_dirnames", "skip_subtrees",
    ),
    "hubofhubs.the_body.internal_context.context": (
        "AssembledContext", "ContextAssembler", "ContextAssemblerBase", "ConversationContext", "ConversationStore", "VectorHit",
        "VectorStore", "VectorStoreBase",
    ),
    "hubofhubs.the_body.internal_context.interface": (
        "InternalContexting",
    ),
    "hubofhubs.the_body.internal_context.run_store.execution_record": (
        "ExecutionFact", "ExecutionRecord", "classify_exec_phase",
    ),
    "hubofhubs.the_body.internal_context.run_store.jsonl_ledger": (
        "default_directory",
    ),
    "hubofhubs.the_body.internal_context.run_store.tool_ledger": (
        "FileToolLedger", "STUCK_OUTPUT_ALIKE", "STUCK_REASON_ALIKE", "ToolOutcome", "alike", "changed_something", "describe_failure",
        "failure_signature", "outcome_from_result", "repeated_failure", "unrecovered_failures",
    ),
    "hubofhubs.the_consciousness.communication": (
        "ANNOUNCE_KEY", "CommunicationPolicy", "DEFAULT_COMMUNICATION_POLICY", "DELIVER_ASK", "DELIVER_DURABLE", "DELIVER_NOTHING", "DELIVER_STATUS",
        "Delivery", "LONG_STRETCH_SECONDS", "TurnCommunicator", "TurnSoFar", "communicate",
    ),
    "hubofhubs.the_consciousness.feedback_learning.interface": (
        "FeedbackLearning",
    ),
    "hubofhubs.the_consciousness.interface": (
        "HumanAdapting",
    ),
    "hubofhubs.the_consciousness.judgment_calls.interface": (
        "JudgmentCalling",
    ),
    "hubofhubs.the_consciousness.prioritization.interface": (
        "Prioritizing",
    ),
    "hubofhubs.the_consciousness.prioritization.types": (
        "Ranked", "Stated",
    ),
    "hubofhubs.the_consciousness.representatives.interface": (
        "Representing",
    ),
    "hubofhubs.the_consciousness.request_intake.interface": (
        "RequestIntaking",
    ),
    "hubofhubs.the_consciousness.terminal.interface": (
        "Conversing",
    ),
    "hubofhubs.the_consciousness.terminal": (
        "Block", "TerminalState", "answer_ask", "close_ask", "continue_message", "fold_ask", "settle", "toggle_trail", "toggle_updates",
        "unfold_ask",
    ),
    "hubofhubs.the_consciousness.feedback_learning.propose": (
        "ScopedRecordEdit", "SIGNALS",
    ),
    "hubofhubs.the_consciousness.terminal.asks": (
        "error_block", "is_for_viewer",
    ),
    "hubofhubs.the_consciousness.terminal.trace": (
        "WorkTrace", "domain_of", "project", "validate",
    ),
    "hubofhubs.the_intelligence.critical_thinking.decision_check.agreement": (
        "AgreementCheck", "AgreementWithKnownMistakes", "DraftAsGiven", "MajorityVote", "SingleVerify", "UNCONFIRMED_REPLY",
    ),
    "hubofhubs.the_intelligence.critical_thinking.decision_check.checks": (
        "CheckBinding", "View", "Vote", "as_binding",
    ),
    "hubofhubs.the_intelligence.critical_thinking.decision_check.interface": (
        "DecisionChecking", "OUTCOMES",
    ),
    "hubofhubs.the_intelligence.critical_thinking.decision_check.remainder": (
        "Unit", "cohere", "cohered_text", "complete", "dangling", "joined", "shorten", "shortened_text", "units_of",
    ),
    "hubofhubs.the_intelligence.critical_thinking.decision_check.mistakes": (
        "CONFIRMED_FAILURE", "Line", "LineBook", "Mistake", "MistakeLog", "adopt", "distill", "new_mistake", "overruled_mistakes", "retire",
    ),
    "hubofhubs.the_intelligence.critical_thinking.esoi_application.apply": (
        "RecordFieldEdit", "TableRecords",
    ),
    "hubofhubs.the_intelligence.critical_thinking.esoi_application.interface": (
        "EsoiApplying", "RecordsSource",
    ),
    "hubofhubs.the_intelligence.critical_thinking.goal_completion.done_evidence": (
        "CONTINUE", "Reading", "clean_requirements", "continue_decision", "coverage_gap", "coverage_progress", "evidence_coverage", "interim_data",
        "measure", "parse_coverage", "render_continue_plan", "render_coverage_line", "render_requirements", "rubric_coverage",
    ),
    "hubofhubs.the_intelligence.critical_thinking.goal_completion.interface": (
        "GoalCompleting",
    ),
    "hubofhubs.the_intelligence.critical_thinking.goal_completion.sufficiency": (
        "AbridgedTurnState", "READ_SPEC_KEYS", "collect_abridged_items", "render_abridged_notice",
    ),
    "hubofhubs.the_intelligence.critical_thinking.pursuit": (
        "BoundedReplan", "Increment", "LADDER", "REFUSED_BOOKKEEPING", "bookkeeping_only", "choose_increment", "doable_by_ai", "only_bookkeeping_writes",
    ),
    "hubofhubs.the_intelligence.critical_thinking.metric_upkeep.interface": (
        "MetricUpkeeping",
    ),
    "hubofhubs.the_intelligence.critical_thinking.metric_upkeep.upkeep": (
        "RecordFieldUpkeep", "state_of",
    ),
    "hubofhubs.the_intelligence.critical_thinking.esoi_application.repo_records": (
        "RepoRecords",
    ),
    "hubofhubs.the_intelligence.critical_thinking.solution_passes.interface": (
        "DEFAULT_LIMITS", "SolutionConsidering",
    ),
    "hubofhubs.the_intelligence.critical_thinking.solution_passes.passes": (
        "NetworkPasses",
    ),
    "hubofhubs.the_intelligence.critical_thinking.solution_passes.depth": (
        "build_out", "default_combine", "default_split", "verbatim_combine",
    ),
    "hubofhubs.the_intelligence.critical_thinking.solution_passes.write_back": (
        "combined_check", "descendants", "proposals_of",
    ),
    "hubofhubs.the_intelligence.subconscious.relevant_solutions.interface": (
        "SolutionRelevance",
    ),
    "hubofhubs.the_intelligence.subconscious.relevant_solutions.network": (
        "SolutionNetwork", "network_of",
    ),
    "hubofhubs.the_intelligence.subconscious.relevant_solutions.records_index": (
        "RecordsIndex", "shaped",
    ),
    "hubofhubs.the_intelligence.subconscious.relevant_solutions.records_then_model": (
        "RecordsThenModel",
    ),
    "hubofhubs.the_intelligence.subconscious.solution_briefs": (
        "briefs",
    ),
    "hubofhubs.the_intelligence.subconscious.cards_from_files.knowledge_cards": (
        "cards_of", "knowledge_card", "solution_card",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.knowledge_pick": (
        "pick",
    ),
    "hubofhubs.the_intelligence.mind.planner.solution_pieces": (
        "tie",
    ),
    "hubofhubs.the_intelligence.critical_thinking.interface": (
        "CriticalThinking",
    ),
    "hubofhubs.the_intelligence.critical_thinking.flow": (
        "CriticalThinkingComposition",
    ),
    "hubofhubs.the_intelligence.critical_thinking.metric_translation.interface": (
        "MetricTranslating",
    ),
    "hubofhubs.the_intelligence.critical_thinking.response_quality.citations": (
        "dois_in", "strip_unlisted_dois",
    ),
    "hubofhubs.the_intelligence.critical_thinking.response_quality.date_arithmetic": (
        "DAY_THEN_MONTH", "MONTHS", "MONTH_NUMBER", "MONTH_THEN_DAY", "dates_in", "day_count_errors", "event_offset_errors", "month_of", "today_of",
    ),
    "hubofhubs.the_intelligence.critical_thinking.response_quality.em_dash_free": (
        "clean_value", "remove_em_dashes",
    ),
    "hubofhubs.the_intelligence.critical_thinking.response_quality.figure_grounding": (
        "evidence_of", "strip_unsupported",
    ),
    "hubofhubs.the_intelligence.critical_thinking.response_quality.interface": (
        "ResponseJudging",
    ),
    "hubofhubs.the_intelligence.critical_thinking.response_quality.link_detect": (
        "MAX_LISTED_LINKS", "links_in_message",
    ),
    "hubofhubs.the_intelligence.critical_thinking.response_quality.machine_paths": (
        "clean_roots", "relativize",
    ),
    "hubofhubs.the_intelligence.critical_thinking.response_quality.link_guard": (
        "DEAD", "LinkGuard", "LinkPolicy", "OK", "UNKNOWN", "build_link_guard", "evidence_text", "normalize_url_for_match",
    ),
    "hubofhubs.the_intelligence.higher_mind.guidance.interface": (
        "Guiding",
    ),
    "hubofhubs.the_intelligence.higher_mind.interface": (
        "HigherMind",
    ),
    "hubofhubs.the_intelligence.higher_mind.long_term_memory.interface": (
        "LongTermMemory",
    ),
    "hubofhubs.the_intelligence.higher_mind.long_term_memory.recall": (
        "CardStoreRecall", "FileRecall", "RecentWindow",
    ),
    "hubofhubs.the_intelligence.higher_mind.objectives.interface": (
        "Objectives",
    ),
    "hubofhubs.the_intelligence.interface": (
        "InformationProcessing",
    ),
    "hubofhubs.the_intelligence.mind.context_intake.doctrine": (
        "Doctrine", "Rule", "assemble_doctrine", "check_rules",
    ),
    "hubofhubs.the_intelligence.mind.context_intake.interface": (
        "ContextTaking",
    ),
    "hubofhubs.the_intelligence.mind.delegation.interface": (
        "Delegating",
    ),
    "hubofhubs.the_intelligence.mind.delegation.limits": (
        "AUTO_FOLLOWUP_ASK_MAX_CHARS", "AUTO_FOLLOWUP_DONE_MAX_CHARS", "AUTO_FOLLOWUP_MAX_RUNS", "AUTO_FOLLOWUP_REMAINING_MAX_CHARS",
        "AUTO_FOLLOWUP_TOKEN_BUDGET", "DEEP_CONTINUATION_TURN_MULTIPLIER_CAP", "DEFAULT_CARD_MERGE_SIMILARITY", "DEFAULT_DEEP_MAX_TURNS",
        "DEFAULT_MAX_CONSECUTIVE_READS", "DEFAULT_MAX_DEEP_SUBTASKS", "DEFAULT_MAX_ELAPSED_SECONDS", "DEFAULT_MAX_GATHERED_CHARS",
        "DEFAULT_MAX_GATHER_CHARS", "DEFAULT_MAX_PARALLEL", "DEFAULT_MAX_PLAN_STAGES", "DEFAULT_MAX_PLAN_TASKS",
        "DEFAULT_MAX_READS_PER_STEP", "DEFAULT_MAX_STEPS", "DEFAULT_MAX_SUBQUESTIONS", "DEFAULT_PLANNER_ABBREVIATE_REPEAT_CONTEXT",
        "DEFAULT_PLANNER_COMPRESS_OVER", "DEFAULT_PLANNER_CONTEXT_MAX_CHARS", "DEFAULT_PLANNER_GATHERED_MAX_CHARS",
        "DEFAULT_PLANNER_RECENT_FULL", "DEFAULT_PLANNER_TRANSCRIPT_MAX_CHARS", "PENDING_READ_MAX_RUNS", "result_landed_work",
        "result_reports_something",
    ),
    "hubofhubs.the_intelligence.mind.delegation.overseer.oversee": (
        "OverseeMixin",
    ),
    "hubofhubs.the_intelligence.mind.delegation.overseer.risk": (
        "OVERSEE_TOOL", "OverseerSignal", "RunOverseer", "to_risk_signal",
    ),
    "hubofhubs.the_intelligence.mind.delegation.overseer.turn": (
        "Emitter", "TurnCardCache",
    ),
    "hubofhubs.the_intelligence.mind.delegation.overseer.watch": (
        "worth_a_look",
    ),
    "hubofhubs.the_intelligence.mind.interface": (
        "Reasoning",
    ),
    "hubofhubs.the_intelligence.mind.phases": (
        "run_phases",
    ),
    "hubofhubs.the_intelligence.mind.planner.cascade": (
        "CONFIDENCE_LEVELS", "ESCALATABLE_ACTIONS", "apply_review", "escalation_spec", "should_escalate", "truncate_keep_both_ends",
        "user_goal_fallback",
    ),
    "hubofhubs.the_intelligence.mind.planner.interface": (
        "Planning",
    ),
    "hubofhubs.the_intelligence.mind.planner.plan": (
        "PlanDecision",
    ),
    "hubofhubs.the_intelligence.mind.planner.schema": (
        "compact_schema", "normalize_choice", "strip_schema_descriptions",
    ),
    "hubofhubs.the_intelligence.mind.planner.staged_plan": (
        "count_tasks", "is_staged", "normalize_staged_subtasks", "sequence_stages", "split_plan", "step_allows", "tasks_flat", "tasks_in",
    ),
    "hubofhubs.the_intelligence.mind.reference_resolver.interface": (
        "OUTCOMES", "ReferenceResolving",
    ),
    "hubofhubs.the_intelligence.mind.reference_resolver.resolving": (
        "ExactMatch", "ModelJudged", "ReferenceNotSettled", "SharedWords",
    ),
    "hubofhubs.the_intelligence.mind.request_router.interface": (
        "ROUTES", "RequestRouting",
    ),
    "hubofhubs.the_intelligence.mind.request_router.routing": (
        "MajorityFloor", "PlanDerived", "RouteError", "SingleClassifier", "parse_route", "route_from_report",
    ),
    "hubofhubs.the_intelligence.mind.response_writer.answer": (
        "AnswerKit", "AnsweringMixin",
    ),
    "hubofhubs.the_intelligence.mind.response_writer.interface": (
        "ResponseWriting",
    ),
    "hubofhubs.the_intelligence.mind.text": (
        "clip_head_and_tail", "ellipsize", "sentence",
    ),
    "hubofhubs.the_intelligence.nervous_system.interface": (
        "RiskWatching",
    ),
    "hubofhubs.the_intelligence.proactivity.interface": (
        "Proactive",
    ),
    "hubofhubs.the_intelligence.proactivity.triggers": (
        "attach_events", "candidate_of", "in_priority_order",
    ),
    "hubofhubs.the_intelligence.proactivity.window": (
        "Window",
    ),
    "hubofhubs.the_intelligence.subconscious.cards_from_files.cards_from_files": (
        "changed_cards", "file_card", "group_card",
    ),
    "hubofhubs.the_intelligence.subconscious.cards_from_files.conversation_card_builder": (
        "ConversationCardBuilder",
    ),
    "hubofhubs.the_intelligence.subconscious.cards_from_files.conversation_format": (
        "compact_message", "conversation_digest", "conversation_messages", "conversation_metadata", "conversation_timestamp",
        "conversation_to_text", "find_conversation_dirs", "is_claude_conversation", "load_conversations", "nl_terms", "parse_date_bound",
        "rank_candidates_by_digest", "resolve_conv_key", "scan_conversation_files", "select_current_slice", "select_related",
        "timestamp_in_range", "truncate_transcript_middle",
    ),
    "hubofhubs.the_intelligence.subconscious.cards_from_files.interface": (
        "CardsFromFiles",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.abstain": (
        "AbstainingHybrid", "AbstainingLearned", "CONFIDENCE_FLOOR", "confidence",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.assemblers.composite_assembler": (
        "CompositeContextAssembler", "find_assembler",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.assemblers.hybrid_assembler": (
        "CONSOLIDATE_MIN_REMAINING_SECONDS", "RRF_K", "VECTOR_RANK_WEIGHT", "arm_scores", "fused_card_order",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.assemblers.record_assembler": (
        "RecordContextAssembler",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.assemblers.vector_assembler": (
        "MAX_SEED_ITEMS_DEFAULT", "SNIPPET_MAX_CHARS", "VECTOR_HIT_MAX_CARD_REFS", "VECTOR_HIT_MAX_CARD_REF_CHARS",
        "seed_source_takes_limit", "snippet", "task_slug",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.affinity_tags": (
        "affinity_factor",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.card_content_render": (
        "MAX_CARD_REFS", "MAX_CARD_REF_CHARS", "MAX_CARD_REF_ITEM_CHARS", "content_identity_key", "content_item_text", "dedupe_content",
        "filter_content_by_time_range", "locator_label", "mark_items_used", "normalize_content", "rank_content_by_recency_relevance",
        "render_block_lines", "render_card_content", "clear_resolution_memo", "render_card_content_blocks", "tokenize",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.card_selection": (
        "CONTEXT_DEPTH_KEY", "DECISIVE_CARD_SCORE", "DEPTH_RETRIEVE", "CardMetadata", "cheap_result_is_decisive", "retrieve_only", "stable_card_order",
        "with_retrieve_depth",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.card_thread": (
        "ACTION_CONTINUE", "ACTION_NEW", "ACTION_SWITCH", "CardCandidate", "CardThreadContext", "CardThreadDecision", "FINISHED_STATUSES",
        "STATUS_ACTIVE", "STATUS_ARCHIVED", "STATUS_COMPLETED", "STATUS_DORMANT", "card_id_set", "find_duplicate_label", "lifecycle_note",
        "merge_candidates", "normalize_label", "parse_card_thread", "penalized_budget", "rank_card_first", "render_thread_hint",
        "select_thread_floor", "split_by_card",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.reference_resolver": (
        "NoteResolver", "ReferenceResolver", "build_resolver_registry", "coerce_resolver", "collect_reference_resolvers",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.context_cards.scope_tags": (
        "ScopeTags", "as_tag_list", "scope_tags_allow", "scope_tags_from_keys", "union_scope_tags",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.dense": (
        "DenseBgeSmall", "LatentSemantic",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.fusion": (
        "Candidates", "FeatureRerank", "FeatureRerankNoPriors", "HybridRrf",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.interface": (
        "ContextRetrieval",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.learned": (
        "LearnedRerank",
    ),
    "hubofhubs.the_intelligence.subconscious.context_retriever.lexical": (
        "Bm25Body", "Bm25Fielded", "Bm25WholeFiles",
    ),
    "hubofhubs.the_intelligence.subconscious.interface": (
        "Remembering",
    ),
    "hubofhubs.the_intelligence.subconscious.intuition.co_taken": (
        "CoTaken",
    ),
    "hubofhubs.the_intelligence.subconscious.intuition.interface": (
        "Intuiting",
    ),
    "hubofhubs.the_intelligence.subconscious.intuition.nearest_cards": (
        "NearestCards",
    ),
    "hubofhubs.the_self.assembler.interface": (
        "WholeAssembling",
    ),
    "hubofhubs.the_self.assembler.oneline": (
        "Result",
    ),
    "hubofhubs.the_self.integrity.audit": (
        "PromptsAsData", "config_share",
    ),
    "hubofhubs.the_self.integrity.interface": (
        "Genericity",
    ),
    "hubofhubs.the_self.integrity.measure": (
        "KINDS",
    ),
    "hubofhubs.the_self.interface": (
        "SelfAnswering",
    ),
    "hubofhubs.the_self.role_understanding.interface": (
        "RoleUnderstanding",
    ),
    "hubofhubs.the_world.interface": (
        "TakingIn",
    ),
    "hubofhubs.the_world.learning.interface": (
        "Staying",
    ),
    "hubofhubs.the_world.learning.research_freshness_reader.interface": (
        "FreshnessReading",
    ),
    "hubofhubs.the_world.model_plumbing.interface": (
        "ModelPlumbing",
    ),
    "hubofhubs.the_world.model_plumbing.model": (
        "ModelProvider", "ModelProviderBase", "STEP_JUDGE", "STEP_NARRATION", "STEP_PLAN", "STEP_REPLY", "STEP_SELECT", "STEP_SUMMARIZE",
        "STEP_UNDERSTAND", "STEP_VERIFY", "answer_with_reasoning", "plan_with_step",
    ),
    "hubofhubs.the_world.model_plumbing.model_tier_chooser.interface": (
        "TierSelection",
    ),
    "hubofhubs.the_world.model_plumbing.model_tier_chooser.tiers": (
        "rates",
    ),
    "hubofhubs.the_world.model_plumbing.scope": (
        "ScopedThreadPoolExecutor",
    ),
    "hubofhubs.the_world.model_plumbing.signature_probe": (
        "accepted_fields", "accepted_keywords", "filter_keywords",
    ),
    "hubofhubs.the_world.model_plumbing.vendor_model_caller.anthropic": (
        "AnthropicProvider",
    ),
    "hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli": (
        "CLI_RUNNABLE_MODELS", "ClaudeCliProvider", "_flatten_block", "_flatten_messages", "extract_json_object",
    ),
    "hubofhubs.the_world.model_plumbing.vendor_model_caller.family": (
        "MODEL_PREFIX_PROVIDERS", "VENDOR_PREFIXES", "newest_in_family", "provider_name_for_model", "resolve_model_name", "split_tokens",
    ),
    "hubofhubs.the_world.model_plumbing.vendor_model_caller.gemini": (
        "GeminiProvider",
    ),
    "hubofhubs.the_world.model_plumbing.vendor_model_caller.interface": (
        "ModelCalling",
    ),
    "hubofhubs.the_world.model_plumbing.vendor_model_caller.layers": (
        "LayerBlock", "join_layers",
    ),
    "hubofhubs.the_world.model_plumbing.vendor_model_caller.openai": (
        "DeepSeekProvider", "OpenAIProvider",
    ),
    "hubofhubs.the_world.model_plumbing.vendor_model_caller.retry": (
        "format_provider_error", "retry_transient",
    ),
    "hubofhubs.the_world.model_plumbing.vendor_model_caller.router": (
        "MultiProvider",
    ),
    "hubofhubs.the_world.observation": (
        "Observation", "RetrievalAdapterBase",
    ),
    "hubofhubs.the_world.science.interface": (
        "WorldKnowing",
    ),
    "hubofhubs.the_world.science.openalex": (
        "OpenAlexWorks", "observation_of",
    ),
    "hubofhubs.the_world.tools.connected_system_operations.interface": (
        "ConnectedOperating",
    ),
    "hubofhubs.the_world.tools.connected_system_operations.mcp_client": (
        "MCPClient", "MCPResourceResult", "MCPServerSpec", "MCPToolResult",
    ),
    "hubofhubs.the_world.tools.connected_system_operations.mcp_operations": (
        "MCPOperationRunner",
    ),
    "hubofhubs.the_world.tools.acknowledge": (
        "ACK_TEXT", "ACK_WITHIN_SECONDS", "Acknowledger", "STATUS_KIND_ACK", "ack_event", "is_ack",
    ),
    "hubofhubs.the_world.tools.deep": (
        "DeepResult", "DeepRunner", "DeepRunnerBase", "FUTURE_CONTEXT_VIA_FIELD", "FUTURE_CONTEXT_VIA_OUTPUT", "FileWriter",
        "FileWriterBase", "LAUNCH_MISSING_PROGRAM", "LAUNCH_PERMISSION_DENIED", "OperationWriter", "OperationWriterBase", "ProgressEvent",
        "ProgressSink", "ProgressSinkBase", "WRITE_SURFACE_AGENT", "WRITE_SURFACE_FILES", "WRITE_SURFACE_OPERATIONS", "WriteResult",
        "runner_starts_background_work", "runner_uses_deep_model",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.acp_config": (
        "ALLOW", "AcpSettings", "HUMAN", "REJECT", "classify_permission", "node_major_version", "permission_response", "select_option",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.acp_protocol": (
        "ACP_MODEL_FAMILIES", "ACP_PROTOCOL_VERSION", "AcpUnavailable", "DEFAULT_AGENT_BINARY", "EFFORT_CONFIG_ID", "FILE_CHANGE_KINDS",
        "FILE_CHANGE_TOOLS", "MAX_MESSAGE_CHARS", "MAX_THOUGHT_CHARS", "MIN_NODE_MAJOR", "MISSING", "MODEL_CONFIG_ID", "PHASE_DONE",
        "PHASE_ERROR", "PHASE_ESCALATED", "PHASE_HEARTBEAT", "PHASE_MESSAGE", "PHASE_PLAN", "PHASE_SESSION", "PHASE_STEER",
        "PHASE_THINKING", "PHASE_TOOL_CALL", "PHASE_TOOL_ERROR", "PHASE_TOOL_PROGRESS", "PHASE_TOOL_RESULT", "STEERING_EXT_METHOD",
        "STEERING_IDLE_BEHAVIOR", "STOP_REASON_FAILURES", "TOOL_COMPLETED", "TOOL_STATUS_PHASES", "chunk_text", "field_of",
        "landed_file_change", "meta_of", "tool_line", "tool_name_of", "translate_session_update", "truncate", "usage_from_prompt_response",
        "usage_from_update",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.acp_runner": (
        "AcpDeepRunner", "acp_model_family",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.acp_session": (
        "AcpRun", "AcpSessionClient", "open_agent_connection",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.contract": (
        "BALANCED_CLI_MODEL", "CANCEL_POLL_SECONDS", "CLAUDE_CODE_MODEL_PATTERN", "DEEP_REVIEW_CALL_TIMEOUT_SECONDS", "DEEP_REVIEW_PROMPT",
        "DEFAULT_CANCEL_GRACE_SECONDS", "DEFAULT_DEEP_REVIEW_MODEL", "DEFAULT_MONITOR_HEARTBEAT_SECONDS", "ESCALATION_ID_RE", "GoalRunner",
        "RESUME_TARGET_MISSING_MARKERS", "SubprocessConfig", "WEB_TOOLS", "envelope_reports_no_work", "kill_process_group",
        "parse_deep_review", "parse_worker_output", "resume_target_missing", "signal_process_group", "stop_process_group",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.control": (
        "ControlMessage", "RunControl",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.arm_choice": (
        "ArmChoice", "build_agent_runner", "choose_agent_arm", "harness_class",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.headless_runner": (
        "CodexCliRunner", "HeadlessCliRunner", "OpencodeRunner",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.interface": (
        "AgentSessions",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.providers": (
        "ANY", "credential_names", "drives", "model_for", "providers_of",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.launch": (
        "DeepLaunchSettings", "build_deep_argv", "lean_flags",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.session": (
        "SESSION_TAIL_MAX_ACTIONS", "SESSION_TAIL_MAX_BYTES", "SESSION_TAIL_MAX_CHARS", "SESSION_TAIL_THIN_OUTPUT_CHARS",
        "resolve_session_file", "session_record_paths", "subagent_work_in_flight", "worker_output_is_thin",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.settings": (
        "GoalSettings",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.stream_runner": (
        "DEFAULT_ECHO_WAIT_SECONDS", "LOOP_TICK_SECONDS", "MIN_STREAM_CONTROL_VERSION", "Sent", "StreamJsonGoalRunner", "StreamRun",
        "VERSION_CACHE", "VERSION_RE", "cli_version", "echo_text", "interrupt_line", "user_line",
    ),
    "hubofhubs.the_world.tools.delegated_agent_sessions.subprocess_runner": (
        "SubprocessGoalRunner",
    ),
    "hubofhubs.the_world.tools.events": (
        "EVENT_CARD_THREAD", "EVENT_CONTEXT", "EVENT_DECISION", "EVENT_DONE", "EVENT_EXEC", "EVENT_EXPLANATION", "EVENT_INTENT",
        "EVENT_INTERIM", "EVENT_MILESTONE", "EVENT_MODE_SIGNAL", "EVENT_OVERSEER", "EVENT_PARTIAL", "EVENT_PLAN", "EVENT_READ",
        "EVENT_REPLAN", "EVENT_RESULT", "EVENT_STATUS", "EVENT_TOKENS", "EVENT_UNDERSTANDING", "EVENT_WORK_TRACE", "Mode",
        "SURFACING_EVENTS",
    ),
    "hubofhubs.the_world.tools.file_editing.fast_edit": (
        "FastEditRunner",
    ),
    "hubofhubs.the_world.tools.file_editing.interface": (
        "FileEditing",
    ),
    "hubofhubs.the_world.tools.file_reading.interface": (
        "FileReading",
    ),
    "hubofhubs.the_world.tools.interface": (
        "Tooling",
    ),
    "hubofhubs.the_world.tools.secret_redaction": (
        "ASSIGNMENT_TEMPLATE", "BARE_PLACEHOLDERS", "CLI_LONG_FLAG", "CLI_SHORT_P", "DIGIT_REQUIRED_PATTERNS", "KEY_ASSIGNMENT",
        "PREFIXED_VALUE_PATTERNS", "REDACTED", "Redactor", "STRONG_ASSIGNMENT", "URI_CREDENTIALS", "digit_gate", "looks_like_reference",
        "redact", "redact_assignment", "redact_cli",
    ),
    "hubofhubs.the_world.tools.web_search.backends": (
        "ConfiguredJsonBackend", "FallbackSearchBackend", "dotted", "fill", "gemini_api_key_from_env", "load_file_specs",
    ),
    "hubofhubs.the_world.tools.web_search.cache": (
        "WebCache", "normalize_query",
    ),
    "hubofhubs.the_world.tools.web_search.fetch": (
        "FetchedPage", "PageFetchError", "UnsupportedContentTypeError", "canonicalize_url", "default_page_fetcher",
    ),
    "hubofhubs.the_world.tools.web_search.gemini": (
        "GeminiGroundingBackend",
    ),
    "hubofhubs.the_world.tools.web_search.interface": (
        "SearchBackend",
    ),
    "hubofhubs.the_world.tools.web_search.limiter": (
        "DailyLimiter",
    ),
    "hubofhubs.the_world.tools.web_search.link_access": (
        "REASON_MESSAGES", "REASON_NOT_FOUND", "REASON_NOT_SHARED", "REASON_TOO_LARGE", "REASON_UNREACHABLE", "REASON_UNSUPPORTED_TYPE",
        "extract_pdf_text", "link_not_read_error", "rewrite_for_export",
    ),
    "hubofhubs.the_world.tools.web_search.page_extract": (
        "check_url_is_safe", "estimate_tokens", "extract_main_text", "select_passages", "split_passages",
    ),
    "hubofhubs.the_world.tools.web_search.provider_adapter": (
        "ProviderWebSearchAdapter",
    ),
    "hubofhubs.the_world.tools.web_search.query_spec": (
        "coerce_web_query",
    ),
    "hubofhubs.the_world.tools.web_search.research": (
        "paginate_text",
    ),
    "hubofhubs.the_world.tools.web_search.search_port": (
        "SearchBackendError", "SearchHit", "SearchResponse",
    ),
}

# public name -> module:attribute, where the public name differs from the attribute
RENAMED = {
    "CANDIDATE_FIELDS": "hubofhubs.the_consciousness.prioritization.types:FIELDS",
    "PRIORITY_SUBJECTS": "hubofhubs.the_consciousness.prioritization.types:SUBJECTS",
    "TRIGGER_KINDS": "hubofhubs.the_intelligence.proactivity.triggers:KINDS",
    "WINDOW_DAYS": "hubofhubs.the_intelligence.proactivity.window:DAYS",
    "acp_protocol_log": "hubofhubs.the_world.tools.delegated_agent_sessions.acp_protocol:log",
    "bm25_store_BOOTSTRAP_MAX_BYTES": "hubofhubs.the_intelligence.subconscious.context_retriever.assemblers.bm25_store:BOOTSTRAP_MAX_BYTES",
    "bm25_store_SOURCE_EXTS": "hubofhubs.the_intelligence.subconscious.context_retriever.assemblers.bm25_store:SOURCE_EXTS",
    "card_store_hygiene_jaccard": "hubofhubs.the_body.internal_context.card_store.card_store_hygiene:jaccard",
    "card_store_hygiene_store_id_of": "hubofhubs.the_body.internal_context.card_store.card_store_hygiene:store_id_of",
    "card_store_identity_BOOTSTRAP_META_FILE": "hubofhubs.the_body.internal_context.card_store.card_store_identity:BOOTSTRAP_META_FILE",
    "card_store_identity_store_id_of": "hubofhubs.the_body.internal_context.card_store.card_store_identity:store_id_of",
    "card_store_tidy_plan_ALL_REASONS": "hubofhubs.the_body.internal_context.card_store.card_store_tidy_plan:ALL_REASONS",
    "context_bootstrap_support_BOOTSTRAP_MAX_BYTES": "hubofhubs.the_body.internal_context.card_store.context_bootstrap_support:BOOTSTRAP_MAX_BYTES",
    "context_bootstrap_support_BOOTSTRAP_META_FILE": "hubofhubs.the_body.internal_context.card_store.context_bootstrap_support:BOOTSTRAP_META_FILE",
    "context_bootstrap_support_SOURCE_EXTS": "hubofhubs.the_body.internal_context.card_store.context_bootstrap_support:SOURCE_EXTS",
    "context_bootstrap_support_jaccard": "hubofhubs.the_body.internal_context.card_store.context_bootstrap_support:jaccard",
    "contract_log": "hubofhubs.the_world.tools.delegated_agent_sessions.contract:log",
    "link_access_ALL_REASONS": "hubofhubs.the_world.tools.web_search.link_access:ALL_REASONS",
    "ordered_ids": "hubofhubs.the_consciousness.prioritization.types:ids_of",
}

LOCATIONS = {**{name: f"{module}:{name}" for module, defined in NAMES.items() for name in defined},
             **{module.rsplit(".", 1)[-1]: module for module in MODULES}, **RENAMED}

FRONT_DOOR = ("run", "assemble", "needs", "Binding", "AssemblyConfig", "AssemblyError", "Assembly", "Result", "assembler", "choice",
              "evaluate", "evaluate_seats", "check", "metrics", "names", "register", "resolve")
__all__ = sorted(set(LOCATIONS) | set(FRONT_DOOR))


def __getattr__(name: str):
    target = LOCATIONS.get(name)
    if target is None:
        raise AttributeError(f"hubofhubs.api has no public name {name!r}")
    module, _, attribute = target.partition(":")
    found = importlib.import_module(module)
    value = getattr(found, attribute) if attribute else found
    globals()[name] = value
    return value


def __dir__():
    return __all__
