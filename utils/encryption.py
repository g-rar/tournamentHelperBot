from cryptography.fernet import Fernet
import hashlib
import base64

def generate_key(password):
    # Use a cryptographic hash function to generate a fixed-length key from the password
    password_bytes = password.encode('utf-8')
    key = hashlib.sha256(password_bytes).digest()
    return base64.urlsafe_b64encode(key)

def encrypt_value(value, password):
    # Generate a key from the password
    key = generate_key(password)
    # Use the key with the Fernet symmetric encryption algorithm to encrypt the value
    f = Fernet(key)
    encrypted_value = f.encrypt(value.encode('utf-8'))
    return encrypted_value

def decrypt_value(encrypted_value, password):
    # Generate a key from the password
    key = generate_key(password)
    # Use the key with the Fernet symmetric encryption algorithm to decrypt the value
    f = Fernet(key)
    decrypted_value = f.decrypt(encrypted_value)
    return decrypted_value.decode('utf-8')