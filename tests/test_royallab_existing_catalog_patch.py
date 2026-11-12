import importlib.util
import pathlib
import unittest

PATH=pathlib.Path(__file__).resolve().parents[1]/".github/ci/royallab_existing_catalog_patch.py"
spec=importlib.util.spec_from_file_location("royallab_existing_catalog_patch",PATH)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ExistingCatalogPatchTests(unittest.TestCase):
    def test_wraps_original_init_without_new_ui(self):
        original="""SCHEMA = 'hospital_lab_tests hospital_lab_parameters'
def init(c):
    c.append('original')
    return 123
"""
        updated=module.patch(original)
        self.assertIn("ROYALLAB_EXISTING_CATALOG_REPLACEMENT",updated)
        self.assertIn("result = _original_nova_lab_init(c, *args, **kwargs)",updated)
        self.assertIn("_replace(c, _library, approved=True)",updated)
        self.assertNotIn("static/app.js",updated)
        compile(updated,"lab.py","exec")
        with self.assertRaises(ValueError):
            module.patch(updated)
    def test_rejects_unrecognized_source(self):
        with self.assertRaises(ValueError):
            module.patch("def init(db): pass")

if __name__=="__main__":
    unittest.main()
