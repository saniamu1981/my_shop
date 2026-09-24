# convert_vapid.py
import base64
from cryptography.hazmat.primitives import serialization


def b64url(data: bytes) -> str:
    """base64url без padding — формат, который ждёт pywebpush и браузер."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


# ===== Публичный ключ =====
with open('public_key.pem', 'rb') as f:
    public_key = serialization.load_pem_public_key(f.read())

# raw uncompressed point (65 байт, начинается с 0x04)
public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint,
)
print('VAPID_PUBLIC_KEY =', b64url(public_bytes))
print()

# ===== Приватный ключ =====
with open('private_key.pem', 'rb') as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

# raw scalar (32 байта)
private_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
print('VAPID_PRIVATE_KEY =', b64url(private_bytes))