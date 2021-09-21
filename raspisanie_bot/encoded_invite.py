import base64
import hmac
import struct
import typing

PACK_SIZE = struct.calcsize("<QLB")


def encode_invite(key, iid: int, gri: typing.Optional[int] = None, tei: typing.Optional[int] = None,
                  isa: bool = False) -> str:
    flags = 0
    flags |= bool(isa) << 0
    flags |= (gri is not None or tei is not None) << 1
    flags |= (gri is not None) << 2

    data = struct.pack("<QLB", iid, gri or tei or 0, flags)
    data += hmac.digest(key, data, 'sha256')
    return base64.urlsafe_b64encode(data).decode().replace("=", "")


def decode_invite(key, data: str):
    data = data.encode("ascii")
    data = base64.urlsafe_b64decode(data + b"=" * (3 - ((len(data) - 1) % 4)))
    if not hmac.compare_digest(data[PACK_SIZE:], hmac.digest(key, data[:PACK_SIZE], 'sha256')):
        raise ValueError("Invalid invite signature")

    iid, eid, flags = struct.unpack("<QLB", data[:PACK_SIZE])

    gri = tei = None
    isa = bool(flags & 1)

    if flags & 0b10:
        if flags & 0b100:
            gri = eid
        else:
            tei = eid

    return iid, gri, tei, isa


if __name__ == '__main__':
    encoded = encode_invite(b"TEST KEY", 12345, 9999, 6666, True)
    print(encoded)
    print(decode_invite(b"TEST KEY", encoded))
