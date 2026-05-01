"""
Library:     lib_mfdb_validator.py
Jurisdiction: ["PYTHON", "CORE_COMMAND"]
Status:      OFFICIAL — Core-Command/Lib (v1.21)
Author:      Elton Boehnen
Version:     1.21 (OFFICIAL) Sticky Mount & Validation Gate
Date:        2026-04-27
Description: MFDB (Multifile Database) validation library.
             Layers entirely on lib_bejson_validator.py — no new BEJSON
             version, no new field types. All entity files remain valid
             standalone BEJSON 104 documents; the manifest is a valid
             BEJSON 104a document.
             v1.2 adds support for validating .mfdb.zip archives.
             v1.21 adds diagnostic context for smart recovery.
"""
import json
import os
import zipfile
from dataclasses import dataclass, field as dc_field
from pathlib import Path

from lib_bejson_validator import (
    BEJSONValidationError,
    bejson_validator_validate_file,
)

# ---------------------------------------------------------------------------
# Error codes (30–49)
# ---------------------------------------------------------------------------

E_MFDB_NOT_MANIFEST           = 30
E_MFDB_NOT_ENTITY_FILE        = 31
E_MFDB_MANIFEST_RECORDS_TYPE  = 32
E_MFDB_ENTITY_NOT_FOUND       = 33
E_MFDB_ENTITY_NAME_MISMATCH   = 34
E_MFDB_DUPLICATE_ENTRY        = 35
E_MFDB_NO_PARENT_HIERARCHY    = 36
E_MFDB_MANIFEST_NOT_FOUND     = 37
E_MFDB_BIDIRECTIONAL_FAIL     = 38
E_MFDB_FK_UNRESOLVED          = 39
E_MFDB_MISSING_REQUIRED_FIELD = 40
E_MFDB_NULL_REQUIRED          = 41
E_MFDB_INVALID_ARCHIVE        = 42


class MFDBValidationError(Exception):
    """Raised when MFDB-level validation fails."""
    def __init__(self, message: str, code: int, context: dict = None):
        super().__init__(message)
        self.code = code
        self.context = context or {}


# ---------------------------------------------------------------------------
# Validation state
# ---------------------------------------------------------------------------

@dataclass
class _MFDBValidationState:
    errors:   list[str] = dc_field(default_factory=list)
    warnings: list[str] = dc_field(default_factory=list)

    def reset(self):
        self.errors.clear()
        self.warnings.clear()

    def add_error(self, message: str, location: str = ""):
        entry = "ERROR"
        if location:
            entry += f" | Location: {location}"
        entry += f" | Message: {message}"
        self.errors.append(entry)

    def add_warning(self, message: str, location: str = ""):
        entry = "WARNING"
        if location:
            entry += f" | Location: {location}"
        entry += f" | Message: {message}"
        self.warnings.append(entry)

    def has_errors(self)   -> bool:     return bool(self.errors)
    def has_warnings(self) -> bool:     return bool(self.warnings)


_mstate = _MFDBValidationState()


# ---------------------------------------------------------------------------
# Internal helpers (also imported by lib_mfdb_core)
# ---------------------------------------------------------------------------

def _load_json(path: str) -> dict:
    """Load raw JSON without BEJSON validation (used internally)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rows_as_dicts(doc: dict) -> list[dict]:
    """Convert a BEJSON document's Values into a list of field-keyed dicts."""
    names = [f["name"] for f in doc["Fields"]]
    return [dict(zip(names, row)) for row in doc["Values"]]


def _resolve_entity_path(manifest_path: str, file_path_rel: str) -> str:
    """Resolve a relative file_path (from manifest record) to an absolute path."""
    manifest_dir = os.path.dirname(os.path.abspath(manifest_path))
    return os.path.normpath(os.path.join(manifest_dir, file_path_rel))


# ---------------------------------------------------------------------------
# Archive Validation (v1.2 Feature)
# ---------------------------------------------------------------------------

def mfdb_validator_validate_archive(archive_path: str) -> bool:
    """
    Validate an MFDB .zip archive.
    Ensures the archive contains a valid 104a.mfdb.bejson manifest at the root.
    """
    _mstate.reset()
    p = Path(archive_path)
    if not p.exists():
        _mstate.add_error(f"Archive not found: {archive_path}", "File System")
        raise MFDBValidationError(f"Archive not found: {archive_path}", E_MFDB_MANIFEST_NOT_FOUND)

    try:
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            nl = zip_ref.namelist()
            if "104a.mfdb.bejson" not in nl:
                _mstate.add_error("Archive missing 104a.mfdb.bejson at root", "Zip Structure")
                raise MFDBValidationError("Missing manifest inside archive", E_MFDB_INVALID_ARCHIVE)
    except zipfile.BadZipFile as exc:
        _mstate.add_error(f"Invalid zip file: {exc}", "Zip Parser")
        raise MFDBValidationError(str(exc), E_MFDB_INVALID_ARCHIVE) from exc

    return True


