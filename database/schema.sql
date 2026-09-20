/*
    Pair 4 Handshake Application Database

    Pair number: 4
    Database: p4_handshake
    Seed: 4
    Backend port: 9040
*/


CREATE DATABASE IF NOT EXISTS p4_handshake
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE p4_handshake;


/*
    USERS TABLE

    Stores login information for both students and companies.
    Passwords are stored as bcrypt hashes, never as plain text.
*/
CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    email VARCHAR(255) NOT NULL UNIQUE,

    password_hash VARCHAR(255) NOT NULL,

    user_role ENUM('student', 'company') NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);


/*
    STUDENT_PROFILES TABLE

    Stores information specific to students.

    user_id is both the primary key and foreign key.
    This creates a one-to-one relationship between users and profiles.
*/
CREATE TABLE IF NOT EXISTS student_profiles (
    user_id BIGINT UNSIGNED PRIMARY KEY,

    full_name VARCHAR(150) NOT NULL,

    date_of_birth DATE NULL,

    city VARCHAR(100) NULL,

    state VARCHAR(100) NULL,

    country VARCHAR(100) NULL,

    career_objective TEXT NULL,

    college VARCHAR(200) NULL,

    degree VARCHAR(150) NULL,

    major VARCHAR(150) NULL,

    graduation_year SMALLINT UNSIGNED NULL,

    cgpa DECIMAL(4,2) NULL,

    experience TEXT NULL,

    phone VARCHAR(30) NULL,

    profile_picture_path VARCHAR(500) NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_student_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);


/*
    COMPANY_PROFILES TABLE

    Stores information specific to companies.
*/
CREATE TABLE IF NOT EXISTS company_profiles (
    user_id BIGINT UNSIGNED PRIMARY KEY,

    company_name VARCHAR(200) NOT NULL,

    location VARCHAR(200) NULL,

    description TEXT NULL,

    contact_email VARCHAR(255) NULL,

    contact_phone VARCHAR(30) NULL,

    profile_picture_path VARCHAR(500) NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_company_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);


/*
    SKILLS TABLE

    Stores reusable skills such as Python, SQL, React, or Docker.
*/
CREATE TABLE IF NOT EXISTS skills (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    skill_name VARCHAR(100) NOT NULL UNIQUE
);


/*
    STUDENT_SKILLS TABLE

    Many-to-many relationship:
    - One student can have many skills.
    - One skill can belong to many students.
*/
CREATE TABLE IF NOT EXISTS student_skills (
    student_id BIGINT UNSIGNED NOT NULL,

    skill_id BIGINT UNSIGNED NOT NULL,

    PRIMARY KEY (student_id, skill_id),

    CONSTRAINT fk_student_skills_student
        FOREIGN KEY (student_id)
        REFERENCES student_profiles(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_student_skills_skill
        FOREIGN KEY (skill_id)
        REFERENCES skills(id)
        ON DELETE CASCADE
);


/*
    JOBS TABLE

    Stores jobs posted by companies.
*/
CREATE TABLE IF NOT EXISTS jobs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    company_id BIGINT UNSIGNED NOT NULL,

    title VARCHAR(200) NOT NULL,

    posted_date DATE NOT NULL,

    deadline DATE NOT NULL,

    location VARCHAR(200) NOT NULL,

    is_remote BOOLEAN NOT NULL DEFAULT FALSE,

    salary_min DECIMAL(12,2) NULL,

    salary_max DECIMAL(12,2) NULL,

    description TEXT NOT NULL,

    category ENUM(
        'full_time',
        'part_time',
        'on_campus',
        'internship'
    ) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_job_company
        FOREIGN KEY (company_id)
        REFERENCES company_profiles(user_id)
        ON DELETE CASCADE,

    INDEX idx_jobs_title (title),

    INDEX idx_jobs_location (location),

    INDEX idx_jobs_category (category),

    INDEX idx_jobs_deadline (deadline)
);


