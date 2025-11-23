import os
import sys
import json
import zipfile
from datetime import datetime
from typing import Any, Dict, Tuple

# ================================================================
#  JSON VALIDATION UTILITIES
# ================================================================

def validate_name(name: str, path: str) -> None:
    """Validate a single file or folder name."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Invalid empty name at path: {path or '<root>'}")
    if "/" in name or "\\" in name:
        raise ValueError(f"Name '{name}' at path '{path}' must not contain '/' or '\\'.")
    if len(name) > 100:
        raise ValueError(f"Name '{name}' at path '{path}' is too long (max 100 chars).")


def validate_structure(node: Any, path: str = "") -> Tuple[int, int]:
    """
    Recursively validate the nested dict and count folders/files.
    Returns (folder_count, file_count).
    """
    folder_count = 0
    file_count = 0

    if not isinstance(node, dict):
        raise ValueError("Top-level structure must be a JSON object (dict).")

    for name, contents in node.items():
        current_path = f"{path}/{name}" if path else name
        validate_name(name, current_path)

        if isinstance(contents, dict):
            folder_count += 1
            sub_f, sub_fl = validate_structure(contents, current_path)
            folder_count += sub_f
            file_count += sub_fl

        elif isinstance(contents, (str, type(None))):
            file_count += 1

        else:
            raise ValueError(
                f"Invalid value type at '{current_path}'. "
                f"Expected dict (folder) or string/None (file contents)."
            )

    return folder_count, file_count


# ================================================================
#  FILESYSTEM CREATION
# ================================================================

def create_structure(structure: Dict[str, Any], root: str) -> Tuple[int, int]:
    """
    Recursively creates folders/files from nested dict.
    Returns (folders_created, files_created).
    """
    folders = 0
    files = 0

    for name, contents in structure.items():
        path = os.path.join(root, name)

        if isinstance(contents, dict):
            os.makedirs(path, exist_ok=True)
            folders += 1
            sub_f, sub_fl = create_structure(contents, path)
            folders += sub_f
            files += sub_fl
        else:
            text = "" if contents is None else str(contents)
            parent = os.path.dirname(path)
            os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            files += 1

    return folders, files


def compute_next_version(base_name: str, parent_dir: str) -> int:
    """Return next version number."""
    existing = []
    if not os.path.isdir(parent_dir):
        return 1

    for entry in os.listdir(parent_dir):
        if entry.startswith(base_name + "_v"):
            suffix = entry[len(base_name) + 2:]
            if suffix.isdigit():
                existing.append(int(suffix))

    return max(existing) + 1 if existing else 1


def make_zip(source_dir: str, zip_path: str) -> None:
    """Zip directory tree."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel = os.path.relpath(full_path, os.path.dirname(source_dir))
                zf.write(full_path, rel)


# ================================================================
#  AUTO-DOC GENERATION
# ================================================================

def generate_folder_docs(root: str, version_label: str) -> None:
    """
    For every folder:
      - Ensure README.md exists (auto-create)
      - Generate Index.md listing contents
    """
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        rel_display = rel if rel != "." else "root"

        readme_path = os.path.join(dirpath, "README.md")
        index_path = os.path.join(dirpath, "Index.md")

        # Create README if missing
        if not os.path.exists(readme_path):
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(
                    f"# {os.path.basename(dirpath)}\n\n"
                    f"_Auto-generated for version {version_label}. Folder: `{rel_display}`._\n"
                )

        # Always regenerate Index.md
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(f"# Index for `{rel_display}` (version {version_label})\n\n")

            if dirnames:
                f.write("## Subfolders\n\n")
                for d in sorted(dirnames):
                    if not d.startswith("."):
                        f.write(f"- `{d}/`\n")
                f.write("\n")

            if filenames:
                f.write("## Files\n\n")
                for fn in sorted(filenames):
                    if not fn.startswith("."):
                        f.write(f"- `{fn}`\n")
                f.write("\n")


# ================================================================
#  CHANGELOG & METADATA
# ================================================================

