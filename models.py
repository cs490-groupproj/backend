from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, DECIMAL, Date, DateTime, ForeignKeyConstraint, Identity, Index, Integer, PrimaryKeyConstraint, String, TEXT, Time, Uuid, text

db = SQLAlchemy()


class BodyParts(db.Model):
    __tablename__ = 'body_parts'
    __table_args__ = (
        PrimaryKeyConstraint('body_part_id', name='PK__body_par__A94D6DCAC87A5DDE'),
        Index('UQ__body_par__72E12F1B0B16A4A7', 'name', mssql_clustered=False, unique=True)
    )

    body_part_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    name = db.Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)

    exercises = db.relationship('Exercises', back_populates='body_part')


class ClientBilling(db.Model):
    __tablename__ = 'client_billing'
    __table_args__ = (
        PrimaryKeyConstraint('client_billing_id', name='PK__client_b__934B3E00115BA8B3'),
        ForeignKeyConstraint(['client_id'], name='FK_ClientBilling_ClientId', refcolumns=['users.user_id']),
    )

    client_billing_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    client_id = db.Column(Uuid, nullable=False)
    card_number = db.Column(String(16, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    card_exp_month = db.Column(Integer, nullable=False)
    card_exp_year = db.Column(Integer, nullable=False)
    card_security_number = db.Column(Integer, nullable=False)
    card_name = db.Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    card_address_1 = db.Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    card_city = db.Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    card_postcode = db.Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    renew_day_number = db.Column(Integer, nullable=False)
    card_address_2 = db.Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))

    client = db.relationship('Users', back_populates='client_billing')
    client_coaches = db.relationship('ClientCoaches', back_populates='client_billing')


class ExerciseCategories(db.Model):
    __tablename__ = 'exercise_categories'
    __table_args__ = (
        PrimaryKeyConstraint('category_id', name='PK__exercise__D54EE9B475005C28'),
        Index('UQ__exercise__72E12F1B482569AC', 'name', mssql_clustered=False, unique=True)
    )

    category_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    name = db.Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)

    exercises = db.relationship('Exercises', back_populates='category')

class MealPlans(db.Model):
    __tablename__ = 'meal_plans'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.user_id'], name='FK_MealPlans_UserId'),
        ForeignKeyConstraint(['meal_type_id'], ['meal_types.meal_type_id'], name='FK_MealPlans_MealTypeId'),
        PrimaryKeyConstraint('meal_plan_id', name='PK__meal_pla__05C57607CEDCD543')
    )

    meal_plan_id= db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    meal_datetime = db.Column(DateTime, nullable=False)
    logged_datetime = db.Column(DateTime)
    meal_type_id = db.Column(Integer, nullable=False)
    user_id = db.Column(Uuid, nullable=False)
    eaten = db.Column(Boolean, nullable=False)
    created_dt = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))
    last_updated = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))

    user = db.relationship('Users', back_populates='meal_plans')
    meal_plan_foods = db.relationship('MealPlanFoods', back_populates='meal_plan')
    meal_type = db.relationship('MealTypes', back_populates='meal_plans')


class MealPlanFoods(db.Model):
    __tablename__ = 'meal_plan_foods'
    __table_args__ = (
        ForeignKeyConstraint(['meal_plan_id'], ['meal_plans.meal_plan_id'], name='FK_MealPlanFoods_MealPlanId'),
        PrimaryKeyConstraint('meal_plan_food_id', name='PK__meal_pla__C8B81100F61548B4')
    )

    meal_plan_food_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    meal_plan_id = db.Column(Integer, nullable=False)
    food_name = db.Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    fdc_id = db.Column(Integer, nullable=False)
    calories = db.Column(Integer, nullable=False, server_default=text('0'))
    serving_size = db.Column(Integer, nullable=False, server_default=text('0'))

    meal_plan = db.relationship('MealPlans', back_populates='meal_plan_foods')


class MealTypes(db.Model):
    __tablename__ = 'meal_types'
    __table_args__ = (
        PrimaryKeyConstraint('meal_type_id', name='PK__meal_typ__6F7616D89F7C22FA'),
    )

    meal_type_id = db.Column(Integer, primary_key=True)
    meal_name = db.Column(String(20, 'SQL_Latin1_General_CP1_CI_AS'))

    meal_plans = db.relationship('MealPlans', back_populates='meal_type')


