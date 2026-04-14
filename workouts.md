# Workouts API

Routes are defined in `endpoints/workouts.py` (`workouts_blueprint`) and registered without an extra URL prefix in `app.py`:

```python
app.register_blueprint(workouts_blueprint)
```

Use `Content-Type: application/json` when sending a body.

---

## Authentication

Every endpoint uses `@require_auth`.

```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

Workout session endpoints are scoped to the authenticated user (`g.user.user_id`).

---

## Endpoint overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/exercise-categories` | List exercise categories |
| GET | `/body-parts` | List body parts |
| GET | `/workout-types` | List workout types |
| GET | `/exercises` | List all exercises (master catalog) |
| GET | `/exercises/<exercise_id>` | Get one exercise |
| GET | `/workout-plans` | List workout plan templates (supports `created_by`) |
| GET | `/workout-plans/<plan_id>` | Plan detail + exercises + assignments |
| POST | `/workout-plans` | Create a workout plan |
| PATCH | `/workout-plans/<plan_id>` | Update a workout plan |
| DELETE | `/workout-plans/<plan_id>` | Delete a workout plan |
| POST | `/workout-plans/<plan_id>/exercises` | Add exercise(s) to a workout plan |
| PUT | `/workout-plan-exercises/<workout_plan_exercise_id>` | Update a workout plan exercise row |
| DELETE | `/workout-plan-exercises/<workout_plan_exercise_id>` | Delete a workout plan exercise row |
| POST | `/workout-plans/<plan_id>/assignments` | Add assignment day/time rows to plan |
| GET | `/workout-plans/<plan_id>/assignments` | List assignment day/time rows for plan |
| DELETE | `/workout-plan-assignments/<assignment_id>` | Delete a workout plan assignment row |
| POST | `/workouts` | Create a workout session |
| POST | `/workouts/from-plan/<plan_id>` | Create workout from plan |
| PATCH | `/workouts/<workout_id>` | Update workout (completion date logging) |
| GET | `/workouts?user_id=<uuid>` | List user workouts |
| GET | `/workouts/weekly-assignments?user_id=<uuid>` | Weekly assignments for user workouts |
| GET | `/workouts/current-week?user_id=<uuid>` | Alias of weekly assignments endpoint |
| GET | `/workouts/<workout_id>` | Get workout detail + exercises + assignments |
| DELETE | `/workouts/<workout_id>` | Delete workout |
| GET | `/workouts/<workout_id>/exercises` | List workout exercises |
| POST | `/workouts/<workout_id>/exercises` | Add workout exercise(s) |
| PUT | `/workout-exercises/<workout_exercise_id>` | Update workout exercise row |
| DELETE | `/workout-exercises/<workout_exercise_id>` | Delete workout exercise row |

---

## Schema changes reflected

- `workout_plans`:
  - `duration_min` (`int`)
  - no direct schedule columns anymore
- `workouts`:
  - `completion_date` (`datetime`)
  - no `schedule_weekday` / `schedule_time`
- `workout_plan_days` (new):
  - `id` (PK)
  - `workout_plan_id` (FK to `workout_plans`)
  - `weekday` (`varchar(10)`)
  - `schedule_time` (`time`)

---

## Workout plan assignments (`workout_plan_days`)

### `POST /workout-plans/<plan_id>/assignments`

Adds one or many assignment rows to a plan.

Send either one object:

```json
{
  "weekday": "Monday",
  "schedule_time": "07:00:00"
}
```

Or bulk:

```json
{
  "assignments": [
    { "weekday": "Monday", "schedule_time": "07:00:00" },
    { "weekday": "Wednesday", "schedule_time": "18:30:00" }
  ]
}
```

Validation:
- `weekday` required, non-empty, max 10 chars
- `schedule_time` required, valid ISO time

Response:
- `201` single created object or bulk wrapper

### `GET /workout-plans/<plan_id>/assignments`

Returns all assignment rows for the plan.

```json
[
  {
    "id": 10,
    "workout_plan_id": 3,
    "weekday": "Monday",
    "schedule_time": "07:00:00"
  }
]
```

### `DELETE /workout-plan-assignments/<assignment_id>`

Deletes one assignment row from `workout_plan_days`.

**200:** `{ "message": "Deleted" }`  
**404:** `{ "error": "Workout plan assignment not found" }`

---

## Workout plan endpoints

### `GET /workout-plans`

Optional query:
- `created_by=me`
- `created_by=<uuid>`

```json
[
  {
    "workout_plan_id": 3,
    "title": "Upper Body",
    "created_by": "uuid",
    "duration_min": 60
  }
]
```

### `GET /workout-plans/<plan_id>`

Includes exercises and assignment rows:

```json
{
  "workout_plan_id": 3,
  "title": "Upper Body",
  "workout_type_id": 2,
  "description": "Push focus",
  "created_by": "uuid",
  "duration_min": 60,
  "assignments": [
    { "id": 10, "workout_plan_id": 3, "weekday": "Monday", "schedule_time": "07:00:00" }
  ],
  "exercises": []
}
```

### `POST /workout-plans`

Fields:
- `title` (required)
- `workout_type_id` (optional)
- `description` (optional)
- `created_by` (optional; defaults to auth user)
- `duration_min` (optional)

### `PATCH /workout-plans/<plan_id>`

Updatable:
- `title`
- `workout_type_id`
- `description`
- `created_by`
- `duration_min`

---

## Workout session endpoints

### `POST /workouts`

Fields:
- `user_id` (required, must match auth user)
- `title` (required)
- `workout_type_id` (optional)
- `workout_plan_id` (optional)
- `completion_date` (optional ISO datetime)

### `POST /workouts/from-plan/<plan_id>`

Optional body:
- `completion_date` (ISO datetime)

### `PATCH /workouts/<workout_id>`

Used to log completion date updates:

```json
{
  "completion_date": "2026-04-14T10:22:00"
}
```

Can also clear it with:

```json
{
  "completion_date": null
}
```

### `GET /workouts?user_id=<uuid>`

Returns workouts with `completion_date`.

### `GET /workouts/weekly-assignments?user_id=<uuid>`

Returns user workouts joined to assignment rows from plan days.

Response shape:

```json
[
  {
    "workout_id": 22,
    "title": "Upper Body",
    "workout_plan_id": 3,
    "completion_date": null,
    "assignments": [
      { "id": 10, "weekday": "Monday", "schedule_time": "07:00:00" }
    ]
  }
]
```

`/workouts/current-week` returns the same output (alias route).

### `GET /workouts/<workout_id>`

Returns workout detail + nested exercises + plan assignments.

---

## Exercise row modification endpoints

- Plan exercise rows:
  - `PUT /workout-plan-exercises/<workout_plan_exercise_id>`
  - `DELETE /workout-plan-exercises/<workout_plan_exercise_id>`
- Workout exercise rows:
  - `PUT /workout-exercises/<workout_exercise_id>`
  - `DELETE /workout-exercises/<workout_exercise_id>`

Both update endpoints support partial field updates and validate `exercise_id` if provided.
# Workouts API

Routes are defined in `endpoints/workouts.py` (`workouts_blueprint`) and registered without an extra URL prefix in `app.py`:

```python
app.register_blueprint(workouts_blueprint)
```

So full paths are rooted at your server host, for example:

`https://<host>/workouts`  
`https://<host>/exercises`

Use `Content-Type: application/json` when sending a body.

---

## Authentication

Every endpoint uses `@require_auth`.

