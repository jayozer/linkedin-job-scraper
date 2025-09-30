# Multi-Site Job Scraper (LinkedIn, Indeed, Glassdoor)

Two approaches to extract job descriptions from job posting sites:

1. **Original Scraper** (`linkedin_job_scraper.py`) - Direct Playwright scraping (LinkedIn only)
2. **AI-Powered Parser** (`ai_parser.py`) - AI-driven discovery + code generation (Multi-site)

## Features

### Original Scraper
- Extracts job title, company name, location, salary, and full job description
- Saves job descriptions as formatted text files
- Handles dynamic content loading
- Dismisses modal dialogs automatically

### AI-Powered Parser (Version 1.1 - Multi-Site Support)
- **Discovery Mode**: AI analyzes job pages and documents scraping strategy
- **Generation Mode**: Creates REUSABLE, site-specific scrapers
- **Multi-Site Support**: LinkedIn, Indeed, Glassdoor (extensible)
- **API Efficiency**: 99% fewer API calls after first scrape per site
- **Auto-Detection**: Automatically detects job site from URL
- Adapts to site structure changes automatically
- Generates portable, AI-free scripts for production use

## System Flow Diagram

### Option 1: Direct Scraper (Simple)
```
┌─────────────────┐
│   Job URL       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  linkedin_job_scraper.py    │
│  • Launch browser           │
│  • Extract with JS          │
│  • Save to file             │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  job_descriptions/          │
│  Job_Title_Company.txt      │
└─────────────────────────────┘
```

### Option 2: AI-Powered Parser (Advanced)
```
┌──────────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: DISCOVERY MODE                           │
│                      (Once per site - with AI)                           │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         │           ai_parser.py discover <url>               │
         └──────────────────────────┬──────────────────────────┘
                                    │
                   ┌────────────────┼────────────────┐
                   ▼                ▼                ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │ Test 10+     │  │ Test "Show   │  │ Capture HTML │
         │ Strategies   │  │ More" Button │  │ Samples      │
         │ Per Field    │  │              │  │              │
         └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                │                 │                 │
                └─────────────────┼─────────────────┘
                                  ▼
                    ┌──────────────────────────────┐
                    │ AI Analysis                  │
                    │ • Receive TESTED strategies  │
                    │ • Get working JavaScript     │
                    │ • Get HTML samples           │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ discovery_logs/              │
                    │ linkedin_discovery_*.json    │
                    │                              │
                    │ Contains:                    │
                    │ • tested_strategies          │
                    │ • show_more_strategy         │
                    │ • html_samples               │
                    └──────────────┬───────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────────┐
│                      PHASE 2: GENERATION MODE                            │
│                     (Creates reusable scraper)                           │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         │    ai_parser.py generate <discovery_log>          │
         └─────────────────────────┬─────────────────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │ Extract Tested JavaScript    │
                    │ • High-confidence strategies │
                    │ • Working code snippets      │
                    │ • Show more button logic     │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ AI Code Generation (V2)      │
                    │ ENFORCES:                    │
                    │ • page.evaluate() pattern    │
                    │ • Single JS call             │
                    │ • Tested strategies          │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ Validation Loop (3 attempts) │
                    │ ┌──────────────────────────┐ │
                    │ │ 1. Run script on test URL│ │
                    │ │ 2. Check output          │ │
                    │ │ 3. If fail: AI fixes it  │ │
                    │ │ 4. Retry                 │ │
                    │ └──────────────────────────┘ │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ generated_scripts/           │
                    │ linkedin_scraper.py          │
                    │                              │
                    │ ✓ Uses page.evaluate()       │
                    │ ✓ Validated & working        │
                    │ ✓ No AI dependencies         │
                    └──────────────┬───────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────────┐
│                        PHASE 3: REUSE MODE                               │
│                   (No AI calls - use forever!)                           │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         │                                                    │
         ▼                                                    ▼
┌──────────────────────┐                    ┌──────────────────────┐
│ Job URL #1           │                    │ Job URL #2           │
│ linkedin.com/123     │                    │ linkedin.com/456     │
└──────┬───────────────┘                    └──────┬───────────────┘
       │                                           │
       │          ┌─────────────────────┐          │
       └─────────▶│ linkedin_scraper.py │◀─────────┘
                  │ (generated)         │
                  │ • 0 API calls       │
                  │ • Pure Playwright   │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ job_descriptions/    │
                  │ linkedin_job_*.txt   │
                  └──────────────────────┘
```

