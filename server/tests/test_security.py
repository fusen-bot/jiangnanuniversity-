from app.security import hash_password, mask_email, mask_identifier, verify_password


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("StrongPassword123!")
    second = hash_password("StrongPassword123!")
    assert first != second
    assert verify_password("StrongPassword123!", first)
    assert not verify_password("wrong", first)
    assert not verify_password("anything", "invalid")


def test_sensitive_fields_are_masked():
    assert mask_email("person@example.com") == "p***@example.com"
    assert mask_identifier("320200199901011234") == "320***********1234"
    assert mask_identifier(None) is None