/*
    JOB_SKILLS TABLE

    Many-to-many relationship:
    - One job can require many skills.
    - One skill can be required by many jobs.
*/
CREATE TABLE IF NOT EXISTS job_skills (
    job_id BIGINT UNSIGNED NOT NULL,

    skill_id BIGINT UNSIGNED NOT NULL,

    PRIMARY KEY (job_id, skill_id),

    CONSTRAINT fk_job_skills_job
        FOREIGN KEY (job_id)
        REFERENCES jobs(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_job_skills_skill
        FOREIGN KEY (skill_id)
        REFERENCES skills(id)
        ON DELETE CASCADE
);


/*
    APPLICATIONS TABLE

    Stores job applications submitted by students.
*/
CREATE TABLE IF NOT EXISTS applications (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    student_id BIGINT UNSIGNED NOT NULL,

    job_id BIGINT UNSIGNED NOT NULL,

    /*
        Stores the location of the uploaded PDF resume.
        The actual PDF will be stored in the backend uploads folder.
    */
    resume_path VARCHAR(500) NOT NULL,

    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    status ENUM(
        'Pending',
        'Reviewed',
        'Declined'
    ) NOT NULL DEFAULT 'Pending',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_application_student
        FOREIGN KEY (student_id)
        REFERENCES student_profiles(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_application_job
        FOREIGN KEY (job_id)
        REFERENCES jobs(id)
        ON DELETE CASCADE,

    /*
        Prevents a student from applying to the same job twice.
    */
    CONSTRAINT unique_student_job_application
        UNIQUE (student_id, job_id)
);


/*
    EVENTS TABLE

    Stores career events posted by companies.
*/
CREATE TABLE IF NOT EXISTS events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    company_id BIGINT UNSIGNED NOT NULL,

    event_name VARCHAR(200) NOT NULL,

    description TEXT NOT NULL,

    event_date DATE NOT NULL,

    event_time TIME NOT NULL,

    location VARCHAR(200) NOT NULL,

    eligibility VARCHAR(500) NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_event_company
        FOREIGN KEY (company_id)
        REFERENCES company_profiles(user_id)
        ON DELETE CASCADE,

    INDEX idx_events_date (event_date),

    INDEX idx_events_name (event_name),

    INDEX idx_events_location (location)
);


/*
    EVENT_REGISTRATIONS TABLE

    Many-to-many relationship:
    - One student can register for many events.
    - One event can have many students.
*/
CREATE TABLE IF NOT EXISTS event_registrations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    student_id BIGINT UNSIGNED NOT NULL,

    event_id BIGINT UNSIGNED NOT NULL,

    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_registration_student
        FOREIGN KEY (student_id)
        REFERENCES student_profiles(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_registration_event
        FOREIGN KEY (event_id)
        REFERENCES events(id)
        ON DELETE CASCADE,

    /*
        Prevents duplicate event registration.
    */
    CONSTRAINT unique_student_event_registration
        UNIQUE (student_id, event_id)
);


/*
    STUDENT_PREFERENCES TABLE

    Stores preferences used by the AI assistant.
*/
CREATE TABLE IF NOT EXISTS student_preferences (
    student_id BIGINT UNSIGNED PRIMARY KEY,

    preferred_city VARCHAR(100) NULL,

    preferred_category ENUM(
        'full_time',
        'part_time',
        'on_campus',
        'internship'
    ) NULL,

    minimum_salary DECIMAL(12,2) NULL,

    preferred_work_mode ENUM(
        'remote',
        'onsite',
        'hybrid'
    ) NULL,

    preferred_major VARCHAR(150) NULL,

    preferred_event_major VARCHAR(150) NULL,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_preferences_student
        FOREIGN KEY (student_id)
        REFERENCES student_profiles(user_id)
        ON DELETE CASCADE
);


/*
    VERIFICATION
*/
SHOW TABLES;

SELECT DATABASE();