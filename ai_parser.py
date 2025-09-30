#!/usr/bin/env python3
"""
AI-Driven Multi-Site Job Parser

Uses Anthropic API with Playwright automation to:
1. Discovery Mode: Explore job pages and document scraping strategy
2. Generation Mode: Convert discovery logs into standalone Playwright scripts
3. Supports: LinkedIn, Indeed, Glassdoor (extensible)
"""

import argparse
import ast
import asyncio
from datetime import datetime
from enum import Enum
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from anthropic import Anthropic
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field

# Import URL utilities for robust URL handling
try:
    from url_utils import normalize_job_url as normalize_url_external
    URL_UTILS_AVAILABLE = True
except ImportError:
    URL_UTILS_AVAILABLE = False
    logging.warning("url_utils module not found - URL normalization disabled")

# Load environment variables
load_dotenv()


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class Config:
    """Application configuration"""
    anthropic_api_key: str
    model_name: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 8192
    browser_timeout: int = 60000
    selector_timeout: int = 15000
    log_level: str = "INFO"
    # Phase 12.5: Validation configuration
    enable_validation: bool = True
    max_validation_attempts: int = 3
    enable_multi_job_testing: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        return cls(
            anthropic_api_key=api_key,
            model_name=os.getenv("MODEL_NAME", cls.model_name),
            max_tokens=int(os.getenv("MAX_TOKENS", cls.max_tokens)),
            log_level=os.getenv("LOG_LEVEL", cls.log_level)
        )


# ============================================================================
# Site Detection & Configuration (Version 1.1)
# ============================================================================

class JobSite(Enum):
    """Supported job sites"""
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"


@dataclass
class SiteConfig:
    """Configuration for a specific job site"""
    name: str
    display_name: str
    url_pattern: str  # Regex pattern to detect site
    job_id_pattern: str  # Regex pattern to extract job ID
    description: str = ""


# Site configurations
SITE_CONFIGS = {
    JobSite.LINKEDIN: SiteConfig(
        name="linkedin",
        display_name="LinkedIn",
        url_pattern=r"linkedin\.com/jobs",
        job_id_pattern=r"/jobs/view/(\d+)",
        description="Path-based job ID: /jobs/view/{id}"
    ),
    JobSite.INDEED: SiteConfig(
        name="indeed",
        display_name="Indeed",
        url_pattern=r"indeed\.com/viewjob",
        job_id_pattern=r"[?&]jk=([a-f0-9]+)",
        description="Query param job ID: ?jk={id}"
    ),
    JobSite.GLASSDOOR: SiteConfig(
        name="glassdoor",
        display_name="Glassdoor",
        url_pattern=r"glassdoor\.com/job-listing",
        job_id_pattern=r"-JV_IC(\d+)",
        description="Mixed pattern job ID: -JV_IC{id}"
    )
}


def detect_job_site(url: str) -> JobSite:
    """
    Auto-detect job site from URL

    Args:
        url: Job posting URL

    Returns:
        JobSite enum value

    Raises:
        ValueError: If URL doesn't match any supported site
    """
    for site, config in SITE_CONFIGS.items():
        if re.search(config.url_pattern, url, re.IGNORECASE):
            logging.debug(f"Detected site: {config.display_name}")
            return site

    raise ValueError(
        f"Unsupported job site: {url}\n"
        f"Supported sites: {', '.join(c.display_name for c in SITE_CONFIGS.values())}"
    )


def get_site_config(site: JobSite) -> SiteConfig:
    """Get configuration for a specific site"""
    return SITE_CONFIGS[site]


def validate_site_url(url: str, expected_site: JobSite) -> bool:
    """
    Validate that URL matches expected site

    Args:
        url: Job posting URL
        expected_site: Expected JobSite enum value

    Returns:
        True if URL matches expected site
    """
    try:
        detected = detect_job_site(url)
        return detected == expected_site
    except ValueError:
        return False


# ============================================================================
# Utility Functions (from original scraper, enhanced for multi-site)
# ============================================================================

def sanitize_filename(text: str) -> str:
    """
    Convert text to a valid filename by removing/replacing special characters
    """
    text = re.sub(r'[<>:"/\\|?*]', '-', text)
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    return text[:100]


def extract_job_id(url: str, site: Optional[JobSite] = None) -> Optional[str]:
    """
    Extract job ID from job posting URL (multi-site support)

    Args:
        url: Job posting URL
        site: Optional JobSite to use specific pattern (auto-detected if None)

    Returns:
        Job ID string or None if not found

    Examples:
        LinkedIn: https://www.linkedin.com/jobs/view/4300362234 -> 4300362234
        Indeed: https://www.indeed.com/viewjob?jk=d7a8476f98b7ec44 -> d7a8476f98b7ec44
        Glassdoor: https://www.glassdoor.com/job-listing/...-JV_IC1234 -> 1234
    """
    # Auto-detect site if not provided
    if site is None:
        try:
            site = detect_job_site(url)
        except ValueError as e:
            logging.error(f"Could not detect site from URL: {url}")
            return None

    # Get site-specific pattern
    config = get_site_config(site)
    match = re.search(config.job_id_pattern, url)

    if match:
        job_id = match.group(1)
        logging.debug(f"Extracted job ID: {job_id} from {config.display_name} URL")
        return job_id
    else:
        logging.error(
            f"Could not extract {config.display_name} job ID from URL: {url}\n"
            f"Expected format: {config.description}"
        )
        return None


