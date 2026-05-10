#!/usr/bin/env python3
"""
Decrypt Bondi Secure DJVU files to standard DjVu format.

Bondi format differences:
  - File magic "SDJV" instead of "AT&T"
  - Chunks replaced with "CELX" (Blowfish-CBC encrypted)
  - Extra "SINF" chunk in FORM:DJVI shared info

Key derivation: MD5(password + username + LizardTech salt)
IV per chunk:   MD5("Blowfish" + counter_big_endian_32)[:8]
"""

import hashlib
import struct
import sys
import os
import subprocess
import tempfile

try:
    from Crypto.Cipher import Blowfish
except ImportError:
    sys.exit("pycryptodome required: pip3 install pycryptodome")

PASSWORD = b"Mhw8FqG2cHRUtsG0J4NxqBcR26mUJtUlzqc6wv51TDM"
USERNAME = b"RollingStone"
SALT     = b"LizardTech_DVDKey_Internal_Salt"
KEY      = hashlib.md5(PASSWORD + USERNAME + SALT).digest()


def _iv(counter: int) -> bytes:
    return hashlib.md5(b"Blowfish" + struct.pack(">I", counter)).digest()[:8]


def _chunk(chunk_id: bytes, data: bytes) -> bytes:
    out = chunk_id + struct.pack(">I", len(data)) + data
    if len(data) % 2:
        out += b"\x00"
    return out


def _decrypt_page(form_body: bytes) -> bytes:
    """Return decrypted FORM:DJVU body, without INCL and with CELX decrypted."""
    out = bytearray(b"DJVU")
    pos = 0
    while pos + 8 <= len(form_body):
        cid  = form_body[pos:pos+4]
        csz  = struct.unpack(">I", form_body[pos+4:pos+8])[0]
        data = form_body[pos+8:pos+8+csz]
        pos += 8 + csz + (csz & 1)

        if cid == b"INCL":
            continue  # strip shared-file reference; SINF not needed
        if cid == b"CELX":
            orig_id   = data[0:4]
            orig_size = struct.unpack(">I", data[4:8])[0]
            counter   = struct.unpack(">I", data[8:12])[0]
            encrypted = data[12:]
            cipher    = Blowfish.new(KEY, Blowfish.MODE_CBC, _iv(counter))
            plain     = cipher.decrypt(encrypted)[:orig_size]
            out += _chunk(orig_id, plain)
        else:
            out += _chunk(cid, data)

    return bytes(out)


def extract_pages(src_data: bytes) -> list[bytes]:
    """Return a list of standalone AT&T FORM:DJVU byte strings, one per page."""
    if src_data[0:4] not in (b"SDJV", b"AT&T"):
        raise ValueError("Not a Bondi/DjVu file")

    top_size  = struct.unpack(">I", src_data[8:12])[0]
    body      = src_data[16:8 + 4 + top_size]  # skip magic + FORM + size + DJVM type

    pages = []
    pos   = 0
    while pos + 8 <= len(body):
        cid  = body[pos:pos+4]
        csz  = struct.unpack(">I", body[pos+4:pos+8])[0]
        data = body[pos+8:pos+8+csz]
        pos += 8 + csz + (csz & 1)

        if cid == b"FORM" and data[0:4] == b"DJVU":
            page_body = _decrypt_page(data[4:])  # data[4:] skips the "DJVU" type prefix
            pages.append(b"AT&T" + _chunk(b"FORM", page_body))

    return pages


def decrypt_file(src: str, dst: str) -> None:
    with open(src, "rb") as f:
        raw = f.read()

    pages = extract_pages(raw)
    if not pages:
        raise ValueError(f"No pages found in {src}")

    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        page_files = []
        for i, page in enumerate(pages):
            path = os.path.join(tmp, f"page_{i+1:04d}.djvu")
            with open(path, "wb") as f:
                f.write(page)
            page_files.append(path)

        subprocess.run(
            ["djvm", "-c", dst] + page_files,
            check=True, capture_output=True
        )


def main():
    if len(sys.argv) < 3:
        print("Usage: bondi_decrypt.py input.djvu output.djvu")
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    print(f"Decrypting {os.path.basename(src)} ...", end=" ", flush=True)
    decrypt_file(src, dst)
    print("done")


if __name__ == "__main__":
    main()