```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

Workout sessions and workout-exercise rows are scoped to the authenticated user (`g.user.user_id`).

---

## Endpoint overview

| Method | Path | Description |
|--------|------|-------------|
| PUT | `/workout-plan-exercises/<workout_plan_exercise_id>` | Update a workout plan exercise row |
| DELETE | `/workout-plan-exercises/<workout_plan_exercise_id>` | Delete a workout plan exercise row |
| GET | `/exercise-categories` | List exercise categories |
| GET | `/body-parts` | List body parts |
| GET | `/workout-types` | List workout types |
| GET | `/exercises` | List all exercises (master catalog) |
| GET | `/exercises/<exercise_id>` | Get one exercise |
| GET | `/workout-plans` | List workout plan templates (supports `created_by` filter) |
| GET | `/workout-plans/<plan_id>` | Plan detail + template exercises |
| POST | `/workout-plans` | Create a plan |
| PATCH | `/workout-plans/<plan_id>` | Partial update of a plan |
| DELETE | `/workout-plans/<plan_id>` | Delete a plan |
| POST | `/workout-plans/<plan_id>/exercises` | Add exercise(s) to a plan (single or bulk) |
| POST | `/workouts` | Create a workout session |
| POST | `/workouts/from-plan/<plan_id>` | New session copied from a template |
| GET | `/workouts?user_id=<uuid>` | List current user workouts |
| GET | `/workouts/current-week?user_id=<uuid>` | List current-week workouts by weekday/time |
| GET | `/workouts/<workout_id>` | Full workout + exercises |
| DELETE | `/workouts/<workout_id>` | Delete workout (cascades exercises) |
| GET | `/workouts/<workout_id>/exercises` | List exercises for a workout |
| POST | `/workouts/<workout_id>/exercises` | Add exercise(s) (single or bulk) |
| PUT | `/workout-exercises/<workout_exercise_id>` | Update a workout exercise row |
| DELETE | `/workout-exercises/<workout_exercise_id>` | Delete a workout exercise row |

---

## New/updated schema fields

### `workouts`
- `schedule_weekday` (`varchar(10)`)
- `schedule_time` (`time`)

### `workout_plans`
- `duration_min` (`int`)
- `created_by` (`uuid`)

---

## Shared: exercise row fields

Used when creating/updating rows in `workout_plan_exercises` and `workout_exercises`. Send only fields you need; decimals are accepted as numbers and returned as JSON floats.

| Field | Type | Notes |
|--------|------|--------|
| `exercise_id` | integer | Required when creating a row |
| `position` | integer | Sort order; defaults to `0` if omitted on create |
| `sets` | integer | |
| `reps` | integer | |
| `weight` | number | Stored as decimal |
| `rpe` | number | Stored as decimal |
| `duration_sec` | integer | |
| `distance_m` | number | Stored as decimal |
| `pace_sec_per_km` | number | Stored as decimal |
| `calories` | integer | |
| `notes` | string | |

Response objects for plan/workout exercises also include:

- `name` - resolved exercise name  
- `workout_plan_exercise_id` or `workout_exercise_id`  
- parent id: `workout_plan_id` or `workout_id`

---

## Shared: scheduling fields on workouts

| Field | Type | Notes |
|--------|------|--------|
| `schedule_weekday` | string | Optional, must be non-empty if provided, max 10 chars |
| `schedule_time` | time string | Optional, must be valid ISO time if provided |

Validation errors:

- `400 { "error": "schedule_weekday must be a non-empty string" }`
- `400 { "error": "schedule_weekday must be 10 characters or fewer" }`
- `400 { "error": "schedule_time must be a valid ISO time" }`

---

## Bulk vs single body (POST exercises)

For:

- `POST /workout-plans/<plan_id>/exercises`
- `POST /workouts/<workout_id>/exercises`

Send either:

1. One object:
```json
{ "exercise_id": 1, "sets": 3 }
```

2. Many:
```json
{
  "exercises": [
    { "exercise_id": 1, "sets": 3 },
    { "exercise_id": 2, "sets": 4 }
  ]
}
```

---

## Workout plans (templates)

### `GET /workout-plans`

Supports optional query filter:

- `created_by=me` -> resolves to authenticated user id (`g.user.user_id`)
- `created_by=<uuid>` -> filters by that UUID

If `created_by` is invalid:

- `400 { "error": "created_by must be a valid UUID or \"me\"" }`

**200:**
```json
[
  {
    "workout_plan_id": 1,
    "title": "Upper body",
    "created_by": "f5d6a8b4-4f95-4f27-8e2a-3b8d6f09a111",
    "duration_min": 60
  }
]
```

### `GET /workout-plans/<plan_id>`

**200:**
```json
{
  "workout_plan_id": 1,
  "title": "Upper body",
  "workout_type_id": 2,
  "description": "...",
  "created_by": "uuid-or-null",
  "duration_min": 60,
  "exercises": []
}
```

**404:** `{ "error": "Workout plan not found" }`

### `POST /workout-plans`

**Body (JSON):**

| Field | Required | Description |
|--------|----------|-------------|
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist in `workout_types` if provided |
| `description` | no | |
| `created_by` | no | UUID string; defaults to authenticated user |
| `duration_min` | no | Integer duration in minutes |

**201:** `{ "workout_plan_id": 1 }`

### `PATCH /workout-plans/<plan_id>`

Body supports any subset:

- `title`
- `workout_type_id`
- `description`
- `created_by`
- `duration_min`

**200:** `{ "message": "Workout plan updated" }`

### `DELETE /workout-plans/<plan_id>`

Deletes the workout plan.

Delete behavior note:
- child `workout_plan_exercises` rows are expected to be removed by database FK `ON DELETE CASCADE`
- ORM relationship uses passive deletes to avoid nulling `workout_plan_id`

**200:** `{ "message": "Workout plan deleted" }`  
**404:** `{ "error": "Workout plan not found" }`

### `POST /workout-plans/<plan_id>/exercises`

Adds one or more `workout_plan_exercises` rows.

**201:** `{ "message": "Added" }`  
**404:** plan not found  
**400:** invalid payload or invalid `exercise_id`

### `PUT /workout-plan-exercises/<workout_plan_exercise_id>`

Partial update: send only fields to change. Non-empty JSON body required.

If `exercise_id` is sent, it must exist in `exercises`.

**200:** `{ "message": "Updated" }`  
**404:** `{ "error": "Workout plan exercise not found" }`  
**400:** invalid body or invalid `exercise_id`

### `DELETE /workout-plan-exercises/<workout_plan_exercise_id>`

Deletes one workout plan exercise row.

**200:** `{ "message": "Deleted" }`  
**404:** `{ "error": "Workout plan exercise not found" }`

---

## Workout sessions

### `POST /workouts`

Creates a `workouts` row.

**Body (JSON):**

| Field | Required | Description |
|--------|----------|-------------|
| `user_id` | yes | UUID string; must equal authenticated user |
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist if provided |
| `workout_plan_id` | no | Must exist if provided |
| `schedule_weekday` | no | Non-empty string; max length 10 |
| `schedule_time` | no | ISO time string |

**201:**
```json
{
  "workout_id": 1,
  "user_id": "uuid-string",
  "title": "Morning lift",
  "workout_type_id": 2,
  "workout_plan_id": null,
  "schedule_weekday": "Monday",
  "schedule_time": "09:30:00"
}
```

### `POST /workouts/from-plan/<plan_id>`

Creates a workout for the authenticated user and copies template exercises.

Optional body:
```json
{
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

**201:**
```json
{
  "workout_id": 42,
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

### `GET /workouts?user_id=<uuid>`

**Query:** `user_id` required; must be valid and must match authenticated user.

**200:**
```json
[
  {
    "workout_id": 3,
    "title": "Leg day",
    "schedule_weekday": "Thursday",
    "schedule_time": "18:00:00"
  }
]
```

### `GET /workouts/current-week?user_id=<uuid>`

Returns workouts that have `schedule_weekday` set, ordered by:

1. `schedule_weekday` ascending
2. `schedule_time` ascending
3. `workout_id` ascending

**200:** same shape as `GET /workouts`.

### `GET /workouts/<workout_id>`

Returns the workout and nested `exercises`.

**200:**
```json
{
  "workout_id": 1,
  "user_id": "uuid-string",
  "title": "Morning lift",
  "workout_type_id": 2,
  "workout_plan_id": null,
  "schedule_weekday": "Monday",
  "schedule_time": "09:30:00",
  "exercises": []
}
```

### `DELETE /workouts/<workout_id>`

**200:** `{ "message": "Workout deleted" }`  
**404 / 403:** not found or not your workout

---

## Workout exercises (session lines)

### `GET /workouts/<workout_id>/exercises`
**200:** array of workout exercise objects  
**404:** workout not found or not yours

### `POST /workouts/<workout_id>/exercises`
**201 (single):** `{ "workout_exercise_id": 1 }`  
**201 (bulk):** `{ "workout_exercise_ids": [1, 2, 3] }`

### `PUT /workout-exercises/<workout_exercise_id>`
**200:** `{ "message": "Updated" }`

### `DELETE /workout-exercises/<workout_exercise_id>`
**200:** `{ "message": "Deleted" }`

---

## Implementation reference

| Item | Location |
|------|----------|
| Routes and logic | `endpoints/workouts.py` |
| Blueprint registration | `app.py` (`app.register_blueprint(workouts_blueprint)`) |
| ORM models | `models.py` (`Workouts`, `WorkoutExercises`, `WorkoutPlans`, `WorkoutPlanExercises`, `Exercises`, `WorkoutTypes`, `BodyParts`, `ExerciseCategories`) |
# Workouts API

Routes are defined in `endpoints/workouts.py` (`workouts_blueprint`) and registered without an extra URL prefix in `app.py`:

```python
app.register_blueprint(workouts_blueprint)
```

So full paths are rooted at your server host, for example:

`https://<host>/workouts`  
`https://<host>/exercises`

Use `Content-Type: application/json` when sending a body.

---

## Authentication

Every endpoint uses `@require_auth`.

```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

Workout sessions and workout-exercise rows are scoped to the authenticated user (`g.user.user_id`).

---

## Endpoint overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/exercise-categories` | List exercise categories |
| GET | `/body-parts` | List body parts |
| GET | `/workout-types` | List workout types |
| GET | `/exercises` | List all exercises (master catalog) |
| GET | `/exercises/<exercise_id>` | Get one exercise |
| GET | `/workout-plans` | List workout plan templates |
| GET | `/workout-plans/<plan_id>` | Plan detail + template exercises |
| POST | `/workout-plans` | Create a plan |
| PATCH | `/workout-plans/<plan_id>` | Partial update of a plan |
| POST | `/workout-plans/<plan_id>/exercises` | Add exercise(s) to a plan (single or bulk) |
| POST | `/workouts` | Create a workout session |
| POST | `/workouts/from-plan/<plan_id>` | New session copied from a template |
| GET | `/workouts?user_id=<uuid>` | List current user workouts |
| GET | `/workouts/current-week?user_id=<uuid>` | List current-week workouts by weekday/time |
| GET | `/workouts/<workout_id>` | Full workout + exercises |
| DELETE | `/workouts/<workout_id>` | Delete workout (cascades exercises) |
| GET | `/workouts/<workout_id>/exercises` | List exercises for a workout |
| POST | `/workouts/<workout_id>/exercises` | Add exercise(s) (single or bulk) |
| PUT | `/workout-exercises/<workout_exercise_id>` | Update a workout exercise row |
| DELETE | `/workout-exercises/<workout_exercise_id>` | Delete a workout exercise row |

---

## New/updated schema fields

### `workouts`
- `schedule_weekday` (`varchar(10)`)
- `schedule_time` (`time`)

### `workout_plans`
- `duration_min` (`int`)

---

## Shared: exercise row fields

Used when creating/updating rows in `workout_plan_exercises` and `workout_exercises`.

| Field | Type | Notes |
|--------|------|--------|
| `exercise_id` | integer | Required when creating a row |
| `position` | integer | Sort order; defaults to `0` if omitted on create |
| `sets` | integer | |
| `reps` | integer | |
| `weight` | number | Stored as decimal |
| `rpe` | number | Stored as decimal |
| `duration_sec` | integer | |
| `distance_m` | number | Stored as decimal |
| `pace_sec_per_km` | number | Stored as decimal |
| `calories` | integer | |
| `notes` | string | |

Response objects for plan/workout exercises also include:
- `name` (resolved exercise name)
- `workout_plan_exercise_id` or `workout_exercise_id`
- parent id (`workout_plan_id` or `workout_id`)

---

## Shared: scheduling fields on workouts

| Field | Type | Notes |
|--------|------|--------|
| `schedule_weekday` | string | Optional; non-empty if provided; max 10 chars |
| `schedule_time` | time string | Optional; must be valid ISO time if provided |

Validation errors:
- `400 { "error": "schedule_weekday must be a non-empty string" }`
- `400 { "error": "schedule_weekday must be 10 characters or fewer" }`
- `400 { "error": "schedule_time must be a valid ISO time" }`

---

## Workout plans (templates)

### `GET /workout-plans`
**200:** `[{ "workout_plan_id": 1, "title": "Upper body", "duration_min": 60 }, ...]`

### `GET /workout-plans/<plan_id>`
**200:**
```json
{
  "workout_plan_id": 1,
  "title": "Upper body",
  "workout_type_id": 2,
  "description": "...",
  "created_by": "uuid-or-null",
  "duration_min": 60,
  "exercises": []
}
```

### `POST /workout-plans`
| Field | Required | Description |
|--------|----------|-------------|
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist if provided |
| `description` | no | |
| `created_by` | no | UUID string; defaults to authenticated user |
| `duration_min` | no | Integer duration in minutes |

**201:** `{ "workout_plan_id": 1 }`

### `PATCH /workout-plans/<plan_id>`
Body supports any subset:
- `title`
- `workout_type_id`
- `description`
- `created_by`
- `duration_min`

**200:** `{ "message": "Workout plan updated" }`

### `POST /workout-plans/<plan_id>/exercises`
Adds one or many plan exercise rows.

**201:** `{ "message": "Added" }`

---

## Workout sessions

### `POST /workouts`
| Field | Required | Description |
|--------|----------|-------------|
| `user_id` | yes | UUID string; must equal authenticated user |
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist if provided |
| `workout_plan_id` | no | Must exist if provided |
| `schedule_weekday` | no | Non-empty string; max length 10 |
| `schedule_time` | no | ISO time string |

**201:**
```json
{
  "workout_id": 1,
  "user_id": "uuid-string",
  "title": "Morning lift",
  "workout_type_id": 2,
  "workout_plan_id": null,
  "schedule_weekday": "Monday",
  "schedule_time": "09:30:00"
}
```

### `POST /workouts/from-plan/<plan_id>`
Optional body:
```json
{
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

**201:**
```json
{
  "workout_id": 42,
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

### `GET /workouts?user_id=<uuid>`
**200:**
```json
[
  {
    "workout_id": 3,
    "title": "Leg day",
    "schedule_weekday": "Thursday",
    "schedule_time": "18:00:00"
  }
]
```

### `GET /workouts/current-week?user_id=<uuid>`
Returns user workouts that have a weekday set, ordered by:
1) `schedule_weekday` ascending  
2) `schedule_time` ascending  
3) `workout_id` ascending

