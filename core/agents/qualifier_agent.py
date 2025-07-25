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
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    # PRAW models are no longer used here, but we need JobLead
except ImportError as e:
    # This will be caught at a higher level, but logging is good practice.
    logging.critical(f"Missing critical dependency: {e}. The QualifierAgent may not function.")
    # Define dummy classes for type hinting if imports fail
    genai = None # To prevent further errors

# Project-specific imports
import config
from core.agents.base_scout import JobLead


logger = logging.getLogger(__name__)


class QualifierAgent:
    """
    Analyzes job leads using an LLM to determine relevance and generate content.

    This agent takes standardized JobLead objects, compares them against
    a user's resume and keywords, and uses the Google Gemini API to generate a
    relevance score, a justification, and a draft cover letter.
    """

    def __init__(self) -> None:
        """
        Initializes the QualifierAgent and the Google Gemini client.

        It checks for the Google API key in the configuration and sets up the
        generative model. If the key is not found, the agent will be in a disabled state.
        """
        self.model: Optional["GenerativeModel"] = None
        if not config.GOOGLE_API_KEY:
            logger.critical(
                "GOOGLE_API_KEY not found in config/.env. "
                "QualifierAgent will be non-functional."
            )
            return

        try:
            genai.configure(api_key=config.GOOGLE_API_KEY)

            system_instruction = (
                "You are an expert career assistant. Your task is to analyze a job posting "
                "based on a user's resume and skills. You MUST respond with a single, "
                "valid JSON object and nothing else. The JSON object must have the "
                "following structure: {\"score\": <integer>, \"justification\": \"<string>\", "
                "\"cover_letter_draft\": \"<string>\", \"extracted_company_name\": "
                "\"<string or null>\", \"extracted_contact_info\": \"<string or null>\"}."
            )

            # Using a fast and capable model, with system instructions for consistent output
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash-latest",
                system_instruction=system_instruction
            )
            # A simple test to ensure the client is configured correctly
            # This is a lightweight call that doesn't consume credits.
            genai.list_models()
            logger.info("Google Gemini client initialized successfully.")
        except google_exceptions.PermissionDenied as e:
            logger.critical(
                f"Google API authentication failed. Please check your API key. Error: {e}"
            )
            self.model = None
        except Exception as e:
            logger.critical(
                f"Failed to initialize Google Gemini client. Error: {e}", exc_info=True
            )
            self.model = None

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
        self, lead: JobLead, resume_content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Analyzes a single job lead, scores it, and generates a cover letter.

        This method takes a standardized `JobLead` object, sends its content
        to the Google Gemini API for analysis, and parses the structured JSON
        response.

        Args:
            lead (JobLead): The standardized lead object from any scout.
            resume_content (str): The text content of the user's resume.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the analyzed data,
                                      including score, justification, cover letter,
                                      and original lead info. Returns None if
                                      analysis fails, the lead is invalid, or
                                      the agent is not initialized.
        """
        if not self.model:
            logger.warning("QualifierAgent not initialized. Skipping analysis.")
            return None

        # If the post body is empty, it's unlikely to be a valid job post.
        if not lead.body.strip():
            logger.info(f"Lead '{lead.title}' has no body text. Skipping analysis.")
            return None

        logger.info(f"Analyzing lead: {lead.title} (from {lead.source})")

        prompt = self._create_prompt(
            lead.title, lead.body, resume_content, config.AI_QUALIFICATION_KEYWORDS
        )

        response_content = None # Initialize for the except block
        try:
            # Configure the model for JSON output and a balanced temperature
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.5
            )

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
            )

            response_content = response.text
            if not response_content:
                # Check for safety ratings or other reasons for an empty response
                try:
                    # Accessing parts can raise an exception if the list is empty
                    if not response.parts:
                        logger.error(f"Gemini response was empty for '{lead.title}'. Finish reason: {response.prompt_feedback}")
                    else:
                        logger.error(f"Gemini response was empty for '{lead.title}'. Candidates: {response.candidates}")
                except (ValueError, IndexError):
                     logger.error(f"Gemini response was empty and content could not be inspected for '{lead.title}'.")
                return None

            llm_data = json.loads(response_content)

            # Basic validation of the parsed data
            required_keys = ["score", "justification", "cover_letter_draft"]
            if not all(key in llm_data for key in required_keys):
                logger.error(f"LLM response missing required keys: {response_content}")
                return None

            # Assemble the final result dictionary
            analyzed_job = {
                "id": lead.id,
                "title": lead.title,
                "url": lead.url,
                "source": lead.source,
                "score": llm_data.get("score", 0),
                "justification": llm_data.get("justification", "N/A"),
                "cover_letter": llm_data.get("cover_letter_draft", ""),
                "company_name": llm_data.get("extracted_company_name"),
                "contact_info": llm_data.get("extracted_contact_info"),
            }
            logger.info(f"Successfully analyzed and qualified job: '{lead.title}'")
            return analyzed_job

        except google_exceptions.GoogleAPICallError as e:
            logger.error(f"Google API error while analyzing '{lead.title}': {e}", exc_info=True)
            return None
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse JSON response from LLM for '{lead.title}': {e}\n"
                f"Raw response: {response_content}",
                exc_info=True
            )
            return None
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during qualification of '{lead.title}': {e}",
                exc_info=True,
            )
            return None