class Users(db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        PrimaryKeyConstraint('user_id', name='PK__users__B9BE370F88FDE7D6'),
    )

    user_id = db.Column(Uuid, primary_key=True, server_default=text('(newid())'))
    firebase_user_id = db.Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    first_name = db.Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    last_name = db.Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    email = db.Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    is_coach = db.Column(Boolean, nullable=False)
    is_client = db.Column(Boolean, nullable=False, server_default=text('((1))'))
    is_admin = db.Column(Boolean, nullable=False, server_default=text('((0))'))
    is_active = db.Column(Boolean, nullable=False)
    date_created = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))
    coach_cost = db.Column(Integer)

    client_coaches_client = db.relationship('ClientCoaches', foreign_keys='[ClientCoaches.client_id]', back_populates='client')
    client_coaches_coach = db.relationship('ClientCoaches', foreign_keys='[ClientCoaches.coach_id]', back_populates='coach')
    client_billing = db.relationship('ClientBilling', foreign_keys='[ClientBilling.client_id]', back_populates='client')
    client_goals = db.relationship('ClientGoals', back_populates='user')
    coach_reviews = db.relationship('CoachReviews', foreign_keys='[CoachReviews.coach_id]', back_populates='coach')
    coach_reviews_left = db.relationship('CoachReviews', foreign_keys='[CoachReviews.left_by_user_id]', back_populates='left_by_user')
    coach_reports = db.relationship('CoachReports', back_populates='coach', uselist=False)
    coach_requests = db.relationship('CoachRequests', foreign_keys='[CoachRequests.coach_id]', back_populates='coach', uselist=False)
    client_requests = db.relationship('CoachRequests', foreign_keys='[CoachRequests.client_id]', back_populates='client', uselist=False)
    coach_surveys = db.relationship('CoachSurveys', back_populates='user', order_by='CoachSurveys.coach_survey_id.desc()')
    daily_survey_responses = db.relationship('DailySurveyResponses', back_populates='user')
    meal_plans = db.relationship('MealPlans', back_populates='user')
    messages_message_recipient = db.relationship('Messages', foreign_keys='[Messages.message_recipient]', back_populates='users')
    messages_message_sender = db.relationship('Messages', foreign_keys='[Messages.message_sender]', back_populates='users_')
    notifications = db.relationship('Notifications', back_populates='users')
    workout_plans = db.relationship('WorkoutPlans', back_populates='users')
    workouts = db.relationship('Workouts', back_populates='user')


class UsersAudit(db.Model):
    __tablename__ = 'users_audit'
    __table_args__ = (
        PrimaryKeyConstraint('audit_id', name='PK__users_au__5AF33E33B0309296'),
    )

    audit_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    user_id = db.Column(Uuid, nullable=False)
    audit_action = db.Column(String(10, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    changed_by_admin = db.Column(Boolean, nullable=False, server_default=text('((0))'))
    change_date = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))
    first_name = db.Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'))
    last_name = db.Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'))
    email = db.Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'))
    is_coach = db.Column(Boolean)
    is_active = db.Column(Boolean)
    password_hash = db.Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))
    date_created = db.Column(DateTime)
    changed_by = db.Column(Uuid)


class WorkoutTypes(db.Model):
    __tablename__ = 'workout_types'
    __table_args__ = (
        PrimaryKeyConstraint('workout_type_id', name='PK__workout___D2C48094765B05CF'),
        Index('UQ__workout___72E12F1BE0002418', 'name', mssql_clustered=False, unique=True)
    )

    workout_type_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    name = db.Column(String(50, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)

    workout_plans = db.relationship('WorkoutPlans', back_populates='workout_type')
    workouts = db.relationship('Workouts', back_populates='workout_type')


class ClientCoaches(db.Model):
    __tablename__ = 'client_coaches'
    __table_args__ = (
        ForeignKeyConstraint(['client_billing_id'], ['client_billing.client_billing_id'], name='FK_UserCoaches_ClientBillingId'),
        ForeignKeyConstraint(['client_id'], ['users.user_id'], name='FK_UserCoaches_ClientId'),
        ForeignKeyConstraint(['coach_id'], ['users.user_id'], name='FK_UserCoaches_CoachId'),
        PrimaryKeyConstraint('user_coach_id', name='PK__client_c__8B71770341DF5D1A')
    )

    user_coach_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    client_id = db.Column(Uuid, nullable=False)
    coach_id = db.Column(Uuid, nullable=False)
    client_billing_id = db.Column(Integer, nullable=False)
    paired_date = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))

    client_billing = db.relationship('ClientBilling', back_populates='client_coaches')
    client = db.relationship('Users', foreign_keys=[client_id], back_populates='client_coaches_client')
    coach = db.relationship('Users', foreign_keys=[coach_id], back_populates='client_coaches_coach')