### `GET /workouts/<workout_id>`
**200:**
```json
{
  "workout_id": 1,
  "user_id": "uuid-string",
  "title": "Morning lift",
  "workout_type_id": 2,
  "workout_plan_id": null,
  "schedule_weekday": "Monday",
  "schedule_time": "09:30:00",
  "exercises": []
}
```

---

## Workout exercises (session lines)

### `GET /workouts/<workout_id>/exercises`
**200:** array of workout exercise objects

### `POST /workouts/<workout_id>/exercises`
**201 (single):** `{ "workout_exercise_id": 1 }`  
**201 (bulk):** `{ "workout_exercise_ids": [1, 2, 3] }`

### `PUT /workout-exercises/<workout_exercise_id>`
**200:** `{ "message": "Updated" }`

### `DELETE /workout-exercises/<workout_exercise_id>`
**200:** `{ "message": "Deleted" }`
# Workouts API

Routes are defined in `endpoints/workouts.py` (`workouts_blueprint`) and registered without an extra URL prefix in `app.py`:

```python
app.register_blueprint(workouts_blueprint)
```

So paths are rooted at your server host, for example:

`https://<host>/workouts`  
`https://<host>/exercises`

Use `Content-Type: application/json` when sending a body.

---

## Authentication

Every endpoint uses `@require_auth`.

