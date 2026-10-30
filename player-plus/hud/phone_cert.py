"""phone_cert.py: the phone door's own certificates, made with the Python standard library only.

WHY
  A phone's browser gives a page the microphone (getUserMedia) and speech recognition only on a
  secure page: https, or localhost. The phone door is neither until it speaks TLS, and Python's ssl
  module serves TLS but cannot make a certificate. So this file makes them itself: an RSA key, a
  certificate authority of this computer's own, and a leaf certificate for the door's one
  private-network address, signed by that authority (PKCS#1 v1.5 with SHA-256, DER by hand).

WHAT IT KEEPS (serve.py's PhoneDoor calls ensure(); nothing here opens a socket)
  <HQ>/.phone-door/<address>/   one folder per private-network address the door has bound
      ca.key  ca.pem  ca.crt    the authority's key, its certificate (PEM, and DER for a phone)
      door.key  door.pem        the door's key, and its certificate followed by the authority's
      meta.json                 fingerprint, expiry dates, when the authority last changed
  Every file mode 0600, every folder 0700; <HQ>/.gitignore-ed (.phone-door/), never in the record.

WHAT THE AUTHORITY MAY VOUCH FOR (the honest limit of trusting it)
  Its name constraints permit exactly one IP address (the door's, as /32) and DNS names only under
  `.invalid` (a name that never resolves). A phone that trusts it trusts it for this computer's
  door at that address, and for nothing else: not a bank, not any website. It lives one year; the
  door's own certificate lives thirty days and is renewed quietly a week before it ends.
"""
import hashlib
import ipaddress
import json
import math
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

CA_DAYS, LEAF_DAYS = 365, 30
CA_RENEW_DAYS, LEAF_RENEW_DAYS = 14, 7       # renewed when this close to its end
KEY_BITS = 2048                              # phones refuse a TLS key under 2048 bits

# ------------------------------------------------------------------ RSA, by hand

_SMALL = [p for p in range(3, 2000, 2) if all(p % q for q in range(3, int(p ** 0.5) + 1, 2))]


def _probable_prime(n, rounds=40):
    for p in _SMALL:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    for _ in range(rounds):
        a = 2 + secrets.randbelow(n - 3)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _prime(bits, e):
    while True:
        c = secrets.randbits(bits) | (3 << (bits - 2)) | 1      # top two bits set: n has its full length
        if math.gcd(c - 1, e) == 1 and _probable_prime(c):
            return c