# ---------------------------------------------------------------------------
# Manifest Validation  (Spec §8.1)
# ---------------------------------------------------------------------------

def mfdb_validator_validate_manifest(manifest_path: str) -> bool:
    """
    Validate an MFDB manifest file (104a.mfdb.bejson).
    """
    _mstate.reset()
    p = Path(manifest_path)

    if not p.exists():
        _mstate.add_error(f"Manifest file not found: {manifest_path}", "File System")
        raise MFDBValidationError(f"File not found: {manifest_path}", E_MFDB_MANIFEST_NOT_FOUND)

    # Delegate BEJSON 104a structural validation
    try:
        bejson_validator_validate_file(manifest_path)
    except BEJSONValidationError as exc:
        _mstate.add_error(f"BEJSON 104a validation failed: {exc}", "BEJSON Validation")
        raise MFDBValidationError(str(exc), E_MFDB_NOT_MANIFEST) from exc

    doc = _load_json(manifest_path)

    if doc.get("Format_Version") != "104a":
        _mstate.add_error("Manifest must be Format_Version '104a'", "Format_Version")
        raise MFDBValidationError("Manifest must be 104a", E_MFDB_NOT_MANIFEST)

    rt = doc.get("Records_Type", [])
    if rt != ["mfdb"]:
        _mstate.add_error(
            f'Records_Type must be ["mfdb"]. Found: {rt}',
            "Records_Type",
        )
        raise MFDBValidationError("Bad manifest Records_Type", E_MFDB_MANIFEST_RECORDS_TYPE)

    field_names = [f["name"] for f in doc.get("Fields", [])]
    for required in ("entity_name", "file_path"):
        if required not in field_names:
            _mstate.add_error(f"Manifest Fields must include '{required}'", "Fields")
            raise MFDBValidationError(
                f"Missing required field '{required}'", E_MFDB_MISSING_REQUIRED_FIELD
            )

    entries = _rows_as_dicts(doc)
    seen_names: set[str] = set()
    seen_paths: set[str] = set()

    for i, entry in enumerate(entries):
        entity_name = entry.get("entity_name")
        file_path   = entry.get("file_path")

        if not entity_name:
            _mstate.add_error(f"Record {i}: entity_name is null or missing", f"Values[{i}]")
            raise MFDBValidationError("Null entity_name", E_MFDB_NULL_REQUIRED)

        if not file_path:
            _mstate.add_error(f"Record {i}: file_path is null or missing", f"Values[{i}]")
            raise MFDBValidationError("Null file_path", E_MFDB_NULL_REQUIRED)

        if entity_name in seen_names:
            _mstate.add_error(f"Duplicate entity_name: '{entity_name}'", f"Values[{i}]")
            raise MFDBValidationError(f"Duplicate entity_name: {entity_name}", E_MFDB_DUPLICATE_ENTRY)
        seen_names.add(entity_name)

        if file_path in seen_paths:
            _mstate.add_error(f"Duplicate file_path: '{file_path}'", f"Values[{i}]")
            raise MFDBValidationError(f"Duplicate file_path: {file_path}", E_MFDB_DUPLICATE_ENTRY)
        seen_paths.add(file_path)

        resolved = _resolve_entity_path(manifest_path, file_path)
        if not os.path.exists(resolved):
            _mstate.add_error(
                f"Entity file '{file_path}' not found (resolved: {resolved})",
                f"Values[{i}]/file_path",
            )
            raise MFDBValidationError(
                f"Entity file not found: {resolved}", 
                E_MFDB_ENTITY_NOT_FOUND,
                context={"entity_name": entity_name, "file_path_rel": file_path, "resolved_path": resolved}
            )

    return True


# ---------------------------------------------------------------------------
# Entity File Validation  (Spec §8.2)
# ---------------------------------------------------------------------------