class ClientGoals(db.Model):
    __tablename__ = 'client_goals'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.user_id'], name='FK_ClientGoals_User'),
        PrimaryKeyConstraint('user_survey_id', name='PK__client_g__642C11AEF8D1AE8E')
    )

    user_survey_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    user_id = db.Column(Uuid, nullable=False)
    date_created = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))
    last_updated = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))
    primary_goals = db.Column(String(6, 'SQL_Latin1_General_CP1_CI_AS'))
    weight_goal = db.Column(Integer)
    exercise_minutes_goal = db.Column(Integer)
    personal_goals = db.Column(TEXT(16, 'SQL_Latin1_General_CP1_CI_AS'))

    user = db.relationship('Users', back_populates='client_goals')


class CoachReviews(db.Model):
    __tablename__ = 'coach_reviews'
    __table_args__ = (
        ForeignKeyConstraint(['coach_id'], ['users.user_id'], name='FK_CoachReviews_Coach'),
        ForeignKeyConstraint(['left_by_user_id'], ['users.user_id'], name='FK_CoachReviews_User'),
        PrimaryKeyConstraint('coach_review_id', name='PK__coach_re__0C597448EA0AB3AC')
    )

    coach_review_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    coach_id = db.Column(Uuid, nullable=False)
    left_by_user_id = db.Column(Uuid, nullable=False)
    rating = db.Column(Integer, nullable=False)

    coach = db.relationship('Users', foreign_keys=[coach_id], back_populates='coach_reviews')
    left_by_user = db.relationship('Users', foreign_keys=[left_by_user_id], back_populates='coach_reviews_left')


class CoachReports(db.Model):
    __tablename__ = 'coach_reports'
    __table_args__ = (
        ForeignKeyConstraint(['coach_id'], ['users.user_id'], name='FK_CoachReports_Coach'),
    )

    coach_report_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    coach_id = db.Column(Uuid, nullable=False)
    report_body = db.Column(TEXT(16, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    submitted_datetime = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))

    coach = db.relationship('Users', back_populates='coach_reports')


class CoachRequests(db.Model):
    __tablename__ = 'coach_requests'
    __table_args__ = (
        ForeignKeyConstraint(['client_id'], ['users.user_id'], name='FK_CoachRequests_Client'),
        ForeignKeyConstraint(['coach_id'], ['users.user_id'], name='FK_CoachRequests_Coach'),
        PrimaryKeyConstraint('coach_request_id', name='PK__coach_re__B29DBB8909159964')
    )

    coach_request_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    client_id = db.Column(Uuid, nullable=False)
    coach_id = db.Column(Uuid, nullable=False)

    client = db.relationship('Users', foreign_keys=[client_id], back_populates='client_requests')
    coach = db.relationship('Users', foreign_keys=[coach_id], back_populates='coach_requests')



class CoachSurveys(db.Model):
    __tablename__ = 'coach_surveys'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.user_id'], name='FK__coach_sur__user___7ADC2F5E'),
        PrimaryKeyConstraint('coach_survey_id', name='PK__coach_su__8E6168BA433627D0')
    )

    coach_survey_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    user_id = db.Column(Uuid, nullable=False)
    specialization = db.Column(String(20, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    qualifications = db.Column(TEXT(16, 'SQL_Latin1_General_CP1_CI_AS'))
    date_created = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))
    last_update = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))

    user = db.relationship('Users', back_populates='coach_surveys')


class DailySurveyResponses(db.Model):
    __tablename__ = 'daily_survey_responses'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.user_id'], name='FK_DailySurveyResponses_User'),
        PrimaryKeyConstraint('daily_survey_response_id', name='PK__daily_su__11D9911E8D15C919'),
    )

    daily_survey_response_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    user_id = db.Column(Uuid, nullable=False)
    mood = db.Column(Integer, nullable=False)
    energy = db.Column(Integer, nullable=False)
    sleep = db.Column(Integer, nullable=False)
    notes = db.Column(TEXT(16, 'SQL_Latin1_General_CP1_CI_AS'))
    date_submitted = db.Column(Date, nullable=False)

    user = db.relationship('Users', back_populates='daily_survey_responses')