def rsa_key(bits=KEY_BITS):
    e = 65537
    while True:
        p, q = _prime(bits // 2, e), _prime(bits // 2, e)
        if p == q:
            continue
        n = p * q
        if n.bit_length() != bits:
            continue
        d = pow(e, -1, math.lcm(p - 1, q - 1))
        return {"n": n, "e": e, "d": d, "p": p, "q": q}


def _sign(key, data: bytes) -> bytes:
    """RSASSA-PKCS1-v1_5 with SHA-256, the private operation by the Chinese remainder theorem."""
    k = (key["n"].bit_length() + 7) // 8
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(data).digest()
    em = b"\x00\x01" + b"\xff" * (k - len(digest_info) - 3) + b"\x00" + digest_info
    m = int.from_bytes(em, "big")
    p, q, d = key["p"], key["q"], key["d"]
    m1, m2 = pow(m, d % (p - 1), p), pow(m, d % (q - 1), q)
    h = (pow(q, -1, p) * (m1 - m2)) % p
    s = m2 + h * q
    assert pow(s, key["e"], key["n"]) == m
    return s.to_bytes(k, "big")

# ------------------------------------------------------------------ DER, by hand


def _len(n):
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def tlv(tag, content: bytes) -> bytes:
    return bytes([tag]) + _len(len(content)) + content


def seq(*parts):
    return tlv(0x30, b"".join(parts))


def der_int(v: int) -> bytes:
    b = v.to_bytes(max(1, (v.bit_length() + 8) // 8), "big", signed=True)
    return tlv(0x02, b)


def oid(dotted: str) -> bytes:
    nums = [int(x) for x in dotted.split(".")]
    out = bytes([40 * nums[0] + nums[1]])
    for n in nums[2:]:
        chunk = [n & 0x7F]
        n >>= 7
        while n:
            chunk.append(0x80 | (n & 0x7F))
            n >>= 7
        out += bytes(reversed(chunk))
    return tlv(0x06, out)


def bitstring(b: bytes, unused=0) -> bytes:
    return tlv(0x03, bytes([unused]) + b)


def octets(b: bytes) -> bytes:
    return tlv(0x04, b)


def _time(t: datetime) -> bytes:
    t = t.astimezone(timezone.utc)
    if t.year < 2050:
        return tlv(0x17, t.strftime("%y%m%d%H%M%SZ").encode())
    return tlv(0x18, t.strftime("%Y%m%d%H%M%SZ").encode())


def _name(cn: str, org: str) -> bytes:
    def rdn(o, v):
        return tlv(0x31, seq(oid(o), tlv(0x0C, v.encode("utf-8"))))
    return seq(rdn("2.5.4.10", org), rdn("2.5.4.3", cn))


SHA256_RSA = seq(oid("1.2.840.113549.1.1.11"), b"\x05\x00")
RSA_ENC = seq(oid("1.2.840.113549.1.1.1"), b"\x05\x00")
TRUE = b"\x01\x01\xff"


def _spki(key):
    return seq(RSA_ENC, bitstring(seq(der_int(key["n"]), der_int(key["e"]))))


def _key_id(key):
    return hashlib.sha1(seq(der_int(key["n"]), der_int(key["e"]))).digest()


def _ext(o, value: bytes, critical=False):
    return seq(oid(o), *( [TRUE] if critical else []), octets(value))


def _cert(subject_key, issuer_key, subject, issuer, days, exts, now):
    tbs = seq(tlv(0xA0, der_int(2)),
              der_int(int.from_bytes(secrets.token_bytes(16), "big") >> 1 | 1),
              SHA256_RSA, issuer,
              seq(_time(now - timedelta(minutes=10)), _time(now + timedelta(days=days))),
              subject, _spki(subject_key),
              tlv(0xA3, seq(*exts)))
    return seq(tbs, SHA256_RSA, bitstring(_sign(issuer_key, tbs)))


def make_ca(addr: str, key, now=None):
    now = now or datetime.now(timezone.utc)
    ip = ipaddress.ip_address(addr)
    mask = b"\xff" * len(ip.packed)
    permitted = tlv(0xA0, seq(tlv(0x87, ip.packed + mask)) + seq(tlv(0x82, b"invalid")))
    name = _name(f"Phone door at {addr}", "LIONSBERG phone door, this computer only")
    exts = [_ext("2.5.29.19", seq(TRUE, der_int(0)), True),            # a CA, no CA beneath it
            _ext("2.5.29.15", bitstring(b"\x06", 1), True),              # keyCertSign, cRLSign
            _ext("2.5.29.30", seq(permitted), True),                     # this address only
            _ext("2.5.29.14", octets(_key_id(key)))]
    return _cert(key, key, name, name, CA_DAYS, exts, now)


def make_leaf(addr: str, key, ca_key, ca_der: bytes, now=None):
    now = now or datetime.now(timezone.utc)
    ip = ipaddress.ip_address(addr)
    issuer = _issuer_of(ca_der)
    exts = [_ext("2.5.29.19", seq(), True),
            _ext("2.5.29.15", bitstring(b"\xa0", 5), True),              # digitalSignature, keyEncipherment
            _ext("2.5.29.37", seq(oid("1.3.6.1.5.5.7.3.1"))),             # a TLS server
            _ext("2.5.29.17", seq(tlv(0x87, ip.packed))),                # the door's one address
            _ext("2.5.29.14", octets(_key_id(key))),
            _ext("2.5.29.35", seq(tlv(0x80, _key_id(ca_key))))]
    # the address lives in the alternative name; a dotted common name would be read as a DNS name
    return _cert(key, ca_key, _name("the phone door", "LIONSBERG phone door"), issuer, LEAF_DAYS, exts, now)


def _read_tlv(b, i):
    tag, n = b[i], b[i + 1]
    i += 2
    if n & 0x80:
        k = n & 0x7F
        n = int.from_bytes(b[i:i + k], "big")
        i += k
    return tag, i, i + n


def _children(b, start, end):
    out = []
    while start < end:
        tag, s, e = _read_tlv(b, start)
        out.append((tag, s, e))
        start = e
    return out


def _tbs_fields(der):
    _, s, e = _read_tlv(der, 0)
    _, ts, te = _children(der, s, e)[0]
    return _children(der, ts, te)


def _issuer_of(ca_der):
    """The CA's subject (field 5 of its TBSCertificate), the leaf's issuer, byte for byte."""
    f = _tbs_fields(ca_der)
    tag, s, e = f[5]
    return ca_der[s - (len(_len(e - s)) + 1):e]


def not_after(der) -> datetime:
    f = _tbs_fields(der)
    _, s, e = f[4]
    t = _children(der, s, e)[1]
    raw = der[t[1]:t[2]].decode()
    fmt = "%y%m%d%H%M%SZ" if t[0] == 0x17 else "%Y%m%d%H%M%SZ"
    return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)


def fingerprint(der) -> str:
    return ":".join(f"{b:02X}" for b in hashlib.sha256(der).digest())

# ------------------------------------------------------------------ PEM and the folder


def pem(kind, der):
    import base64
    b = base64.b64encode(der).decode()
    return f"-----BEGIN {kind}-----\n" + "\n".join(b[i:i + 64] for i in range(0, len(b), 64)) + f"\n-----END {kind}-----\n"


def key_der(k):
    p, q, d = k["p"], k["q"], k["d"]
    return seq(der_int(0), der_int(k["n"]), der_int(k["e"]), der_int(d), der_int(p), der_int(q),
               der_int(d % (p - 1)), der_int(d % (q - 1)), der_int(pow(q, -1, p)))


def _key_from_der(b):
    _, s, e = _read_tlv(b, 0)
    vals = [int.from_bytes(b[cs:ce], "big", signed=True) for _, cs, ce in _children(b, s, e)]
    return {"n": vals[1], "e": vals[2], "d": vals[3], "p": vals[4], "q": vals[5]}


def _pem_body(text):
    import base64
    lines = [l for l in text.splitlines() if l and not l.startswith("-----")]
    return base64.b64decode("".join(lines))


def _write(path: Path, data):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data.encode() if isinstance(data, str) else data)
    os.chmod(str(path), 0o600)


def folder(hq, addr) -> Path:
    root = Path(hq) / ".phone-door"
    root.mkdir(mode=0o700, exist_ok=True)
    os.chmod(str(root), 0o700)
    d = root / str(ipaddress.ip_address(addr))
    d.mkdir(mode=0o700, exist_ok=True)
    os.chmod(str(d), 0o700)
    return d


def ensure(hq, addr, now=None) -> dict:
    """Make or renew what the door needs for this address; return its meta:
    {address, fingerprint, ca_expires, leaf_expires, ca_changed (iso time or None), renewed: [..],
     cert, key, ca_der (paths)}. A new authority (first time, or near its end) has a new fingerprint:
    `renewed` then names "ca" and the phone must trust this computer again."""
    now = now or datetime.now(timezone.utc)
    d = folder(hq, addr)
    meta_p = d / "meta.json"
    try:
        meta = json.loads(meta_p.read_text())
    except (OSError, ValueError):
        meta = {}
    renewed = []
    ca_der = ca_key = None
    try:
        ca_der = (d / "ca.crt").read_bytes()
        ca_key = _key_from_der(_pem_body((d / "ca.key").read_text()))
        if not_after(ca_der) - now < timedelta(days=CA_RENEW_DAYS):
            ca_der = None
    except (OSError, ValueError, IndexError):
        ca_der = None
    if ca_der is None:
        prior = meta.get("fingerprint")
        ca_key = rsa_key(KEY_BITS)
        ca_der = make_ca(addr, ca_key, now)
        _write(d / "ca.key", pem("RSA PRIVATE KEY", key_der(ca_key)))
        _write(d / "ca.crt", ca_der)
        _write(d / "ca.pem", pem("CERTIFICATE", ca_der))
        for f in ("door.key", "door.pem"):
            try:
                (d / f).unlink()
            except OSError:
                pass
        renewed.append("ca")
        meta = {"ca_changed": now.isoformat(timespec="seconds"), "prior_fingerprint": prior}
    try:
        leaf_text = (d / "door.pem").read_text()
        leaf_der = _pem_body(leaf_text.split("-----END CERTIFICATE-----")[0])
        if not_after(leaf_der) - now < timedelta(days=LEAF_RENEW_DAYS) or not (d / "door.key").exists():
            raise ValueError("near its end")
    except (OSError, ValueError, IndexError):
        k = rsa_key(KEY_BITS)
        leaf_der = make_leaf(addr, k, ca_key, ca_der, now)
        _write(d / "door.key", pem("RSA PRIVATE KEY", key_der(k)))
        _write(d / "door.pem", pem("CERTIFICATE", leaf_der) + pem("CERTIFICATE", ca_der))
        renewed.append("leaf")
    meta.update({"address": str(addr), "fingerprint": fingerprint(ca_der),
                 "ca_expires": not_after(ca_der).isoformat(timespec="seconds"),
                 "leaf_expires": not_after(leaf_der).isoformat(timespec="seconds")})
    _write(meta_p, json.dumps(meta, indent=1) + "\n")
    return dict(meta, renewed=renewed, cert=str(d / "door.pem"), key=str(d / "door.key"), ca_der=str(d / "ca.crt"))
