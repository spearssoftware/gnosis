from gnosis.ids import disambiguate, make_uuid, slugify


def test_slugify_basic():
    assert slugify("Abraham") == "abraham"
    assert slugify("Mount Sinai") == "mount-sinai"
    assert slugify("Mary Magdalene") == "mary-magdalene"


def test_slugify_diacritics():
    assert slugify("Mëlchîzédek") == "melchizedek"


def test_slugify_special_chars():
    assert slugify("Simon (Peter)") == "simon-peter"


def test_make_uuid_deterministic():
    u1 = make_uuid("abraham")
    u2 = make_uuid("abraham")
    assert u1 == u2
    assert len(u1) == 36


def test_make_uuid_different_for_different_slugs():
    assert make_uuid("abraham") != make_uuid("isaac")


def test_disambiguate_single():
    records = [{"_airtable_id": "rec1"}]
    result = disambiguate("Abraham", records, id_field="_airtable_id")
    assert result == {"rec1": "abraham"}


def test_disambiguate_with_patronymic():
    records = [
        {"_airtable_id": "rec1", "father": ["Jacob"]},
        {"_airtable_id": "rec2", "father": ["Esau"]},
    ]
    result = disambiguate("Zechariah", records, id_field="_airtable_id")
    slugs = set(result.values())
    assert len(slugs) == 2
    assert all("zechariah" in s for s in slugs)


def test_disambiguate_numeric_fallback():
    records = [
        {"_airtable_id": "rec1"},
        {"_airtable_id": "rec2"},
    ]
    result = disambiguate("Zechariah", records, id_field="_airtable_id")
    slugs = set(result.values())
    assert len(slugs) == 2
