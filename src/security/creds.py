import bcrypt
import hashlib
import base64
from configs.ext import SALT
from cryptography.fernet import Fernet

# Generate a key and instantiate a Fernet instance (store the key securely)
cipher_suite = Fernet(SALT)


# Encrypt the token
def encrypt_token(token: str) -> str:
    return cipher_suite.encrypt(token.encode()).decode()

# Decrypt the token
def decrypt_token(encrypted_token: str) -> str:
    return cipher_suite.decrypt(encrypted_token.encode()).decode()

def hash_password(password: str) -> str:
    """Hashes a password using SHA-256 with a pepper, then bcrypts it, and returns a base64-encoded string."""
    # Concatenate pepper with password
    peppered_password = f"{password}{SALT}"
    hashed_password = hashlib.sha256(peppered_password.encode('UTF-8')).digest()

    # Hash with bcrypt
    bcrypted = bcrypt.hashpw(hashed_password, bcrypt.gensalt())

    # Encode in base64 for storage
    return base64.b64encode(bcrypted).decode('utf-8')

def verify_password(plain_password: str, stored_password: str) -> bool:
    """Verifies a password against a base64-encoded bcrypt hash, with peppering."""
    # Concatenate pepper with password for verification
    peppered_password = f"{plain_password}{SALT}"
    hashed_password = hashlib.sha256(peppered_password.encode('UTF-8')).digest()

    # Decode base64 stored password back to bytes
    bcrypted_password = base64.b64decode(stored_password.encode('utf-8'))
    # Check with bcrypt
    return bcrypt.checkpw(hashed_password, bcrypted_password)
