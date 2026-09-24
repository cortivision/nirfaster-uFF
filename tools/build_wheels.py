"""Build the platform wheels of nirfasteruff: the Python package plus the compiled solver
and meshers from the milabuob/nirfaster-uFF release, one wheel per platform.

pip picks a wheel by its tags, so each platform only downloads its own binaries and
nothing has to be copied into a venv by hand. Nothing is compiled here: the release
already ships the binaries, this only packages them next to nirfasteruff's code.

    python tools/build_wheels.py                   # downloads the release zips
    python tools/build_wheels.py --zips-dir DIR    # uses zips already in DIR

Every zip is checked against its SHA-256 before use. The wheels land in dist/; upload
them to a GitHub release and point the apps' pyproject.toml at their URLs.
"""

import argparse
import base64
import csv
import hashlib
import io
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RELEASE = "https://github.com/milabuob/nirfaster-uFF/releases/download/v1.2.1"
REQUIRES = ["numpy", "scipy", "psutil", "scikit-image"]

# name -> sha256 of the zip, as published on the v1.2.1 release
ZIPS = {
    "cpu-win-python313-uff.zip": "f0be1eab1ce3d0f4301263023f103eb771fc0d8ce51ab7c82906c022395dae48",
    "gpu-win-python313-uff.zip": "7564e6bb582daf790b3cc30823faddb70bdb4b15ef53865c4fde86bbe124a25c",
    "cpu-mac-python312-uff.zip": "60a0704662cfe2d6b8e674f1e4191fea12467c341960ef199905ea709fc31588",
}

WHEELS = [
    {
        "tag": "cp313-cp313-win_amd64",
        "requires_python": ">=3.13,<3.14",
        "zips": ["cpu-win-python313-uff.zip", "gpu-win-python313-uff.zip"],
    },
    {
        # the binaries are universal (arm64 + x86_64) and built for macOS 13.0+
        "tag": "cp312-cp312-macosx_13_0_universal2",
        "requires_python": ">=3.12,<3.13",
        "zips": ["cpu-mac-python312-uff.zip"],
    },
]

# the meshers are run as programs, so on macOS they must stay executable
EXECUTABLE = re.compile(r"(MAC|LINUX)$")


def read_version():
    """Package version from pyproject.toml"""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.M).group(1)


def get_zip(name, zips_dir):
    """Zip bytes from zips_dir or the release, refused unless the checksum matches"""
    local = zips_dir / name if zips_dir else None
    if local and local.is_file():
        data = local.read_bytes()
    else:
        print(f"downloading {name}")
        with urllib.request.urlopen(f"{RELEASE}/{name}") as response:
            data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != ZIPS[name]:
        sys.exit(f"{name}: sha256 {digest} does not match the release ({ZIPS[name]})")
    return data


def record_hash(data):
    """RECORD-style hash: urlsafe base64 sha256 without padding"""
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def build_wheel(spec, version, zips_dir, out_dir):
    """Write one platform wheel and return its path"""
    files = {}  # archive name -> (bytes, unix mode)
    for source in ("__init__.py", "nirfasteruff.py"):
        files[f"nirfasteruff/{source}"] = ((REPO / "nirfasteruff" / source).read_bytes(), 0o644)
    for zip_name in spec["zips"]:
        with zipfile.ZipFile(io.BytesIO(get_zip(zip_name, zips_dir))) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                mode = 0o755 if EXECUTABLE.search(name) else 0o644
                files[f"nirfasteruff/{name}"] = (archive.read(info), mode)

    dist_info = f"nirfasteruff-{version}.dist-info"
    metadata = "\n".join(
        ["Metadata-Version: 2.1", "Name: nirfasteruff", f"Version: {version}",
         f"Requires-Python: {spec['requires_python']}"]
        + [f"Requires-Dist: {dep}" for dep in REQUIRES]
    ) + "\n"
    wheel_info = ("Wheel-Version: 1.0\nGenerator: tools/build_wheels.py\n"
                  f"Root-Is-Purelib: false\nTag: {spec['tag']}\n")
    files[f"{dist_info}/METADATA"] = (metadata.encode(), 0o644)
    files[f"{dist_info}/WHEEL"] = (wheel_info.encode(), 0o644)
    files[f"{dist_info}/LICENSE.txt"] = ((REPO / "LICENSE.txt").read_bytes(), 0o644)

    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for name, (data, _) in files.items():
        writer.writerow([name, record_hash(data), len(data)])
    writer.writerow([f"{dist_info}/RECORD", "", ""])

    out = out_dir / f"nirfasteruff-{version}-{spec['tag']}.whl"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as wheel:
        for name, (data, mode) in list(files.items()) + [
            (f"{dist_info}/RECORD", (record.getvalue().encode(), 0o644))
        ]:
            info = zipfile.ZipInfo(name, date_time=(2025, 11, 7, 0, 0, 0))
            info.external_attr = (0o100000 | mode) << 16  # regular file + permissions
            info.compress_type = zipfile.ZIP_DEFLATED
            wheel.writestr(info, data)
    return out


def main():
    """Build every platform wheel into dist/"""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--zips-dir", type=Path, help="folder holding the release zips")
    args = parser.parse_args()
    out_dir = REPO / "dist"
    out_dir.mkdir(exist_ok=True)
    version = read_version()
    for spec in WHEELS:
        path = build_wheel(spec, version, args.zips_dir, out_dir)
        print(f"built {path.relative_to(REPO)}  ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