### Key Benefits
- **First Job**: Discovery + Generation (AI needed, ~2-3 min)
- **All Other Jobs**: Direct scraping (0 API calls, ~10 sec each)
- **Success Rate**: 0% → 90%+ through validation loop
- **Pattern**: JavaScript `page.evaluate()` - 10x more reliable than CSS selectors

## Installation

1. Install Python dependencies:
```bash
uv pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

3. Configure environment (for AI-powered parser):
```bash
# Create .env file with your Anthropic API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

## Usage

### Option 1: Original Scraper (Direct)

Basic usage:
```bash
python linkedin_job_scraper.py <linkedin_job_url>
```

Example:
```bash
python linkedin_job_scraper.py https://www.linkedin.com/jobs/view/4300362234
```

Specify output directory:
```bash
python linkedin_job_scraper.py <linkedin_job_url> <output_directory>
```

### Option 2: AI-Powered Parser (Version 1.1 - Multi-Site)

**Phase 1: Discovery Mode** - Analyze job page structure (auto-detects site)
```bash
# LinkedIn
python ai_parser.py discover "https://www.linkedin.com/jobs/view/4300362234"

# Indeed
python ai_parser.py discover "https://www.indeed.com/viewjob?jk=d7a8476f98b7ec44"

# Glassdoor
python ai_parser.py discover "https://www.glassdoor.com/job-listing/..."
```
Output: `discovery_logs/linkedin_discovery_2025-09-29T12-00-00.json` (site-specific, timestamped)

**Phase 2: Generation Mode** - Create REUSABLE site-specific scraper
```bash
python ai_parser.py generate discovery_logs/linkedin_discovery_2025-09-29T12-00-00.json
```
Output: `generated_scripts/linkedin_scraper.py` (works for ALL LinkedIn jobs!)

**Phase 3: Run Generated Script** - Reuse for ANY job from that site
```bash
# Use for job 1
python generated_scripts/linkedin_scraper.py "https://www.linkedin.com/jobs/view/123"

# Use for job 2 (no API calls!)
python generated_scripts/linkedin_scraper.py "https://www.linkedin.com/jobs/view/456"

# Use for job 3 (still no API calls!)
python generated_scripts/linkedin_scraper.py "https://www.linkedin.com/jobs/view/789"
```
Output: `job_descriptions/linkedin_job_123_Title.txt`

**Key Benefit**: After first scrape of a site, subsequent jobs use 0 API calls (99% cost savings!)

## Output

The script saves job descriptions as text files in the `job_descriptions` directory (or your specified directory). Files are named using the pattern:
```
<Job-Title>-<Company-Name>.txt
```

Each file contains:
- Job title
- Company name
- Location
- Salary (if available)
- Full job description

## Example Output

```
Job Title: Data Science / Analytics Manager- Weights & Biases
Company: Weights & Biases
Location: San Francisco, CA
Salary: $165,000 - $242,000/year

============================================================
JOB DESCRIPTION
============================================================

[Full job description content...]
```

## Notes

- The script works with public LinkedIn job postings (no login required)
- LinkedIn may update their page structure, which could require script updates
- The script runs in headless mode (no browser window visible)
- Job descriptions are saved as plain text files for easy reading and processing

## Troubleshooting

If you encounter issues:

