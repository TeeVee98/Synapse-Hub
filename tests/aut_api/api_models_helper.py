# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/aut_api/api_models_helper.py — Contract Schemas & Structural Validators for Book & User APIs.
Validates payload integrity adhering to OpenAPI 3.0 specs and ISO/IEC/IEEE 29119-3 criteria.
"""

import os
import secrets
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class PaginationData:
    total: int
    totalPage: int
    currentPage: int
    lengthData: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaginationData":
        return cls(
            total=int(data.get("total", 0)),
            totalPage=int(data.get("totalPage", 0)),
            currentPage=int(data.get("currentPage", 1)),
            lengthData=int(data.get("lengthData", 0)),
        )


@dataclass
class BookData:
    name: str
    price: float
    description: str = ""
    category: str = "General"
    author: str = "Synapse Author"
    id: Optional[int] = None
    viewCount: int = 0
    status: int = 1

    def to_payload(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "price": self.price,
            "description": self.description,
            "category": self.category,
            "author": self.author,
        }


@dataclass
class UserData:
    name: str
    email: str
    password: str = field(default_factory=lambda: os.getenv("AUT_TEST_PASSWORD") or secrets.token_urlsafe(16))
    phone: str = "0987654321"
    address: str = "Hanoi, Vietnam"
    isActive: bool = True
    id: Optional[int] = None

    def to_payload(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "email": self.email,
            "password": self.password,
            "phone": self.phone,
            "address": self.address,
            "isActive": self.isActive,
        }


def validate_pagination(pagination: Any) -> bool:
    """Validates pagination object has required keys and non-negative integer types."""
    if not isinstance(pagination, dict):
        return False
    required_keys = {"total", "totalPage", "currentPage", "lengthData"}
    if not required_keys.issubset(pagination.keys()):
        return False
    return all(isinstance(pagination[k], int) and pagination[k] >= 0 for k in required_keys)


def validate_book_item(item: Any) -> bool:
    """Validates book object conforms to schema specification."""
    if not isinstance(item, dict):
        return False
    if "id" not in item or "name" not in item:
        return False
    if not isinstance(item["id"], (int, str)):
        return False
    if not isinstance(item["name"], str):
        return False
    return True


def validate_book_list_response(data: Any) -> bool:
    """Validates GET /api/book root response conforms to list and pagination contract."""
    if not isinstance(data, dict):
        return False
    if "list" not in data or "pagination" not in data:
        return False
    if not isinstance(data["list"], list):
        return False
    if not validate_pagination(data["pagination"]):
        return False
    return all(validate_book_item(b) for b in data["list"])


def validate_user_item(item: Any) -> bool:
    """Validates user object conforms to schema specification."""
    if not isinstance(item, dict):
        return False
    if "id" not in item or "name" not in item or "email" not in item:
        return False
    if not isinstance(item["id"], (int, str)):
        return False
    if not isinstance(item["name"], str):
        return False
    return True


def validate_user_list_response(data: Any) -> bool:
    """Validates GET /api/user root response conforms to list and pagination contract."""
    if not isinstance(data, dict):
        return False
    if "list" not in data or "pagination" not in data:
        return False
    if not isinstance(data["list"], list):
        return False
    if not validate_pagination(data["pagination"]):
        return False
    return all(validate_user_item(u) for u in data["list"])
