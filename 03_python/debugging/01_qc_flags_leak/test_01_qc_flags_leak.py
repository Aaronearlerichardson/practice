from buggy import collect_flags, summarize, validate_batch


def make_batch():
    return [
        {"record_id": "R1", "patient_id": "P001", "site_id": "S01",
         "encounter_date": "2026-07-02", "age": 54, "sex": "F", "weight_kg": 71.2},
        {"record_id": "R2", "patient_id": "", "site_id": "S01",
         "encounter_date": "2026-07-03", "age": 61, "sex": "M", "weight_kg": 88.0},
        {"record_id": "R3", "patient_id": "P003", "site_id": "S01",
         "encounter_date": "2026-07-03", "age": 47, "sex": "F", "weight_kg": 64.5},
        {"record_id": "R4", "patient_id": "P004", "site_id": "S01",
         "encounter_date": "2026-07-05", "age": 212, "sex": "X", "weight_kg": 80.1},
        {"record_id": "R5", "patient_id": "P005", "site_id": "S01",
         "encounter_date": "2026-07-06", "age": 33, "sex": "U", "weight_kg": 59.9},
    ]


def test_clean_record_has_no_flags():
    rec = make_batch()[0]
    assert collect_flags(rec) == []


def test_bad_record_flags_only_its_own_problems():
    collect_flags(make_batch()[1])  # an earlier record with a problem
    assert collect_flags(make_batch()[3]) == ["implausible:age", "invalid:sex"]


def test_seeded_flags_are_kept():
    assert collect_flags(make_batch()[0], ["parse:trailing_delimiter"]) == [
        "parse:trailing_delimiter"
    ]


def test_batch_flags_per_record():
    results = validate_batch(make_batch())
    assert results == {
        "R1": [],
        "R2": ["missing:patient_id"],
        "R3": [],
        "R4": ["implausible:age", "invalid:sex"],
        "R5": [],
    }


def test_rerunning_a_batch_gives_same_summary():
    first = summarize(validate_batch(make_batch()))
    second = summarize(validate_batch(make_batch()))
    assert first == second
    assert first["n_clean"] == 3
    assert first["flag_counts"] == {
        "missing:patient_id": 1, "implausible:age": 1, "invalid:sex": 1,
    }
