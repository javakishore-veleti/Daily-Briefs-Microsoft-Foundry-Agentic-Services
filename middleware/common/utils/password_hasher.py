import hashlib
import hmac
import secrets

from middleware.common.utils.logger_util import log_methods


@log_methods
class PasswordHasher:
    _iterations = 600_000

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            PasswordHasher._iterations,
        )
        return f"pbkdf2_sha256${PasswordHasher._iterations}${salt}${digest.hex()}"

    @staticmethod
    def verify(password: str, stored: str) -> bool:
        parts = stored.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        try:
            iterations = int(parts[1])
        except ValueError:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), parts[2].encode(), iterations)
        return hmac.compare_digest(digest.hex(), parts[3])
