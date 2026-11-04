import unittest
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "tools"))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import _openapi_parser as parser


class TestOpenAPIParser(unittest.TestCase):
    def setUp(self):
        self.sample_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Sample API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List Users",
                        "operationId": "getUsers",
                        "parameters": [
                            {"name": "limit", "in": "query", "schema": {"type": "integer"}}
                        ],
                        "responses": {"200": {"description": "OK"}}
                    },
                    "post": {
                        "summary": "Create User",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/UserInput"}
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            },
            "components": {
                "schemas": {
                    "UserInput": {
                        "type": "object",
                        "required": ["username"],
                        "properties": {
                            "username": {"type": "string", "minLength": 3, "maxLength": 20},
                            "age": {"type": "integer", "minimum": 18, "maximum": 99}
                        }
                    }
                }
            }
        }

    def test_resolve_ref(self):
        resolved = parser.resolve_ref(self.sample_spec, "#/components/schemas/UserInput")
        self.assertEqual(resolved.get("type"), "object")
        self.assertIn("username", resolved.get("properties", {}))

    def test_extract_endpoints(self):
        endpoints = parser.extract_endpoints(self.sample_spec)
        self.assertEqual(len(endpoints), 2)
        get_ep = [ep for ep in endpoints if ep["method"] == "GET"][0]
        self.assertEqual(get_ep["path"], "/users")
        self.assertEqual(get_ep["operation_id"], "getUsers")

        post_ep = [ep for ep in endpoints if ep["method"] == "POST"][0]
        self.assertEqual(post_ep["method"], "POST")
        self.assertIn("username", post_ep["request_schema"].get("properties", {}))

    def test_generate_boundary_scenarios_string(self):
        scenarios = parser.generate_boundary_scenarios("username", {"type": "string", "minLength": 3, "maxLength": 20})
        self.assertTrue(len(scenarios) >= 5)
        scenarios_names = [s["scenario"] for s in scenarios]
        self.assertTrue(any("Empty String" in s for s in scenarios_names))
        self.assertTrue(any("MaxLength" in s for s in scenarios_names))

    def test_generate_boundary_scenarios_number(self):
        scenarios = parser.generate_boundary_scenarios("age", {"type": "integer", "minimum": 18, "maximum": 99})
        self.assertTrue(len(scenarios) >= 5)
        scenarios_names = [s["scenario"] for s in scenarios]
        self.assertTrue(any("Negative Value" in s for s in scenarios_names))
        self.assertTrue(any("Boundary Minimum" in s for s in scenarios_names))


if __name__ == "__main__":
    unittest.main()
