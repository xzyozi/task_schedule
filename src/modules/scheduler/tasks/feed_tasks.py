import json
from typing import Literal

import feedparser
import requests

from util import logger_util

from ..task_utils import task

logger = logger_util.get_logger(__name__)

FormattingStyle = Literal["summary", "full_content", "json_summary", "json_full"]


@task(enabled=True, name="Read RSS Feed", description="Fetches and parses an RSS or Atom feed from a URL.")
def read_rss_feed(url: str, formatting_style: FormattingStyle = "summary", max_entries: int = 10) -> str:
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
        # Convert max_entries to an integer
        try:
            num_max_entries = int(max_entries)
        except (ValueError, TypeError):
            logger.warning(f"Invalid value for max_entries: '{max_entries}'. Using default value of 10.")
            num_max_entries = 10

        # Use requests to fetch the content, which can help with encoding issues
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Pass the content to feedparser. It's often better at detecting encoding from raw bytes.
        feed = feedparser.parse(response.content)

        if feed.bozo:
            bozo_exception = feed.get("bozo_exception", "Unknown parsing error")
            # Downgrade log level for common, non-fatal encoding errors
            if "document declared as" in str(bozo_exception):
                logger.info(f"Handled a non-fatal encoding issue in feed from {url}. Reason: {bozo_exception}")
            else:
                logger.warning(f"Feed at {url} may not be well-formed. Reason: {bozo_exception}")

        entries = feed.entries[:num_max_entries]

        if not entries:
            logger.warning(f"No entries found in feed: {url}")
            return "No entries found in feed."

        logger.info(f"Found {len(entries)} entries in feed.")

        if formatting_style == "summary":
            output_lines = [f"Feed: {feed.feed.get('title', 'Untitled')}\n"]
            for entry in entries:
                output_lines.append(f"- {entry.get('title', 'No Title')}")
                output_lines.append(f"  Link: {entry.get('link', 'No Link')}")
            return "\n".join(output_lines)

        elif formatting_style == "full_content":
            output_lines = [f"Feed: {feed.feed.get('title', 'Untitled')}\n"]
            for entry in entries:
                output_lines.append("---")
                output_lines.append(f"Title: {entry.get('title', 'No Title')}")
                output_lines.append(f"Link: {entry.get('link', 'No Link')}")
                output_lines.append(f"Published: {entry.get('published', 'N/A')}")
                output_lines.append(f"Summary: {entry.get('summary', 'N/A')}")
            return "\n".join(output_lines)

        elif formatting_style == "json_summary":
            summary_list = []
            for entry in entries:
                summary_list.append(
                    {"title": entry.get("title"), "link": entry.get("link"), "published": entry.get("published")}
                )
            return json.dumps(summary_list, indent=2)

        elif formatting_style == "json_full":
            # feedparser entry objects are already dict-like
            return json.dumps(entries, indent=2)

        else:
            raise ValueError(f"Unknown formatting_style: {formatting_style}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch URL {url}: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Failed to process RSS feed from {url}: {e}", exc_info=True)
        # Re-raise the exception to make the job fail
        raise