def mfdb_validator_validate_entity_file(
    entity_path: str,
    check_bidirectional: bool = True,
) -> bool:
    """
    Validate an MFDB entity file (BEJSON 104 with Parent_Hierarchy back-link).
    """
    _mstate.reset()
    p = Path(entity_path)

    if not p.exists():
        _mstate.add_error(f"Entity file not found: {entity_path}", "File System")
        raise MFDBValidationError(f"File not found: {entity_path}", E_MFDB_ENTITY_NOT_FOUND)

    try:
        bejson_validator_validate_file(entity_path)
    except BEJSONValidationError as exc:
        _mstate.add_error(f"BEJSON 104 validation failed: {exc}", "BEJSON Validation")
        raise MFDBValidationError(str(exc), E_MFDB_NOT_ENTITY_FILE) from exc

    doc = _load_json(entity_path)

    if doc.get("Format_Version") != "104":
        _mstate.add_error("Entity file must be Format_Version '104'", "Format_Version")
        raise MFDBValidationError("Entity file must be 104", E_MFDB_NOT_ENTITY_FILE)

    rt = doc.get("Records_Type", [])
    entity_name = rt[0] if isinstance(rt, list) and len(rt) > 0 else "Unknown"

    parent_hierarchy = doc.get("Parent_Hierarchy")
    if not parent_hierarchy:
        _mstate.add_error(
            "Entity file must contain Parent_Hierarchy pointing to the manifest",
            "Parent_Hierarchy",
        )
        raise MFDBValidationError("Missing Parent_Hierarchy", E_MFDB_NO_PARENT_HIERARCHY)

    entity_dir    = os.path.dirname(os.path.abspath(entity_path))
    manifest_path = os.path.normpath(os.path.join(entity_dir, parent_hierarchy))

    if not os.path.exists(manifest_path):
        _mstate.add_error(
            f"Parent_Hierarchy '{parent_hierarchy}' resolves to '{manifest_path}' which does not exist",
            "Parent_Hierarchy",
        )
        raise MFDBValidationError(
            f"Manifest not found: {manifest_path}", 
            E_MFDB_MANIFEST_NOT_FOUND,
            context={
                "entity_name": entity_name,
                "actual_path": os.path.abspath(entity_path),
                "suggested_hierarchy": "../104a.mfdb.bejson"
            }
        )

    if not os.path.basename(manifest_path).endswith(".mfdb.bejson"):
        _mstate.add_warning(
            f"Parent_Hierarchy target '{manifest_path}' does not end in '.mfdb.bejson'. "
            f"Expected filename: 104a.mfdb.bejson",
            "Parent_Hierarchy",
        )

    rt = doc.get("Records_Type", [])
    if len(rt) != 1:
        _mstate.add_error(
            f"Entity file Records_Type must contain exactly one string. Found: {rt}",
            "Records_Type",
        )
        raise MFDBValidationError("Entity Records_Type must be single-entry", E_MFDB_NOT_ENTITY_FILE)

    entity_name = rt[0]

    try:
        manifest_doc = _load_json(manifest_path)
        entries      = _rows_as_dicts(manifest_doc)
        manifest_entity_names = [e.get("entity_name") for e in entries]
    except Exception as exc:
        _mstate.add_error(f"Could not read manifest: {exc}", "Manifest")
        raise MFDBValidationError(f"Cannot read manifest: {exc}", E_MFDB_MANIFEST_NOT_FOUND) from exc

    if entity_name not in manifest_entity_names:
        _mstate.add_error(
            f"Records_Type '{entity_name}' does not appear as entity_name in the manifest",
            "Records_Type vs Manifest",
        )
        raise MFDBValidationError(
            f"Entity '{entity_name}' not registered in manifest", E_MFDB_ENTITY_NAME_MISMATCH
        )

    if check_bidirectional:
        match = next((e for e in entries if e.get("entity_name") == entity_name), None)
        if match:
            manifest_dir  = os.path.dirname(os.path.abspath(manifest_path))
            from_manifest = os.path.normpath(
                os.path.join(manifest_dir, match.get("file_path", ""))
            )
            this_file     = os.path.normpath(os.path.abspath(entity_path))
            if from_manifest != this_file:
                _mstate.add_error(
                    f"Bidirectional check failed for entity '{entity_name}': "
                    f"manifest points to '{from_manifest}', but this file is '{this_file}'",
                    "Bidirectional Path Check",
                )
                raise MFDBValidationError(
                    "Bidirectional path check failed", 
                    E_MFDB_BIDIRECTIONAL_FAIL,
                    context={
                        "entity_name": entity_name,
                        "manifest_path": manifest_path,
                        "expected_path": from_manifest,
                        "actual_path": this_file,
                        "suggested_hierarchy": os.path.relpath(manifest_path, entity_dir)
                    }
                )

    return True


# ---------------------------------------------------------------------------
# Database-Level Validation  (Spec §8.3)
# ---------------------------------------------------------------------------