def save_discovery_log(
    site: JobSite,
    log_data: Dict[str, Any],
    output_dir: str = "discovery_logs"
) -> Path:
    """
    Save discovery log to JSON file with site-specific, timestamped naming

    Args:
        site: JobSite enum value
        log_data: Discovery log data to save
        output_dir: Output directory path

    Returns:
        Path to saved file

    Naming format: {site}_discovery_{iso_timestamp}.json
    Example: linkedin_discovery_2025-09-29T12-00-00.json
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Generate timestamp (ISO format with safe filename chars)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

    # Add metadata
    log_data["site"] = site.value
    log_data["timestamp"] = datetime.now().isoformat()
    log_data["script_version"] = "1.1"

    # Create filename
    filepath = output_path / f"{site.value}_discovery_{timestamp}.json"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    logging.info(f"Discovery log saved: {filepath}")
    return filepath


def load_discovery_log(filepath: str) -> Dict[str, Any]:
    """Load discovery log from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_latest_discovery_log(site: JobSite, log_dir: str = "discovery_logs") -> Optional[Path]:
    """
    Find the most recent discovery log for a specific site

    Args:
        site: JobSite enum value
        log_dir: Directory containing discovery logs

    Returns:
        Path to latest log file or None if no logs found
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return None

    # Find all logs for this site
    pattern = f"{site.value}_discovery_*.json"
    logs = sorted(log_path.glob(pattern), reverse=True)

    return logs[0] if logs else None


# ============================================================================
# Code Execution Tool (Phase 3)
# ============================================================================

# Safe modules that can be imported
ALLOWED_IMPORTS = {
    'playwright', 'playwright.sync_api', 'playwright.async_api',
    're', 'pathlib', 'time', 'sys', 'json', 'typing',
    'dataclasses', 'datetime', 'collections'
}

# Dangerous operations to block
DANGEROUS_PATTERNS = [
    r'\bos\.system\b',
    r'\bsubprocess\b',
    r'\beval\b',
    r'\bexec\b',
    r'\b__import__\b',
    r'\bopen\([^)]*[\'"]w[\'"]',  # Writing files (except our specific case)
    r'\brmtree\b',
    r'\bunlink\b',
    r'\bremove\b'
]


def validate_python_syntax(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Python code syntax using AST parsing

    Returns:
        (is_valid, error_message)
    """
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def check_code_safety(code: str) -> Tuple[bool, Optional[str]]:
    """
    Check if code contains dangerous operations

    Returns:
        (is_safe, warning_message)
    """
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, code):
            return False, f"Dangerous operation detected: {pattern}"

    return True, None


def validate_imports(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that only safe imports are used

    Returns:
        (is_valid, error_message)
    """
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module not in ALLOWED_IMPORTS and module not in {'os', 'pathlib'}:
                        # Allow os and pathlib for basic operations
                        pass
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module not in ALLOWED_IMPORTS and module not in {'os', 'pathlib'}:
                        pass
        return True, None
    except Exception as e:
        return False, str(e)


def execute_python_code(code: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Execute Python code in a subprocess with timeout and safety checks

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds

    Returns:
        Dict with keys: success, stdout, stderr, error
    """
    # Validate syntax
    is_valid, error = validate_python_syntax(code)
    if not is_valid:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Syntax validation failed: {error}",
            "error": error
        }

    # Check safety (warning only, not blocking for generated scripts)
    is_safe, warning = check_code_safety(code)
    if not is_safe:
        logging.warning(f"Code safety warning: {warning}")

    try:
        # Execute in subprocess with timeout
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )

        # Limit output size
        max_output = 10240  # 10KB
        stdout = result.stdout[:max_output] if result.stdout else ""
        stderr = result.stderr[:max_output] if result.stderr else ""

        if len(result.stdout) > max_output:
            stdout += "\n... (output truncated)"
        if len(result.stderr) > max_output:
            stderr += "\n... (output truncated)"

        return {
            "success": result.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "error": None
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution timeout after {timeout} seconds",
            "error": "timeout"
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "error": str(e)
        }


