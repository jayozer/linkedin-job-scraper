#!/usr/bin/env python3
#!/usr/bin/env python3

import re
import time
import argparse
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def sanitize_filename(text):
    """Sanitize text to be safe for use in filenames"""
    if not text or text == "Not found":
        return "unknown"
    # Remove or replace problematic characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', text)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = sanitized.strip('._')
    # Limit length
    if len(sanitized) > 50:
        sanitized = sanitized[:50]
    return sanitized or "unknown"

def extract_job_id(url):
    """Extract job ID from LinkedIn URL"""
    # Pattern: /jobs/view/{id}
    match = re.search(r'/jobs/view/(\d+)', url)
    if match:
        return match.group(1)
    
    # Fallback patterns
    match = re.search(r'/jobs/(\d+)', url)
    if match:
        return match.group(1)
    
    # Extract any numeric ID from URL
    match = re.search(r'(\d{8,})', url)
    if match:
        return match.group(1)
    
    return "unknown"

def scrape_linkedin_job(page, job_url):
    """Scrape a LinkedIn job posting using page.evaluate()"""
    print(f"Navigating to: {job_url}")
    
    try:
        page.goto(job_url, timeout=60000)
        time.sleep(3)
        
        # Extract ALL data in single JavaScript evaluation
        job_data = page.evaluate('''() => {
            const title = document.querySelector("h1")?.textContent?.trim() || 'Not found';
            const company = document.querySelector(".company")?.textContent?.trim() || 'Not found';
            const location = document.querySelector(".location")?.textContent?.trim() || 'Not found';
            const description = document.querySelector('div.show-more-less-html__markup')?.innerText || document.querySelector('div.show-more-less-html__markup')?.textContent || 'Not found';
            
            return {
                title: title,
                company: company,
                location: location,
                description: description
            };
        }''')
        
        return job_data
        
    except PlaywrightTimeoutError:
        print(f"Timeout while loading {job_url}")
        return None
    except Exception as e:
        print(f"Error scraping {job_url}: {str(e)}")
        return None

def format_job_description(job_data, job_url, job_id):
    """Format the job data for output"""
    if not job_data:
        return "Error: Could not scrape job data"
    
    formatted = f"""LinkedIn Job Posting
====================

Job ID: {job_id}
URL: {job_url}

Title: {job_data.get('title', 'Not found')}
Company: {job_data.get('company', 'Not found')}
Location: {job_data.get('location', 'Not found')}

Job Description:
{job_data.get('description', 'Not found')}

---
Scraped at: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
    return formatted

def main():
    parser = argparse.ArgumentParser(description='Scrape LinkedIn job postings')
    parser.add_argument('job_url', help='LinkedIn job URL to scrape')
    args = parser.parse_args()
    
    job_url = args.job_url
    job_id = extract_job_id(job_url)
    
    print(f"Starting LinkedIn scraper for job ID: {job_id}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = context.new_page()
        
        try:
            job_data = scrape_linkedin_job(page, job_url)
            
            if job_data:
                # Create output directory
                os.makedirs('job_descriptions', exist_ok=True)
                
                # Generate filename
                title_clean = sanitize_filename(job_data.get('title', 'unknown'))
                filename = f"linkedin_job_{job_id}_{title_clean}.txt"
                filepath = os.path.join('job_descriptions', filename)
                
                # Format and save
                formatted_output = format_job_description(job_data, job_url, job_id)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(formatted_output)
                
                print(f"Job data saved to: {filepath}")
                print(f"Title: {job_data.get('title', 'Not found')}")
                print(f"Company: {job_data.get('company', 'Not found')}")
                print(f"Location: {job_data.get('location', 'Not found')}")
            else:
                print("Failed to scrape job data")
                
        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()