def mfdb_validator_check_integrity(manifest_path: str) -> bool:
    """
    Strict integrity check for MFDB boot.
    Asserts that the record_count in the manifest matches the actual row count
    for every entity file.
    """
    manifest_doc = _load_json(manifest_path)
    entries      = _rows_as_dicts(manifest_doc)
    
    for entry in entries:
        entity_name    = entry["entity_name"]
        file_path_rel  = entry["file_path"]
        declared_count = entry.get("record_count")
        
        if declared_count is None:
            continue
            
        resolved = _resolve_entity_path(manifest_path, file_path_rel)
        if not os.path.exists(resolved):
            continue
            
        entity_doc   = _load_json(resolved)
        actual_count = len(entity_doc.get("Values", []))
        
        if actual_count != declared_count:
            msg = f"Integrity Failure: Entity '{entity_name}' declares {declared_count} records, but found {actual_count}."
            _mstate.add_error(msg, f"Entity/{entity_name}/record_count")
            raise MFDBValidationError(msg, E_MFDB_BIDIRECTIONAL_FAIL)
            
    return True

def mfdb_validator_validate_database(
    manifest_path: str,
    strict_fk: bool = False,
) -> bool:
    """
    Full MFDB database validation.
    """
    _mstate.reset()

    # Step 1: Validate the manifest itself.
    try:
        mfdb_validator_validate_manifest(manifest_path)
    except MFDBValidationError:
        raise

    manifest_doc = _load_json(manifest_path)
    entries      = _rows_as_dicts(manifest_doc)

    pk_map = {
        e["entity_name"]: e.get("primary_key")
        for e in entries
        if e.get("primary_key")
    }

    # Step 2: Validate each entity file.
    for entry in entries:
        entity_name    = entry["entity_name"]
        file_path_rel  = entry["file_path"]
        declared_count = entry.get("record_count")

        resolved = _resolve_entity_path(manifest_path, file_path_rel)

        try:
            mfdb_validator_validate_entity_file(resolved, check_bidirectional=True)
        except MFDBValidationError as exc:
            _mstate.add_error(
                f"Entity '{entity_name}' failed validation: {exc}",
                f"Entity/{entity_name}",
            )
            raise

        if declared_count is not None:
            entity_doc   = _load_json(resolved)
            actual_count = len(entity_doc.get("Values", []))
            if actual_count != declared_count:
                _mstate.add_warning(
                    f"Entity '{entity_name}': manifest declares record_count={declared_count}, "
                    f"actual={actual_count}. Call mfdb_core_sync_all_counts() to correct.",
                    f"Entity/{entity_name}/record_count",
                )

        if strict_fk:
            entity_doc = _load_json(resolved)
            fk_fields  = [
                f["name"]
                for f in entity_doc.get("Fields", [])
                if f["name"].endswith("_fk")
            ]
            for fk_field in fk_fields:
                target_found = any(
                    pk and (pk in fk_field or en.lower() in fk_field.lower())
                    for en, pk in pk_map.items()
                )
                if not target_found:
                    _mstate.add_warning(
                        f"Entity '{entity_name}': FK field '{fk_field}' has no matching "
                        f"primary_key declaration in the manifest.",
                        f"Entity/{entity_name}/{fk_field}",
                    )

    return True


# ---------------------------------------------------------------------------
# Validation report
# ---------------------------------------------------------------------------

def mfdb_validator_get_report(manifest_path: str, strict_fk: bool = False) -> str:
    """Run full database validation and return a human-readable report string."""
    valid = False
    try:
        valid = mfdb_validator_validate_database(manifest_path, strict_fk=strict_fk)
    except (MFDBValidationError, Exception):
        pass

    lines = [
        "=== MFDB Validation Report ===",
        f"Manifest : {manifest_path}",
        f"Status   : {'VALID' if valid else 'INVALID'}",
        "",
        f"Errors   : {len(_mstate.errors)}",
    ]
    if _mstate.has_errors():
        lines.append("---")
        lines.extend(_mstate.errors)

    lines += ["", f"Warnings : {len(_mstate.warnings)}"]
    if _mstate.has_warnings():
        lines.append("---")
        lines.extend(_mstate.warnings)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# State accessors
# ---------------------------------------------------------------------------

def mfdb_validator_reset_state():                   _mstate.reset()
def mfdb_validator_has_errors()    -> bool:         return _mstate.has_errors()
def mfdb_validator_has_warnings()  -> bool:         return _mstate.has_warnings()
def mfdb_validator_get_errors()    -> list[str]:    return list(_mstate.errors)
def mfdb_validator_get_warnings()  -> list[str]:    return list(_mstate.warnings)
def mfdb_validator_error_count()   -> int:          return len(_mstate.errors)
def mfdb_validator_warning_count() -> int:          return len(_mstate.warnings)
