import os
import json
import sys
import zipfile
import shutil
import time
import datetime
import subprocess
from typing import Tuple, Dict, Any, List


# ===============================
# CONFIG FLAGS (you can tweak these)
# ===============================

AUTO_GIT_COMMIT = True          # Set False if you don't want auto-commits
AUTO_GIT_TAG = False            # If True, will create a git tag for each version
AUTO_GIT_PUSH = False           # If True, will attempt to git push (requires remote set up)

ENABLE_GOOGLE_DRIVE_UPLOAD = False  # Stub only; requires your API credentials to be wired in

BUILD_LOG_FILENAME = "build_log.txt"
RELEASES_DIRNAME = "Releases"


# ===============================
# VALIDATION
# ===============================

INVALID_CHARS = set('/\\:*?"<>|')


def validate_name(name: str, path: str, errors: List[str]):
    """Validate a single file or folder name."""
    if not name:
        errors.append(f"Empty name found at path: {path!r}")
        return

    bad = [ch for ch in name if ch in INVALID_CHARS]
    if bad:
        errors.append(
            f"Invalid characters {bad} in name {name!r} at path: {path!r}"
        )


def validate_tree(tree: Dict[str, Any], prefix: str = "", depth: int = 0, errors: List[str] = None):
    """Recursively validate the structure tree."""
    if errors is None:
        errors = []

    if depth > 20:
        errors.append(f"Tree too deep at prefix {prefix!r} (depth > 20).")
        return errors

    if not isinstance(tree, dict):
        errors.append(f"Expected dict at {prefix!r}, got {type(tree).__name__}.")
        return errors

    for name, value in tree.items():
        current_path = os.path.join(prefix, name) if prefix else name
        validate_name(name, current_path, errors)

        if isinstance(value, dict):
            validate_tree(value, current_path, depth + 1, errors)
        elif not isinstance(value, str):
            errors.append(
                f"Invalid value type at {current_path!r}: expected dict or str, got {type(value).__name__}."
            )

    return errors


# ===============================
# CORE BUILD FUNCTIONS
# ===============================

def build_tree(base_path: str, tree: Dict[str, Any]) -> Tuple[int, int]:
    """
    Build the folder/file tree.
    Returns: (folder_count, file_count)
    """
    folder_count = 0
    file_count = 0

    for name, value in tree.items():
        current_path = os.path.join(base_path, name)

        if isinstance(value, dict):
            os.makedirs(current_path, exist_ok=True)
            folder_count += 1
            sub_folders, sub_files = build_tree(current_path, value)
            folder_count += sub_folders
            file_count += sub_files
        else:
            os.makedirs(os.path.dirname(current_path), exist_ok=True)
            with open(current_path, "w", encoding="utf-8") as f:
                f.write(value)
            file_count += 1

    return folder_count, file_count


def zip_directory(folder_path: str, zip_path: str):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zf.write(file_path, arcname)


# ===============================
# GIT INTEGRATION
# ===============================

def find_git_root(start_path: str) -> str:
    """Find the git repository root starting from start_path and walking up."""
    current = os.path.abspath(start_path)
    while current != os.path.dirname(current):
        if os.path.isdir(os.path.join(current, ".git")):
            return current
        current = os.path.dirname(current)
    return ""


