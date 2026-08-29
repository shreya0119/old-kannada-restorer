import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.dynasty import guess_dynasty

def test_guess_dynasty_no_key():
    # Test error handling when API key is missing
    os.environ.pop("GROQ_API_KEY", None)
    res = guess_dynasty("svasti śrî", [], api_key="")
    assert "error" in res
    assert "GROQ_API_KEY" in res["error"]

if __name__ == "__main__":
    test_guess_dynasty_no_key()
    print("Dynasty unit test passed!")
