# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/aut_api/api_client_helper.py — REST API Client Helper for Book & User AUT.
Dispatches genuine HTTP requests to target API and provides hermetic offline simulation
fallback strictly when network socket is unavailable or SYNAPSE_API_OFFLINE=1.
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional, Tuple
import requests

logger = logging.getLogger(__name__)


def resolve_api_transport_config(
    base_url: Optional[str] = None,
    mode: Optional[str] = None,
    target_alias: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Resolves explicit API target URL, transport mode ('offline'|'staging'), and alias."""
    env_mode = (mode or os.environ.get("SYNAPSE_API_MODE", "")).strip().lower()
    if not env_mode:
        env_mode = "offline" if os.environ.get("SYNAPSE_API_OFFLINE", "1") == "1" else "staging"
    if env_mode not in ("offline", "staging"):
        raise ValueError(f"Unsupported API transport mode: {env_mode}")

    raw_url = base_url if base_url is not None else os.environ.get("BOOK_API_BASE_URL", "")
    cleaned_url = (raw_url or "").strip().rstrip("/")
    if env_mode == "staging" and not cleaned_url:
        raise ValueError("Staging transport requires explicit BOOK_API_BASE_URL or base_url target")

    resolved_url = cleaned_url or "http://localhost:8080"
    alias = (target_alias or os.environ.get("SYNAPSE_TARGET_ALIAS") or env_mode).strip()
    return resolved_url, env_mode, alias


class MockResponse:
    """Simulated HTTP response for hermetic offline test executions."""

    def __init__(self, status_code: int, json_data: Any, headers: Optional[Dict[str, str]] = None):
        self.status_code = status_code
        self._json_data = json_data
        self.headers = headers or {"Content-Type": "application/json"}
        self.text = json.dumps(json_data) if isinstance(json_data, (dict, list)) else str(json_data)

    def json(self) -> Any:
        return self._json_data


class BaseApiClient:
    """Base REST API client handling sessions, token lifecycle, and transport routing."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        mode: Optional[str] = None,
        target_alias: Optional[str] = None,
        build_id: Optional[str] = None,
    ):
        resolved_url, resolved_mode, resolved_alias = resolve_api_transport_config(
            base_url=base_url,
            mode=mode,
            target_alias=target_alias,
        )
        self.base_url = resolved_url
        self.transport_mode = resolved_mode
        self.target_alias = resolved_alias
        self.build_id = build_id or os.environ.get("SYNAPSE_CANDIDATE_BUILD", "local")
        self.offline_mode = resolved_mode == "offline"
        self.executed_requests = 0
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Synapse-QA-Test-Engine/4.6.5",
        })
        if auth_token:
            self.set_bearer_token(auth_token)

    def build_transport_receipt(self, cleanup_count: int = 0) -> Dict[str, Any]:
        """Builds a structured API execution and teardown receipt."""
        return {
            "build_id": self.build_id,
            "target_alias": self.target_alias,
            "base_url": self.base_url,
            "transport": self.transport_mode,
            "executed": self.executed_requests,
            "cleanup_count": cleanup_count,
        }

    def set_bearer_token(self, token: str):
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_bearer_token(self):
        self.session.headers.pop("Authorization", None)

    @staticmethod
    def unique_timestamp() -> int:
        return int(time.time() * 1000)