def write_changelog(root: str, version: str, folders: int, files: int, zip_name: str):
    """Write CHANGELOG.md."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    path = os.path.join(root, "CHANGELOG.md")

    lines = [
        f"# Bravo Maids Media Center – {version}",
        "",
        f"- Build time: {now}",
        f"- Folders: {folders}",
        f"- Files: {files}",
        f"- ZIP: {zip_name}",
        "",
        "> Auto-generated changelog.",
        "",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_latest_json(root: str, base_name: str, version: str, zip_name: str, folders: int, files: int):
    """Write latest.json metadata."""
    meta = {
        "project": base_name,
        "version": version,
        "zip_name": zip_name,
        "generated_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "folders": folders,
        "files": files,
    }

    path = os.path.join(root, "latest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def append_build_log(parent_dir: str, base_name: str, version: str, out_dir: str, zip_path: str, folders: int, files: int):
    """Append summary to build_log.txt."""
    log = os.path.join(parent_dir, "build_log.txt")
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    line = (
        f"{now} | {base_name} | {version} | "
        f"folders={folders} | files={files} | "
        f"out={out_dir} | zip={zip_path}\n"
    )

    with open(log, "a", encoding="utf-8") as f:
        f.write(line)


# ================================================================
#  MAIN BUILD LOGIC
# ================================================================

def main():
    if len(sys.argv) < 3:
        print("Usage: python builder_agent_fixed.py structure.json BaseName [output_dir]")
        sys.exit(1)

    json_path = sys.argv[1]
    base_name = sys.argv[2]
    output_parent = sys.argv[3] if len(sys.argv) >= 4 else "."

    abs_parent = os.path.abspath(output_parent)

    # Load JSON
    if not os.path.isfile(json_path):
        print(f"ERROR: JSON not found: {json_path}")
        sys.exit(1)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"ERROR parsing JSON: {e}")
        sys.exit(1)

    # Determine root key
    if base_name in raw:
        structure = raw[base_name]
        root_key = base_name
    elif len(raw) == 1:
        root_key = next(iter(raw.keys()))
        structure = raw[root_key]
    else:
        print("ERROR: JSON must contain the given base name or only one top-level key.")
        sys.exit(1)

    # Validate structure
    try:
        pre_folders, pre_files = validate_structure(structure, path=root_key)
    except Exception as e:
        print(f"\n❌ Validation failed:\n{e}\n")
        sys.exit(1)

    # Preflight report
    print("\n================ PRE-FLIGHT REPORT ================")
    print(f" Base name:        {base_name}")
    print(f" JSON root key:    {root_key}")
    print(f" Output parent:    {abs_parent}")
    print(f" Planned folders:  {pre_folders}")
    print(f" Planned files:    {pre_files}")
    print("===================================================\n")

    os.makedirs(abs_parent, exist_ok=True)

    # Versioning
    version_num = compute_next_version(base_name, abs_parent)
    version_label = f"v{version_num}"
    out_folder = f"{base_name}_v{version_num}"
    out_dir = os.path.join(abs_parent, out_folder)

    # Releases folder
    releases_dir = os.path.join(abs_parent, "Releases")
    os.makedirs(releases_dir, exist_ok=True)

    # Build structure
    folders_created, files_created = create_structure(structure, out_dir)

    # Root-level docs
    generate_folder_docs(out_dir, version_label)

    # Metadata + changelog
    zip_basename = f"{out_folder}_{datetime.utcnow().strftime('%Y-%m-%d')}.zip"
    zip_path = os.path.join(releases_dir, zip_basename)

    write_changelog(out_dir, version_label, folders_created, files_created, zip_basename)
    write_latest_json(out_dir, base_name, version_label, zip_basename, folders_created, files_created)

    # ZIP PACKAGE
    make_zip(out_dir, zip_path)

    # Build log
    append_build_log(abs_parent, base_name, version_label, out_dir, zip_path, folders_created, files_created)

    # Final summary
    print("\n================ BUILD SUMMARY ====================")
    print(f" Base name:       {base_name}")
    print(f" Version:         {version_label}")
    print(f" Output folder:   {out_dir}")
    print(f" Releases folder: {releases_dir}")
    print(f" ZIP file:        {zip_path}")
    print(f" Folders created: {folders_created}")
    print(f" Files created:   {files_created}")
    print("===================================================\n")


if __name__ == "__main__":
    main()