def git_run(args: List[str], cwd: str):
    try:
        subprocess.run(args, cwd=cwd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print(f"⚠️  Git command failed {args}: {e}")


def git_automations(git_root: str, final_root: str, zip_path: str, base_name: str, version: int):
    if not git_root:
        print("ℹ️  No git repository detected. Skipping git automations.")
        return

    print(f"🧩 Git repo detected at: {git_root}")

    if AUTO_GIT_COMMIT:
        msg = f"Build {base_name} v{version}"
        print(f"📝 Running git add & commit: {msg!r}")
        git_run(["git", "add", final_root, zip_path], cwd=git_root)
        git_run(["git", "commit", "-m", msg], cwd=git_root)

    tag_name = f"{base_name}_v{version}"
    if AUTO_GIT_TAG:
        print(f"🏷️  Creating git tag: {tag_name}")
        git_run(["git", "tag", tag_name], cwd=git_root)

    if AUTO_GIT_PUSH:
        print("🚀 Running git push (and push tags if tagging enabled)...")
        git_run(["git", "push"], cwd=git_root)
        if AUTO_GIT_TAG:
            git_run(["git", "push", "--tags"], cwd=git_root)


# ===============================
# GOOGLE DRIVE (STUB)
# ===============================

def upload_to_google_drive(file_path: str):
    """
    Stub for Google Drive upload.
    To enable:
      - Set ENABLE_GOOGLE_DRIVE_UPLOAD = True
      - Implement actual upload using Google Drive API here.
    """
    if not ENABLE_GOOGLE_DRIVE_UPLOAD:
        print("☁️  Google Drive upload skipped (ENABLE_GOOGLE_DRIVE_UPLOAD=False).")
        return

    # TODO: Implement Google Drive upload logic with your credentials.
    print(f"☁️  (Stub) Would upload to Google Drive: {file_path}")


# ===============================
# BUILD LOGGING
# ===============================

def append_build_log(log_path: str,
                     base_name: str,
                     version: int,
                     final_root: str,
                     zip_path: str,
                     folder_count: int,
                     file_count: int,
                     elapsed: float):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    size_bytes = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0

    line = (
        f"[{ts}] base={base_name} "
        f"version=v{version} "
        f"folders={folder_count} "
        f"files={file_count} "
        f"zip={zip_path} "
        f"zip_size={size_bytes}B "
        f"elapsed={elapsed:.3f}s\n"
    )

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


# ===============================
# VERSIONING / PATH LOGIC
# ===============================

def compute_versioned_output(output_folder: str) -> Tuple[str, str, int, str, str]:
    """
    Given an output_folder argument, compute:
      - abs_parent_dir: absolute parent directory
      - base_name: base name used for versions
      - version: next version number (int)
      - final_root: full path to versioned build folder
      - releases_dir: full path to Releases directory
    """
    abs_output = os.path.abspath(output_folder)
    abs_parent_dir = os.path.dirname(abs_output)
    base_name = os.path.basename(abs_output)

    # Ensure parent exists
    os.makedirs(abs_parent_dir, exist_ok=True)

    # Determine next version
    existing_versions = []
    for entry in os.listdir(abs_parent_dir):
        if entry.startswith(base_name + "_v"):
            suffix = entry[len(base_name) + 2:]  # after base_name_v
            if suffix.isdigit():
                existing_versions.append(int(suffix))

    version = max(existing_versions) + 1 if existing_versions else 1

    versioned_name = f"{base_name}_v{version}"
    final_root = os.path.join(abs_parent_dir, versioned_name)

    releases_dir = os.path.join(abs_parent_dir, RELEASES_DIRNAME)
    os.makedirs(releases_dir, exist_ok=True)

    return abs_parent_dir, base_name, version, final_root, releases_dir


# ===============================
# MAIN
# ===============================

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 builder_agent_fixed.py <structure.json> <output_folder>")
        sys.exit(1)

    structure_file = sys.argv[1]
    output_folder = sys.argv[2]

    start_time = time.time()

    # ---------------------------
    # Load and validate JSON
    # ---------------------------
    try:
        with open(structure_file, "r", encoding="utf-8") as f:
            structure = json.load(f)
    except Exception as e:
        print(f"❌ ERROR: Failed to load JSON file {structure_file!r}: {e}")
        sys.exit(1)

    if not isinstance(structure, dict) or len(structure.keys()) != 1:
        print("❌ ERROR: structure.json must contain exactly one root key at top level.")
        sys.exit(1)

    json_root_name, json_tree = next(iter(structure.items()))

    if not isinstance(json_tree, dict):
        print(f"❌ ERROR: Root key {json_root_name!r} must map to a dictionary.")
        sys.exit(1)

    # Validate entire tree
    errors = validate_tree(json_tree, prefix=json_root_name)
    if errors:
        print("❌ JSON structure validation failed with the following issues:")
        for err in errors:
            print(f"   - {err}")
        sys.exit(1)

    # ---------------------------
    # Versioning / Path setup
    # ---------------------------
    abs_parent_dir, base_name, version, final_root, releases_dir = compute_versioned_output(output_folder)

    # Clean up if this version folder somehow already exists
    if os.path.exists(final_root):
        shutil.rmtree(final_root)

    os.makedirs(final_root, exist_ok=True)

    # ---------------------------
    # Build structure
    # ---------------------------
    folder_count, file_count = build_tree(final_root, json_tree)

    # ---------------------------
    # ZIP creation (date-stamped)
    # ---------------------------
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    zip_filename = f"{base_name}_v{version}_{today_str}.zip"
    zip_path = os.path.join(releases_dir, zip_filename)

    if os.path.exists(zip_path):
        os.remove(zip_path)

    zip_directory(final_root, zip_path)

    elapsed = time.time() - start_time

    # ---------------------------
    # Git automations
    # ---------------------------
    git_root = find_git_root(abs_parent_dir)
    if git_root:
        git_automations(git_root, final_root, zip_path, base_name, version)

    # ---------------------------
    # Google Drive (stub)
    # ---------------------------
    upload_to_google_drive(zip_path)

    # ---------------------------
    # Build log
    # ---------------------------
    log_path = os.path.join(abs_parent_dir, BUILD_LOG_FILENAME)
    append_build_log(
        log_path=log_path,
        base_name=base_name,
        version=version,
        final_root=final_root,
        zip_path=zip_path,
        folder_count=folder_count,
        file_count=file_count,
        elapsed=elapsed,
    )

    # ---------------------------
    # Summary
    # ---------------------------
    zip_size = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0

    print("\n================ BUILD SUMMARY ================")
    print(f" Base name:       {base_name}")
    print(f" Version:         v{version}")
    print(f" JSON root key:   {json_root_name}")
    print(f" Output folder:   {final_root}")
    print(f" Releases folder: {releases_dir}")
    print(f" ZIP file:        {zip_path}")
    print(f" ZIP size:        {zip_size} bytes")
    print(f" Folders created: {folder_count}")
    print(f" Files created:   {file_count}")
    print(f" Elapsed time:    {elapsed:.3f} seconds")
    print("===============================================\n")


if __name__ == "__main__":
    main()
