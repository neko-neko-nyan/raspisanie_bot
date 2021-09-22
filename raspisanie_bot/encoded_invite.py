import base64
import hmac
import struct

PACK_SIZE = struct.calcsize("<Q")


class InviteSignatureError(Exception):
    pass


def encode_invite(key, iid: int) -> str:
    data = struct.pack("<Q", iid)
    data += hmac.digest(key, data, 'sha256')
    return base64.urlsafe_b64encode(data).decode().replace("=", "")


def decode_invite(key, data: str):
    data = data.encode("ascii")
    data = base64.urlsafe_b64decode(data + b"=" * (3 - ((len(data) - 1) % 4)))
    if not hmac.compare_digest(data[PACK_SIZE:], hmac.digest(key, data[:PACK_SIZE], 'sha256')):
        raise InviteSignatureError()

    return struct.unpack("<Q", data[:PACK_SIZE])[0]
