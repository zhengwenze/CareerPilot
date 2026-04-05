# Resume Pipeline Contract

## Purpose

Describe the shared facts for the master-resume workflow.

## Core entities

- resume record
- resume parse job
- resume parse artifacts
- structured resume data

## Required guarantees

- uploaded resume can be converted into editable Markdown
- saved Markdown remains reusable by later workflow stages
- parse status and task state are explicit
- downstream flows can reference resume version

## Example payload fields

- `id`
- `parse_status`
- `parse_error`
- `structured_json`
- `parse_artifacts_json`
- `latest_version`
- `latest_parse_job`