class Exercises(db.Model):
    __tablename__ = 'exercises'
    __table_args__ = (
        ForeignKeyConstraint(['body_part_id'], ['body_parts.body_part_id'], name='FK__exercises__body___10CB707D'),
        ForeignKeyConstraint(['category_id'], ['exercise_categories.category_id'], name='FK__exercises__categ__11BF94B6'),
        PrimaryKeyConstraint('exercise_id', name='PK__exercise__C121418E36037AC6')
    )

    exercise_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    name = db.Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    youtube_url = db.Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'))
    body_part_id = db.Column(Integer, nullable=False)
    category_id = db.Column(Integer, nullable=False)

    body_part = db.relationship('BodyParts', back_populates='exercises')
    category = db.relationship('ExerciseCategories', back_populates='exercises')
    workout_plan_exercises = db.relationship('WorkoutPlanExercises', back_populates='exercise')
    workout_exercises = db.relationship('WorkoutExercises', back_populates='exercise')


class Messages(db.Model):
    __tablename__ = 'messages'
    __table_args__ = (
        ForeignKeyConstraint(['message_recipient'], ['users.user_id'], name='FK_Messages_MessageRecipient'),
        ForeignKeyConstraint(['message_sender'], ['users.user_id'], name='FK_Messages_MessageSender'),
        PrimaryKeyConstraint('message_id', name='PK__messages__0BBF6EE6A885E629')
    )

    message_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    message_sender = db.Column(Uuid, nullable=False)
    message_recipient = db.Column(Uuid, nullable=False)
    read = db.Column(Boolean, nullable=False)
    message_body = db.Column(TEXT(16, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    sent_date = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))

    users = db.relationship('Users', foreign_keys=[message_recipient], back_populates='messages_message_recipient')
    users_ = db.relationship('Users', foreign_keys=[message_sender], back_populates='messages_message_sender')


