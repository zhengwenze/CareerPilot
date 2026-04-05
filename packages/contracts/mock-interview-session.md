# Mock Interview Session Contract

## Purpose

Describe the shared facts for session-based interview practice.

## Core entities

- mock interview session
- interview turn
- review summary

## Required guarantees

- session keeps source job and resume context
- current turn and question progression are explicit
- prep, retry, finish, and delete remain modeled as lifecycle actions
- review output is part of the persistent workflow result

## Example payload fields

- `status`
- `question_count`
- `main_question_index`
- `followup_count_for_current_main`
- `prep_state`
- `current_turn`
- `turns`
- `review`
