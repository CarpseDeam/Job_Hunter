# config.py
"""
To centralize application configurations such as API keys, subreddit lists,
resume paths, and AI scoring keywords.

This module loads sensitive information from a .env file and defines static
configuration values used throughout the application. It is intended to be the
single source of truth for all configurable parameters.
"""

import logging
import os
from typing import List, Optional

from dotenv import load_dotenv

# Set up logger for this module
logger = logging.getLogger(__name__)

# Load environment variables from a .env file at the project root
# This allows for secure management of API keys and other secrets.
load_dotenv()
logger.info(".env file loaded (if present).")

# --- API Credentials ---
# These are loaded from environment variables for security.
# A .env.example file should guide the user in setting these up.

OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
REDDIT_CLIENT_ID: Optional[str] = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET: Optional[str] = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT: Optional[str] = os.getenv("REDDIT_USER_AGENT")

# --- Validation for Critical Configurations ---
# The application cannot function without these core credentials.
_CRITICAL_CONFIGS = {
    "OpenAI API Key": OPENAI_API_KEY,
    "Reddit Client ID": REDDIT_CLIENT_ID,
    "Reddit Client Secret": REDDIT_CLIENT_SECRET,
    "Reddit User Agent": REDDIT_USER_AGENT,
}

for name, value in _CRITICAL_CONFIGS.items():
    if not value:
        logger.critical(
            f"Configuration Error: '{name}' is not set. "
            "Please check your .env file or environment variables."
        )
        # In a real application, you might want to raise an exception
        # or exit here to prevent it from running in a broken state.
        # For now, we just log a critical error.

# --- Reddit Scout Configuration ---

# A list of subreddits to scan for job postings.
# Add or remove subreddit names as needed.
SUBREDDITS_TO_SCAN: List[str] = [
    "forhire",
    "jobbit",
    "hiring",
    "PythonJobs",
    "remotejs",
    "freelance_for_hire",
]

# The number of recent posts to fetch from each subreddit per scan.
REDDIT_POST_LIMIT: int = 50

# --- AI Qualifier Agent Configuration ---

# A list of keywords the AI should prioritize when analyzing job descriptions.
# This helps focus the AI's analysis on roles most relevant to the user's skills.
AI_QUALIFICATION_KEYWORDS: List[str] = [
    "Python",
    "Software Engineer",
    "Developer",
    "Backend",
    "Full Stack",
    "Remote",
    "Contract",
    "Freelance",
    "PySide6",
    "PyQt",
    "Qt",
    "Desktop Application",
    "API Integration",
    "LLM",
    "AI",
]

# The path to the user's resume file.
# The content of this file will be used by the AI to tailor cover letters.
# Set to None if no resume is available.
RESUME_FILE_PATH: Optional[str] = "path/to/your/resume.md"
# Note: The user will be able to change this in the GUI. This is a default.

# --- Application Behavior ---

# The maximum number of concurrent threads to use for scraping/analysis tasks.
MAX_WORKER_THREADS: int = 4

# The delay in seconds between automatic refresh cycles.
# Set to None to disable automatic refresh.
AUTO_REFRESH_INTERVAL_SECONDS: Optional[int] = 60 * 15  # 15 minutes

logger.info("Configuration constants defined.")
if RESUME_FILE_PATH and not os.path.exists(RESUME_FILE_PATH):
    logger.warning(
        f"Default resume file not found at: {RESUME_FILE_PATH}. "
        "Please update the path in the GUI or config.py."
    )