# RollingStonerPy

Convert **Bondi Secure DJVU** files to PDF natively on macOS (Apple Silicon & Intel) and Linux — no Windows, no Wine, no Docker required.

Bondi Secure DJVU is the proprietary encrypted format used by the *Rolling Stone: Cover to Cover* DVD archive (2007). This tool reverse-engineers the encryption and produces standard PDFs directly from the `.djvu` files on your disc.

---

## Requirements

```bash
brew install djvulibre        # macOS
# apt install djvulibre-bin   # Linux (Debian/Ubuntu)

pip3 install pycryptodome
```

Python 3.10+ required. Works on any architecture.

---

## Quick start

```bash
# Convert a single issue
./convert.sh Issues/RS0001_19671109.djvu

# Convert all issues in a directory
./convert.sh /path/to/Issues

# Specify a custom output directory
./convert.sh /path/to/Issues /path/to/output

# Smaller files (~100MB vs ~350MB per issue) at the cost of resolution
SUBSAMPLE=2 ./convert.sh /path/to/Issues
```

PDFs are written to `./output/` by default. Already-converted files are skipped, so re-runs are safe.

---

## How it works

The Bondi format replaces standard DjVu chunks with encrypted `CELX` chunks. Each chunk is encrypted with **Blowfish in CBC mode**, using:

- **Key**: `MD5(password + username + "LizardTech_DVDKey_Internal_Salt")`
- **IV**: `MD5(b"Blowfish" + counter_big_endian_32)[:8]` — unique per chunk

The credentials (`RollingStone` / `Mhw8FqG2cHRUtsG0J4NxqBcR26mUJtUlzqc6wv51TDM`) are hardcoded in the original software for the Rolling Stone collection.

`bondi_decrypt.py` decrypts each CELX chunk back to its original DjVu form (INFO, BG44, Sjbz, FG44) and reassembles a valid multi-page DjVu file using `djvm`. `convert.sh` then passes that to `ddjvu` for PDF rendering.

The encryption was reverse-engineered from `FataMorgana.framework` (the macOS PowerPC/i386 library bundled with the original Mac installer), specifically the `FMDVDKSPAuthenticateUser` and `FMCBCCipherFeederSetVectorFromSalt` functions.

---

## File size

| Mode | Size per issue | Notes |
|------|---------------|-------|
| Default (full quality) | 300–800 MB | Full scan resolution, ~299–399 DPI |
| `SUBSAMPLE=2` | 100–200 MB | Half linear resolution, still very readable |
| `SUBSAMPLE=3` | 50–80 MB | Suitable for screen reading |

---

## Windows users

If you're on Windows, [RollingStoner](https://github.com/reconSuave/RollingStoner) by reconSuave uses the original `BondiReader.DJVU.dll` directly and may suit you better. This project was built specifically to serve Mac and Linux users who can't run that tool.

---

## Acknowledgements

Inspired by [RollingStoner](https://github.com/reconSuave/RollingStoner) (reconSuave), which first cracked the format on Windows. The cross-platform approach here was made possible by reverse-engineering the original `FataMorgana.framework` bundled in the Mac installer.

---

## License

MIT