def validate_script_structure(code: str) -> Tuple[bool, List[str]]:
    """
    Validate that generated script has required functions and structure

    Returns:
        (is_valid, list_of_issues)
    """
    issues = []

    # Required function names
    required_functions = {
        'sanitize_filename',
        'extract_job_id',
        'scrape_linkedin_job',
        'format_job_description',
        'main'
    }

    try:
        tree = ast.parse(code)

        # Extract function names
        found_functions = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                found_functions.add(node.name)

        # Check for missing functions
        missing = required_functions - found_functions
        if missing:
            issues.append(f"Missing required functions: {', '.join(missing)}")

        # Check for AI/MCP imports (should not be present)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if 'anthropic' in alias.name.lower() or 'mcp' in alias.name.lower():
                        issues.append(f"Generated script should not import AI libraries: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and ('anthropic' in node.module.lower() or 'mcp' in node.module.lower()):
                    issues.append(f"Generated script should not import AI libraries: {node.module}")

        return len(issues) == 0, issues

    except SyntaxError as e:
        issues.append(f"Syntax error: {e.msg} at line {e.lineno}")
        return False, issues


# ============================================================================
# Live Strategy Testing (Phase 12.1)
# ============================================================================

async def test_extraction_strategies(page, field_name: str) -> List[Dict[str, Any]]:
    """
    Test multiple extraction strategies for a field and return what works.

    Args:
        page: Playwright page object
        field_name: Field to extract (title, company, location, description)

    Returns:
        List of strategy results, sorted by confidence (high → low)

    Example result:
    [
        {
            "strategy": "javascript_evaluation",
            "code": "document.querySelector('h1').textContent",
            "success": True,
            "sample": "Engineering Manager, API Product",
            "length": 57,
            "confidence": "high"
        }
    ]
    """
    results = []

    # Strategy 1: JavaScript evaluation (PREFERRED - like original scraper)
    js_strategies = {
        "title": "document.querySelector('h1')?.textContent?.trim()",
        "company": "document.querySelector('a[data-tracking-control-name*=\"topcard\"]')?.textContent?.trim()",
        "location": "document.querySelector('.topcard__flavor--bullet')?.parentElement?.textContent?.match(/·\\s*([^·]+)/)?.[1]?.trim()",
        "description": "document.querySelector('div.show-more-less-html__markup')?.innerText || document.querySelector('div.show-more-less-html__markup')?.textContent"
    }

    if field_name in js_strategies:
        try:
            result = await page.evaluate(f"() => {{ return {js_strategies[field_name]}; }}")
            if result and len(str(result).strip()) > 10:
                results.append({
                    "strategy": "javascript_evaluation",
                    "code": js_strategies[field_name],
                    "success": True,
                    "sample": str(result)[:200],
                    "length": len(str(result)),
                    "confidence": "high" if len(str(result)) > 100 else "medium"
                })
                logging.debug(f"✓ JS evaluation success for {field_name}: {len(str(result))} chars")
        except Exception as e:
            logging.debug(f"JS evaluation failed for {field_name}: {e}")

    # Strategy 2: Common CSS selectors (FALLBACK)
    css_selectors = {
        "title": ["h1", "h1.title", "[data-test-id='job-title']", ".job-title"],
        "company": ["a[data-tracking-control-name*='topcard']", ".company-name", "[data-company-name]"],
        "location": [".topcard__flavor", ".location", "[data-job-location]"],
        "description": [".description", ".job-description", "[class*='description']", ".show-more-less-html__markup"]
    }

    for selector in css_selectors.get(field_name, []):
        try:
            element = await page.wait_for_selector(selector, timeout=3000)
            text = await element.text_content()
            if text and len(text.strip()) > 10:
                results.append({
                    "strategy": "css_selector",
                    "selector": selector,
                    "success": True,
                    "sample": text[:200],
                    "length": len(text),
                    "confidence": "medium" if len(text) > 50 else "low"
                })
                logging.debug(f"✓ CSS selector success for {field_name} ({selector}): {len(text)} chars")
        except:
            continue

    # Sort by confidence: high → medium → low
    confidence_order = {"high": 3, "medium": 2, "low": 1}
    results.sort(key=lambda x: confidence_order.get(x.get("confidence", "low"), 0), reverse=True)

    return results


async def test_show_more_button(page) -> Dict[str, Any]:
    """
    Test if "show more" button exists and measure its impact.

    Returns:
        {
            "needed": bool,
            "selector": str (if found),
            "before_length": int,
            "after_length": int,
            "impact": str,
            "strategy": str
        }
    """
    # Measure description length before
    try:
        desc_before = await page.evaluate("""() => {
            const el = document.querySelector('div.show-more-less-html__markup');
            return el ? el.textContent.length : 0;
        }""")
    except:
        return {"needed": False}

    # Try to find and click show more button
    button_selectors = [
        "button[aria-expanded='false']",
        "button:has-text('Show more')",
        ".show-more-less-html__button--more",
        "button[data-tracking-control-name*='show-more']"
    ]

    clicked = False
    clicked_selector = None

    for selector in button_selectors:
        try:
            button = await page.wait_for_selector(selector, timeout=2000)
            if button:
                await button.click()
                await page.wait_for_timeout(1500)  # Wait for expansion
                clicked = True
                clicked_selector = selector
                logging.debug(f"✓ Clicked show more button: {selector}")
                break
        except:
            continue

    if not clicked:
        return {"needed": False, "before_length": desc_before}

    # Measure description length after
    try:
        desc_after = await page.evaluate("""() => {
            const el = document.querySelector('div.show-more-less-html__markup');
            return el ? el.textContent.length : 0;
        }""")
    except:
        desc_after = desc_before

    return {
        "needed": True,
        "selector": clicked_selector,
        "before_length": desc_before,
        "after_length": desc_after,
        "impact": f"{desc_before} → {desc_after} chars (+{desc_after - desc_before})",
        "strategy": f"Click {clicked_selector} before extraction"
    }


async def capture_html_samples(page, tested_strategies: Dict[str, List[Dict]]) -> Dict[str, str]:
    """
    Capture HTML snippets for fields with working strategies.

    Args:
        page: Playwright page object
        tested_strategies: Dict of field -> strategy results

    Returns:
        Dict of field -> HTML snippet (first 500 chars)
    """
    html_samples = {}

    # Map fields to their selectors based on working strategies
    field_selectors = {
        "title": "h1",
        "company": "a[data-tracking-control-name*='topcard']",
        "location": ".topcard__flavor--bullet",
        "description": "div.show-more-less-html__markup"
    }

    for field, selector in field_selectors.items():
        # Only capture if we have a working strategy for this field
        if field in tested_strategies and tested_strategies[field]:
            try:
                html = await page.evaluate(f"""() => {{
                    const el = document.querySelector('{selector}');
                    return el ? el.outerHTML : null;
                }}""")
                if html:
                    html_samples[field] = html[:500]
                    logging.debug(f"✓ Captured HTML sample for {field}: {len(html)} chars")
            except Exception as e:
                logging.debug(f"Failed to capture HTML for {field}: {e}")

    return html_samples


# ============================================================================
# Discovery Mode
# ============================================================================

DISCOVERY_SYSTEM_PROMPT = """You are a web scraping expert analyzing job postings from various job sites.

Your task: Explore the job page and document every action needed to extract job data.

Process:
1. Navigate to the provided job URL
2. Observe the page structure and identify interactive elements
3. Check for and note any modal dialogs or pop-ups that need dismissal
4. Identify CSS selectors for: title, company, location, salary (optional), description
5. Consider site-specific patterns (path-based vs query parameter URLs, etc.)
6. Document your findings in structured JSON format

Output a JSON object with this structure:
{
  "job_id": "extracted from URL",
  "url": "original URL",
  "observations": [
    "Step-by-step observations about the page structure and elements"
  ],
  "data_extraction": {
    "title": {
      "selector": "CSS selector",
      "strategy": "extraction method (text_content, innerHTML, etc.)",
      "fallback": "alternative selector or null"
    },
    "company": { ... },
    "location": { ... },
    "salary": { ... },
    "description": { ... }
  },
  "edge_cases": [
    "List any special cases, potential issues, or site-specific quirks"
  ],
  "recommended_wait_times": {
    "initial_load": "milliseconds to wait after page load",
    "after_modal_dismiss": "milliseconds to wait after dismissing popups",
    "description_expansion": "milliseconds to wait after expanding content"
  }
}

Be thorough and precise. Every detail matters for generating a reusable site-specific scraper."""


async def run_discovery_mode(
    job_url: str,
    config: Config,
    site: Optional[JobSite] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run Phase 1: Discovery Mode (multi-site support)

    Uses Playwright to explore the job page and AI to document the strategy

    Args:
        job_url: Job posting URL
        config: Application configuration
        site: Optional JobSite (auto-detected if None)
        verbose: Enable verbose logging

    Returns:
        Discovery log dictionary
    """
    # Auto-detect site if not provided
    if site is None:
        site = detect_job_site(job_url)

    site_config = get_site_config(site)

    job_id = extract_job_id(job_url, site)
    if not job_id:
        raise ValueError(f"Could not extract job ID from URL: {job_url}")

    logging.info(f"Starting discovery mode for {site_config.display_name} job ID: {job_id}")

    # Initialize Playwright browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        try:
            # Navigate to job page
            logging.info(f"Navigating to: {job_url}")
            await page.goto(job_url, wait_until='domcontentloaded', timeout=config.browser_timeout)
            await page.wait_for_timeout(3000)  # Wait for dynamic content

            # Capture page HTML for AI analysis
            page_html = await page.content()
            page_title = await page.title()

            # Check for modals
            modal_present = await page.locator('button:has-text("Dismiss")').is_visible()

            # Get page snapshot for AI
            observations = {
                "page_title": page_title,
                "modal_present": modal_present,
                "url": job_url
            }

            logging.info(f"Page loaded. Modal present: {modal_present}")

            # NEW: Test extraction strategies for all fields (Phase 12.1)
            logging.info("🧪 Testing extraction strategies...")
            tested_strategies = {}

            for field in ['title', 'company', 'location', 'description']:
                logging.info(f"  Testing {field} extraction...")
                strategies = await test_extraction_strategies(page, field)
                tested_strategies[field] = strategies

                if strategies:
                    best = strategies[0]
                    logging.info(f"  ✓ Found working strategy for {field}: {best['strategy']} (confidence: {best['confidence']})")
                    logging.debug(f"    Sample: {best['sample'][:100]}...")
                else:
                    logging.warning(f"  ✗ No working strategy found for {field}")

            # NEW: Test show more button (Phase 12.1)
            logging.info("🧪 Testing show more button...")
            show_more_strategy = await test_show_more_button(page)
            if show_more_strategy.get("needed"):
                logging.info(f"  ✓ Show more button required: {show_more_strategy['impact']}")
            else:
                logging.info(f"  ✗ Show more button not needed")

            # NEW: Capture HTML samples (Phase 12.1)
            logging.info("🧪 Capturing HTML samples...")
            html_samples = await capture_html_samples(page, tested_strategies)
            if html_samples:
                logging.info(f"  ✓ Captured HTML samples for {len(html_samples)} fields")

            # Use AI to analyze the page structure
            anthropic_client = Anthropic(api_key=config.anthropic_api_key)

            # NEW: Enhanced analysis prompt with REAL tested data (Phase 12.1)
            analysis_prompt = f"""Analyze this {site_config.display_name} job posting.

I have TESTED these extraction strategies and they WORK:

Title extraction results:
{json.dumps(tested_strategies.get('title', []), indent=2)}

Company extraction results:
{json.dumps(tested_strategies.get('company', []), indent=2)}

Location extraction results:
{json.dumps(tested_strategies.get('location', []), indent=2)}

Description extraction results:
{json.dumps(tested_strategies.get('description', []), indent=2)}

Show more button strategy:
{json.dumps(show_more_strategy, indent=2)}

HTML samples from the page:
Title area: {html_samples.get('title', 'N/A')[:300]}
Company area: {html_samples.get('company', 'N/A')[:300]}
Description area: {html_samples.get('description', 'N/A')[:300]}

Based on these TESTED and VERIFIED strategies, document the scraping approach.
CRITICAL: Prioritize strategies marked with "confidence": "high".
CRITICAL: Use the exact JavaScript code provided in the tested strategies.
Note: {site_config.description}

Output your analysis as the specified JSON structure with:
- observations: What you notice about the tested strategies
- data_extraction: Document the WORKING strategies from above
- edge_cases: Potential issues discovered during testing
- recommended_wait_times: Timeouts based on button click testing"""

            logging.info("Requesting AI analysis...")

            message = anthropic_client.messages.create(
                model=config.model_name,
                max_tokens=config.max_tokens,
                system=DISCOVERY_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ]
            )

            # Extract JSON from response
            response_text = message.content[0].text

            # Try to parse JSON from response
            try:
                # Look for JSON in code blocks or plain text
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    discovery_log = json.loads(json_match.group(1))
                else:
                    # Try parsing entire response as JSON
                    discovery_log = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback: create structured log from text
                discovery_log = {
                    "job_id": job_id,
                    "url": job_url,
                    "observations": [response_text],
                    "data_extraction": {},
                    "edge_cases": [],
                    "raw_response": response_text
                }

            # Ensure job_id and url are set
            discovery_log["job_id"] = job_id
            discovery_log["url"] = job_url

            # NEW: Add tested strategies to discovery log (Phase 12.1)
            discovery_log["tested_strategies"] = tested_strategies
            discovery_log["show_more_strategy"] = show_more_strategy
            discovery_log["html_samples"] = html_samples

            logging.info("✓ Discovery complete with live testing")
            logging.info(f"  Tested {len(tested_strategies)} fields")
            logging.info(f"  High-confidence strategies: {sum(1 for field in tested_strategies.values() for s in field if s.get('confidence') == 'high')}")
            return discovery_log

        finally:
            await browser.close()


# ============================================================================
# Validation Loop (Phase 12.3)
# ============================================================================

async def validate_generated_script(
    script_path: str,
    test_url: str,
    discovery_log: Dict[str, Any],
    config: Config,
    max_attempts: int = 3
) -> Tuple[bool, List[str]]:
    """
    Validate generated script by running it and checking output.
    If validation fails, request AI to fix it.

    Args:
        script_path: Path to generated script
        test_url: Job URL to test with (from discovery)
        discovery_log: Discovery log with working strategies
        config: Application configuration
        max_attempts: Maximum fix attempts

    Returns:
        (success: bool, issues: List[str])
    """
    anthropic_client = Anthropic(api_key=config.anthropic_api_key)

    for attempt in range(1, max_attempts + 1):
        logging.info(f"🧪 Validation attempt {attempt}/{max_attempts}")

        # Run the script
        try:
            result = subprocess.run(
                [sys.executable, script_path, test_url],
                capture_output=True,
                text=True,
                timeout=90
            )
        except subprocess.TimeoutExpired:
            error_msg = "Script execution timeout (90s)"
            logging.error(f"❌ {error_msg}")

            if attempt < max_attempts:
                # Request fix from AI
                fixed_script = await request_fix_from_ai(
                    script_path, error_msg, discovery_log, config
                )
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write("#!/usr/bin/env python3\n")
                    f.write(fixed_script)
                logging.info("💾 Applied fix, retrying...")
                continue
            else:
                return False, [error_msg]

        # Check exit code
        if result.returncode != 0:
            error_msg = f"Script failed with exit code {result.returncode}"
            logging.error(f"❌ {error_msg}")
            logging.error(f"   stderr: {result.stderr[:500]}")

            if attempt < max_attempts:
                # Request fix
                fixed_script = await request_fix_from_ai(
                    script_path, result.stderr, discovery_log, config
                )
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write("#!/usr/bin/env python3\n")
                    f.write(fixed_script)
                logging.info("💾 Applied fix, retrying...")
                continue
            else:
                return False, [error_msg, result.stderr[:500]]

        # Find output file
        job_id = extract_job_id(test_url)
        output_files = list(Path("job_descriptions").glob(f"*{job_id}*"))

        if not output_files:
            error_msg = "No output file generated"
            logging.error(f"❌ {error_msg}")

            if attempt < max_attempts:
                fixed_script = await request_fix_from_ai(
                    script_path, error_msg, discovery_log, config
                )
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write("#!/usr/bin/env python3\n")
                    f.write(fixed_script)
                logging.info("💾 Applied fix, retrying...")
                continue
            else:
                return False, [error_msg]

        # Validate output content
        with open(output_files[0], 'r', encoding='utf-8') as f:
            content = f.read()

        if len(content) > 500 and ("About" in content or "responsibilities" in content.lower() or "description" in content.lower()):
            logging.info(f"✅ Validation passed! Description length: {len(content)} chars")
            return True, []
        else:
            error_msg = f"Output too short ({len(content)} chars) or missing key content"
            logging.warning(f"⚠️  {error_msg}")

            if attempt < max_attempts:
                fixed_script = await request_fix_from_ai(
                    script_path, error_msg, discovery_log, config
                )
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write("#!/usr/bin/env python3\n")
                    f.write(fixed_script)
                logging.info("💾 Applied fix, retrying...")
                continue
            else:
                return False, [error_msg]

    return False, ["Validation failed after all attempts"]


async def request_fix_from_ai(
    script_path: str,
    error_message: str,
    discovery_log: Dict[str, Any],
    config: Config
) -> str:
    """
    Request AI to fix broken script using discovery log as reference.

    Args:
        script_path: Path to broken script
        error_message: Error from validation
        discovery_log: Discovery log with working strategies
        config: Application configuration

    Returns:
        Fixed script code
    """
    logging.info("🔧 Requesting fix from AI...")

    # Read current broken script
    with open(script_path, 'r', encoding='utf-8') as f:
        broken_script = f.read()

    # Extract working strategies
    tested_strategies = discovery_log.get('tested_strategies', {})
    working_js = {}
    for field, strategies in tested_strategies.items():
        for strategy in strategies:
            if strategy.get('strategy') == 'javascript_evaluation' and strategy.get('success'):
                working_js[field] = strategy['code']
                break

    fix_prompt = f"""This Playwright scraper failed with this error:

ERROR: {error_message}

BROKEN SCRIPT:
```python
{broken_script}
```

WORKING JAVASCRIPT STRATEGIES (from discovery testing):
{json.dumps(working_js, indent=2)}

Fix the script using the WORKING JavaScript strategies above.
The script MUST use page.evaluate() with the exact JavaScript that worked during discovery.
DO NOT use page.wait_for_selector() loops or CSS selectors for data extraction.

Output the COMPLETE fixed script."""

    anthropic_client = Anthropic(api_key=config.anthropic_api_key)

    message = anthropic_client.messages.create(
        model=config.model_name,
        max_tokens=config.max_tokens,
        system=CODE_GENERATION_SYSTEM_PROMPT_V2,
        messages=[{"role": "user", "content": fix_prompt}]
    )

    # Extract code
    response_text = message.content[0].text
    code_match = re.search(r'```python\s*(.*?)\s*```', response_text, re.DOTALL)
    if code_match:
        fixed_script = code_match.group(1)
    else:
        code_match = re.search(r'```\s*(.*?)\s*```', response_text, re.DOTALL)
        if code_match:
            fixed_script = code_match.group(1)
        else:
            fixed_script = response_text

    logging.info("✓ Received fix from AI")
    return fixed_script


# ============================================================================
# Multi-Job Testing (Phase 12.4)
# ============================================================================

# Test URL sets for each site
TEST_URLS = {
    JobSite.LINKEDIN: [
        "https://www.linkedin.com/jobs/view/4305267405",
        # Can add more LinkedIn test URLs here
    ],
    JobSite.INDEED: [
        "https://www.indeed.com/viewjob?jk=ee188e8f304a1b67&from=shareddesktop_copy",
        # Can add more Indeed test URLs here
    ],
    JobSite.GLASSDOOR: [
        # Add Glassdoor test URLs when available
    ]
}


async def validate_scraper_multi_job(
    script_path: str,
    site: JobSite,
    test_urls: Optional[List[str]] = None
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Validate scraper with multiple jobs from the same site.

    Args:
        script_path: Path to scraper script
        site: Job site enum
        test_urls: Optional list of test URLs (uses TEST_URLS if None)

    Returns:
        (success_rate: float, results: List[Dict])
    """
    if test_urls is None:
        test_urls = TEST_URLS.get(site, [])

    if not test_urls:
        logging.warning(f"No test URLs defined for {site.value}")
        return 0.0, []

    logging.info(f"Testing scraper with {len(test_urls)} jobs from {site.value}...")

    results = []
    for i, url in enumerate(test_urls, 1):
        logging.info(f"  Test {i}/{len(test_urls)}: {url}")

        result = {
            "url": url,
            "job_id": extract_job_id(url, site),
            "success": False,
            "output_file": None,
            "description_length": 0,
            "error": None
        }

        try:
            # Run script with timeout
            proc_result = subprocess.run(
                [sys.executable, script_path, url],
                capture_output=True,
                text=True,
                timeout=90
            )

            if proc_result.returncode == 0:
                # Find output file
                job_id = result["job_id"]
                output_files = list(Path("job_descriptions").glob(f"*{job_id}*"))

                if output_files:
                    output_file = output_files[0]
                    with open(output_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    result["output_file"] = str(output_file)
                    result["description_length"] = len(content)

                    # Check if content is valid
                    if len(content) > 500:
                        result["success"] = True
                        logging.info(f"    ✓ Success: {len(content)} chars")
                    else:
                        result["error"] = f"Output too short ({len(content)} chars)"
                        logging.warning(f"    ✗ Failed: {result['error']}")
                else:
                    result["error"] = "No output file generated"
                    logging.warning(f"    ✗ Failed: {result['error']}")
            else:
                result["error"] = f"Exit code {proc_result.returncode}: {proc_result.stderr[:200]}"
                logging.warning(f"    ✗ Failed: Script error")

        except subprocess.TimeoutExpired:
            result["error"] = "Timeout (90s)"
            logging.warning(f"    ✗ Failed: Timeout")
        except Exception as e:
            result["error"] = str(e)
            logging.warning(f"    ✗ Failed: {e}")

        results.append(result)

    # Calculate success rate
    successful = sum(1 for r in results if r["success"])
    success_rate = (successful / len(results)) * 100 if results else 0.0

    logging.info(f"Multi-job test complete: {success_rate:.1f}% success ({successful}/{len(results)})")

    return success_rate, results


def generate_test_report(
    site: JobSite,
    script_path: str,
    success_rate: float,
    results: List[Dict[str, Any]]
) -> str:
    """
    Generate a test report from multi-job validation results.

    Args:
        site: Job site enum
        script_path: Path to tested script
        success_rate: Success rate percentage
        results: List of test results

    Returns:
        Report content as string
    """
    report_lines = [
        f"Multi-Job Test Report: {site.value.upper()} Scraper",
        "=" * 60,
        f"Script: {script_path}",
        f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Success Rate: {success_rate:.1f}% ({sum(1 for r in results if r['success'])}/{len(results)})",
        "",
        "Detailed Results:",
        "-" * 60,
    ]

    for i, result in enumerate(results, 1):
        status = "✓" if result["success"] else "✗"
        report_lines.append(f"\nTest {i}: {status}")
        report_lines.append(f"  URL: {result['url']}")
        report_lines.append(f"  Job ID: {result['job_id']}")

        if result["success"]:
            report_lines.append(f"  Output: {result['output_file']}")
            report_lines.append(f"  Description Length: {result['description_length']} chars")
        else:
            report_lines.append(f"  Error: {result['error']}")

    report_lines.append("")
    report_lines.append("=" * 60)

    return "\n".join(report_lines)


def save_test_report(
    site: JobSite,
    script_path: str,
    success_rate: float,
    results: List[Dict[str, Any]],
    output_dir: str = "test_reports"
) -> Path:
    """
    Save test report to file.

    Args:
        site: Job site enum
        script_path: Path to tested script
        success_rate: Success rate percentage
        results: List of test results
        output_dir: Output directory for reports

    Returns:
        Path to saved report file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    report_filename = f"{site.value}_scraper_test_{timestamp}.txt"
    report_path = output_path / report_filename

    report_content = generate_test_report(site, script_path, success_rate, results)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    logging.info(f"Test report saved: {report_path}")
    return report_path


# ============================================================================
# Code Generation Mode (Phase 12.2)
# ============================================================================

CODE_GENERATION_SYSTEM_PROMPT_V2 = """You are a Python developer specializing in Playwright automation.

CRITICAL REQUIREMENT: Generated scripts MUST use page.evaluate() with JavaScript for data extraction.
DO NOT use page.wait_for_selector() or page.query_selector() for extracting data.

Why JavaScript Evaluation is Mandatory:
1. **10x more reliable**: Single atomic operation vs multiple round trips
2. **No race conditions**: All data extracted in one browser context call
3. **Proven pattern**: Original scraper achieves 100% success rate with this approach
4. **Handles dynamic content**: JavaScript executes after all content loaded

REQUIRED PATTERN (page.evaluate with single JavaScript block):

```python
def scrape_{site}_job(page, job_url):
    page.goto(job_url, timeout=60000)
    time.sleep(3)

    # Click show more if needed (from discovery log)
    try:
        page.click("button[aria-expanded='false']", timeout=5000)
        time.sleep(1.5)
    except:
        pass

    # Extract ALL data in single JavaScript evaluation
    job_data = page.evaluate('''() => {
        // Use EXACT JavaScript code from discovery log that has "confidence": "high"
        const title = document.querySelector('h1')?.textContent?.trim() || 'Not found';
        const company = document.querySelector('a[data-tracking-control-name*="topcard"]')?.textContent?.trim() || 'Not found';
        const description = document.querySelector('div.show-more-less-html__markup')?.innerText || 'Not found';

        return {
            title: title,
            company: company,
            description: description
        };
    }''')

    return job_data
```

CRITICAL: Use EXACTLY the JavaScript strategies from the discovery log that have "success": true and "confidence": "high".

DO NOT generate code like this:
```python
# WRONG - DO NOT DO THIS
for selector in title_selectors:
    element = page.wait_for_selector(selector, timeout=15000)
    if element:
        title = element.text_content()
```

Your task: Convert a discovery log into a standalone, REUSABLE, production-ready Playwright script.

This script will be used for MANY different jobs on the same site.
It MUST:
1. Accept job_url as a command-line argument (use argparse)
2. Extract job_id DYNAMICALLY from the provided URL
3. Work for ANY job on the target site, not just one specific job
4. NEVER hardcode job-specific information (job IDs, titles, company names, etc.)
5. Use page.evaluate() with JavaScript from discovery log (NOT CSS selectors)

Example usage that MUST work:
  python {site}_scraper.py "https://{site}.com/jobs/123"
  python {site}_scraper.py "https://{site}.com/jobs/456"
  python {site}_scraper.py "https://{site}.com/jobs/789"

Requirements:
1. Use sync_playwright API (not async)
2. Implement these functions:
   - sanitize_filename: Clean filenames
   - extract_job_id: Extract job ID from URL dynamically
   - scrape_{site}_job: Main scraping function using page.evaluate()
   - format_job_description: Format output
   - main: Entry point with argparse for URL argument
3. Include robust error handling (TimeoutError, missing elements)
4. Save output to job_descriptions/ directory
5. Script must run independently (no AI/MCP dependencies)

Match this structure:
- Browser: chromium, headless=True
- Viewport: 1920x1080
- User agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
- Timeout: 60000ms for navigation
- Wait: 3 seconds after page load

Output ONLY the complete Python script as a code block. No explanations."""


async def run_generation_mode(
    discovery_log_path: str,
    config: Config,
    site: Optional[JobSite] = None,
    verbose: bool = False
) -> str:
    """
    Run Phase 2: Code Generation Mode (multi-site support)

    Converts discovery log into standalone, reusable Playwright script

    Args:
        discovery_log_path: Path to discovery log JSON file
        config: Application configuration
        site: Optional JobSite (read from log if None)
        verbose: Enable verbose logging

    Returns:
        Path to generated script file
    """
    logging.info(f"Loading discovery log: {discovery_log_path}")
    discovery_log = load_discovery_log(discovery_log_path)

    # Get site from log or parameter
    if site is None:
        site_name = discovery_log.get("site")
        if site_name:
            site = JobSite(site_name)
        else:
            # Fallback: Try to detect from URL in log
            url = discovery_log.get("url")
            if url:
                site = detect_job_site(url)
            else:
                raise ValueError("Cannot determine site from discovery log")

    site_config = get_site_config(site)

    job_id = discovery_log.get("job_id")
    if not job_id:
        raise ValueError("Discovery log missing job_id field")

    logging.info(f"Generating REUSABLE {site_config.display_name} scraper (tested with job ID: {job_id})")

    # NEW: Extract tested JavaScript strategies (Phase 12.2)
    tested_strategies = discovery_log.get('tested_strategies', {})
    show_more_strategy = discovery_log.get('show_more_strategy', {})

    # Extract high-confidence JavaScript code
    js_code_snippets = {}
    for field, strategies in tested_strategies.items():
        for strategy in strategies:
            if strategy.get('strategy') == 'javascript_evaluation' and strategy.get('confidence') == 'high':
                js_code_snippets[field] = strategy['code']
                logging.info(f"  ✓ Using tested JS for {field}: {strategy['code'][:60]}...")
                break

    if not js_code_snippets:
        logging.warning("⚠️  No high-confidence JavaScript strategies found. Using all tested strategies.")
        # Fallback: use any JavaScript strategy
        for field, strategies in tested_strategies.items():
            for strategy in strategies:
                if strategy.get('strategy') == 'javascript_evaluation':
                    js_code_snippets[field] = strategy['code']
                    break

    # Initialize Anthropic client
    anthropic_client = Anthropic(api_key=config.anthropic_api_key)

    # NEW: Enhanced generation prompt with working JavaScript (Phase 12.2)
    generation_prompt = f"""Generate a REUSABLE Playwright scraper for {site_config.display_name}.

TESTED JAVASCRIPT STRATEGIES (use these EXACTLY in page.evaluate()):

Title: {js_code_snippets.get('title', 'document.querySelector("h1")?.textContent?.trim()')}
Company: {js_code_snippets.get('company', 'document.querySelector(".company")?.textContent?.trim()')}
Location: {js_code_snippets.get('location', 'document.querySelector(".location")?.textContent?.trim()')}
Description: {js_code_snippets.get('description', 'document.querySelector(".description")?.innerText')}

Show more button handling:
{json.dumps(show_more_strategy, indent=2)}

CRITICAL REMINDERS:
1. This script will be used for MANY different {site_config.display_name} jobs
2. Accept job_url as command-line argument (use argparse)
3. Extract job_id DYNAMICALLY from URL (pattern: {site_config.description})
4. NEVER hardcode: job IDs, job titles, company names, or any job-specific data
5. MUST use page.evaluate() with the EXACT JavaScript above in a SINGLE call
6. DO NOT use page.wait_for_selector() or CSS selectors for data extraction

Example structure for scraping function:
```python
job_data = page.evaluate('''() => {{
    const title = {js_code_snippets.get('title', 'document.querySelector("h1").textContent')};
    const company = {js_code_snippets.get('company', 'document.querySelector(".company").textContent')};
    const location = {js_code_snippets.get('location', 'document.querySelector(".location").textContent')};
    const description = {js_code_snippets.get('description', 'document.querySelector(".description").innerText')};

    return {{
        title: title,
        company: company,
        location: location,
        description: description
    }};
}}''')
```

The script should:
- Use sync_playwright (not async)
- Combine all field extractions in ONE page.evaluate() call
- Click show more button if needed (before evaluate): {show_more_strategy.get('selector', 'N/A')}
- Save output to job_descriptions/ directory with format: {site.value}_job_{{job_id}}_{{title}}.txt
- Be named: {site.value}_scraper.py (not job-specific)

Output the complete, runnable Python script."""

    logging.info("Requesting code generation with V2 prompt...")

    message = anthropic_client.messages.create(
        model=config.model_name,
        max_tokens=config.max_tokens,
        system=CODE_GENERATION_SYSTEM_PROMPT_V2,  # NEW: Use V2 prompt
        messages=[
            {
                "role": "user",
                "content": generation_prompt
            }
        ]
    )

    # Extract code from response
    response_text = message.content[0].text

    # Extract Python code from markdown code blocks
    code_match = re.search(r'```python\s*(.*?)\s*```', response_text, re.DOTALL)
    if code_match:
        generated_script = code_match.group(1)
    else:
        # Try without language specifier
        code_match = re.search(r'```\s*(.*?)\s*```', response_text, re.DOTALL)
        if code_match:
            generated_script = code_match.group(1)
        else:
            generated_script = response_text

    # Validate syntax
    logging.info("Validating generated script syntax...")
    is_valid, error = validate_python_syntax(generated_script)
    if not is_valid:
        logging.error(f"Generated script has syntax errors: {error}")
        raise ValueError(f"Generated script validation failed: {error}")

    # NEW: Validate uses page.evaluate() pattern (Phase 12.2.4)
    logging.info("Validating page.evaluate() usage...")
    if 'page.evaluate(' not in generated_script:
        logging.error("❌ Generated script does NOT use page.evaluate() for data extraction")
        logging.error("   Script must use JavaScript evaluation, not CSS selectors")
        raise ValueError("Generated script must use page.evaluate() pattern")
    else:
        logging.info("✓ Script uses page.evaluate() pattern")

    # Check it doesn't use fragile CSS selector loops
    if 'page.wait_for_selector(' in generated_script and 'for selector in' in generated_script:
        logging.warning("⚠️  Script appears to use CSS selector loops (fragile pattern)")

    # Validate structure
    logging.info("Validating script structure...")
    is_valid, issues = validate_script_structure(generated_script)
    if not is_valid:
        logging.warning(f"Script validation issues: {', '.join(issues)}")
        # Don't fail, just warn - AI might use different patterns

    # Test that it can be compiled
    logging.info("Testing script can be compiled...")
    try:
        compile(generated_script, '<generated>', 'exec')
        logging.info("✓ Script compiles successfully")
    except SyntaxError as e:
        logging.error(f"Script compilation failed: {e.msg} at line {e.lineno}")
        raise ValueError(f"Generated script has syntax error: {e.msg} at line {e.lineno}")

    logging.info("✓ Validation passed")

    # Save generated script with site-specific naming
    output_dir = Path("generated_scripts")
    output_dir.mkdir(exist_ok=True)

    # Site-specific filename (reusable for all jobs from this site)
    script_path = output_dir / f"{site.value}_scraper.py"

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write("#!/usr/bin/env python3\n")
        f.write(generated_script)

    # Make executable
    script_path.chmod(0o755)

    logging.info(f"✓ REUSABLE {site_config.display_name} scraper generated: {script_path}")
    logging.info(f"  This script can be used for ANY {site_config.display_name} job")
    logging.info(f"  Usage: python {script_path} <job_url>")

    # NEW: Mandatory validation with fix loop (Phase 12.3)
    test_url = discovery_log.get("url")
    if test_url:
        logging.info("")
        logging.info("=" * 60)
        logging.info("VALIDATION PHASE: Testing generated script")
        logging.info("=" * 60)

        success, issues = await validate_generated_script(
            str(script_path),
            test_url,
            discovery_log,
            config,
            max_attempts=3
        )

        if success:
            logging.info("")
            logging.info("=" * 60)
            logging.info("✅ VALIDATION PASSED - Script is production-ready!")
            logging.info("=" * 60)
        else:
            logging.error("")
            logging.error("=" * 60)
            logging.error("❌ VALIDATION FAILED after 3 attempts")
            logging.error(f"   Issues: {', '.join(issues)}")
            logging.error("=" * 60)
            raise ValueError(f"Generated script validation failed: {', '.join(issues)}")
    else:
        logging.warning("⚠️  No test URL in discovery log - skipping validation")

    return str(script_path)


# ============================================================================
# CLI Interface
# ============================================================================

def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='AI-Driven Multi-Site Job Parser (LinkedIn, Indeed, Glassdoor)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discovery mode - analyze job page (auto-detects site)
  %(prog)s discover "https://www.linkedin.com/jobs/view/4300362234"
  %(prog)s discover "https://www.indeed.com/viewjob?jk=abc123"

  # Generation mode - create site-specific scraper from discovery log
  %(prog)s generate discovery_logs/linkedin_discovery_2025-09-29T12-00-00.json

Supported sites: LinkedIn, Indeed, Glassdoor
        """
    )

    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')

    # Discovery mode
    discover_parser = subparsers.add_parser('discover',
        help='Analyze job page and create discovery log')
    discover_parser.add_argument('url', help='Job posting URL (site auto-detected)')
    discover_parser.add_argument('--site', choices=['linkedin', 'indeed', 'glassdoor'],
        help='Manually specify site (overrides auto-detection)')
    discover_parser.add_argument('--verbose', '-v', action='store_true',
        help='Enable verbose logging')

    # Generation mode
    generate_parser = subparsers.add_parser('generate',
        help='Generate reusable site-specific scraper from discovery log')
    generate_parser.add_argument('log_file', help='Path to discovery log JSON file')
    generate_parser.add_argument('--verbose', '-v', action='store_true',
        help='Enable verbose logging')
    generate_parser.add_argument('--multi-job-test', action='store_true',
        help='Run multi-job testing after generation (Phase 12.4)')

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    # Setup
    setup_logging(args.verbose)

    try:
        config = Config.from_env()
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)

    # Run selected mode
    try:
        if args.mode == 'discover':
            # Normalize URL if url_utils is available (handles query parameters)
            original_url = args.url
            if URL_UTILS_AVAILABLE:
                try:
                    normalized = normalize_url_external(args.url)
                    args.url = normalized.canonical_url
                    if original_url != args.url:
                        print(f"✓ URL normalized (tracking params removed)")
                        logging.info(f"Original: {original_url}")
                        logging.info(f"Canonical: {args.url}")
                except Exception as e:
                    # Fall back to original URL if normalization fails
                    logging.warning(f"URL normalization failed: {e}")
                    print(f"⚠️  URL normalization failed, using original URL")

            # Get site (manual or auto-detect)
            site = None
            if hasattr(args, 'site') and args.site:
                site = JobSite(args.site)
            else:
                # Auto-detect site from URL
                site = detect_job_site(args.url)

            # Run discovery
            discovery_log = asyncio.run(run_discovery_mode(
                args.url,
                config,
                site=site,
                verbose=args.verbose
            ))

            # Get site info
            site_config = get_site_config(site)
            job_id = discovery_log['job_id']

            # Save with site-specific naming
            filepath = save_discovery_log(site, discovery_log)

            print(f"\n✓ Discovery complete!")
            print(f"  Site: {site_config.display_name}")
            print(f"  Job ID: {job_id}")
            print(f"  Log saved: {filepath}")
            print(f"\nNext step:")
            print(f"  python {sys.argv[0]} generate {filepath}")

        elif args.mode == 'generate':
            script_path = asyncio.run(run_generation_mode(
                args.log_file,
                config,
                verbose=args.verbose
            ))

            print(f"\n✓ Reusable site-specific scraper generated!")
            print(f"  Location: {script_path}")
            print(f"\nThis scraper can be used for ANY job from this site:")
            print(f"  python {script_path} <job_url>")

            # NEW: Multi-job testing if requested (Phase 12.5)
            if hasattr(args, 'multi_job_test') and args.multi_job_test:
                # Load discovery log to get site info
                discovery_log = load_discovery_log(args.log_file)
                site_name = discovery_log.get("site")
                if site_name:
                    site = JobSite(site_name)

                    print(f"\n" + "=" * 60)
                    print(f"MULTI-JOB TESTING")
                    print(f"=" * 60)

                    success_rate, results = asyncio.run(validate_scraper_multi_job(
                        script_path,
                        site
                    ))

                    # Save test report
                    report_path = save_test_report(site, script_path, success_rate, results)

                    print(f"\n✓ Multi-job testing complete!")
                    print(f"  Success rate: {success_rate:.1f}%")
                    print(f"  Report: {report_path}")

                    if success_rate < 85.0:
                        print(f"\n⚠️  Warning: Success rate below 85% target")
                else:
                    print(f"\n⚠️  Cannot run multi-job test: Site not found in discovery log")

    except Exception as e:
        logging.error(f"Error: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()