import os
import sys
import tempfile

# Point the app at a throwaway database and an unreachable model server *before* main is imported.
os.environ["REVOLT_DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="revolt-tests-"), "revolt.db")
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:9"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
