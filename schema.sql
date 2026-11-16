--BridgeTheSkill: normalized SQLite schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS career_roles (
    role_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (length(trim(title)) > 0),
    description TEXT NOT NULL CHECK (length(trim(description)) > 0)
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS role_skills (
    role_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    PRIMARY KEY (role_id, skill_id),
    FOREIGN KEY (role_id) REFERENCES career_roles(role_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS courses (
    course_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (length(trim(title)) > 0),
    description TEXT NOT NULL CHECK (length(trim(description)) > 0),
    url TEXT  -- Nullable: fictional sample courses have no real provider URLs.
);

CREATE TABLE IF NOT EXISTS course_skills (
    course_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    PRIMARY KEY (course_id, skill_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_role_skills_skill ON role_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_course_skills_skill ON course_skills(skill_id);
