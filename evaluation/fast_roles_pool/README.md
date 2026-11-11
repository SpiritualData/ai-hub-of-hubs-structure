# fast_roles_pool

Measured evidence that the fast tier does the jobs of the roles that resolve to it (`hubofhubs/the_world/model_plumbing/model_tier_chooser/role_tiers.csv`),
by pooling those roles' own existing cases into one stage and running a tier's model over all of them. It does not choose a tier's default model (that
stays on public evaluations); it answers whether a role's row may say "measured".

- **Cases** (112, none new): the consumer's goal doability, assignee and quest ranking cases, rendered once with its production prompts into
  `datasets/consumer_cases.json` by the consumer's own script (`scripts/build_fast_roles_pool_cases.py` in Quest AI Runner); and the 41 cases of
  `evaluation/folder_view`, read at run time and scored by that component's own scorer through its `model_pick` arm.
- **Weights, fixed before scoring** (`score.py`): every case counts once; an unreadable reply fails; a tier is adequate when its pooled rate is within 0.05
  of the reference's.
- **Arm**: `tier_arm` (parameters `tier`, `candidate`): the model comes from `tier_arms.csv`. Anthropic runs on the Claude CLI login with no key; another
  provider needs its key and its Python library (`openai`), and a missing one stops the arm instead of failing its cases.
- **Run**: `esoi run fast_roles_pool --impl tier_arm@tier=fast --max-calls 150 --keep-going --record --force "<reason>"` (paid; the cost column is what the
  provider reports, informational on a subscription). Free baseline: `--impl fast_roles_pool.broken.no_answer:build --keep-going`.
- **Not pooled** (no case set that fits one call): request_extraction, context_retrieval, card_building, web_search, learning_investigation,
  liveness_review, status_narration, frame_building.
- **Reading it**: the pool is easy for current models and the Folder View cases are passed by the evidence arm with no model (40 of 41), so the stage shows a
  tier is not worse than the tier above; it cannot rank close models.
