# Tailored Resume Contract

## Purpose

Describe the shared facts for the bridge from saved job data to a reusable tailored resume result.

## Core entities

- job record
- match report
- resume optimization session

## Required guarantees

- job data remains structured enough for downstream use
- tailored resume state can expose loading, success, failure, retry, and stale conditions
- result remains downloadable when available
- the same result can be used to start mock interview

## Example payload fields

- `status`
- `fit_band`
- `stale_status`
- `resume_version`
- `job_version`
- `selected_tasks`
- `draft_sections`
- `optimized_resume_md`
- `has_downloadable_markdown`
