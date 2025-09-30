#!/usr/bin/env python3
"""
URL Utilities for Job Scraper

Provides robust URL parsing, validation, and normalization for job posting URLs
from multiple sites (LinkedIn, Indeed, Glassdoor).

Functions:
    normalize_job_url: Parse and clean job URLs, extract job IDs
    get_canonical_url: Reconstruct clean URLs without tracking parameters
    validate_job_url: Check if URL is from a supported job site
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlunparse


class JobSite(Enum):
    """Supported job sites"""
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"


@dataclass
class JobURL:
    """Parsed job URL information"""
    site: JobSite
    job_id: str
    original_url: str
    canonical_url: str

    def __str__(self) -> str:
        return f"{self.site.value}:{self.job_id}"


@dataclass
class SitePattern:
    """URL pattern configuration for a job site"""
    site: JobSite
    display_name: str
    domain_pattern: str  # Regex to detect domain
    job_id_pattern: str  # Regex to extract job ID
    canonical_template: str  # Template for clean URL
    description: str = ""


# Site-specific patterns and configurations
SITE_PATTERNS = {
    JobSite.LINKEDIN: SitePattern(
        site=JobSite.LINKEDIN,
        display_name="LinkedIn",
        domain_pattern=r"linkedin\.com",
        job_id_pattern=r"/jobs/view/(\d+)",
        canonical_template="https://www.linkedin.com/jobs/view/{job_id}",
        description="LinkedIn job postings"
    ),
    JobSite.INDEED: SitePattern(
        site=JobSite.INDEED,
        display_name="Indeed",
        domain_pattern=r"indeed\.com",
        job_id_pattern=r"[?&]jk=([a-f0-9]+)",
        canonical_template="https://www.indeed.com/viewjob?jk={job_id}",
        description="Indeed job postings"
    ),
    JobSite.GLASSDOOR: SitePattern(
        site=JobSite.GLASSDOOR,
        display_name="Glassdoor",
        domain_pattern=r"glassdoor\.com",
        job_id_pattern=r"job-listing/[^/]+-JV_IC(\d+)",
        canonical_template="https://www.glassdoor.com/job-listing/-JV_IC{job_id}",
        description="Glassdoor job postings"
    )
}


def detect_job_site(url: str) -> Optional[JobSite]:
    """
    Detect which job site a URL belongs to

    Args:
        url: Job posting URL

    Returns:
        JobSite enum or None if not recognized
    """
    url_lower = url.lower()

    for site, pattern in SITE_PATTERNS.items():
        if re.search(pattern.domain_pattern, url_lower, re.IGNORECASE):
            return site

    return None


def extract_job_id(url: str, site: JobSite) -> Optional[str]:
    """
    Extract job ID from URL based on site-specific pattern

    Args:
        url: Job posting URL
        site: Detected job site

    Returns:
        Job ID string or None if not found
    """
    pattern = SITE_PATTERNS[site].job_id_pattern
    match = re.search(pattern, url, re.IGNORECASE)

    if match:
        return match.group(1)

    return None


def normalize_job_url(url: str) -> JobURL:
    """
    Parse and normalize a job posting URL

    Handles:
    - URLs with query parameters and tracking codes
    - Case variations
    - Trailing slashes
    - URL fragments

    Args:
        url: Job posting URL (can include query parameters)

    Returns:
        JobURL object with parsed information

    Raises:
        ValueError: If URL is not from a supported site or job ID cannot be extracted

    Examples:
        >>> result = normalize_job_url("https://www.linkedin.com/jobs/view/4300371471/?param=value&other=value")
        >>> result.job_id
        '4300371471'
        >>> result.canonical_url
        'https://www.linkedin.com/jobs/view/4300371471'
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    # Strip whitespace
    url = url.strip()

    # Detect job site
    site = detect_job_site(url)
    if not site:
        supported_sites = ", ".join(p.display_name for p in SITE_PATTERNS.values())
        raise ValueError(
            f"Unsupported job site. URL must be from: {supported_sites}\n"
            f"Provided URL: {url}"
        )

    # Extract job ID
    job_id = extract_job_id(url, site)
    if not job_id:
        raise ValueError(
            f"Could not extract job ID from {SITE_PATTERNS[site].display_name} URL.\n"
            f"Expected pattern: {SITE_PATTERNS[site].description}\n"
            f"Provided URL: {url}"
        )

    # Generate canonical URL (without tracking parameters)
    canonical_url = SITE_PATTERNS[site].canonical_template.format(job_id=job_id)

    return JobURL(
        site=site,
        job_id=job_id,
        original_url=url,
        canonical_url=canonical_url
    )


def get_canonical_url(url: str) -> str:
    """
    Get clean canonical URL without tracking parameters

    Args:
        url: Job posting URL

    Returns:
        Clean canonical URL

    Raises:
        ValueError: If URL cannot be normalized

    Examples:
        >>> get_canonical_url("https://www.linkedin.com/jobs/view/123/?refId=tracking")
        'https://www.linkedin.com/jobs/view/123'
    """
    job_url = normalize_job_url(url)
    return job_url.canonical_url


def validate_job_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if URL is from a supported job site and can be parsed

    Args:
        url: Job posting URL

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_job_url("https://www.linkedin.com/jobs/view/123")
        (True, None)
        >>> validate_job_url("https://example.com/job/123")
        (False, "Unsupported job site...")
    """
    try:
        normalize_job_url(url)
        return (True, None)
    except ValueError as e:
        return (False, str(e))


def get_site_info(site: JobSite) -> SitePattern:
    """
    Get configuration information for a job site

    Args:
        site: JobSite enum

    Returns:
        SitePattern configuration
    """
    return SITE_PATTERNS[site]


# Convenience function for chatbot integration
def extract_job_info(url: str) -> dict:
    """
    Extract structured job information from URL for easy integration

    Args:
        url: Job posting URL

    Returns:
        Dictionary with job information

    Example:
        >>> extract_job_info("https://www.linkedin.com/jobs/view/123/?tracking=params")
        {
            'site': 'linkedin',
            'job_id': '123',
            'canonical_url': 'https://www.linkedin.com/jobs/view/123',
            'original_url': 'https://www.linkedin.com/jobs/view/123/?tracking=params'
        }
    """
    job_url = normalize_job_url(url)
    return {
        'site': job_url.site.value,
        'job_id': job_url.job_id,
        'canonical_url': job_url.canonical_url,
        'original_url': job_url.original_url
    }


if __name__ == "__main__":
    # Test examples
    test_urls = [
        "https://www.linkedin.com/jobs/view/4300371471",
        "https://www.linkedin.com/jobs/view/4300371471/?alternateChannel=search&eBP=tracking&trk=d_flagship3",
        "https://www.indeed.com/viewjob?jk=d7a8476f98b7ec44",
        "https://www.indeed.com/viewjob?jk=d7a8476f98b7ec44&from=serp&vjs=3",
    ]

    print("URL Normalization Tests")
    print("=" * 60)

    for url in test_urls:
        try:
            result = normalize_job_url(url)
            print(f"\n✓ Original:  {result.original_url[:80]}...")
            print(f"  Site:      {result.site.value}")
            print(f"  Job ID:    {result.job_id}")
            print(f"  Canonical: {result.canonical_url}")
        except ValueError as e:
            print(f"\n✗ Error: {e}")