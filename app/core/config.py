from dotenv import load_dotenv
import os

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

### LOAD THE NECESSARY ENV VARS 
GOOGLE_API_KEY = require_env("GOOGLE_API_KEY")
GROQ_API_KEY = require_env("GROQ_API_KEY")
OLLAMA_MODEL = require_env("OLLAMA_MODEL")
GOOGLE_MODEL = require_env("GOOGLE_MODEL")
GROQ_MODEL = require_env("GROQ_MODEL")
GROQ_OCR_MODEL = require_env("GROQ_OCR_MODEL")

