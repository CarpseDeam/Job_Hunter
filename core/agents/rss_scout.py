# core/agents/rss_scout.py
"""
To implement an RSS scout plugin, using the feedparser library to find
potential job leads from configured RSS feeds.
"""

import logging
from typing import List
from urllib.parse import urlparse

import feedparser

from core.agents.base_scout import BaseScout, JobLead
import config

logger = logging.getLogger(__name__)


class RSSScout(BaseScout):
    """
    A scout agent that searches for job leads from RSS feeds.

    This class uses the `feedparser` library to connect to various job board
    RSS feeds, parse their content, and collect them as potential job leads.
    """

    def __init__(self) -> None:
        """Initializes the RSSScout."""
        super().__init__()
        # No special client initialization needed for feedparser

    def find_leads(self) -> List[JobLead]:
        """
        Parses configured RSS feeds for new posts (leads).

        Iterates through the list of feed URLs defined in `config.RSS_FEEDS_TO_SCAN`,
        fetching and parsing the content of each.

        Returns:
            List[JobLead]: A list of `JobLead` objects, each representing a
                           potential job lead. Returns an empty list if no
                           feeds are configured or no leads are found.
        """
        feeds = config.RSS_FEEDS_TO_SCAN
        if not feeds:
            logger.info("No RSS feeds configured to scan.")
            return []

        leads: List[JobLead] = []
        seen_lead_urls = set()

        logger.info(f"Starting RSS scan across {len(feeds)} feeds.")

        for feed_url in feeds:
            try:
                logger.debug(f"Parsing feed: {feed_url}")
                parsed_feed = feedparser.parse(feed_url)

                # feedparser sets a 'bozo' flag if the feed is malformed.
                if parsed_feed.bozo:
                    logger.warning(
                        f"Feed at {feed_url} may be malformed. "
                        f"Error: {parsed_feed.bozo_exception}"
                    )
                    # We can still try to process it, as some data might be valid.

                source_name = urlparse(feed_url).hostname or feed_url

                for entry in parsed_feed.entries:
                    # Use link as a unique identifier
                    if entry.link not in seen_lead_urls:
                        # RSS feeds can have content in 'summary' or 'content' fields
                        body = entry.get("summary", "")
                        if not body and entry.get("content"):
                             # The content can be a list of dictionaries
                             body = entry.content[0].get("value", "")

                        lead = JobLead(
                            id=entry.get("id", entry.link),
                            title=entry.title,
                            body=body,
                            url=entry.link,
                            source=source_name,
                        )
                        leads.append(lead)
                        seen_lead_urls.add(entry.link)

            except Exception as e:
                logger.error(
                    f"An unexpected error occurred while processing feed {feed_url}: {e}",
                    exc_info=True,
                )

        logger.info(f"RSS scan complete. Found {len(leads)} unique potential leads.")
        return leads