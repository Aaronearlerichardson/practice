CREATE TABLE clinics (
    clinic_id  INT PRIMARY KEY,
    name       TEXT NOT NULL
);

CREATE TABLE visits (
    visit_id    INT PRIMARY KEY,
    clinic_id   INT NOT NULL REFERENCES clinics(clinic_id),
    visit_date  DATE NOT NULL,
    status      TEXT NOT NULL  -- 'completed', 'cancelled', ...
);

INSERT INTO clinics (clinic_id, name) VALUES
    (1, 'Eastside'),
    (2, 'Westside'),
    (3, 'Northgate'),
    (4, 'Southgate');

INSERT INTO visits (visit_id, clinic_id, visit_date, status) VALUES
    (1, 2, '2025-03-02', 'completed'),
    (2, 2, '2025-06-10', 'cancelled'),
    (3, 3, '2024-11-05', 'completed'),
    (4, 4, '2025-01-15', 'completed'),
    (5, 4, '2025-02-20', 'completed'),
    (6, 4, '2026-02-01', 'completed');
