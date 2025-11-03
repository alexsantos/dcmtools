from pydicom.uid import generate_uid

DEFAULT_ORG_UID_ROOT = "1.3.6.1.4.1.62860."  # change if needed

def make_target_study_uid(prefix: str = DEFAULT_ORG_UID_ROOT) -> str:
    """Generate a StudyInstanceUID using your org root (with trailing dot)."""
    if not prefix.endswith("."):
        prefix = prefix + "."
    return generate_uid(prefix=prefix)