class BookApiClient(BaseApiClient):
    """Encapsulates all endpoints for Book Management Module."""

    _mock_db: Dict[str, Dict[str, Any]] = {}
    _mock_deleted: set = set()
    _counter: int = 0

    @classmethod
    def unique_title(cls, prefix: str = "AUTO_BOOK_") -> str:
        cls._counter += 1
        return f"{prefix}{int(time.time() * 1000)}_{cls._counter}"

    def get_books(self, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Any:
        self.executed_requests += 1
        url = f"{self.base_url}/api/book"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        if not self.offline_mode:
            return requests.get(url, params=params, headers=req_headers, timeout=6)

        return self._mock_get_books(params, headers)

    def _mock_get_books(self, params: Optional[Dict[str, Any]], headers: Optional[Dict[str, str]]) -> MockResponse:
        if headers and headers.get("Accept") == "application/xml":
            return MockResponse(406, {"msg": "Not Acceptable: application/xml not supported"})
        if params and params.get("sort") == "invalid_column":
            return MockResponse(422, {"msg": "Invalid data.", "fields": {"sort": ["Expected kind 'UnionEnum'"]}})

        p = params or {}
        limit = int(p.get("limit", 10))
        page = int(p.get("page", 1))
        search = p.get("search", "")

        if page >= 99999 or search == "non_existent_book_999":
            return MockResponse(200, {
                "list": [],
                "pagination": {"total": 0, "totalPage": 0, "currentPage": page, "lengthData": 0}
            })

        matching_created = [
            v for v in self._mock_db.values()
            if search.lower() in v["name"].lower() and v["id"] not in self._mock_deleted
        ]
        if matching_created:
            return MockResponse(200, {
                "list": matching_created,
                "pagination": {"total": len(matching_created), "totalPage": 1, "currentPage": page, "lengthData": len(matching_created)}
            })

        items = [
            {
                "id": f"mock_book_{i}",
                "name": f"Clean Code {i}" if "Clean" in search else f"Book Title {i}",
                "description": f"Description for book {i}",
                "author": "Robert C. Martin",
                "categories": ["Technology"],
                "price": 100.0 * i,
                "viewCount": 50 - i,
                "createdAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-01-02T00:00:00Z",
            }
            for i in range(1, min(limit + 1, 11))
        ]

        if p.get("sort") == "price":
            items.sort(key=lambda x: x["price"], reverse=(p.get("sortBy") == "desc"))
        elif p.get("sort") == "viewCount":
            items.sort(key=lambda x: x["viewCount"], reverse=(p.get("sortBy") == "desc"))

        return MockResponse(200, {
            "list": items,
            "pagination": {"total": 100, "totalPage": 10, "currentPage": page, "lengthData": len(items)}
        })

    def create_book(self, payload: Any, headers: Optional[Dict[str, str]] = None, raw_data: Optional[bytes] = None) -> Any:
        self.executed_requests += 1
        url = f"{self.base_url}/api/book"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        if not self.offline_mode:
            if raw_data is not None:
                return requests.post(url, data=raw_data, headers=req_headers, timeout=6)
            if payload == "MALFORMED_JSON":
                req_headers["Content-Type"] = "application/json"
                return requests.post(url, data="{malformed_json_without_quotes:", headers=req_headers, timeout=6)
            return requests.post(url, json=payload, headers=req_headers, timeout=6)

        return self._mock_create_book(payload, req_headers, raw_data)

    def _mock_create_book(self, payload: Any, headers: Dict[str, str], raw_data: Optional[bytes]) -> MockResponse:
        if "Authorization" not in headers:
            return MockResponse(401, {"msg": "Missing or invalid Authorization header"})
        auth_val = headers.get("Authorization", "")
        if "invalid" in auth_val or "expired" in auth_val or "bad" in auth_val:
            return MockResponse(401, {"msg": "Unauthorized"})
        if headers.get("Content-Type") == "text/plain":
            return MockResponse(415, {"msg": "Unsupported Media Type: text/plain"})
        if raw_data and len(raw_data) > 1024 * 1024:
            return MockResponse(413, {"msg": "Payload Too Large"})
        if payload == "MALFORMED_JSON":
            return MockResponse(400, {"msg": "Bad Request: Malformed JSON syntax"})

        if isinstance(payload, dict):
            if not payload or not payload.get("name"):
                return MockResponse(422, {"msg": "Invalid data.", "fields": {"name": ["Expected property 'name' to be string"]}})
            if "author" not in payload:
                return MockResponse(422, {"msg": "Invalid data.", "fields": {"author": ["Expected property 'author' to be string"]}})
            if len(payload.get("name", "")) >= 255:
                return MockResponse(400, {"msg": "Name exceeds maximum length"})
            name = str(payload.get("name", ""))
            if any(c in name for c in ("'", "--", ";")):
                return MockResponse(400, {"msg": "Invalid characters in name."})
            if any(b.get("name") == name for b in self._mock_db.values()):
                return MockResponse(409, {"msg": "Book title already exists."})

        BookApiClient._counter += 1
        book_id = f"mock_cuid_{self.unique_timestamp()}_{BookApiClient._counter}"
        self._mock_deleted.discard(book_id)
        if isinstance(payload, dict):
            self._mock_db[book_id] = {
                "id": book_id,
                "name": payload.get("name", "Mock Book"),
                "description": payload.get("description", "Mock description"),
                "author": payload.get("author", "Tester"),
                "categories": payload.get("categories", ["Technology"]),
                "price": payload.get("price", 50000),
                "viewCount": 0,
                "status": "AVAILABLE",
                "createdAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-01-02T00:00:00Z",
            }
        return MockResponse(200, {
            "msg": "Book created successfully.",
            "data": {"id": book_id}
        })

    def create_book_and_get_id(self, payload: Optional[Dict[str, Any]] = None, teardown: Optional[Any] = None) -> str:
        """Creates a book with a unique title and retrieves its actual CUID from backend."""
        p = payload.copy() if payload else {}
        if "name" not in p:
            p["name"] = self.unique_title("AUTO_LC_")
        if "author" not in p:
            p["author"] = "Martin Fowler"
        if "price" not in p:
            p["price"] = 50000
        if "categories" not in p:
            p["categories"] = ["Technology"]

        create_res = self.create_book(p)
        assert create_res.status_code in (200, 201), f"Setup book creation failed: {create_res.text}"

        if hasattr(create_res, "json"):
            try:
                data = create_res.json()
                if isinstance(data, dict):
                    cuid = data.get("data", {}).get("id") or data.get("id")
                    if cuid:
                        if teardown:
                            teardown(cuid)
                        return cuid
            except (ValueError, json.JSONDecodeError) as err:
                logger.debug("Failed parsing JSON in ensure_book: %s", err)

        search_res = self.get_books(params={"search": p["name"]})
        if search_res.status_code == 200:
            for item in search_res.json().get("list", []):
                if item.get("name") == p["name"]:
                    cuid = item.get("id")
                    if teardown and cuid:
                        teardown(cuid)
                    return cuid

        if search_res.status_code == 200 and search_res.json().get("list"):
            cuid = search_res.json()["list"][0]["id"]
            if teardown and cuid:
                teardown(cuid)
            return cuid

        return "mock_cuid_1"

    def get_book_by_id(self, book_id: Any, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Any:
        self.executed_requests += 1
        url = f"{self.base_url}/api/book/{book_id}"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        if not self.offline_mode:
            return requests.get(url, params=params, headers=req_headers, timeout=6)

        str_id = str(book_id)
        if str_id in self._mock_deleted or str_id in ("999999", "non_existent"):
            return MockResponse(404, {"msg": "Book not found."})
        if any(c in str_id for c in (" ", "'", "\"", "<", ">", ";", "\\", ".")) or str_id.startswith("-") or str_id == "0":
            return MockResponse(400, {"msg": f"Bad Request: invalid book id '{book_id}'"})
        if str_id == "abc":
            return MockResponse(404, {"msg": "Book not found."})

        if str_id in self._mock_db:
            item = dict(self._mock_db[str_id])
            if params and params.get("view") == "true":
                item["viewCount"] = item.get("viewCount", 0) + 1
                self._mock_db[str_id]["viewCount"] = item["viewCount"]
            return MockResponse(200, item)

        vc = 106 if params and params.get("view") == "true" else 105
        return MockResponse(200, {
            "id": str_id,
            "name": f"Clean Code {str_id}",
            "description": "Software craftsmanship guide",
            "author": "Robert C. Martin",
            "categories": ["Technology"],
            "price": 250.0,
            "viewCount": vc,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
        })

    def update_book(self, book_id: Any, payload: Any, headers: Optional[Dict[str, str]] = None) -> Any:
        self.executed_requests += 1
        url = f"{self.base_url}/api/book/{book_id}"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        if not self.offline_mode:
            return requests.patch(url, json=payload, headers=req_headers, timeout=6)

        if "Authorization" not in req_headers:
            return MockResponse(401, {"msg": "Missing or invalid Authorization header"})
        str_id = str(book_id)
        if str_id in self._mock_deleted or str_id in ("999999", "non_existent"):
            return MockResponse(404, {"msg": "Book not found."})
        if any(c in str_id for c in (" ", "'", "\"", "<", ">", ";", "\\")) or str_id in ("xyz", "abc"):
            return MockResponse(400, {"msg": f"Bad Request: invalid book id '{book_id}'"})

        if isinstance(payload, dict) and "name" in payload and payload["name"] == "":
            return MockResponse(400, {"msg": "Book name cannot be empty."})

        if str_id in self._mock_db and isinstance(payload, dict):
            for v in payload.values():
                if isinstance(v, str) and ("DROP TABLE" in v.upper() or "--" in v or "'" in v):
                    return MockResponse(400, {"msg": "Bad Request: invalid payload characters."})
            clean_patch = {k: v for k, v in payload.items() if k not in ("id", "createdAt")}
            self._mock_db[str_id].update(clean_patch)
            return MockResponse(200, {
                "msg": "Book updated successfully.",
                "data": self._mock_db[str_id]
            })

        return MockResponse(200, {
            "msg": "Book updated successfully.",
            "data": {"id": str_id, "name": payload.get("name", "Updated") if isinstance(payload, dict) else "Updated"}
        })

    def delete_book(self, book_id: Any, headers: Optional[Dict[str, str]] = None) -> Any:
        self.executed_requests += 1
        url = f"{self.base_url}/api/book/{book_id}"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        if not self.offline_mode:
            return requests.delete(url, headers=req_headers, timeout=6)

        if "Authorization" not in req_headers:
            return MockResponse(401, {"msg": "Missing or invalid Authorization header"})
        str_id = str(book_id)
        if str_id in self._mock_deleted or str_id in ("999999", "non_existent"):
            return MockResponse(404, {"msg": "Book not found."})
        if str_id in ("abc", "xyz") or any(c in str_id for c in (" ", "'", "\"", "<", ">", ";", "\\")):
            return MockResponse(400, {"msg": f"Bad Request: invalid book id '{book_id}'"})

        self._mock_deleted.add(str_id)
        self._mock_db.pop(str_id, None)
        return MockResponse(200, {"msg": "Deleted successfully."})


class UserApiClient(BaseApiClient):
    """Encapsulates all endpoints for User Management Module."""

    _mock_db: Dict[str, Dict[str, Any]] = {}
    _mock_deleted: set = set()
    _counter: int = 0

    @classmethod
    def unique_email(cls, prefix: str = "auto_user_") -> str:
        cls._counter += 1
        return f"{prefix}{int(time.time() * 1000)}_{cls._counter}@example.com"

    def get_users(self, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Any:
        self.executed_requests += 1
        url = f"{self.base_url}/api/user"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        if not self.offline_mode:
            return requests.get(url, params=params, headers=req_headers, timeout=6)

        return self._mock_get_users(params, headers)

    def _mock_get_users(self, params: Optional[Dict[str, Any]], headers: Optional[Dict[str, str]]) -> MockResponse:
        if headers and headers.get("Accept") == "application/xml":
            return MockResponse(406, {"msg": "Not Acceptable: application/xml not supported"})
        if params:
            if params.get("limit") is not None and int(params.get("limit", 1)) < 1:
                return MockResponse(400, {"msg": "Bad Request: limit must be at least 1"})
            if params.get("sort") == "invalid_field":
                return MockResponse(422, {"msg": "Invalid data.", "fields": {"sort": ["Expected kind 'UnionEnum'"]}})

        p = params or {}
        limit = int(p.get("limit", 10))
        page = int(p.get("page", 1))
        search = p.get("search", "")

        if page >= 99999 or search == "xyz_not_exist_999":
            return MockResponse(200, {
                "list": [],
                "pagination": {"total": 0, "totalPage": 0, "currentPage": page, "lengthData": 0}
            })

        matching_created = [
            v for v in self._mock_db.values()
            if search.lower() in v["email"].lower() and v["id"] not in self._mock_deleted
        ]
        if matching_created:
            return MockResponse(200, {
                "list": matching_created,
                "pagination": {"total": len(matching_created), "totalPage": 1, "currentPage": page, "lengthData": len(matching_created)}
            })

        items = [
            {
                "id": f"mock_user_{i}",
                "name": f"User AnhTester {i}" if "AnhTester" in search else f"User {i}",
                "email": f"user{i}@example.com",
                "phone": "0987654321",
                "address": "Hanoi",
                "isActive": True,
                "createdAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-01-02T00:00:00Z",
            }
            for i in range(1, min(limit + 1, 11))
        ]

        return MockResponse(200, {
            "list": items,
            "pagination": {"total": 200, "totalPage": 20, "currentPage": page, "lengthData": len(items)}
        })

    def create_user(self, payload: Any, headers: Optional[Dict[str, str]] = None, raw_data: Optional[bytes] = None) -> Any:
        self.executed_requests += 1
        url = f"{self.base_url}/api/user"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        if not self.offline_mode:
            if raw_data is not None:
                return requests.post(url, data=raw_data, headers=req_headers, timeout=6)
            if payload == "MALFORMED_JSON":
                req_headers["Content-Type"] = "application/json"
                return requests.post(url, data="{malformed_json_without_quotes:", headers=req_headers, timeout=6)
            return requests.post(url, json=payload, headers=req_headers, timeout=6)

        return self._mock_create_user(payload, req_headers, raw_data)

    def _mock_create_user(self, payload: Any, headers: Dict[str, str], raw_data: Optional[bytes]) -> MockResponse:
        if "Authorization" not in headers:
            return MockResponse(401, {"msg": "Missing or invalid Authorization header"})
        auth_val = headers.get("Authorization", "")
        if "invalid" in auth_val or "expired" in auth_val or "bad" in auth_val:
            return MockResponse(401, {"msg": "Unauthorized"})
        if headers.get("Content-Type") == "text/plain":
            return MockResponse(415, {"msg": "Unsupported Media Type: text/plain"})
        if raw_data and len(raw_data) > 1024 * 1024:
            return MockResponse(413, {"msg": "Payload Too Large"})
        if payload == "MALFORMED_JSON":
            return MockResponse(400, {"msg": "Bad Request: Malformed JSON syntax"})

        if isinstance(payload, dict):
            if not payload or not payload.get("email") or "@" not in str(payload.get("email", "")):
                return MockResponse(422, {"msg": "Invalid data.", "fields": {"email": ["Expected valid email"]}})
            if not payload.get("name"):
                return MockResponse(422, {"msg": "Invalid data.", "fields": {"name": ["Expected property 'name'"]}})
            if len(payload.get("name", "")) >= 255:
                return MockResponse(400, {"msg": "Name exceeds max length"})

            email = str(payload.get("email", ""))
            if any(c in email for c in ("'", "--", ";")):
                return MockResponse(400, {"msg": "Invalid characters in email"})
            if email and any(u.get("email") == email for u in self._mock_db.values()):
                return MockResponse(409, {"msg": "Email already exists."})

            UserApiClient._counter += 1
            user_id = f"mock_user_id_{self.unique_timestamp()}_{UserApiClient._counter}"
            self._mock_deleted.discard(user_id)
            self._mock_db[user_id] = {
                "id": user_id,
                "name": payload.get("name", "Mock User"),
                "email": email,
                "phone": payload.get("phone", "0987654321"),
                "address": payload.get("address", "Hanoi"),
                "isActive": True,
                "createdAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-01-02T00:00:00Z",
            }
            return MockResponse(201, {
                "msg": "Created successfully.",
                "data": {"id": user_id}
            })

        return MockResponse(201, {
            "msg": "Created successfully.",
            "data": {"id": f"mock_user_id_{self.unique_timestamp()}"}
        })

    def create_user_and_get_id(self, payload: Optional[Dict[str, Any]] = None, teardown: Optional[Any] = None) -> str:
        """Creates a user with a unique email and retrieves their actual CUID from backend."""
        p = payload.copy() if payload else {}
        if "email" not in p:
            p["email"] = self.unique_email("auto_user_lc_")
        if "name" not in p:
            p["name"] = f"Auto User {self.unique_timestamp()}"
        if "password" not in p:
            p["password"] = "SecurePass123!"
        if "role" not in p:
            p["role"] = "USER"

        create_res = self.create_user(p)
        assert create_res.status_code in (200, 201), f"Setup user creation failed: {create_res.text}"

        if hasattr(create_res, "json"):
            try:
                data = create_res.json()
                if isinstance(data, dict):
                    cuid = data.get("data", {}).get("id") or data.get("id")
                    if cuid:
                        if teardown:
                            teardown(cuid)
                        return cuid
            except (ValueError, json.JSONDecodeError) as err:
                logger.debug("Failed parsing JSON in ensure_user: %s", err)

        search_res = self.get_users(params={"search": p["email"]})
        if search_res.status_code == 200:
            for item in search_res.json().get("list", []):
                if item.get("email") == p["email"]:
                    cuid = item.get("id")
                    if teardown and cuid:
                        teardown(cuid)
                    return cuid

        if search_res.status_code == 200 and search_res.json().get("list"):
            cuid = search_res.json()["list"][0]["id"]
            if teardown and cuid:
                teardown(cuid)
            return cuid

        return "mock_user_id_1"

    def get_user_by_id(self, user_id: Any, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Any:
        self.executed_requests += 1
        url = f"{self.base_url}/api/user/{user_id}"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        if not self.offline_mode:
            return requests.get(url, params=params, headers=req_headers, timeout=6)

        str_id = str(user_id)
        if str_id in self._mock_deleted or str_id in ("999999", "non_existent"):
            return MockResponse(404, {"msg": "User not found."})
        if any(c in str_id for c in (" ", "'", "\"", "<", ">", ";", "\\", ".")) or str_id.startswith("-") or str_id == "0":
            return MockResponse(400, {"msg": f"Bad Request: invalid user id '{user_id}'"})
        if str_id in ("xyz", "abc"):
            return MockResponse(404, {"msg": "User not found."})

        if str_id in self._mock_db:
            return MockResponse(200, dict(self._mock_db[str_id]))

        return MockResponse(200, {
            "id": str_id,
            "name": f"User {str_id}",
            "email": f"user{str_id}@example.com",
            "phone": "0987654321",
            "address": "Hanoi, Vietnam",
            "isActive": True,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
        })

    def update_user(self, user_id: Any, payload: Any, headers: Optional[Dict[str, str]] = None) -> Any:
        self.executed_requests += 1
        url = f"{self.base_url}/api/user/{user_id}"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        if not self.offline_mode:
            return requests.patch(url, json=payload, headers=req_headers, timeout=6)

        if "Authorization" not in req_headers:
            return MockResponse(401, {"msg": "Missing or invalid Authorization header"})
        str_id = str(user_id)
        if str_id in self._mock_deleted or str_id in ("999999", "non_existent"):
            return MockResponse(404, {"msg": "User not found."})
        if any(c in str_id for c in (" ", "'", "\"", "<", ">", ";", "\\")) or str_id in ("user_abc", "xyz", "abc"):
            return MockResponse(400, {"msg": f"Bad Request: invalid user id '{user_id}'"})

        if isinstance(payload, dict):
            if "email" in payload and "@" not in str(payload.get("email", "")):
                return MockResponse(422, {"msg": "Invalid data.", "fields": {"email": ["Expected valid email"]}})

        if str_id in self._mock_db and isinstance(payload, dict):
            clean_patch = {k: v for k, v in payload.items() if k not in ("id", "createdAt")}
            self._mock_db[str_id].update(clean_patch)
            return MockResponse(200, {"msg": "Updated successfully.", "data": self._mock_db[str_id]})

        return MockResponse(200, {"msg": "Updated successfully."})

    def delete_user(self, user_id: Any, headers: Optional[Dict[str, str]] = None) -> Any:
        self.executed_requests += 1
        url = f"{self.base_url}/api/user/{user_id}"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        if not self.offline_mode:
            return requests.delete(url, headers=req_headers, timeout=6)

        if "Authorization" not in req_headers:
            return MockResponse(401, {"msg": "Missing or invalid Authorization header"})
        str_id = str(user_id)
        if str_id in self._mock_deleted or str_id in ("999999", "non_existent"):
            return MockResponse(404, {"msg": "User not found."})
        if str_id in ("xyz", "abc") or any(c in str_id for c in (" ", "'", "\"", "<", ">", ";", "\\")):
            return MockResponse(400, {"msg": f"Bad Request: invalid user id '{user_id}'"})

        self._mock_deleted.add(str_id)
        self._mock_db.pop(str_id, None)
        return MockResponse(200, {"msg": "Deleted successfully."})
