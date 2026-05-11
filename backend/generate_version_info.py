"""Generates a PyInstaller Windows VERSIONINFO resource file."""
import os
import sys


def generate(version_str: str):
    parts = version_str.strip().lstrip("v").split(".")
    while len(parts) < 4:
        parts.append("0")
    try:
        ver_tuple = tuple(int(p) for p in parts[:4])
    except ValueError:
        ver_tuple = (1, 0, 0, 0)

    ver_str = ".".join(str(v) for v in ver_tuple)

    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={ver_tuple},
    prodvers={ver_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Rahul Roy'),
         StringStruct(u'FileDescription', u'AI Skill Generator - Convert PDFs and websites to AI skill files'),
         StringStruct(u'FileVersion', u'{ver_str}'),
         StringStruct(u'InternalName', u'ai-skill-generator'),
         StringStruct(u'LegalCopyright', u'Copyright 2026 Rahul Roy'),
         StringStruct(u'OriginalFilename', u'ai-skill-generator.exe'),
         StringStruct(u'ProductName', u'AI Skill Generator'),
         StringStruct(u'ProductVersion', u'{ver_str}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version_info.txt")
    with open(out, "w") as f:
        f.write(content)
    print(f"Created {out} (version {ver_str})")


if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"
    generate(version)
