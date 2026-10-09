-- Shared clinical practice schema (Postgres 14+).
-- Loaded by `python tasks.py setup-db`, which runs this file and then seed.py.
-- Only primary keys exist. There are no secondary indexes on purpose:
-- adding them is part of the performance problems.

DROP TABLE IF EXISTS labs, encounters, enrollments, quarterly_loads, patients, sites CASCADE;

-- One row per contributing health system.
CREATE TABLE sites (
    site_id       text PRIMARY KEY,          -- 'S01'..'S12'
    site_name     text NOT NULL,
    state         char(2) NOT NULL,
    ehr_vendor    text NOT NULL,
    onboarded_on  date NOT NULL              -- first quarter a site owes a submission
);

-- Patient demographics as delivered by the site. Fill rates vary by site:
-- missing values arrive as NULL, '' or 'Unknown'/'U' depending on the site.
CREATE TABLE patients (
    patient_id    integer PRIMARY KEY,
    site_id       text NOT NULL,
    birth_date    date,
    sex           text,                      -- 'F','M','U','' or NULL
    race          text,
    ethnicity     text,
    zip3          char(3)
);

-- Coverage periods at a site. Periods for one patient can be adjacent,
-- overlapping, or separated by gaps. end_date NULL = still enrolled.
CREATE TABLE enrollments (
    enrollment_id integer PRIMARY KEY,
    patient_id    integer NOT NULL,
    site_id       text NOT NULL,
    start_date    date NOT NULL,
    end_date      date
);

CREATE TABLE encounters (
    encounter_id   bigint PRIMARY KEY,
    patient_id     integer NOT NULL,
    site_id        text NOT NULL,
    encounter_type text NOT NULL,            -- outpatient | telehealth | ed | inpatient
    admit_at       timestamp NOT NULL,
    discharge_at   timestamp,
    primary_dx     text,                     -- ICD-10-CM code
    provider_id    text
);

-- One row per file delivery attempt. A site-quarter can have a rejected
-- attempt followed by an accepted one, or no row at all.
CREATE TABLE quarterly_loads (
    load_id        integer PRIMARY KEY,
    site_id        text NOT NULL,
    quarter_start  date NOT NULL,            -- first day of the quarter the data covers
    received_at    timestamp NOT NULL,
    status         text NOT NULL,            -- accepted | rejected
    row_count      integer NOT NULL
);

-- Lab results, append-only, exactly as loaded.
-- (site_id, source_record_id) is the site's own record key. When a site
-- corrects a result, it resends the same source_record_id in a later
-- batch with a later loaded_at; the old row stays. Units follow each
-- site's convention (some sites use SI units, one lowercases 'mg/dl').
CREATE TABLE labs (
    lab_id            bigint PRIMARY KEY,    -- increases in load order
    patient_id        integer NOT NULL,
    site_id           text NOT NULL,
    source_record_id  text NOT NULL,
    test_code         text NOT NULL,         -- GLU CREAT HGB K NA ALT HBA1C PLT
    value             numeric(10,2),
    unit              text NOT NULL,
    collected_at      timestamp NOT NULL,
    loaded_at         timestamp NOT NULL,
    load_batch        text NOT NULL          -- e.g. 'S03-2025Q2'
);
