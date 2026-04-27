# Workouts Endpoints Backend Guide

This guide summarizes the `Workouts` API endpoints documented in Swagger comments in `endpoints/workouts.py`.

## Base Notes

- All routes in this module require authentication (`@require_auth`).
- The workouts blueprint is registered without a URL prefix in `app.py`, so paths below are absolute.
- UUID values are expected for user identifiers.

## 1) Lookup Endpoints

### `GET /exercise-categories`
- Purpose: list available exercise categories.
- Response `200`: array of `{ category_id, name }`.

### `GET /body-parts`
- Purpose: list available body parts.
- Response `200`: array of `{ body_part_id, name }`.

### `GET /workout-types`
- Purpose: list available workout types.
- Response `200`: array of `{ workout_type_id, name }`.

## 2) Master Exercises

### `GET /exercises`
- Purpose: list master exercise catalog.
- Response `200`: array with fields like:
  - `exercise_id`, `name`, `youtube_url`
  - `body_part_id`, `category_id`
  - `body_part`, `category`

### `GET /exercises/<exercise_id>`
- Purpose: fetch a single exercise from the catalog.
- Path params: `exercise_id` (int).
- Responses:
  - `200`: exercise object (same fields as list).
  - `404`: exercise not found.

## 3) Workout Plans (Templates)

### `GET /workout-plans`
- Purpose: list workout plans.
- Query params in implementation:
  - `created_by` (UUID or `"me"`) to filter owner.
- Responses:
  - `200`: array of plans (`workout_plan_id`, `title`, `created_by`, `duration_min`).
  - `400`: invalid filter format.
  - `403`: unauthorized owner access.

### `GET /workout-plans/<plan_id>`
- Purpose: fetch a plan with assignments and exercises.
- Path params: `plan_id` (int).
- Responses:
  - `200`: plan object including:
    - plan metadata (`title`, `workout_type_id`, `description`, `created_by`, `duration_min`)
    - `assignments[]` (`id`, `weekday`, `schedule_time`)
    - `exercises[]` (`workout_plan_exercise_id`, `exercise_id`, `position`, training fields)
  - `404`: plan not found.

### `POST /workout-plans`
- Purpose: create a new workout plan.
- Body fields:
  - required: `title`
  - optional: `workout_type_id`, `description`, `duration_min`, `created_by`
- Responses:
  - `201`: `{ workout_plan_id }`
  - `400`: invalid input
  - `403`: unauthorized owner assignment.

### `PATCH /workout-plans/<plan_id>`
- Purpose: partially update plan metadata.
- Body fields: `title`, `workout_type_id`, `description`, `duration_min`, `created_by`.
- Responses:
  - `200`: `{ message }`
  - `400`: invalid body/fields
  - `404`: plan not found.

### `POST /workout-plans/<plan_id>/exercises`
- Purpose: add one or multiple exercises to a plan.
- Body:
  - either a single exercise object, or `{ "exercises": [ ... ] }`.
  - each exercise supports `exercise_id`, `position`, and training fields (`sets`, `reps`, `weight`, `rpe`, `duration_sec`, `distance_m`, `pace_sec_per_km`, `calories`, `notes`).
- Responses:
  - `201`: `{ workout_plan_exercise_id }` or `{ workout_plan_exercise_ids: [] }`
  - `400`: invalid exercise/body
  - `404`: plan not found.

### `PUT /workout-plan-exercises/<workout_plan_exercise_id>`
- Purpose: update a plan exercise row.
- Body fields: same training fields as above (and optionally `exercise_id` if valid).
- Responses:
  - `200`: `{ message }`
  - `400`: invalid parameters
  - `404`: plan exercise not found.

### `DELETE /workout-plan-exercises/<workout_plan_exercise_id>`
- Purpose: delete a plan exercise row.
- Responses:
  - `200`: `{ message }`
  - `404`: plan exercise not found.

### `POST /workout-plans/<plan_id>/assignments`
- Purpose: create schedule assignments for a workout plan.
- Body supports one object or `{ "assignments": [ ... ] }`.
- Assignment fields:
  - `weekday` (required)
  - optional: `schedule_time` (`HH:MM[:SS]`).
- Responses:
  - `201`: `{ assignment_id }` or `{ assignment_ids: [] }`
  - `400`: invalid fields
  - `404`: plan not found.

### `GET /workout-plans/<plan_id>/assignments`
- Purpose: list assignments for a plan.
- Response `200`: array of `{ id, workout_plan_id, weekday, schedule_time }`.

### `DELETE /workout-plan-assignments/<assignment_id>`
- Purpose: delete a single assignment.
- Responses:
  - `200`: `{ message }`
  - `404`: assignment not found.

