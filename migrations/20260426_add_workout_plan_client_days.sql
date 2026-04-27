BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.workout_plan_client_days', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.workout_plan_client_days (
        id INT IDENTITY(1,1) NOT NULL,
        assignment_id INT NOT NULL,
        weekday VARCHAR(10) NOT NULL,
        schedule_time TIME NOT NULL,
        CONSTRAINT PK_workout_plan_client_days PRIMARY KEY (id),
        CONSTRAINT FK_workout_plan_client_days_assignment
            FOREIGN KEY (assignment_id)
            REFERENCES dbo.workout_plan_clients (assignment_id)
            ON DELETE CASCADE
    );
END;

COMMIT TRANSACTION;
