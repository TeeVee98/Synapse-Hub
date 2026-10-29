#!/usr/bin/env python3
"""
Universal Testing Intermediate Representation (IR) Schema
---------------------------------------------------------
Defines a language-agnostic and framework-agnostic schema for test automation.
Represents pages, locators, methods, test cases, and assertions independently of
whether the target is Playwright, Selenium, Cypress, Katalon, or Appium.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import json


class ActionType(str, Enum):
    GOTO = "goto"
    CLICK = "click"
    DBLCLICK = "dblclick"
    FILL = "fill"
    PRESS_KEY = "press_key"
    HOVER = "hover"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    WAIT = "wait"
    ASSERT = "assert"
    CUSTOM_CALL = "custom_call"
    API_CALL = "api_call"


class LocatorStrategy(str, Enum):
    ROLE = "role"
    LABEL = "label"
    TEST_ID = "test_id"
    TEXT = "text"
    CSS = "css"
    XPATH = "xpath"
    PLACEHOLDER = "placeholder"
    ID = "id"
    NAME = "name"
    CLASS_NAME = "class_name"
    UNKNOWN = "unknown"


class AssertionType(str, Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    EQUALS = "equals"
    CONTAINS_TEXT = "contains_text"
    HAS_VALUE = "has_value"
    IS_ENABLED = "is_enabled"
    IS_DISABLED = "is_disabled"
    URL_CONTAINS = "url_contains"


class WaitStrategy(str, Enum):
    AUTO = "auto"
    EXPLICIT_VISIBLE = "explicit_visible"
    NETWORK_IDLE = "network_idle"
    STATIC_SLEEP = "static_sleep"  # Flagged antipattern


@dataclass
class LocatorIR:
    name: str
    strategy: LocatorStrategy
    value: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "strategy": self.strategy.value if isinstance(self.strategy, LocatorStrategy) else self.strategy,
            "value": self.value,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocatorIR":
        strat = data.get("strategy", "unknown")
        try:
            strategy_enum = LocatorStrategy(strat)
        except ValueError:
            strategy_enum = LocatorStrategy.UNKNOWN
        return cls(
            name=data.get("name", "loc_unnamed"),
            strategy=strategy_enum,
            value=data.get("value", ""),
            description=data.get("description", ""),
        )


@dataclass
class StepIR:
    action: ActionType
    target: Optional[str] = None  # Locator name or raw selector
    value: Optional[str] = None   # Input text, key code, URL, etc.
    assertion_type: Optional[AssertionType] = None
    expected: Optional[str] = None
    wait_strategy: Optional[WaitStrategy] = None
    is_sanitized_wait: bool = False
    timeout_ms: int = 5000
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value if isinstance(self.action, ActionType) else self.action,
            "target": self.target,
            "value": self.value,
            "assertion_type": self.assertion_type.value if isinstance(self.assertion_type, AssertionType) and self.assertion_type else (self.assertion_type or None),
            "expected": self.expected,
            "wait_strategy": self.wait_strategy.value if isinstance(self.wait_strategy, WaitStrategy) and self.wait_strategy else (self.wait_strategy or None),
            "is_sanitized_wait": self.is_sanitized_wait,
            "timeout_ms": self.timeout_ms,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepIR":
        act = data.get("action", "custom_call")
        try:
            act_enum = ActionType(act)
        except ValueError:
            act_enum = ActionType.CUSTOM_CALL

        assert_type = data.get("assertion_type")
        assert_enum = None
        if assert_type:
            try:
                assert_enum = AssertionType(assert_type)
            except ValueError:
                assert_enum = None

        wait_strat = data.get("wait_strategy")
        wait_enum = None
        if wait_strat:
            try:
                wait_enum = WaitStrategy(wait_strat)
            except ValueError:
                wait_enum = None

        return cls(
            action=act_enum,
            target=data.get("target"),
            value=data.get("value"),
            assertion_type=assert_enum,
            expected=data.get("expected"),
            wait_strategy=wait_enum,
            is_sanitized_wait=data.get("is_sanitized_wait", False),
            timeout_ms=data.get("timeout_ms", 5000),
            description=data.get("description", ""),
        )


@dataclass
class MethodIR:
    name: str
    parameters: List[str] = field(default_factory=list)
    return_type: str = "void"
    steps: List[StepIR] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "steps": [s.to_dict() for s in self.steps],
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MethodIR":
        return cls(
            name=data.get("name", "execute"),
            parameters=data.get("parameters", []),
            return_type=data.get("return_type", "void"),
            steps=[StepIR.from_dict(s) for s in data.get("steps", [])],
            description=data.get("description", ""),
        )


@dataclass
class PageClassIR:
    name: str
    base_class: str = "BasePage"
    url: Optional[str] = None
    locators: List[LocatorIR] = field(default_factory=list)
    methods: List[MethodIR] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "base_class": self.base_class,
            "url": self.url,
            "locators": [loc.to_dict() for loc in self.locators],
            "methods": [m.to_dict() for m in self.methods],
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageClassIR":
        return cls(
            name=data.get("name", "UnnamedPage"),
            base_class=data.get("base_class", "BasePage"),
            url=data.get("url"),
            locators=[LocatorIR.from_dict(loc) for loc in data.get("locators", [])],
            methods=[MethodIR.from_dict(m) for m in data.get("methods", [])],
            description=data.get("description", ""),
        )


@dataclass
class TestCaseIR:
    id: str
    title: str
    steps: List[StepIR] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "steps": [s.to_dict() for s in self.steps],
            "tags": self.tags,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCaseIR":
        return cls(
            id=data.get("id", "TC_001"),
            title=data.get("title", "Automated Test Case"),
            steps=[StepIR.from_dict(s) for s in data.get("steps", [])],
            tags=data.get("tags", []),
            description=data.get("description", ""),
        )


@dataclass
class ProjectIR:
    name: str = "OmniTestProject"
    source_language: str = "generic"
    source_framework: str = "generic"
    pages: List[PageClassIR] = field(default_factory=list)
    test_cases: List[TestCaseIR] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source_language": self.source_language,
            "source_framework": self.source_framework,
            "pages": [p.to_dict() for p in self.pages],
            "test_cases": [tc.to_dict() for tc in self.test_cases],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectIR":
        return cls(
            name=data.get("name", "OmniTestProject"),
            source_language=data.get("source_language", "generic"),
            source_framework=data.get("source_framework", "generic"),
            pages=[PageClassIR.from_dict(p) for p in data.get("pages", [])],
            test_cases=[TestCaseIR.from_dict(tc) for tc in data.get("test_cases", [])],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ProjectIR":
        data = json.loads(json_str)
        return cls.from_dict(data)
