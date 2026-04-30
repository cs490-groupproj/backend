/*
  Three global workout templates (created_by = NULL) using exercises from dbo.exercises.

  Target: SQL Server (matches models: workout_plans, workout_plan_exercises)

  Exercise names are taken from scripts/seed_body_parts_categories_exercises.sql.
  If your database used different names, either:
    - adjust the names in the "wanted" CTEs below, or
    - run:  SELECT exercise_id, name FROM exercises ORDER BY name;
    and replace names to match your rows.

  Safe to re-run: skips a plan if a row with the same title and created_by IS NULL
  already exists (does not duplicate lines on partial failure — delete those plans
  first if you need a clean re-seed).

  Optional: set workout_type_id to a valid row in workout_types, e.g.:
    UPDATE workout_plans SET workout_type_id = 1 WHERE title LIKE N'Global:%' AND created_by IS NULL;
*/

SET NOCOUNT ON;

DECLARE @p1 INT;
DECLARE @p2 INT;
DECLARE @p3 INT;

/* ---------- Plan 1: Upper body (chest, shoulders, arms) ---------- */
IF NOT EXISTS (
    SELECT 1 FROM workout_plans
    WHERE title = N'Global: Upper Body Strength' AND created_by IS NULL
)
BEGIN
    INSERT INTO workout_plans (title, workout_type_id, description, created_by, duration_min)
    VALUES (
        N'Global: Upper Body Strength',
        NULL,
        N'Template: bench and accessory pressing, shoulders, arms. Adjust sets/reps to your level.',
        NULL,
        50
    );

    SET @p1 = SCOPE_IDENTITY();

    ;WITH wanted ([position], exercise_name, sets, reps) AS (
        SELECT * FROM (VALUES
            (0, N'Barbell Bench Press', 3, 8),
            (1, N'Incline Dumbbell Press', 3, 10),
            (2, N'Cable Fly', 3, 12),
            (3, N'Overhead Press', 3, 8),
            (4, N'Lateral Raise', 3, 12),
            (5, N'Barbell Curl', 3, 10),
            (6, N'Tricep Rope Pushdown', 3, 12)
        ) AS v([position], exercise_name, sets, reps)
    )
    INSERT INTO workout_plan_exercises (
        workout_plan_id, exercise_id, [position], sets, reps,
        weight, rpe, duration_sec, distance_m, pace_sec_per_km, calories, notes
    )
    SELECT
        @p1,
        e.exercise_id,
        w.[position],
        w.sets,
        w.reps,
        NULL, NULL, NULL, NULL, NULL, NULL, NULL
    FROM wanted w
    INNER JOIN exercises e ON e.name = w.exercise_name;

    PRINT N'Inserted plan: Global: Upper Body Strength (id=' + CAST(@p1 AS NVARCHAR(20)) + N').';
END
ELSE
    PRINT N'Skip: Global: Upper Body Strength already exists.';

/* ---------- Plan 2: Lower body & pull ---------- */
IF NOT EXISTS (
    SELECT 1 FROM workout_plans
    WHERE title = N'Global: Lower Body & Pull' AND created_by IS NULL
)
BEGIN
    INSERT INTO workout_plans (title, workout_type_id, description, created_by, duration_min)
    VALUES (
        N'Global: Lower Body & Pull',
        NULL,
        N'Template: squat hinge and leg work plus vertical and horizontal pulls.',
        NULL,
        55
    );

    SET @p2 = SCOPE_IDENTITY();

    ;WITH wanted ([position], exercise_name, sets, reps) AS (
        SELECT * FROM (VALUES
            (0, N'Back Squat', 4, 6),
            (1, N'Romanian Deadlift', 3, 8),
            (2, N'Leg Press', 3, 10),
            (3, N'Pull-Up', 3, 8),
            (4, N'Barbell Row', 3, 8),
            (5, N'Lat Pulldown', 3, 10)
        ) AS v([position], exercise_name, sets, reps)
    )
    INSERT INTO workout_plan_exercises (
        workout_plan_id, exercise_id, [position], sets, reps,
        weight, rpe, duration_sec, distance_m, pace_sec_per_km, calories, notes
    )
    SELECT
        @p2,
        e.exercise_id,
        w.[position],
        w.sets,
        w.reps,
        NULL, NULL, NULL, NULL, NULL, NULL, NULL
    FROM wanted w
    INNER JOIN exercises e ON e.name = w.exercise_name;

    PRINT N'Inserted plan: Global: Lower Body & Pull (id=' + CAST(@p2 AS NVARCHAR(20)) + N').';
END
ELSE
    PRINT N'Skip: Global: Lower Body & Pull already exists.';

/* ---------- Plan 3: Full body mixed ---------- */
IF NOT EXISTS (
    SELECT 1 FROM workout_plans
    WHERE title = N'Global: Full Body Mixed' AND created_by IS NULL
)
BEGIN
    INSERT INTO workout_plans (title, workout_type_id, description, created_by, duration_min)
    VALUES (
        N'Global: Full Body Mixed',
        NULL,
        N'Template: power, legs, conditioning, and core. Swap movements if equipment differs.',
        NULL,
        45
    );

    SET @p3 = SCOPE_IDENTITY();

    ;WITH wanted ([position], exercise_name, sets, reps, duration_sec) AS (
        SELECT * FROM (VALUES
            (0, N'Power Clean', 3, 5, NULL),
            (1, N'Back Squat', 3, 6, NULL),
            (2, N'Rowing Erg', 3, NULL, 60),
            (3, N'Jump Rope', 3, NULL, 45),
            (4, N'Plank', 3, NULL, 45),
            (5, N'Dead Bug', 3, 12, NULL)
        ) AS v([position], exercise_name, sets, reps, duration_sec)
    )
    INSERT INTO workout_plan_exercises (
        workout_plan_id, exercise_id, [position], sets, reps,
        weight, rpe, duration_sec, distance_m, pace_sec_per_km, calories, notes
    )
    SELECT
        @p3,
        e.exercise_id,
        w.[position],
        w.sets,
        w.reps,
        NULL, NULL, w.duration_sec, NULL, NULL, NULL, NULL
    FROM wanted w
    INNER JOIN exercises e ON e.name = w.exercise_name;

    PRINT N'Inserted plan: Global: Full Body Mixed (id=' + CAST(@p3 AS NVARCHAR(20)) + N').';
END
ELSE
    PRINT N'Skip: Global: Full Body Mixed already exists.';

PRINT N'Done. Verify with:';
PRINT N'  SELECT wp.workout_plan_id, wp.title, wp.created_by, COUNT(*) AS lines';
PRINT N'  FROM workout_plans wp';
PRINT N'  LEFT JOIN workout_plan_exercises wpe ON wpe.workout_plan_id = wp.workout_plan_id';
PRINT N'  WHERE wp.title LIKE N''Global:%'' AND wp.created_by IS NULL';
PRINT N'  GROUP BY wp.workout_plan_id, wp.title, wp.created_by;';
