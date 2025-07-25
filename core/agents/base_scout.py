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
from typing import List
from dataclasses import dataclass


# Set up logger for this module
logger = logging.getLogger(__name__)


@dataclass
class JobLead:
    """
    A standardized data structure for a potential job lead.

    This class ensures that no matter the source (Reddit, RSS, etc.), the data
    passed to the QualifierAgent has a consistent structure.
    """
    id: str
    title: str
    body: str
    url: str
    source: str


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
    def find_leads(self) -> List[JobLead]:
        """
        Searches for and returns a list of potential job leads.

        This is the core method for any scout agent. The implementation should
        contain the logic for connecting to the data source, querying for
        relevant information, and returning a list of standardized `JobLead`
        objects.

        Each implementation is responsible for its own error handling and should
        return an empty list if no leads can be found or an unrecoverable
        error occurs.

        Returns:
            List[JobLead]: A list of `JobLead` objects. The QualifierAgent will
                           process this standardized list.
        """
        pass