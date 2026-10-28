import unittest
import os
import tempfile
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import test_impact


class TestTestImpact(unittest.TestCase):
    def test_get_total_test_cases_override(self):
        total = test_impact.get_total_test_cases(override_total=50)
        self.assertEqual(total, 50)

    def test_analyze_impact_graph(self):
        mock_graph = {
            "nodes": [
                {"id": "CategoryPage", "label": "CategoryPage", "file": "Keywords/pages/CategoryPage.groovy"},
                {"id": "HelperClass", "label": "HelperClass", "file": "Keywords/helpers/HelperClass.groovy"},
                {"id": "TC_CreateCategory", "label": "TC_CreateCategory", "file": "Scripts/TC_CreateCategory/Script1.groovy"},
                {"id": "TC_Unrelated", "label": "TC_Unrelated", "file": "Scripts/TC_Unrelated/Script2.groovy"},
            ],
            "edges": [
                # Edge: caller -> callee (source calls target)
                {"source": "TC_CreateCategory", "target": "CategoryPage"},
                {"source": "CategoryPage", "target": "HelperClass"}
            ]
        }

        # If HelperClass is modified, both CategoryPage and TC_CreateCategory are impacted
        impacted = test_impact.analyze_impact(mock_graph, ["Keywords/helpers/HelperClass.groovy"])
        self.assertIn("TC_CreateCategory", impacted)
        self.assertNotIn("TC_Unrelated", impacted)

        # If CategoryPage is modified, TC_CreateCategory is impacted
        impacted_cat = test_impact.analyze_impact(mock_graph, ["Keywords/pages/CategoryPage.groovy"])
        self.assertIn("TC_CreateCategory", impacted_cat)
        self.assertNotIn("TC_Unrelated", impacted_cat)


if __name__ == "__main__":
    unittest.main()