### `DELETE /workout-plans/<plan_id>`
- Purpose: delete an entire plan.
- Responses:
  - `200`: `{ message }`
  - `404`: plan not found.

## 4) Workout Sessions

### `POST /workouts`
- Purpose: create an ad hoc workout session.
- Body fields:
  - required: `user_id` (UUID), `title`
  - optional: `workout_type_id`, `workout_plan_id`, `notes`, `mood`, `duration_mins`, `completion_date` (ISO datetime)
- Responses:
  - `201`: created workout object
  - `400`: invalid input
  - `403`: unauthorized target user
  - `404`: referenced plan not found.

### `POST /workouts/from-plan/<plan_id>`
- Purpose: instantiate a workout session from a plan and clone plan exercises.
- Path params: `plan_id` (int).
- Body fields:
  - optional: `user_id`, `completion_date`, `notes`, `mood`, `duration_mins`
- Responses:
  - `201`: `{ workout_id, notes, mood, duration_mins, completion_date }`
  - `400`: invalid input
  - `404`: plan not found.

### `PATCH /workouts/<workout_id>`
- Purpose: partially update workout metadata.
- Body fields: `notes`, `mood`, `duration_mins`, `completion_date`.
- Responses:
  - `200`: `{ message }`
  - `400`: invalid body/date
  - `404`: workout not found.

### `GET /workouts`
- Purpose: list workouts for a user.
- Query params in implementation:
  - `user_id` (UUID, required).
- Response `200`: array of workout summaries (`workout_id`, `title`, `notes`, `mood`, `duration_mins`, `completion_date`).

### `GET /workouts/<workout_id>`
- Purpose: get full workout details.
- Response `200` includes:
  - workout metadata
  - `assignments[]` from associated plan (if any)
  - `exercises[]` for the workout.
- Response `404`: workout not found.

### `DELETE /workouts/<workout_id>`
- Purpose: delete a workout session.
- Responses:
  - `200`: `{ message }`
  - `404`: workout not found.

## 5) Workout History & Schedule

### `GET /workouts/history/sets-logged`
- Query params used by implementation:
  - `user_id` (UUID), `days` (int).
- Response `200`: array of `{ workout_id, sets_logged, completion_date }`.

### `GET /workouts/history/total-workout-time`
- Query params: `user_id`, `days`.
- Response `200`: array of `{ workout_id, total_workout_time, completion_date }`.

### `GET /workouts/history/total-volume`
- Query params: `user_id`, `days`.
- Response `200`: array of `{ workout_id, total_volume, completion_date }`.

### `GET /workouts/weekly-assignments` and `GET /workouts/current-week`
- Purpose: list workouts for a user with associated weekly assignment slots.
- Query params: `user_id`.
- Response `200`: array of workouts with embedded `assignments[]`.

### `GET /workouts/my_schedule`
- Purpose: return a user's workout plan schedule.
- Query params: `user_id`.
- Response `200`: object containing `my_schedule[]` items:
  - `assignment_id`, `weekday`, `schedule_time`, `workout_plan_id`, `title`, `duration_min`.

## 6) Workout Exercise Rows (Per Workout Session)

### `GET /workouts/<workout_id>/exercises`
- Purpose: list all exercises logged under a workout session.
- Response `200`: array of workout exercise objects.
- Response `404`: workout not found.

### `POST /workouts/<workout_id>/exercises`
- Purpose: add one or more exercises to a workout session.
- Body format:
  - single object or `{ "exercises": [ ... ] }`
  - supports `exercise_id`, `position`, and the training fields.
- Responses:
  - `201`: `{ workout_exercise_id }` or `{ workout_exercise_ids: [] }`
  - `400`: invalid input
  - `404`: workout not found.

### `PUT /workout-exercises/<workout_exercise_id>`
- Purpose: update one workout exercise row.
- Body fields: `position`, `sets`, `reps`, `weight`, `rpe`, `duration_sec`, `distance_m`, `pace_sec_per_km`, `calories`, `notes`.
- Responses:
  - `200`: `{ message }`
  - `400`: invalid input
  - `404`: workout exercise not found.

### `DELETE /workout-exercises/<workout_exercise_id>`
- Purpose: delete one workout exercise row.
- Responses:
  - `200`: `{ message }`
  - `404`: workout exercise not found.

## Common Error Patterns

- `400`: missing required field, invalid UUID, invalid datetime, or malformed body.
- `403`: authenticated user is not allowed to access/modify the target user/plan/workout.
- `404`: requested resource does not exist.

