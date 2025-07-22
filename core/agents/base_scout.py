# core/agents/base_scout.py
"""
To define the abstract base class for scout agents, establishing a modular
plugin architecture for different job sources.

This module provides the `BaseScout` abstract class, which serves as a contract
for all concrete scout implementations (e.g., RedditScout). Any class that
inherits from `BaseScout` must implement the `find_leads` method, ensuring
that the core application logic can interact with any job source in a
standardized way.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, List

# Set up logger for this module
logger = logging.getLogger(__name__)


class BaseScout(ABC):
    """
    An abstract base class for all scout agents.

    Scout agents are responsible for searching a specific source (like a website,
    API, or forum) for potential job leads. This class defines the common
    interface that all scouts must implement.
    """

    def __init__(self) -> None:
        """
        Initializes the BaseScout.

        This constructor can be extended by subclasses to handle specific
        setup requirements, such as initializing API clients.
        """
        logger.info(f"Initializing {self.__class__.__name__}.")

    @abstractmethod
    def find_leads(self) -> List[Any]:
        """
        Searches for and returns a list of potential job leads.

        This is the core method for any scout agent. The implementation should
        contain the logic for connecting to the data source (e.g., Reddit API),
        querying for relevant information (e.g., posts in 'forhire' subreddits),
        and returning a list of raw lead objects.

        Each implementation is responsible for its own error handling (e.g.,
        network issues, authentication failures) and should return an empty
        list if no leads can be found or an unrecoverable error occurs.

        Returns:
            List[Any]: A list of raw lead objects. The type of objects in the
                       list is specific to the scout's implementation (e.g.,
                       `praw.models.Submission` for a Reddit scout). The
                       QualifierAgent will be responsible for processing these
                       diverse object types.
        """
        pass