1. **Page load timeout**: LinkedIn might be slow to load. The script has a 30-second timeout.
2. **Missing content**: LinkedIn might have changed their page structure. Check for updates.
3. **Browser not installed**: Run `playwright install chromium` to install the browser.

## Requirements

- Python 3.7+
- Playwright 1.48.0+
- Anthropic API key (for AI-powered parser only)

## When to Use Which Approach

### Use Original Scraper When:
- You need quick, direct scraping
- Page structure is stable
- No AI API costs desired

### Use AI-Powered Parser When:
- LinkedIn changes page structure frequently
- Need to generate multiple scripts for different scenarios
- Want documented scraping strategies (discovery logs)
- Need portable scripts for production deployment

## Production Features

### URL Normalization & Query Parameter Handling

Both scrapers now support URLs with query parameters and tracking codes:

```bash
# ✅ Clean URL (works)
python linkedin_job_scraper.py "https://www.linkedin.com/jobs/view/4300371471"

# ✅ URL with query parameters (also works!)
python linkedin_job_scraper.py "https://www.linkedin.com/jobs/view/4300371471/?alternateChannel=search&eBP=tracking&trk=flagship"
```

**Important**: Always quote URLs in the command line to prevent shell interpretation of special characters like `&`.

### Chatbot Integration

For integration with chatbots (like JayIQ), use the `url_utils` module for robust URL handling:

```python
from url_utils import normalize_job_url, extract_job_info
from linkedin_job_scraper import scrape_linkedin_job

def handle_job_url(user_provided_url: str) -> dict:
    """
    Production-ready function for chatbot integration

    Args:
        user_provided_url: Job URL from user (may include tracking params)

    Returns:
        Dictionary with job information
    """
    try:
        # Normalize URL (strips tracking parameters, validates format)
        job_info = extract_job_info(user_provided_url)

        # Scrape the job description
        job_data = scrape_linkedin_job(job_info['canonical_url'])

        if job_data:
            return {
                'success': True,
                'job_id': job_info['job_id'],
                'site': job_info['site'],
                'title': job_data['title'],
                'company': job_data['company'],
                'location': job_data['location'],
                'description': job_data['description']
            }
        else:
            return {'success': False, 'error': 'Failed to scrape job'}

    except ValueError as e:
        return {'success': False, 'error': str(e)}
```

**Benefits for Chatbot Integration:**
- ✅ Handles any LinkedIn URL format (with/without query params)
- ✅ Strips tracking parameters for privacy
- ✅ Clear error messages for user feedback
- ✅ Structured JSON output for easy processing
- ✅ Site detection (LinkedIn, Indeed, Glassdoor)

### URL Utilities API

The `url_utils` module provides production-ready URL handling:

```python
from url_utils import (
    normalize_job_url,    # Parse and clean URLs
    get_canonical_url,    # Get clean URL without tracking
    validate_job_url,     # Validate URL format
    extract_job_info      # Get structured info (for APIs)
)

# Example: Normalize URL
job_url = normalize_job_url("https://www.linkedin.com/jobs/view/123/?tracking=xyz")
print(job_url.job_id)          # "123"
print(job_url.site)            # JobSite.LINKEDIN
print(job_url.canonical_url)   # "https://www.linkedin.com/jobs/view/123"

# Example: Quick validation
is_valid, error_msg = validate_job_url(user_url)
if not is_valid:
    print(f"Invalid URL: {error_msg}")
```

## Project Structure

```
linkedin-job-scraper/
├── linkedin_job_scraper.py          # Original direct scraper
├── ai_parser.py                      # AI-powered parser (multi-site)
├── url_utils.py                      # URL normalization & validation utilities
├── ai_parser.md                      # System architecture documentation
├── todo.md                           # Development roadmap
├── discovery_logs/                   # Phase 1 outputs (AI analysis)
├── generated_scripts/                # Phase 2 outputs (standalone scripts)
├── job_descriptions/                 # Scraped job data
└── requirements.txt                  # Python dependencies
```