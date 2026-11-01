# Reference Implementation: Comprehensive 5-Vector Test Suite

Demonstration of full-spectrum test engineering for a `TokenAuthenticator` service.

```python
import hmac
import time
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------
# Vector A: Functional Coverage (Positive, Negative, Boundary)
# ---------------------------------------------------------
class TestFunctionalVectors:
    def test_valid_token_authentication(self):
        auth = TokenAuthenticator(secret="test-secret")
        token = auth.generate("user_123")
        assert auth.verify(token) == "user_123"

    def test_empty_and_null_byte_tokens(self):
        auth = TokenAuthenticator(secret="test-secret")
        with pytest.raises(ValueError):
            auth.verify("")
        with pytest.raises(ValueError):
            auth.verify("invalid\x00token")

    def test_unicode_normalization_handling(self):
        auth = TokenAuthenticator(secret="test-secret")
        user_id = "user_café"
        token = auth.generate(user_id)
        assert auth.verify(token) == user_id


# ---------------------------------------------------------
# Vector B: Security & Adversarial Attacks
# ---------------------------------------------------------
class TestSecurityVectors:
    def test_constant_time_signature_verification(self, monkeypatch):
        called_constant_time = False

        def mock_compare(a, b):
            nonlocal called_constant_time
            called_constant_time = True
            return hmac.compare_digest(a, b)

        monkeypatch.setattr(hmac, "compare_digest", mock_compare)
        auth = TokenAuthenticator(secret="test-secret")
        token = auth.generate("user_admin")
        auth.verify(token)
        assert called_constant_time, "Verification MUST use constant-time comparison."

    def test_path_traversal_payload_in_user_id(self):
        auth = TokenAuthenticator(secret="test-secret")
        with pytest.raises(ValueError):
            auth.generate("../../etc/passwd")


# ---------------------------------------------------------
# Vector C: Combinatorial Permutative Matrix
# ---------------------------------------------------------
@pytest.mark.parametrize(
    "role,status,expected_allowed",
    [
        pytest.param("admin", "active", True, id="admin-active"),
        pytest.param("admin", "suspended", False, id="admin-suspended"),
        pytest.param("user", "active", True, id="user-active"),
        pytest.param("user", "suspended", False, id="user-suspended"),
        pytest.param("guest", "active", False, id="guest-active"),
        pytest.param("guest", "suspended", False, id="guest-suspended"),
    ],
)
def test_role_matrix(role, status, expected_allowed):
    acl = AccessControlEngine()
    result = acl.can_access(role=role, status=status, action="WRITE")
    assert result == expected_allowed


# ---------------------------------------------------------
# Vector D: Performance & Asymptotic Complexity
# ---------------------------------------------------------
@pytest.mark.benchmark
def test_linear_verification_complexity():
    auth = TokenAuthenticator(secret="test-secret")
    tokens_100 = [auth.generate(f"user_{i}") for i in range(100)]
    tokens_1000 = [auth.generate(f"user_{i}") for i in range(1000)]

    start = time.perf_counter()
    for t in tokens_100:
        auth.verify(t)
    t_100 = time.perf_counter() - start

    start = time.perf_counter()
    for t in tokens_1000:
        auth.verify(t)
    t_1000 = time.perf_counter() - start

    ratio = t_1000 / max(t_100, 1e-9)
    assert ratio < 15.0, f"Verification scaling ratio exceeded linear bounds: {ratio:.2f}"
```
