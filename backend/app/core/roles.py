from enum import Enum
from typing import Set, Any


class Role(str, Enum):
    CITIZEN = "citizen"
    DISTRICT_OFFICER = "district_officer"
    STATE_ADMIN = "state_admin"
    SYSTEM_ADMIN = "system_admin"

    @classmethod
    def normalize(cls, role_input: Any) -> "Role":
        """Normalizes role strings, enums, or model values to standardized Role enum."""
        if isinstance(role_input, Role):
            return role_input
        if hasattr(role_input, "value"):
            role_input = role_input.value
        s = str(role_input).lower().strip()
        if "district_officer" in s or s == "officer":
            return cls.DISTRICT_OFFICER
        elif "system_admin" in s or s == "admin":
            return cls.SYSTEM_ADMIN
        elif "state_admin" in s or "state_administrator" in s:
            return cls.STATE_ADMIN
        return cls.CITIZEN

    @classmethod
    def all_roles(cls) -> Set[str]:
        return {r.value for r in cls}
