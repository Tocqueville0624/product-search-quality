# Development case review protocol

Status: the script creates a reading queue. Human review remains pending until a
person actually records their judgements. Automatic sampling, CSV generation, and
model explanations are not human annotation or inter-annotator agreement.

## Scope and provenance

`scripts/development_cases.py` reads the selected model name and seed from
`experiments/frozen_study.json`, then reads only that model's validation
predictions and the validation feature partition. It does not access test
predictions, refit a model, edit the freeze, or change the operational review
policy. The model and final evaluation code remain unchanged.

Within each published-label versus predicted-label error combination, it takes
up to four examples using a deterministic SHA-256 ordering of seed and example
ID. There are twelve off-diagonal confusion cells, so the queue contains at most
48 cases. This deliberate balance helps a reader encounter several error types.
Its percentages cannot estimate the frequency of errors in the benchmark or in
production. A missing cell means that this fitted model made no such validation
error, rather than a sampling failure.

This teaching queue uses known validation labels to select illustrative errors.
It is separate from the project's operational review simulation, which selects
predicted-Exact pairs using model scores without observing their labels.

## Files

- `experiments/runs/development_cases.csv`: local query/title text, published
  label, model prediction, numeric evidence, selection reason, and empty human
  review fields. This file is ignored by Git.
- `reports/development_case_index.csv`: public example IDs, published labels,
  predictions, `p_e`, and numerical feature evidence. It contains neither raw
  query/product text nor invented reviewer judgements.

The script's console summary records the selected model, sampling seed, freeze
checksum, available validation error count, and selected count. Keep this
summary with the experiment's execution record. Re-running the script replaces
the CSVs, so preserve a separate version of any completed human annotations
before rerunning it.

## What a reviewer records

1. Read the query and product title and note whether the title provides enough
   context to assess the query's specific requirements.
2. Record the reviewer's own E/S/C/I judgement or `uncertain`. Do not overwrite
   the published label. The available title can omit relevant information.
3. If disagreeing with the published judgement, explain the concrete reason and
   uncertainty. Disagreement is not automatically evidence of a dataset error.
4. Inspect the feature evidence and state which information the model could see
   and which meaning it could not represent. Avoid claiming that one feature
   caused the prediction without a separate attribution analysis.
5. Fill in reviewer, date, judgement, notes, and review status. Keep model-assisted
   observations explicitly marked as such. One reviewer's decisions do not
   establish inter-annotator agreement.

## Reading the numerical evidence

`query_coverage = 1` means every distinct normalized query token appears in the
title. It does not establish relevance: a case, accessory, or incompatible item
can share all those words. `token_jaccard` measures shared vocabulary relative
to the union of both token sets and has no understanding of synonyms.

`query_in_title` checks a full normalized token sequence. `brand_match` requires
all available brand tokens to occur in the query. Neither resolves brand intent,
negation, substitute acceptability, or the distinction between a product and a
compatible accessory.

`numeric_mismatch = 1` means at least one query digit chunk is absent from the
title. The feature cannot equate units or distinguish model numbers from sizes.
`numeric_mismatch = 0` therefore does not demonstrate numerical compatibility.
`title_missing` describes unavailable normalized title text.

`p_e` is the model's Exact score. In particular, class-weighted model scores are
not calibrated probabilities of a naturally occurring user outcome. The score
does not measure confidence that a reviewer will agree or a customer will buy.

## Subsequent iterations

If these cases motivate changes after the final test has been examined, describe
the changes as a new exploratory iteration. Do not retrospectively present them
as choices frozen before that test. New confirmatory claims need a fresh
holdout under the project's evaluation plan.