class Notifications(db.Model):
    __tablename__ = 'notifications'
    __table_args__ = (
        ForeignKeyConstraint(['notification_recipient'], ['users.user_id'], name='FK_Notifications_NotificationRecipient'),
        PrimaryKeyConstraint('notification_id', name='PK__notifica__E059842F267F080A')
    )

    notification_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    notification_recipient = db.Column(Uuid, nullable=False)
    dismissed = db.Column(Boolean, nullable=False, server_default=text('((1))'))
    notification_body = db.Column(TEXT(16, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    sent_date = db.Column(DateTime, nullable=False, server_default=text('(getdate())'))

    users = db.relationship('Users', back_populates='notifications')


class WorkoutPlans(db.Model):
    __tablename__ = 'workout_plans'
    __table_args__ = (
        ForeignKeyConstraint(['created_by'], ['users.user_id'], name='FK__workout_p__creat__2101D846'),
        ForeignKeyConstraint(['workout_type_id'], ['workout_types.workout_type_id'], name='FK__workout_p__worko__200DB40D'),
        PrimaryKeyConstraint('workout_plan_id', name='PK__workout___63DB3C9085BA90E6')
    )

    workout_plan_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    title = db.Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    workout_type_id = db.Column(Integer)
    description = db.Column(String(1000, 'SQL_Latin1_General_CP1_CI_AS'))
    created_by = db.Column(Uuid)
    duration_min = db.Column(Integer)

    users = db.relationship('Users', back_populates='workout_plans')
    workout_type = db.relationship('WorkoutTypes', back_populates='workout_plans')
    workout_plan_exercises = db.relationship(
        'WorkoutPlanExercises',
        back_populates='workout_plan',
        passive_deletes=True,
    )
    workouts = db.relationship('Workouts', back_populates='workout_plan')
    workout_plan_days = db.relationship('WorkoutPlanDays', back_populates='workout_plan')


class WorkoutPlanExercises(db.Model):
    __tablename__ = 'workout_plan_exercises'
    __table_args__ = (
        ForeignKeyConstraint(['exercise_id'], ['exercises.exercise_id'], name='FK__workout_p__exerc__25C68D63'),
        ForeignKeyConstraint(['workout_plan_id'], ['workout_plans.workout_plan_id'], ondelete='CASCADE', name='FK__workout_p__worko__24D2692A'),
        PrimaryKeyConstraint('workout_plan_exercise_id', name='PK__workout___20D1E9E41C33385E')
    )

    workout_plan_exercise_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    workout_plan_id = db.Column(Integer, nullable=False)
    exercise_id = db.Column(Integer, nullable=False)
    position = db.Column(Integer, nullable=False, server_default=text('((0))'))
    sets = db.Column(Integer)
    reps = db.Column(Integer)
    weight = db.Column(DECIMAL(8, 2))
    rpe = db.Column(DECIMAL(3, 1))
    duration_sec = db.Column(Integer)
    distance_m = db.Column(DECIMAL(10, 2))
    pace_sec_per_km = db.Column(DECIMAL(8, 2))
    calories = db.Column(Integer)
    notes = db.Column(TEXT(16, 'SQL_Latin1_General_CP1_CI_AS'))

    exercise = db.relationship('Exercises', back_populates='workout_plan_exercises')
    workout_plan = db.relationship('WorkoutPlans', back_populates='workout_plan_exercises')


class WorkoutPlanDays(db.Model):
    __tablename__ = 'workout_plan_days'
    __table_args__ = (
        ForeignKeyConstraint(['workout_plan_id'], ['workout_plans.workout_plan_id'], name='FK_WorkoutPlanDays_WorkoutPlanId'),
        PrimaryKeyConstraint('id', name='PK_workout_plan_days')
    )

    id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    workout_plan_id = db.Column(Integer, nullable=False)
    weekday = db.Column(String(10, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    schedule_time = db.Column(Time, nullable=False)

    workout_plan = db.relationship('WorkoutPlans', back_populates='workout_plan_days')


class Workouts(db.Model):
    __tablename__ = 'workouts'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.user_id'], name='FK__workouts__user_i__17786E0C'),
        ForeignKeyConstraint(['workout_plan_id'], ['workout_plans.workout_plan_id'], name='FK__workouts__workou__21F5FC7F'),
        ForeignKeyConstraint(['workout_type_id'], ['workout_types.workout_type_id'], name='FK__workouts__workou__186C9245'),
        PrimaryKeyConstraint('workout_id', name='PK__workouts__02AB2F8EF047554B')
    )

    workout_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    user_id = db.Column(Uuid, nullable=False)
    title = db.Column(String(255, 'SQL_Latin1_General_CP1_CI_AS'), nullable=False)
    workout_type_id = db.Column(Integer)
    workout_plan_id = db.Column(Integer)
    notes = db.Column(TEXT(16, 'SQL_Latin1_General_CP1_CI_AS'))
    mood = db.Column(Integer)
    duration_mins = db.Column(Integer)
    completion_date = db.Column(DateTime)

    user = db.relationship('Users', back_populates='workouts')
    workout_plan = db.relationship('WorkoutPlans', back_populates='workouts')
    workout_type = db.relationship('WorkoutTypes', back_populates='workouts')
    workout_exercises = db.relationship('WorkoutExercises', back_populates='workout')


class WorkoutExercises(db.Model):
    __tablename__ = 'workout_exercises'
    __table_args__ = (
        ForeignKeyConstraint(['exercise_id'], ['exercises.exercise_id'], name='FK__workout_e__exerc__1C3D2329'),
        ForeignKeyConstraint(['workout_id'], ['workouts.workout_id'], ondelete='CASCADE', name='FK__workout_e__worko__1B48FEF0'),
        PrimaryKeyConstraint('workout_exercise_id', name='PK__workout___12A7653332BFAFB3')
    )

    workout_exercise_id = db.Column(Integer, Identity(start=1, increment=1), primary_key=True)
    workout_id = db.Column(Integer, nullable=False)
    exercise_id = db.Column(Integer, nullable=False)
    position = db.Column(Integer, nullable=False, server_default=text('((0))'))
    sets = db.Column(Integer)
    reps = db.Column(Integer)
    weight = db.Column(DECIMAL(8, 2))
    rpe = db.Column(DECIMAL(3, 1))
    duration_sec = db.Column(Integer)
    distance_m = db.Column(DECIMAL(10, 2))
    pace_sec_per_km = db.Column(DECIMAL(8, 2))
    calories = db.Column(Integer)
    notes = db.Column(TEXT(16, 'SQL_Latin1_General_CP1_CI_AS'))

    exercise = db.relationship('Exercises', back_populates='workout_exercises')
    workout = db.relationship('Workouts', back_populates='workout_exercises')
