#!/usr/bin/env python3
"""
LinkedIn Job Description Scraper
Extracts job description from LinkedIn job posting URLs using Playwright
"""

import sys
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError

# Import URL utilities for robust URL handling
from url_utils import normalize_job_url, JobSite


def sanitize_filename(text):
    """
    Convert text to a valid filename by removing/replacing special characters
    """
    # Remove or replace characters that are invalid in filenames
    text = re.sub(r'[<>:"/\\|?*]', '-', text)
    text = re.sub(r'\s+', '-', text)  # Replace spaces with hyphens
    text = re.sub(r'-+', '-', text)   # Replace multiple hyphens with single
    text = text.strip('-')             # Remove leading/trailing hyphens
    return text[:100]  # Limit filename length


def extract_job_id(url):
    """
    Extract job ID from LinkedIn URL
    Example: https://www.linkedin.com/jobs/view/4300362234 -> 4300362234

    Note: This function is deprecated. Use url_utils.normalize_job_url() instead.
    Kept for backward compatibility.
    """
    pattern = r'/jobs/view/(\d+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def scrape_linkedin_job(url, output_dir="job_descriptions"):
    """
    Scrape job description from LinkedIn job posting

    Args:
        url: LinkedIn job posting URL
        output_dir: Directory to save job descriptions (default: job_descriptions)

    Returns:
        Dictionary with job information or None if failed
    """

    # Normalize and validate URL using url_utils
    try:
        job_url = normalize_job_url(url)

        # Ensure it's a LinkedIn URL
        if job_url.site != JobSite.LINKEDIN:
            print(f"Error: This scraper only supports LinkedIn URLs")
            print(f"Detected site: {job_url.site.value}")
            print(f"For multi-site support, use ai_parser.py")
            return None

        # Use canonical URL for scraping (removes tracking parameters)
        canonical_url = job_url.canonical_url
        job_id = job_url.job_id

        print(f"Starting to scrape job ID: {job_id}")
        if url != canonical_url:
            print(f"Using canonical URL (tracking params removed)")

    except ValueError as e:
        print(f"Error: Invalid LinkedIn job URL")
        print(f"Details: {e}")
        print(f"Expected format: https://www.linkedin.com/jobs/view/[job-id]")
        return None

    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        try:
            # Navigate to the job page (use canonical URL)
            print(f"Navigating to: {canonical_url}")
            page.goto(canonical_url, wait_until='domcontentloaded', timeout=60000)

            # Wait for content to load
            try:
                page.wait_for_selector('h1', timeout=15000)
            except:
                # Sometimes the selector might be different
                page.wait_for_timeout(5000)

            time.sleep(3)  # Additional wait for dynamic content

            # Check for and dismiss any modal dialogs
            try:
                dismiss_button = page.locator('button:has-text("Dismiss")')
                if dismiss_button.is_visible():
                    dismiss_button.click()
                    time.sleep(1)
            except:
                pass  # No modal to dismiss

            # Extract job information using JavaScript
            job_data = page.evaluate('''() => {
                // Get job title
                const titleElement = document.querySelector('h1');
                const jobTitle = titleElement ? titleElement.textContent.trim() : 'Unknown Job';

                // Get company name
                const companyElement = document.querySelector('a[data-tracking-control-name*="topcard-org-name"], a[data-tracking-control-name*="topcard_org_name"]');
                const companyName = companyElement ? companyElement.textContent.trim() : 'Unknown Company';

                // Get location
                const locationElement = document.querySelector('.topcard__flavor--bullet');
                let location = 'Unknown Location';
                if (locationElement && locationElement.parentElement) {
                    const text = locationElement.parentElement.textContent;
                    const match = text.match(/·\\s*([^·]+?)(?:\\s+\\d+|$)/);
                    if (match) location = match[1].trim();
                }

                // Get salary if available
                let salary = 'Not specified';
                const salaryElement = document.querySelector('[class*="compensation"]');
                if (salaryElement) {
                    salary = salaryElement.textContent.trim();
                }

                // Extract the main job description content
                let jobDescription = '';
                const mainContent = document.querySelector('div.show-more-less-html__markup');

                if (mainContent) {
                    jobDescription = mainContent.innerText || mainContent.textContent || '';
                } else {
                    // Alternative: look for container with job details
                    const containers = document.querySelectorAll('div');
                    for (const container of containers) {
                        const text = container.textContent || '';
                        if (text.includes('About the role') || text.includes('What We Do') ||
                            text.includes('About the job') || text.includes('Job Description')) {
                            jobDescription = text;
                            break;
                        }
                    }
                }

                return {
                    title: jobTitle,
                    company: companyName,
                    location: location,
                    salary: salary,
                    description: jobDescription,
                    url: window.location.href
                };
            }''')

            if job_data and job_data['description']:
                # Format the job description for better readability
                formatted_description = format_job_description(job_data)

                # Create output directory if it doesn't exist
                output_path = Path(output_dir)
                output_path.mkdir(exist_ok=True)

                # Generate filename
                filename = f"{sanitize_filename(job_data['title'])}-{sanitize_filename(job_data['company'])}.txt"
                filepath = output_path / filename

                # Save to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(formatted_description)

                print(f"✓ Successfully scraped job: {job_data['title']}")
                print(f"✓ Saved to: {filepath}")

                return job_data
            else:
                print("Error: Could not extract job description")
                return None

        except TimeoutError:
            print(f"Error: Page load timeout - the page took too long to load")
            return None
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            return None
        finally:
            browser.close()


def format_job_description(job_data):
    """
    Format job data into a readable text format
    """
    formatted = f"""Job Title: {job_data['title']}
Company: {job_data['company']}
Location: {job_data['location']}
Salary: {job_data['salary']}
URL: {job_data['url']}

{'='*60}
JOB DESCRIPTION
{'='*60}

{job_data['description']}
"""
    return formatted


def main():
    """
    Main function to run the scraper
    """
    if len(sys.argv) < 2:
        print("LinkedIn Job Description Scraper")
        print("="*40)
        print("Usage: python linkedin_job_scraper.py <linkedin_job_url>")
        print("\nExample:")
        print("  python linkedin_job_scraper.py https://www.linkedin.com/jobs/view/4300362234")
        print("\nOptional: You can specify output directory as second argument")
        print("  python linkedin_job_scraper.py <url> <output_dir>")
        sys.exit(1)

    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "job_descriptions"

    # Run the scraper
    result = scrape_linkedin_job(url, output_dir)

    if result:
        print("\n" + "="*40)
        print("Job scraping completed successfully!")
        print(f"Title: {result['title']}")
        print(f"Company: {result['company']}")
        print(f"Location: {result['location']}")
    else:
        print("\nFailed to scrape job description")
        sys.exit(1)


if __name__ == "__main__":
    main()