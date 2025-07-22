# core/agents/reddit_scout.py
"""
To implement the Reddit scout plugin, using the PRAW library to find potential
job leads from configured subreddits.
"""

import logging
from typing import List, Optional

import praw
import prawcore
from praw.models import Submission

from core.agents.base_scout import BaseScout
import config

# Set up logger for this module
logger = logging.getLogger(__name__)


class RedditScout(BaseScout):
    """
    A scout agent that searches for job leads on Reddit.

    This class uses the PRAW (Python Reddit API Wrapper) library to connect to
    Reddit's API, scan a predefined list of subreddits for new posts, and
    collect them as potential job leads. It handles authentication and error
    handling for the API interactions.
    """

    def __init__(self) -> None:
        """
        Initializes the RedditScout.

        This constructor sets up the PRAW client using credentials from the
        application's configuration. If the required credentials are not
        provided, the PRAW client will not be initialized, and an error will
        be logged.
        """
        super().__init__()
        self.reddit: Optional[praw.Reddit] = None

        # Validate that all necessary Reddit credentials are provided in the config
        if not all(
            [
                config.REDDIT_CLIENT_ID,
                config.REDDIT_CLIENT_SECRET,
                config.REDDIT_USER_AGENT,
            ]
        ):
            logger.critical(
                "Reddit API credentials (CLIENT_ID, CLIENT_SECRET, USER_AGENT) "
                "are not fully configured in the .env file. RedditScout will be disabled."
            )
            return

        try:
            # Initialize the PRAW client
            self.reddit = praw.Reddit(
                client_id=config.REDDIT_CLIENT_ID,
                client_secret=config.REDDIT_CLIENT_SECRET,
                user_agent=config.REDDIT_USER_AGENT,
                read_only=True,  # We only need to read posts
            )
            # The PRAW instance is lazy-loaded, so check if credentials are valid
            # by making a simple, authenticated request.
            self.reddit.user.me()  # This will raise an exception if auth fails
            logger.info("PRAW client initialized and authenticated successfully.")
        except prawcore.exceptions.ResponseException as e:
            logger.critical(
                f"Failed to authenticate with Reddit API. Please check credentials. Error: {e}"
            )
            self.reddit = None
        except Exception as e:
            logger.critical(f"An unexpected error occurred during PRAW initialization: {e}")
            self.reddit = None

    def find_leads(self) -> List[Submission]:
        """
        Searches configured subreddits for new posts (leads).

        Iterates through the list of subreddits defined in `config.SUBREDDITS_TO_SCAN`,
        fetching the latest posts from each. It ensures that duplicate posts
        (e.g., cross-posts) are not included in the final list.

        Returns:
            List[Submission]: A list of `praw.models.Submission` objects, each
                              representing a potential job lead. Returns an empty
                              list if the PRAW client is not initialized or if
                              no leads are found.
        """
        if not self.reddit:
            logger.warning(
                "Reddit client not initialized. Cannot find leads. "
                "Check API credentials."
            )
            return []

        leads: List[Submission] = []
        seen_post_ids = set()
        subreddits = config.SUBREDDITS_TO_SCAN
        limit = config.REDDIT_POST_LIMIT

        logger.info(
            f"Starting Reddit scan across {len(subreddits)} subreddits "
            f"(limit: {limit} posts per subreddit)."
        )

        for subreddit_name in subreddits:
            try:
                logger.debug(f"Scanning subreddit: r/{subreddit_name}")
                subreddit = self.reddit.subreddit(subreddit_name)
                # Fetch the newest submissions from the subreddit
                for submission in subreddit.new(limit=limit):
                    if submission.id not in seen_post_ids:
                        leads.append(submission)
                        seen_post_ids.add(submission.id)

            except prawcore.exceptions.Redirect:
                logger.warning(f"Subreddit r/{subreddit_name} not found or is private.")
            except prawcore.exceptions.PrawcoreException as e:
                logger.error(
                    f"An API error occurred while scanning r/{subreddit_name}: {e}"
                )
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred while processing r/{subreddit_name}: {e}",
                    exc_info=True,
                )

        logger.info(f"Reddit scan complete. Found {len(leads)} unique potential leads.")
        return leads