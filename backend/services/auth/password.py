from passlib.context import CryptContext


# Prefer Argon2id for new secrets while still accepting legacy PBKDF2 hashes already stored.
pwd_context = CryptContext(schemes=["argon2", "pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
