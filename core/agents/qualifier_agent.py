# core/agents/qualifier_agent.py
"""
To implement the LLM-based agent responsible for analyzing job descriptions,
assigning relevance scores, and generating draft cover letters.
"""

import logging
import json
from typing import Dict, Optional, Any, List

# External dependencies
try:
    import openai
    from openai import OpenAI
    # PRAW models are only used for type hinting, not direct functionality here.
    from praw.models import Submission
except ImportError as e:
    # This will be caught at a higher level, but logging is good practice.
    logging.critical(f"Missing critical dependency: {e}. The QualifierAgent may not function.")
    # Define dummy classes for type hinting if imports fail
    class Submission: pass
    class OpenAI: pass

# Project-specific imports
import config

logger = logging.getLogger(__name__)


class QualifierAgent:
    """
    Analyzes job leads using an LLM to determine relevance and generate content.

    This agent takes raw job leads (e.g., Reddit posts), compares them against
    a user's resume and keywords, and uses the OpenAI API to generate a
    relevance score, a justification, and a draft cover letter.
    """

    def __init__(self) -> None:
        """
        Initializes the QualifierAgent and the OpenAI client.

        It checks for the OpenAI API key in the configuration and sets up the
        client. If the key is not found, the agent will be in a disabled state.
        """
        self.client: Optional[OpenAI] = None
        if not config.OPENAI_API_KEY:
            logger.critical(
                "OPENAI_API_KEY not found in config/.env. "
                "QualifierAgent will be non-functional."
            )
            return

        try:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            # A simple test to ensure the client is configured correctly
            # This is a lightweight call that doesn't consume many tokens.
            self.client.models.list()
            logger.info("OpenAI client initialized successfully.")
        except openai.AuthenticationError as e:
            logger.critical(
                f"OpenAI authentication failed. Please check your API key. Error: {e}"
            )
            self.client = None
        except Exception as e:
            logger.critical(
                f"Failed to initialize OpenAI client. Error: {e}", exc_info=True
            )
            self.client = None

    def _create_prompt(
        self, job_title: str, job_body: str, resume_content: str, keywords: List[str]
    ) -> str:
        """
        Constructs the detailed prompt for the LLM.

        Args:
            job_title (str): The title of the job posting.
            job_body (str): The body text of the job posting.
            resume_content (str): The user's resume text.
            keywords (List[str]): A list of user-defined keywords.

        Returns:
            str: The fully formatted prompt to be sent to the LLM.
        """
        keywords_str = ", ".join(keywords)

        # The user's resume might be empty or not provided.
        resume_section = "No resume provided."
        if resume_content and resume_content.strip():
            resume_section = f"Here is my resume for context:\n\n---\n{resume_content}\n---"

        prompt = f"""
Analyze the following job posting based on my skills and resume.

**My Key Skills/Interests:**
{keywords_str}

**My Resume/CV:**
{resume_section}

**Job Posting to Analyze:**
Title: {job_title}
Body:
{job_body}

---
**Your Task:**
Based on all the information, evaluate the job posting's relevance to my profile.
Provide a relevance score from 0 (not relevant) to 100 (perfect match).
Write a brief justification for your score.
Draft a concise, professional, and tailored cover letter.
Extract the company name and any contact information if available.

Return a single, valid JSON object with the following exact structure:
{{
  "score": <integer, 0-100>,
  "justification": "<string, your reasoning for the score>",
  "cover_letter_draft": "<string, the drafted cover letter text>",
  "extracted_company_name": "<string or null, the company name if found>",
  "extracted_contact_info": "<string or null, email or contact person if found>"
}}
"""
        return prompt.strip()

    def analyze_and_qualify(
        self, lead: Any, resume_content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Analyzes a single job lead, scores it, and generates a cover letter.

        This method takes a lead object (currently supporting PRAW Submissions),
        sends its content to the OpenAI API for analysis, and parses the
        structured JSON response.

        Args:
            lead (Any): The raw lead object. Expected to be a `praw.models.Submission`.
            resume_content (str): The text content of the user's resume.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the analyzed data,
                                      including score, justification, cover letter,
                                      and original lead info. Returns None if
                                      analysis fails, the lead is invalid, or
                                      the agent is not initialized.
        """
        if not self.client:
            logger.warning("QualifierAgent not initialized. Skipping analysis.")
            return None

        # Ensure the lead is a Reddit submission, as that's what we currently support.
        if not isinstance(lead, Submission):
            logger.warning(
                f"Unsupported lead type: {type(lead).__name__}. Skipping analysis."
            )
            return None

        job_title = lead.title
        job_body = lead.selftext
        job_id = lead.id
        job_url = f"https://www.reddit.com{lead.permalink}"

        # If the post body is empty, it's unlikely to be a valid job post.
        if not job_body.strip():
            logger.info(f"Lead '{job_title}' has no body text. Skipping analysis.")
            return None

        logger.info(f"Analyzing lead: {job_title}")

        prompt = self._create_prompt(
            job_title, job_body, resume_content, config.AI_QUALIFICATION_KEYWORDS
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # A capable and cost-effective model
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert career assistant. Your task is to analyze a job posting "
                            "based on a user's resume and skills. You MUST respond with a single, "
                            "valid JSON object and nothing else. The JSON object must have the "
                            "following structure: {\"score\": <integer>, \"justification\": \"<string>\", "
                            "\"cover_letter_draft\": \"<string>\", \"extracted_company_name\": "
                            "\"<string or null>\", \"extracted_contact_info\": \"<string or null>\"}."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.5,  # A bit of creativity for the cover letter but still factual
            )

            response_content = response.choices[0].message.content
            if not response_content:
                logger.error("OpenAI response was empty.")
                return None

            llm_data = json.loads(response_content)

            # Basic validation of the parsed data
            required_keys = ["score", "justification", "cover_letter_draft"]
            if not all(key in llm_data for key in required_keys):
                logger.error(f"LLM response missing required keys: {response_content}")
                return None

            # Assemble the final result dictionary
            analyzed_job = {
                "id": job_id,
                "title": job_title,
                "url": job_url,
                "source": "Reddit",
                "score": llm_data.get("score", 0),
                "justification": llm_data.get("justification", "N/A"),
                "cover_letter": llm_data.get("cover_letter_draft", ""),
                "company_name": llm_data.get("extracted_company_name"),
                "contact_info": llm_data.get("extracted_contact_info"),
            }
            logger.info(f"Successfully analyzed and qualified job: '{job_title}'")
            return analyzed_job

        except openai.APIError as e:
            logger.error(f"OpenAI API error while analyzing '{job_title}': {e}", exc_info=True)
            return None
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse JSON response from LLM for '{job_title}': {e}\n"
                f"Raw response: {response_content}",
                exc_info=True
            )
            return None
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during qualification of '{job_title}': {e}",
                exc_info=True,
            )
            return None