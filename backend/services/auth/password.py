from passlib.context import CryptContext


# Use a passlib-managed scheme that is stable on the current local Python toolchain.
# The architecture doc still defines the target auth design; this keeps the scaffold testable.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
