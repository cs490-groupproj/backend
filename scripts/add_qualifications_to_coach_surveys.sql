-- Add qualifications column to coach_surveys (idempotent).
IF COL_LENGTH('coach_surveys', 'qualifications') IS NULL
BEGIN
    ALTER TABLE coach_surveys
    ADD qualifications TEXT NULL;
END
GO

-- Rollback (manual):
-- IF COL_LENGTH('coach_surveys', 'qualifications') IS NOT NULL
-- BEGIN
--     ALTER TABLE coach_surveys
--     DROP COLUMN qualifications;
-- END
-- GO
