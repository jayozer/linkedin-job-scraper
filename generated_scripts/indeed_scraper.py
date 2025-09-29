#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Indeed Job Scraper - Production Ready
Extracts job postings from Indeed.com using Playwright
"""

import argparse
import os
import re
import urllib.parse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def sanitize_filename(filename):
    """Clean filename for safe file system storage"""
    # Remove/replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove extra whitespace and replace with underscores
    filename = re.sub(r'\s+', '_', filename)
    # Remove leading/trailing underscores and dots
    filename = filename.strip('_.')
    # Limit length
    return filename[:100] if filename else 'untitled'


def extract_job_id(url):
    """Extract job ID from Indeed URL"""
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    
    # Indeed uses 'jk' parameter for job ID
    if 'jk' in query_params:
        return query_params['jk'][0]
    
    raise ValueError(f"Could not extract job ID from URL: {url}")


def scrape_indeed_job(page, url):
    """Generic Indeed job scraper that works for any job URL"""
    try:
        # Navigate to job page
        print(f"Navigating to: {url}")
        page.goto(url, timeout=60000, wait_until='networkidle')
        
        # Wait for initial load
        page.wait_for_timeout(2000)
        
        # Try to dismiss cookie banner if present
        try:
            cookie_banner = page.locator('#onetrust-accept-btn-handler, .onetrust-close-btn-handler')
            if cookie_banner.is_visible(timeout=3000):
                cookie_banner.click()
                page.wait_for_timeout(1000)
        except:
            pass
        
        # Extract job data using fallback selectors
        job_data = {}
        
        # Title extraction
        title_selectors = [
            "h1[data-jk] span[title]",
            "h1.jobsearch-JobInfoHeader-title span[title]", 
            ".jobsearch-JobInfoHeader-title span",
            "h1 span",
            "[data-testid='job-title']",
            ".jobsearch-JobInfoHeader-title"
        ]
        
        job_data['title'] = None
        for selector in title_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=5000):
                    title = element.text_content().strip()
                    if title:
                        job_data['title'] = title
                        break
            except:
                continue
        
        # Company extraction
        company_selectors = [
            "[data-testid='inlineHeader-companyName'] a",
            ".jobsearch-InlineCompanyRating div[data-testid='inlineHeader-companyName'] a",
            "[data-testid='inlineHeader-companyName'] span",
            ".jobsearch-CompanyInfoContainer a",
            ".jobsearch-InlineCompanyRating a"
        ]
        
        job_data['company'] = None
        for selector in company_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=5000):
                    company = element.text_content().strip()
                    if company:
                        job_data['company'] = company
                        break
            except:
                continue
        
        # Location extraction
        location_selectors = [
            "[data-testid='job-location']",
            ".jobsearch-JobInfoHeader-subtitle div:last-child",
            "[data-testid='inlineHeader-companyLocation']",
            ".jobsearch-JobInfoHeader-subtitle div",
            ".companyLocation"
        ]
        
        job_data['location'] = None
        for selector in location_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=5000):
                    location = element.text_content().strip()
                    if location:
                        job_data['location'] = location
                        break
            except:
                continue
        
        # Salary extraction (optional)
        salary_selectors = [
            "[data-testid='inlineHeader-salary'] span",
            ".attribute_snippet",
            ".salary-snippet",
            ".estimated-salary"
        ]
        
        job_data['salary'] = None
        for selector in salary_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=5000):
                    salary = element.text_content().strip()
                    if salary and '$' in salary:
                        job_data['salary'] = salary
                        break
            except:
                continue
        
        # Description extraction
        description_selectors = [
            "#jobDescriptionText",
            ".jobsearch-jobDescriptionText",
            "[data-testid='jobsearch-JobComponent-description']",
            ".jobsearch-JobComponent-description",
            "#vjs-desc",
            ".jobsearch-JobDescriptionSection-section"
        ]
        
        job_data['description'] = None
        for selector in description_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=10000):
                    # Check for "Show more" buttons and click them
                    try:
                        show_more_buttons = page.locator("button:has-text('Show more'), .jobsearch-JobDescriptionSection-showmore")
                        if show_more_buttons.count() > 0:
                            show_more_buttons.first.click()
                            page.wait_for_timeout(1500)
                    except:
                        pass
                    
                    description_html = element.inner_html()
                    if description_html and description_html.strip():
                        job_data['description'] = description_html
                        break
            except:
                continue
        
        return job_data
        
    except PlaywrightTimeoutError as e:
        print(f"Timeout error: {e}")
        return None
    except Exception as e:
        print(f"Error during scraping: {e}")
        return None


def format_job_description(job_data, job_id):
    """Format the job data into a readable text format"""
    output = []
    output.append("=" * 80)
    output.append("INDEED JOB POSTING")
    output.append("=" * 80)
    output.append(f"Job ID: {job_id}")
    output.append("")
    
    if job_data.get('title'):
        output.append(f"Title: {job_data['title']}")
    else:
        output.append("Title: Not found")
    
    if job_data.get('company'):
        output.append(f"Company: {job_data['company']}")
    else:
        output.append("Company: Not found")
    
    if job_data.get('location'):
        output.append(f"Location: {job_data['location']}")
    else:
        output.append("Location: Not found")
    
    if job_data.get('salary'):
        output.append(f"Salary: {job_data['salary']}")
    else:
        output.append("Salary: Not specified")
    
    output.append("")
    output.append("DESCRIPTION:")
    output.append("-" * 40)
    
    if job_data.get('description'):
        # Convert HTML to more readable text while preserving structure
        description_text = job_data['description']
        # Basic HTML tag removal and formatting
        description_text = re.sub(r'<br\s*/?>', '\n', description_text)
        description_text = re.sub(r'<li[^>]*>', '\n• ', description_text)
        description_text = re.sub(r'<p[^>]*>', '\n\n', description_text)
        description_text = re.sub(r'<h[1-6][^>]*>', '\n\n', description_text)
        description_text = re.sub(r'<[^>]+>', '', description_text)
        # Clean up extra whitespace
        description_text = re.sub(r'\n\s*\n\s*\n', '\n\n', description_text)
        description_text = description_text.strip()
        output.append(description_text)
    else:
        output.append("Description not found")
    
    output.append("")
    output.append("=" * 80)
    
    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(description='Scrape Indeed job posting')
    parser.add_argument('job_url', help='Indeed job URL')
    args = parser.parse_args()
    
    try:
        # Extract job ID from URL
        job_id = extract_job_id(args.job_url)
        print(f"Extracted job ID: {job_id}")
        
        # Create output directory
        output_dir = "job_descriptions"
        os.makedirs(output_dir, exist_ok=True)
        
        # Launch browser and scrape
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            page.set_default_timeout(15000)
            
            # Scrape the job
            job_data = scrape_indeed_job(page, args.job_url)
            
            browser.close()
        
        if job_data is None:
            print("Failed to scrape job data")
            return
        
        # Format and save the job description
        formatted_description = format_job_description(job_data, job_id)
        
        # Generate filename
        title_part = sanitize_filename(job_data.get('title', 'unknown'))
        filename = f"indeed_job_{job_id}_{title_part}.txt"
        filepath = os.path.join(output_dir, filename)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(formatted_description)
        
        print(f"Job description saved to: {filepath}")
        print("\nJob Summary:")
        print(f"Title: {job_data.get('title', 'Not found')}")
        print(f"Company: {job_data.get('company', 'Not found')}")
        print(f"Location: {job_data.get('location', 'Not found')}")
        print(f"Salary: {job_data.get('salary', 'Not specified')}")
        
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()