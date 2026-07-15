import pytest
from cryptography.fernet import Fernet, InvalidToken

from conditioner.core.services.auth.token_cipher import TokenCipher


def test_encrypt_and_decrypt_round_trips() -> None:
    cipher = TokenCipher(Fernet.generate_key().decode())

    ciphertext = cipher.encrypt("plaintext-token")

    assert cipher.decrypt(ciphertext) == "plaintext-token"
    assert ciphertext != "plaintext-token"


def test_different_keys_cannot_decrypt_each_others_ciphertext() -> None:
    cipher_a = TokenCipher(Fernet.generate_key().decode())
    cipher_b = TokenCipher(Fernet.generate_key().decode())

    ciphertext = cipher_a.encrypt("plaintext-token")

    with pytest.raises(InvalidToken):
        cipher_b.decrypt(ciphertext)
