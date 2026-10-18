USE p4_handshake;


/*
    DEMO COMPANY 1
    This company exists only so students can browse its jobs.
*/
INSERT INTO users (
    email,
    password_hash,
    user_role
)
VALUES (
    'demo.company1@example.com',
    'demo-company-password-hash',
    'company'
)
ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id);

SET @company1_id = LAST_INSERT_ID();

INSERT INTO company_profiles (
    user_id,
    company_name,
    location,
    description,
    contact_email,
    contact_phone
)
VALUES (
    @company1_id,
    'TechNova Solutions',
    'San Jose, California',
    'A technology company focused on cloud computing and data platforms.',
    'careers@technova.example.com',
    '408-555-1001'
)
ON DUPLICATE KEY UPDATE
    company_name = VALUES(company_name);


/*
    DEMO COMPANY 2
*/
INSERT INTO users (
    email,
    password_hash,
    user_role
)
VALUES (
    'demo.company2@example.com',
    'demo-company-password-hash',
    'company'
)
ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id);

SET @company2_id = LAST_INSERT_ID();

INSERT INTO company_profiles (
    user_id,
    company_name,
    location,
    description,
    contact_email,
    contact_phone
)
VALUES (
    @company2_id,
    'DataBridge Analytics',
    'San Francisco, California',
    'An analytics company helping organizations make data-driven decisions.',
    'careers@databridge.example.com',
    '415-555-2002'
)
ON DUPLICATE KEY UPDATE
    company_name = VALUES(company_name);


/*
    DEMO SKILLS
*/
INSERT IGNORE INTO skills (skill_name)
VALUES
    ('Python'),
    ('SQL'),
    ('React'),
    ('Machine Learning'),
    ('FastAPI'),
    ('Data Analysis');


/*
    DEMO JOB 1
*/
INSERT INTO jobs (
    company_id,
    title,
    posted_date,
    deadline,
    location,
    is_remote,
    salary_min,
    salary_max,
    description,
    category
)
SELECT
    @company1_id,
    'Data Science Intern',
    '2026-09-20',
    '2026-12-31',
    'San Jose, California',
    FALSE,
    25.00,
    35.00,
    'Work with data scientists to build machine learning models and analyze business data.',
    'internship'
WHERE NOT EXISTS (
    SELECT 1
    FROM jobs
    WHERE company_id = @company1_id
      AND title = 'Data Science Intern'
);


/*
    DEMO JOB 2
*/
INSERT INTO jobs (
    company_id,
    title,
    posted_date,
    deadline,
    location,
    is_remote,
    salary_min,
    salary_max,
    description,
    category
)
SELECT
    @company1_id,
    'Python Backend Developer Intern',
    '2026-09-20',
    '2026-11-30',
    'San Jose, California',
    FALSE,
    24.00,
    32.00,
    'Build backend APIs using Python and FastAPI.',
    'internship'
WHERE NOT EXISTS (
    SELECT 1
    FROM jobs
    WHERE company_id = @company1_id
      AND title = 'Python Backend Developer Intern'
);


/*
    DEMO JOB 3
*/
INSERT INTO jobs (
    company_id,
    title,
    posted_date,
    deadline,
    location,
    is_remote,
    salary_min,
    salary_max,
    description,
    category
)
SELECT
    @company2_id,
    'Machine Learning Analyst',
    '2026-09-20',
    '2026-12-15',
    'Remote',
    TRUE,
    70000.00,
    90000.00,
    'Analyze datasets and create machine learning solutions for business problems.',
    'full_time'
WHERE NOT EXISTS (
    SELECT 1
    FROM jobs
    WHERE company_id = @company2_id
      AND title = 'Machine Learning Analyst'
);


/*
    DEMO JOB 4
*/
INSERT INTO jobs (
    company_id,
    title,
    posted_date,
    deadline,
    location,
    is_remote,
    salary_min,
    salary_max,
    description,
    category
)
SELECT
    @company2_id,
    'SQL Data Analyst Intern',
    '2026-09-20',
    '2026-10-31',
    'San Francisco, California',
    FALSE,
    23.00,
    30.00,
    'Write SQL queries, create reports, and support data analysis projects.',
    'internship'
WHERE NOT EXISTS (
    SELECT 1
    FROM jobs
    WHERE company_id = @company2_id
      AND title = 'SQL Data Analyst Intern'
);


/*
    CONNECT JOBS TO SKILLS
*/
INSERT IGNORE INTO job_skills (job_id, skill_id)
SELECT j.id, s.id
FROM jobs j
JOIN skills s
WHERE j.title = 'Data Science Intern'
  AND s.skill_name IN (
      'Python',
      'SQL',
      'Machine Learning'
  );

INSERT IGNORE INTO job_skills (job_id, skill_id)
SELECT j.id, s.id
FROM jobs j
JOIN skills s
WHERE j.title = 'Python Backend Developer Intern'
  AND s.skill_name IN (
      'Python',
      'FastAPI'
  );

INSERT IGNORE INTO job_skills (job_id, skill_id)
SELECT j.id, s.id
FROM jobs j
JOIN skills s
WHERE j.title = 'Machine Learning Analyst'
  AND s.skill_name IN (
      'Python',
      'SQL',
      'Machine Learning',
      'Data Analysis'
  );

INSERT IGNORE INTO job_skills (job_id, skill_id)
SELECT j.id, s.id
FROM jobs j
JOIN skills s
WHERE j.title = 'SQL Data Analyst Intern'
  AND s.skill_name IN (
      'SQL',
      'Data Analysis'
  );


/*
    VERIFY DEMO JOBS
*/
SELECT
    j.id,
    j.title,
    c.company_name,
    j.location,
    j.category,
    j.is_remote
FROM jobs j
JOIN company_profiles c
    ON j.company_id = c.user_id;