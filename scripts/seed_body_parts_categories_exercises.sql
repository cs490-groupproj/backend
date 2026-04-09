/*
  Mock seed data for: body_parts, exercise_categories, exercises
  Target: SQL Server (matches Flask-SQLAlchemy models: Identity PKs, FKs)

  - Safe to re-run: skips rows that already exist (by unique name on lookup tables;
    by exercise name for exercises).
  - Run order: body_parts and exercise_categories first, then exercises.

  If you need a clean slate first (DESTRUCTIVE), uncomment the block at the bottom
  only if no workout_plan_exercises / workout_exercises reference these rows.
*/

SET NOCOUNT ON;

/* ---------- body_parts (name is unique) ---------- */
IF NOT EXISTS (SELECT 1 FROM body_parts WHERE name = N'Chest')
    INSERT INTO body_parts (name) VALUES (N'Chest');
IF NOT EXISTS (SELECT 1 FROM body_parts WHERE name = N'Back')
    INSERT INTO body_parts (name) VALUES (N'Back');
IF NOT EXISTS (SELECT 1 FROM body_parts WHERE name = N'Legs')
    INSERT INTO body_parts (name) VALUES (N'Legs');
IF NOT EXISTS (SELECT 1 FROM body_parts WHERE name = N'Shoulders')
    INSERT INTO body_parts (name) VALUES (N'Shoulders');
IF NOT EXISTS (SELECT 1 FROM body_parts WHERE name = N'Arms')
    INSERT INTO body_parts (name) VALUES (N'Arms');
IF NOT EXISTS (SELECT 1 FROM body_parts WHERE name = N'Core')
    INSERT INTO body_parts (name) VALUES (N'Core');
IF NOT EXISTS (SELECT 1 FROM body_parts WHERE name = N'Full Body')
    INSERT INTO body_parts (name) VALUES (N'Full Body');

/* ---------- exercise_categories = "exercise types" (name is unique) ---------- */
IF NOT EXISTS (SELECT 1 FROM exercise_categories WHERE name = N'Strength')
    INSERT INTO exercise_categories (name) VALUES (N'Strength');
IF NOT EXISTS (SELECT 1 FROM exercise_categories WHERE name = N'Cardio')
    INSERT INTO exercise_categories (name) VALUES (N'Cardio');
IF NOT EXISTS (SELECT 1 FROM exercise_categories WHERE name = N'Flexibility')
    INSERT INTO exercise_categories (name) VALUES (N'Flexibility');
IF NOT EXISTS (SELECT 1 FROM exercise_categories WHERE name = N'Olympic')
    INSERT INTO exercise_categories (name) VALUES (N'Olympic');
IF NOT EXISTS (SELECT 1 FROM exercise_categories WHERE name = N'Plyometric')
    INSERT INTO exercise_categories (name) VALUES (N'Plyometric');
IF NOT EXISTS (SELECT 1 FROM exercise_categories WHERE name = N'Recovery')
    INSERT INTO exercise_categories (name) VALUES (N'Recovery');

/* ---------- exercises (FK: body_part_id, category_id) ---------- */
/* Format: exercise_name, body_part_name, category_name */

DECLARE @rows TABLE (
    exercise_name NVARCHAR(255) NOT NULL,
    body_part_name NVARCHAR(50) NOT NULL,
    category_name NVARCHAR(50) NOT NULL
);

INSERT INTO @rows (exercise_name, body_part_name, category_name) VALUES
    (N'Barbell Bench Press', N'Chest', N'Strength'),
    (N'Incline Dumbbell Press', N'Chest', N'Strength'),
    (N'Cable Fly', N'Chest', N'Strength'),
    (N'Pull-Up', N'Back', N'Strength'),
    (N'Barbell Row', N'Back', N'Strength'),
    (N'Lat Pulldown', N'Back', N'Strength'),
    (N'Back Squat', N'Legs', N'Strength'),
    (N'Romanian Deadlift', N'Legs', N'Strength'),
    (N'Leg Press', N'Legs', N'Strength'),
    (N'Overhead Press', N'Shoulders', N'Strength'),
    (N'Lateral Raise', N'Shoulders', N'Strength'),
    (N'Barbell Curl', N'Arms', N'Strength'),
    (N'Tricep Rope Pushdown', N'Arms', N'Strength'),
    (N'Plank', N'Core', N'Strength'),
    (N'Dead Bug', N'Core', N'Strength'),
    (N'Treadmill Run', N'Legs', N'Cardio'),
    (N'Stationary Bike', N'Legs', N'Cardio'),
    (N'Jump Rope', N'Full Body', N'Cardio'),
    (N'Rowing Erg', N'Full Body', N'Cardio'),
    (N'Static Stretch — Hamstrings', N'Legs', N'Flexibility'),
    (N'Yoga Sun Salutation', N'Full Body', N'Flexibility'),
    (N'Power Clean', N'Full Body', N'Olympic'),
    (N'Box Jump', N'Legs', N'Plyometric'),
    (N'Foam Roll — Upper Back', N'Back', N'Recovery');

INSERT INTO exercises (name, body_part_id, category_id)
SELECT r.exercise_name, bp.body_part_id, c.category_id
FROM @rows r
INNER JOIN body_parts bp ON bp.name = r.body_part_name
INNER JOIN exercise_categories c ON c.name = r.category_name
WHERE NOT EXISTS (
    SELECT 1 FROM exercises e WHERE e.name = r.exercise_name
);

PRINT 'Seed complete. body_parts / exercise_categories / exercises inserted where missing.';

/*
  --- OPTIONAL: wipe reference data (DANGEROUS) ---
  Only use if nothing references these exercises yet.

DELETE FROM workout_exercises;
DELETE FROM workout_plan_exercises;
DELETE FROM exercises;
DELETE FROM exercise_categories;
DELETE FROM body_parts;
*/