```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

Workout sessions and workout-exercise rows are scoped to the authenticated user (`g.user.user_id`).

---

## Endpoint overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/exercise-categories` | List exercise categories |
| GET | `/body-parts` | List body parts |
| GET | `/workout-types` | List workout types |
| GET | `/exercises` | List all exercises (master catalog) |
| GET | `/exercises/<exercise_id>` | Get one exercise |
| GET | `/workout-plans` | List workout plan templates |
| GET | `/workout-plans/<plan_id>` | Plan detail + template exercises |
| POST | `/workout-plans` | Create a plan |
| PATCH | `/workout-plans/<plan_id>` | Partial update of a plan |
| POST | `/workout-plans/<plan_id>/exercises` | Add exercise(s) to a plan (single or bulk) |
| POST | `/workouts` | Create a workout session |
| POST | `/workouts/from-plan/<plan_id>` | New session copied from a template |
| GET | `/workouts?user_id=<uuid>` | List current user workouts |
| GET | `/workouts/current-week?user_id=<uuid>` | List current-week workouts by weekday/time |
| GET | `/workouts/<workout_id>` | Full workout + exercises |
| DELETE | `/workouts/<workout_id>` | Delete workout (cascades exercises) |
| GET | `/workouts/<workout_id>/exercises` | List exercises for a workout |
| POST | `/workouts/<workout_id>/exercises` | Add exercise(s) (single or bulk) |
| PUT | `/workout-exercises/<workout_exercise_id>` | Update a workout exercise row |
| DELETE | `/workout-exercises/<workout_exercise_id>` | Delete a workout exercise row |

---

## New/updated schema fields

### `workouts`

- `schedule_date` (`datetime`)
- `schedule_weekday` (`varchar(10)`)
- `schedule_time` (`time`)

### `workout_plans`

- `duration_min` (`int`)

---

## Shared: exercise row fields

Used when creating or updating rows in `workout_plan_exercises` and `workout_exercises`. Send only fields you need; decimals are accepted as numbers and returned as JSON floats.

| Field | Type | Notes |
|--------|------|--------|
| `exercise_id` | integer | Required when creating a row |
| `position` | integer | Sort order; defaults to `0` if omitted on create |
| `sets` | integer | |
| `reps` | integer | |
| `weight` | number | Stored as decimal |
| `rpe` | number | Stored as decimal |
| `duration_sec` | integer | |
| `distance_m` | number | Stored as decimal |
| `pace_sec_per_km` | number | Stored as decimal |
| `calories` | integer | |
| `notes` | string | |

Response objects for plan/workout exercises also include:

- `name` - resolved exercise name  
- `workout_plan_exercise_id` or `workout_exercise_id`  
- Parent id: `workout_plan_id` or `workout_id`

---

## Shared: scheduling fields on workouts

Applies to workout sessions (`workouts`):

| Field | Type | Notes |
|--------|------|--------|
| `schedule_date` | datetime string | Optional on create, defaults to server current datetime |
| `schedule_weekday` | string | Optional, must be non-empty if provided, max 10 chars |
| `schedule_time` | time string | Optional, must be valid ISO time if provided |

Create endpoints supporting these:

- `POST /workouts`
- `POST /workouts/from-plan/<plan_id>`

Returned in responses for:

- `POST /workouts`
- `POST /workouts/from-plan/<plan_id>`
- `GET /workouts`
- `GET /workouts/current-week`
- `GET /workouts/<workout_id>`

Validation errors:

- `400 { "error": "schedule_date must be a valid ISO datetime" }`
- `400 { "error": "schedule_weekday must be a non-empty string" }`
- `400 { "error": "schedule_weekday must be 10 characters or fewer" }`
- `400 { "error": "schedule_time must be a valid ISO time" }`

---

## Shared: plan duration field

`duration_min` lives on `workout_plans`.

- Type: integer minutes
- Optional on create/update
- Returned by:
  - `GET /workout-plans`
  - `GET /workout-plans/<plan_id>`

---

## Workout plans (templates)

### `GET /workout-plans`

**200:** `[{ "workout_plan_id": 1, "title": "Upper body", "duration_min": 60 }, ...]`

### `GET /workout-plans/<plan_id>`

**200:**

```json
{
  "workout_plan_id": 1,
  "title": "Upper body",
  "workout_type_id": 2,
  "description": "...",
  "created_by": "uuid-or-null",
  "duration_min": 60,
  "exercises": []
}
```

### `POST /workout-plans`

| Field | Required | Description |
|--------|----------|-------------|
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist in `workout_types` if provided |
| `description` | no | |
| `created_by` | no | UUID string; defaults to authenticated user |
| `duration_min` | no | Integer duration in minutes |

**201:** `{ "workout_plan_id": 1 }`

### `PATCH /workout-plans/<plan_id>`

Body supports any subset:

- `title`
- `workout_type_id`
- `description`
- `created_by`
- `duration_min`

**200:** `{ "message": "Workout plan updated" }`

---

## Workout sessions

### `POST /workouts`

| Field | Required | Description |
|--------|----------|-------------|
| `user_id` | yes | UUID string; must equal authenticated user |
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist if provided |
| `workout_plan_id` | no | Must exist if provided |
| `schedule_date` | no | ISO datetime; defaults to current datetime if omitted |
| `schedule_weekday` | no | Non-empty string; max length 10 |
| `schedule_time` | no | ISO time string |

**201:**

```json
{
  "workout_id": 1,
  "user_id": "uuid-string",
  "title": "Morning lift",
  "workout_type_id": 2,
  "workout_plan_id": null,
  "schedule_date": "2026-04-13T09:30:00",
  "schedule_weekday": "Monday",
  "schedule_time": "09:30:00"
}
```

### `POST /workouts/from-plan/<plan_id>`

