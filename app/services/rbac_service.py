from typing import List, Dict

# Role-Based Access Control mapping: user role -> allowed folders in resources/data/
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "engineering": ["engineering", "general"],
    "finance": ["finance", "general"],
    "hr": ["hr", "general"],
    "marketing": ["marketing", "general"],
    "general": ["general"],
}


def get_permitted_folders(role: str) -> List[str]:
    """
    Returns the list of folder names inside resources/data/ that the specified user role is permitted to access.
    Defaults to ['general'] if the role is unrecognized.
    """
    normalized_role = role.strip().lower()
    return ROLE_PERMISSIONS.get(normalized_role, ["general"])
