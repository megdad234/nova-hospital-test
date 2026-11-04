import unittest
from unittest.mock import patch
from commercial_pharmacy.smoke_http import inspect

class HttpSmokeTests(unittest.TestCase):
    def test_unreachable_server_does_not_claim_runtime_verified(self):
        with patch("commercial_pharmacy.smoke_http.urlopen", side_effect=OSError("offline")):
            result = inspect("127.0.0.1", 18763)
        self.assertFalse(result["reachable"])
        self.assertFalse(result["runtime_verified"])

    def test_http_response_is_not_business_workflow_acceptance(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
        with patch("commercial_pharmacy.smoke_http.urlopen", return_value=Response()):
            result = inspect("127.0.0.1", 18763)
        self.assertTrue(result["http_responded"])
        self.assertFalse(result["runtime_verified"])

if __name__ == "__main__":
    unittest.main()