Optional body:
```json
{
  "schedule_date": "2026-04-18T07:00:00",
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

**201:**
```json
{
  "workout_id": 42,
  "schedule_date": "2026-04-18T07:00:00",
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

### `GET /workouts?user_id=<uuid>`

**200:**
```json
[
  {
    "workout_id": 3,
    "title": "Leg day",
    "schedule_date": "2026-04-16T18:00:00",
    "schedule_weekday": "Thursday",
    "schedule_time": "18:00:00"
  }
]
```

### `GET /workouts/current-week?user_id=<uuid>`

Current week window:
- Monday `00:00` inclusive
- next Monday `00:00` exclusive

**200:** same shape as `GET /workouts`.

### `GET /workouts/<workout_id>`

**200:**
```json
{
  "workout_id": 1,
  "user_id": "uuid-string",
  "title": "Morning lift",
  "workout_type_id": 2,
  "workout_plan_id": null,
  "schedule_date": "2026-04-13T09:30:00",
  "schedule_weekday": "Monday",
  "schedule_time": "09:30:00",
  "exercises": []
}
```

---

## Workout exercises (session lines)

### `GET /workouts/<workout_id>/exercises`
**200:** array of workout exercise objects

### `POST /workouts/<workout_id>/exercises`
**201 (single):** `{ "workout_exercise_id": 1 }`  
**201 (bulk):** `{ "workout_exercise_ids": [1, 2, 3] }`

### `PUT /workout-exercises/<workout_exercise_id>`
**200:** `{ "message": "Updated" }`

### `DELETE /workout-exercises/<workout_exercise_id>`
**200:** `{ "message": "Deleted" }`
# Workouts API

Routes are defined in `endpoints/workouts.py` (`workouts_blueprint`) and registered without an extra URL prefix in `app.py`:

```python
app.register_blueprint(workouts_blueprint)
```

So paths are rooted at your server host, for example:

`https://<host>/workouts`  
`https://<host>/exercises`

Use `Content-Type: application/json` when sending a body.

---

## Authentication

Every endpoint uses `@require_auth`.

```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

Workout sessions and workout-exercise rows are scoped to the authenticated user (`g.user.user_id`).

---

## Endpoint overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/exercise-categories` | List exercise categories |
| GET | `/body-parts` | List body parts |
| GET | `/workout-types` | List workout types |
| GET | `/exercises` | List all exercises (master catalog) |
| GET | `/exercises/<exercise_id>` | Get one exercise |
| GET | `/workout-plans` | List workout plan templates |
| GET | `/workout-plans/<plan_id>` | Plan detail + template exercises |
| POST | `/workout-plans` | Create a plan |
| PATCH | `/workout-plans/<plan_id>` | Partial update of a plan |
| POST | `/workout-plans/<plan_id>/exercises` | Add exercise(s) to a plan (single or bulk) |
| POST | `/workouts` | Create a workout session |
| POST | `/workouts/from-plan/<plan_id>` | New session copied from a template |
| GET | `/workouts?user_id=<uuid>` | List current user workouts |
| GET | `/workouts/current-week?user_id=<uuid>` | List current-week workouts by `schedule_date` |
| GET | `/workouts/<workout_id>` | Full workout + exercises |
| DELETE | `/workouts/<workout_id>` | Delete workout (cascades exercises) |
| GET | `/workouts/<workout_id>/exercises` | List exercises for a workout |
| POST | `/workouts/<workout_id>/exercises` | Add exercise(s) (single or bulk) |
| PUT | `/workout-exercises/<workout_exercise_id>` | Update a workout exercise row |
| DELETE | `/workout-exercises/<workout_exercise_id>` | Delete a workout exercise row |

---

## New/updated schema fields

### `workouts`

- `schedule_date` (`datetime`)
- `schedule_weekday` (`varchar(10)`)
- `schedule_time` (`time`)

### `workout_plans`

- `duration_min` (`int`)

---

## Shared: exercise row fields

Used when creating or updating rows in `workout_plan_exercises` and `workout_exercises`. Send only fields you need; decimals are accepted as numbers and returned as JSON floats.

| Field | Type | Notes |
|--------|------|--------|
| `exercise_id` | integer | Required when creating a row |
| `position` | integer | Sort order; defaults to `0` if omitted on create |
| `sets` | integer | |
| `reps` | integer | |
| `weight` | number | Stored as decimal |
| `rpe` | number | Stored as decimal |
| `duration_sec` | integer | |
| `distance_m` | number | Stored as decimal |
| `pace_sec_per_km` | number | Stored as decimal |
| `calories` | integer | |
| `notes` | string | |

Response objects for plan/workout exercises also include:

- `name` - resolved exercise name  
- `workout_plan_exercise_id` or `workout_exercise_id`  
- Parent id: `workout_plan_id` or `workout_id`

---

## Shared: scheduling fields on workouts

Applies to workout sessions (`workouts`):

| Field | Type | Notes |
|--------|------|--------|
| `schedule_date` | datetime string | Optional on create, defaults to server current datetime |
| `schedule_weekday` | string | Optional, must be non-empty if provided, max 10 chars |
| `schedule_time` | time string | Optional, must be valid ISO time if provided |

Create endpoints supporting these:

- `POST /workouts`
- `POST /workouts/from-plan/<plan_id>`

Returned in responses for:

- `POST /workouts`
- `POST /workouts/from-plan/<plan_id>`
- `GET /workouts`
- `GET /workouts/current-week`
- `GET /workouts/<workout_id>`

Validation errors:

- `400 { "error": "schedule_date must be a valid ISO datetime" }`
- `400 { "error": "schedule_weekday must be a non-empty string" }`
- `400 { "error": "schedule_weekday must be 10 characters or fewer" }`
- `400 { "error": "schedule_time must be a valid ISO time" }`

---

## Shared: plan duration field

`duration_min` lives on `workout_plans`.

- Type: integer minutes
- Optional on create/update
- Returned by:
  - `GET /workout-plans`
  - `GET /workout-plans/<plan_id>`

---

## Bulk vs single body (POST exercises)

For:

- `POST /workout-plans/<plan_id>/exercises`
- `POST /workouts/<workout_id>/exercises`

Send either:

1. One object:
```json
{ "exercise_id": 1, "sets": 3 }
```

2. Many:
```json
{
  "exercises": [
    { "exercise_id": 1, "sets": 3 },
    { "exercise_id": 2, "sets": 4 }
  ]
}
```

---

## Workout plans (templates)

### `GET /workout-plans`

**200:** `[{ "workout_plan_id": 1, "title": "Upper body", "duration_min": 60 }, ...]`

### `GET /workout-plans/<plan_id>`

**200:**

```json
{
  "workout_plan_id": 1,
  "title": "Upper body",
  "workout_type_id": 2,
  "description": "...",
  "created_by": "uuid-or-null",
  "duration_min": 60,
  "exercises": []
}
```

Exercises are ordered by `position`, then id.

**404:** `{ "error": "Workout plan not found" }`

### `POST /workout-plans`

**Body (JSON):**

| Field | Required | Description |
|--------|----------|-------------|
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist in `workout_types` if provided |
| `description` | no | |
| `created_by` | no | UUID string; defaults to authenticated user |
| `duration_min` | no | Integer duration in minutes |

**201:** `{ "workout_plan_id": 1 }`

### `PATCH /workout-plans/<plan_id>`

Body supports any subset:

- `title`
- `workout_type_id`
- `description`
- `created_by`
- `duration_min`

Example:

```json
{
  "title": "Updated Upper Body",
  "duration_min": 70
}
```

**200:** `{ "message": "Workout plan updated" }`

---

## Workout sessions

### `POST /workouts`

**Body (JSON):**

| Field | Required | Description |
|--------|----------|-------------|
| `user_id` | yes | UUID string; must equal authenticated user |
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist if provided |
| `workout_plan_id` | no | Must exist if provided |
| `schedule_date` | no | ISO datetime; defaults to current datetime if omitted |
| `schedule_weekday` | no | Non-empty string; max length 10 |
| `schedule_time` | no | ISO time string |

**201:**

```json
{
  "workout_id": 1,
  "user_id": "uuid-string",
  "title": "Morning lift",
  "workout_type_id": 2,
  "workout_plan_id": null,
  "schedule_date": "2026-04-13T09:30:00",
  "schedule_weekday": "Monday",
  "schedule_time": "09:30:00"
}
```

### `POST /workouts/from-plan/<plan_id>`

Optional body:
```json
{
  "schedule_date": "2026-04-18T07:00:00",
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

**201:**
```json
{
  "workout_id": 42,
  "schedule_date": "2026-04-18T07:00:00",
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

### `GET /workouts?user_id=<uuid>`

**200:**
```json
[
  {
    "workout_id": 3,
    "title": "Leg day",
    "schedule_date": "2026-04-16T18:00:00",
    "schedule_weekday": "Thursday",
    "schedule_time": "18:00:00"
  }
]
```

### `GET /workouts/current-week?user_id=<uuid>`

Current week window:
- Monday `00:00` inclusive
- next Monday `00:00` exclusive

**200:** same shape as `GET /workouts`.

### `GET /workouts/<workout_id>`

**200:**
```json
{
  "workout_id": 1,
  "user_id": "uuid-string",
  "title": "Morning lift",
  "workout_type_id": 2,
  "workout_plan_id": null,
  "schedule_date": "2026-04-13T09:30:00",
  "schedule_weekday": "Monday",
  "schedule_time": "09:30:00",
  "exercises": []
}
```

### `DELETE /workouts/<workout_id>`

**200:** `{ "message": "Workout deleted" }`

---

## Workout exercises (session lines)

### `GET /workouts/<workout_id>/exercises`
**200:** array of workout exercise objects

### `POST /workouts/<workout_id>/exercises`
**201 (single):** `{ "workout_exercise_id": 1 }`  
**201 (bulk):** `{ "workout_exercise_ids": [1, 2, 3] }`

### `PUT /workout-exercises/<workout_exercise_id>`
**200:** `{ "message": "Updated" }`

### `DELETE /workout-exercises/<workout_exercise_id>`
**200:** `{ "message": "Deleted" }`

---

## Implementation reference

| Item | Location |
|------|----------|
| Routes and logic | `endpoints/workouts.py` |
| Blueprint registration | `app.py` (`app.register_blueprint(workouts_blueprint)`) |
| ORM models | `models.py` (`Workouts`, `WorkoutExercises`, `WorkoutPlans`, `WorkoutPlanExercises`, `Exercises`, `WorkoutTypes`, `BodyParts`, `ExerciseCategories`) |
# Workouts API

Routes are defined in `endpoints/workouts.py` (`workouts_blueprint`) and registered without an extra URL prefix in `app.py`:

```python
app.register_blueprint(workouts_blueprint)
```

So paths are rooted at your server host, e.g.:

`https://<host>/workouts`  
`https://<host>/exercises`

Use `Content-Type: application/json` for requests with a body.

---

## Authentication

Every endpoint uses `@require_auth`.

```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

Workout sessions and workout-exercise rows are scoped to the authenticated user (`g.user.user_id`).

---

## Endpoint Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/exercise-categories` | List exercise categories |
| GET | `/body-parts` | List body parts |
| GET | `/workout-types` | List workout types |
| GET | `/exercises` | List all exercises (master catalog) |
| GET | `/exercises/<exercise_id>` | Get one exercise |
| GET | `/workout-plans` | List workout plan templates |
| GET | `/workout-plans/<plan_id>` | Plan detail + template exercises |
| POST | `/workout-plans` | Create a plan |
| PATCH | `/workout-plans/<plan_id>` | Partial update of a plan |
| POST | `/workout-plans/<plan_id>/exercises` | Add exercise(s) to a plan (single or bulk) |
| POST | `/workouts` | Create a workout session |
| POST | `/workouts/from-plan/<plan_id>` | New session copied from a template |
| GET | `/workouts?user_id=<uuid>` | List current user workouts |
| GET | `/workouts/current-week?user_id=<uuid>` | List current-week workouts by `schedule_date` |
| GET | `/workouts/<workout_id>` | Full workout + exercises |
| DELETE | `/workouts/<workout_id>` | Delete workout (cascades exercises) |
| GET | `/workouts/<workout_id>/exercises` | List exercises for a workout |
| POST | `/workouts/<workout_id>/exercises` | Add exercise(s) (single or bulk) |
| PUT | `/workout-exercises/<workout_exercise_id>` | Update a workout exercise row |
| DELETE | `/workout-exercises/<workout_exercise_id>` | Delete a workout exercise row |

---

## New/Updated Schema Fields

### `workouts`

- `schedule_date` (`datetime`)
- `schedule_weekday` (`varchar(10)`)
- `schedule_time` (`time`)

### `workout_plans`

- `duration_min` (`int`)

---

## Shared: exercise row fields

Used when creating or updating rows in `workout_plan_exercises` and `workout_exercises`. Send only the fields you need; decimals are accepted as numbers and returned as JSON floats.

| Field | Type | Notes |
|--------|------|--------|
| `exercise_id` | integer | Required when creating a row |
| `position` | integer | Sort order; defaults to `0` if omitted on create |
| `sets` | integer | |
| `reps` | integer | |
| `weight` | number | Stored as decimal |
| `rpe` | number | Stored as decimal |
| `duration_sec` | integer | |
| `distance_m` | number | Stored as decimal |
| `pace_sec_per_km` | number | Stored as decimal |
| `calories` | integer | |
| `notes` | string | |

Response objects for plan/workout exercises also include:

- `name` - resolved exercise name  
- `workout_plan_exercise_id` or `workout_exercise_id`  
- Parent id: `workout_plan_id` or `workout_id`

---

## Shared: scheduling fields on workouts

These apply to workout sessions (`workouts`) and appear in relevant request/response payloads.

| Field | Type | Notes |
|--------|------|--------|
| `schedule_date` | datetime string | Optional on create; defaults to current server datetime |
| `schedule_weekday` | string | Optional; if provided must be non-empty and max 10 chars |
| `schedule_time` | time string | Optional; if provided must be valid ISO time |

Create endpoints supporting scheduling fields:

- `POST /workouts`
- `POST /workouts/from-plan/<plan_id>`

Returned in responses for:

- `POST /workouts`
- `POST /workouts/from-plan/<plan_id>`
- `GET /workouts`
- `GET /workouts/current-week`
- `GET /workouts/<workout_id>`

Examples:

- `schedule_date`: `2026-04-13T09:30:00`, `2026-04-13T09:30:00Z`
- `schedule_time`: `09:30:00`

Validation errors:

- `400 { "error": "schedule_date must be a valid ISO datetime" }`
- `400 { "error": "schedule_weekday must be a non-empty string" }`
- `400 { "error": "schedule_weekday must be 10 characters or fewer" }`
- `400 { "error": "schedule_time must be a valid ISO time" }`

---

## Shared: duration on workout plans

`duration_min` lives on `workout_plans`.

- Type: integer seconds
- Optional on create/update
- Returned by:
  - `GET /workout-plans`
  - `GET /workout-plans/<plan_id>`

---

## Bulk vs single body (POST exercises)

For:

- `POST /workout-plans/<plan_id>/exercises`
- `POST /workouts/<workout_id>/exercises`

Send either:

1. One object:
```json
{ "exercise_id": 1, "sets": 3 }
```

2. Many:
```json
{
  "exercises": [
    { "exercise_id": 1, "sets": 3 },
    { "exercise_id": 2, "sets": 4 }
  ]
}
```

---

## Lookup tables

### `GET /exercise-categories`

**200:** `[{ "category_id": 1, "name": "Strength" }, ...]`

### `GET /body-parts`

**200:** `[{ "body_part_id": 1, "name": "Chest" }, ...]`

### `GET /workout-types`

**200:** `[{ "workout_type_id": 1, "name": "HIIT" }, ...]`

---

## Master exercises

### `GET /exercises`

**200:** Array of:

```json
{
  "exercise_id": 1,
  "name": "Bench press",
  "youtube_url": "https://www.youtube.com/watch?v=example",
  "body_part_id": 2,
  "category_id": 1,
  "body_part": "Chest",
  "category": "Strength"
}
```

### `GET /exercises/<exercise_id>`

**200:** One object in the same shape as above.

**404:** `{ "error": "Exercise not found" }`

---

## Workout plans (templates)

### `GET /workout-plans`

**200:** `[{ "workout_plan_id": 1, "title": "Upper body", "duration_min": 60 }, ...]`

### `GET /workout-plans/<plan_id>`

**200:**

```json
{
  "workout_plan_id": 1,
  "title": "Upper body",
  "workout_type_id": 2,
  "description": "...",
  "created_by": "uuid-or-null",
  "duration_min": 60,
  "exercises": []
}
```

Exercises are ordered by `position`, then id.

**404:** `{ "error": "Workout plan not found" }`

### `POST /workout-plans`

**Body (JSON):**

| Field | Required | Description |
|--------|----------|-------------|
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist in `workout_types` if provided |
| `description` | no | |
| `created_by` | no | UUID string; defaults to authenticated user |
| `duration_min` | no | Integer duration in minutes |

**201:** `{ "workout_plan_id": 1 }`

**400:** Missing `title`, invalid `created_by`, or invalid `workout_type_id`.

### `PATCH /workout-plans/<plan_id>`

Body supports any subset:

- `title`
- `workout_type_id`
- `description`
- `created_by`
- `duration_min`

Rules:

- `title` cannot be empty if present
- `workout_type_id` must exist if non-null
- `created_by` must be UUID if non-null
- `description` and `created_by` can be set to `null`

Example body:
```json
{
  "title": "Updated Upper Body",
  "workout_type_id": 2,
  "description": "Updated template notes",
  "created_by": "f5d6a8b4-4f95-4f27-8e2a-3b8d6f09a111",
  "duration_min": 70
}
```

**200:** `{ "message": "Workout plan updated" }`

**404:** `{ "error": "Workout plan not found" }`  
**400:** invalid body/values

### `POST /workout-plans/<plan_id>/exercises`

Adds one or more `workout_plan_exercises` rows (see Bulk vs single).

**201:** `{ "message": "Added" }`

**404:** Plan not found. **400:** Invalid payload or invalid `exercise_id`.

---

## Workout sessions

### `POST /workouts`

Creates a `workouts` row.

**Body (JSON):**

| Field | Required | Description |
|--------|----------|-------------|
| `user_id` | yes | UUID string; must equal authenticated user |
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist if provided |
| `workout_plan_id` | no | Must exist if provided |
| `schedule_date` | no | ISO datetime; defaults to current datetime if omitted |
| `schedule_weekday` | no | Non-empty string; max length 10 |
| `schedule_time` | no | ISO time string |

**201:**

```json
{
  "workout_id": 1,
  "user_id": "uuid-string",
  "title": "Morning lift",
  "workout_type_id": 2,
  "workout_plan_id": null,
  "schedule_date": "2026-04-13T09:30:00",
  "schedule_weekday": "Monday",
  "schedule_time": "09:30:00"
}
```

**400 / 403:** Invalid `user_id`, missing `title`, invalid scheduling fields, wrong user, or invalid FKs.

### `POST /workouts/from-plan/<plan_id>`

Creates a workout for the authenticated user, copies `title`, `workout_type_id`, and `workout_plan_id` from the plan, and copies all template exercises into `workout_exercises`.

Optional body:
```json
{
  "schedule_date": "2026-04-18T07:00:00",
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

**201:**
```json
{
  "workout_id": 42,
  "schedule_date": "2026-04-18T07:00:00",
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

**404:** `{ "error": "Workout plan not found" }`

### `GET /workouts?user_id=<uuid>`

**Query:** `user_id` required; must be a valid UUID and must match the authenticated user.

**200:** newest `workout_id` first:
```json
[
  {
    "workout_id": 3,
    "title": "Leg day",
    "schedule_date": "2026-04-16T18:00:00",
    "schedule_weekday": "Thursday",
    "schedule_time": "18:00:00"
  }
]
```

**400 / 403:** Missing/invalid `user_id`, or not listing your own id.

### `GET /workouts/current-week?user_id=<uuid>`

Returns workouts scheduled in current week window:
- start: Monday `00:00`
- end: next Monday `00:00` (exclusive)

Query `user_id` is required and must match the authenticated user.

**200:**
```json
[
  {
    "workout_id": 7,
    "title": "Tempo Run",
    "schedule_date": "2026-04-17T06:30:00",
    "schedule_weekday": "Friday",
    "schedule_time": "06:30:00"
  }
]
```

**400 / 403:** invalid/missing user id or forbidden

### `GET /workouts/<workout_id>`

Returns the workout and nested `exercises`.

**200:**
```json
{
  "workout_id": 1,
  "user_id": "uuid-string",
  "title": "Morning lift",
  "workout_type_id": 2,
  "workout_plan_id": null,
  "schedule_date": "2026-04-13T09:30:00",
  "schedule_weekday": "Monday",
  "schedule_time": "09:30:00",
  "exercises": []
}
```

**404:** `{ "error": "Workout not found" }`

### `DELETE /workouts/<workout_id>`

**200:** `{ "message": "Workout deleted" }`

**404 / 403:** Not found or not your workout.

---

## Workout exercises (session lines)

### `GET /workouts/<workout_id>/exercises`

**200:** Array of workout exercise objects (same fields as in `GET /workouts/<id>` nested list).

**404:** Workout not found or not yours.

### `POST /workouts/<workout_id>/exercises`

**201:**

- One created: `{ "workout_exercise_id": 1 }`
- Several: `{ "workout_exercise_ids": [1, 2, 3] }`

**404 / 403 / 400:** As for other workout mutations.

### `PUT /workout-exercises/<workout_exercise_id>`

Partial update: send only fields to change. Non-empty JSON body required.

If `exercise_id` is sent, it must exist in `exercises`.

**200:** `{ "message": "Updated" }`

**404:** Row not found or parent workout not yours.

### `DELETE /workout-exercises/<workout_exercise_id>`

**200:** `{ "message": "Deleted" }`

**404:** Same as PUT.

---

## Example flows

**Browse catalog -> start empty session**

1. `GET /exercises` (and lookups as needed)  
2. `POST /workouts` with your `user_id`, `title`, and optional scheduling fields  
3. `POST /workouts/<id>/exercises` with one or more exercise payloads  

**Start from a template**

1. `GET /workout-plans` -> pick `plan_id`  
2. `POST /workouts/from-plan/<plan_id>`  
3. Optionally `PUT /workout-exercises/...` to adjust sets/reps during the session  

**Update a plan template**

1. `GET /workout-plans/<plan_id>`  
2. `PATCH /workout-plans/<plan_id>` (including optional `duration_min`)
3. `POST /workout-plans/<plan_id>/exercises` to add rows

---

## Implementation reference

| Item | Location |
|------|----------|
| Routes and logic | `endpoints/workouts.py` |
| Blueprint registration | `app.py` (`app.register_blueprint(workouts_blueprint)`) |
| ORM models | `models.py` (`Workouts`, `WorkoutExercises`, `WorkoutPlans`, `WorkoutPlanExercises`, `Exercises`, `WorkoutTypes`, `BodyParts`, `ExerciseCategories`) |
# Workouts API

Routes are defined in `endpoints/workouts.py` (`workouts_blueprint`) and registered without an extra URL prefix in `app.py`:

```python
app.register_blueprint(workouts_blueprint)
```

Use `Content-Type: application/json` for requests with a body.

---

## Authentication

Every endpoint uses `@require_auth`.

```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

Workout sessions and workout-exercise rows are scoped to the authenticated user (`g.user.user_id`).

---

## Endpoint Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/exercise-categories` | List exercise categories |
| GET | `/body-parts` | List body parts |
| GET | `/workout-types` | List workout types |
| GET | `/exercises` | List all exercises |
| GET | `/exercises/<exercise_id>` | Get one exercise |
| GET | `/workout-plans` | List workout plan templates |
| GET | `/workout-plans/<plan_id>` | Plan detail + template exercises |
| POST | `/workout-plans` | Create a workout plan |
| PATCH | `/workout-plans/<plan_id>` | Partial update for plan |
| POST | `/workout-plans/<plan_id>/exercises` | Add exercise(s) to a plan |
| POST | `/workouts` | Create a workout session |
| POST | `/workouts/from-plan/<plan_id>` | Create session from plan |
| GET | `/workouts?user_id=<uuid>` | List user workouts |
| GET | `/workouts/current-week?user_id=<uuid>` | List user workouts for current week |
| GET | `/workouts/<workout_id>` | Get workout + exercises |
| DELETE | `/workouts/<workout_id>` | Delete workout |
| GET | `/workouts/<workout_id>/exercises` | List workout exercises |
| POST | `/workouts/<workout_id>/exercises` | Add workout exercise(s) |
| PUT | `/workout-exercises/<workout_exercise_id>` | Update a workout exercise row |
| DELETE | `/workout-exercises/<workout_exercise_id>` | Delete a workout exercise row |

---

## New Schema Fields Reflected

### `workouts`

- `schedule_date` (`datetime`)
- `schedule_weekday` (`varchar(10)`)
- `schedule_time` (`time`)

### `workout_plans`

- `duration_min` (`int`)

---

## Shared: Exercise Row Fields

Used for `workout_plan_exercises` and `workout_exercises`.

| Field | Type | Notes |
|--------|------|--------|
| `exercise_id` | integer | Required on create |
| `position` | integer | Defaults to `0` on create |
| `sets` | integer | Optional |
| `reps` | integer | Optional |
| `weight` | number | Decimal |
| `rpe` | number | Decimal |
| `duration_sec` | integer | Optional |
| `distance_m` | number | Decimal |
| `pace_sec_per_km` | number | Decimal |
| `calories` | integer | Optional |
| `notes` | string | Optional |

---

## Shared: Scheduling Fields

Used on workout creation endpoints:

- `schedule_date` (optional ISO datetime, defaults to now)
- `schedule_weekday` (optional non-empty string, max 10 chars)
- `schedule_time` (optional ISO time, e.g. `06:30:00`)

Validation errors:
- `400` if `schedule_date` invalid
- `400` if `schedule_weekday` empty/too long
- `400` if `schedule_time` invalid

These are returned in workout responses:
- `POST /workouts`
- `POST /workouts/from-plan/<plan_id>`
- `GET /workouts`
- `GET /workouts/current-week`
- `GET /workouts/<workout_id>`

---

## Workout Plans (Templates)

### `GET /workout-plans`

Returns a light plan list.

**200:**
```json
[
  {
    "workout_plan_id": 1,
    "title": "Upper Body",
    "duration_min": 60
  }
]
```

### `GET /workout-plans/<plan_id>`

**200:**
```json
{
  "workout_plan_id": 1,
  "title": "Upper Body",
  "workout_type_id": 2,
  "description": "Push emphasis",
  "created_by": "uuid-or-null",
  "duration_min": 60,
  "exercises": []
}
```

### `POST /workout-plans`

Body:

| Field | Required | Notes |
|--------|----------|------|
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist if provided |
| `description` | no | |
| `created_by` | no | UUID; defaults to authenticated user |
| `duration_min` | no | Integer minutes |

**201:** `{ "workout_plan_id": 1 }`

### `PATCH /workout-plans/<plan_id>`

Partial update. Any subset of:
- `title`
- `workout_type_id`
- `description`
- `created_by`
- `duration_min`

**200:** `{ "message": "Workout plan updated" }`

---

## Workout Sessions

### `POST /workouts`

Body:

| Field | Required | Notes |
|--------|----------|------|
| `user_id` | yes | Must match authenticated user |
| `title` | yes | Non-empty string |
| `workout_type_id` | no | Must exist if provided |
| `workout_plan_id` | no | Must exist if provided |
| `schedule_date` | no | ISO datetime; defaults to now |
| `schedule_weekday` | no | Non-empty string, max 10 |
| `schedule_time` | no | ISO time |

**201:**
```json
{
  "workout_id": 12,
  "user_id": "uuid",
  "title": "Morning Lift",
  "workout_type_id": 2,
  "workout_plan_id": null,
  "schedule_date": "2026-04-13T09:30:00",
  "schedule_weekday": "Monday",
  "schedule_time": "09:30:00"
}
```

### `POST /workouts/from-plan/<plan_id>`

Optional body:
```json
{
  "schedule_date": "2026-04-18T07:00:00",
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

**201:**
```json
{
  "workout_id": 42,
  "schedule_date": "2026-04-18T07:00:00",
  "schedule_weekday": "Saturday",
  "schedule_time": "07:00:00"
}
```

### `GET /workouts?user_id=<uuid>`

**200:**
```json
[
  {
    "workout_id": 42,
    "title": "Push Day",
    "schedule_date": "2026-04-18T07:00:00",
    "schedule_weekday": "Saturday",
    "schedule_time": "07:00:00"
  }
]
```

### `GET /workouts/current-week?user_id=<uuid>`

Week window:
- start: Monday `00:00`
- end: next Monday `00:00` (exclusive)

**200:** same shape as `GET /workouts`.

### `GET /workouts/<workout_id>`

Returns workout detail plus nested exercises, including scheduling fields.

### `DELETE /workouts/<workout_id>`

**200:** `{ "message": "Workout deleted" }`

---

## Workout Exercises

### `GET /workouts/<workout_id>/exercises`
Returns workout exercise rows.

### `POST /workouts/<workout_id>/exercises`
Single or bulk create.

**201 single:** `{ "workout_exercise_id": 1 }`  
**201 bulk:** `{ "workout_exercise_ids": [1, 2] }`

### `PUT /workout-exercises/<workout_exercise_id>`
Partial update for workout exercise row.

**200:** `{ "message": "Updated" }`

### `DELETE /workout-exercises/<workout_exercise_id>`
**200:** `{ "message": "Deleted" }`

---

## Common Error Patterns

- `400` validation/malformed input
- `403` ownership/auth scope violation
- `404` not found
