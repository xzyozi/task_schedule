import feedparser
import json
from typing import Literal, List
from ..task_utils import task
from util import logger_util

logger = logger_util.get_logger(__name__)

FormattingStyle = Literal['summary', 'full_content', 'json_summary', 'json_full']

@task(enabled=True, name="Read RSS Feed", description="Fetches and parses an RSS or Atom feed from a URL.")
def read_rss_feed(
    url: str,
    formatting_style: FormattingStyle = 'summary',
    max_entries: int = 10
) -> str:
    """
    Reads an RSS feed and returns the content in a specified format.

    Args:
        url: The URL of the RSS or Atom feed.
        formatting_style: The desired output format.
            - 'summary': A plain text list of entry titles and links.
            - 'full_content': A plain text list with titles, links, and summaries.
            - 'json_summary': A JSON string with titles, links, and published dates.
            - 'json_full': A JSON string with all available entry data.
        max_entries: The maximum number of feed entries to process.

    Returns:
        A string containing the formatted feed content.
    """
    logger.info(f"Fetching RSS feed from URL: {url}")
    
    if not url:
        raise ValueError("URL parameter cannot be empty.")

    try:
        feed = feedparser.parse(url)

        if feed.bozo:
            bozo_exception = feed.get('bozo_exception', 'Unknown parsing error')
            logger.warning(f"Feed at {url} is not well-formed. Reason: {bozo_exception}")
            # Continue processing, as some data might still be available

        entries = feed.entries[:max_entries]

        if not entries:
            logger.warning(f"No entries found in feed: {url}")
            return "No entries found in feed."

        logger.info(f"Found {len(entries)} entries in feed.")

        if formatting_style == 'summary':
            output_lines = [f"Feed: {feed.feed.get('title', 'Untitled')}\n"]
            for entry in entries:
                output_lines.append(f"- {entry.get('title', 'No Title')}")
                output_lines.append(f"  Link: {entry.get('link', 'No Link')}")
            return "\n".join(output_lines)

        elif formatting_style == 'full_content':
            output_lines = [f"Feed: {feed.feed.get('title', 'Untitled')}\n"]
            for entry in entries:
                output_lines.append(f"---")
                output_lines.append(f"Title: {entry.get('title', 'No Title')}")
                output_lines.append(f"Link: {entry.get('link', 'No Link')}")
                output_lines.append(f"Published: {entry.get('published', 'N/A')}")
                output_lines.append(f"Summary: {entry.get('summary', 'N/A')}")
            return "\n".join(output_lines)
        
        elif formatting_style == 'json_summary':
            summary_list = []
            for entry in entries:
                summary_list.append({
                    "title": entry.get('title'),
                    "link": entry.get('link'),
                    "published": entry.get('published')
                })
            return json.dumps(summary_list, indent=2)

        elif formatting_style == 'json_full':
            # feedparser entry objects are already dict-like
            return json.dumps(entries, indent=2)
            
        else:
            raise ValueError(f"Unknown formatting_style: {formatting_style}")

    except Exception as e:
        logger.error(f"Failed to fetch or parse RSS feed from {url}: {e}", exc_info=True)
        # Re-raise the exception to make the job fail
        raise
