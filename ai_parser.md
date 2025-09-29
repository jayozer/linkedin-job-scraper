# AI-Driven LinkedIn Job Parser System

## Overview
Transform the existing Playwright-based scraper into an AI-powered system that:
1. **Phase 1**: Uses Anthropic API with Playwright MCP to interactively scrape LinkedIn jobs and document steps
2. **Phase 2**: Converts documented steps into standalone Playwright scripts using code execution tool

## Current State Analysis
- Existing script: `linkedin_job_scraper.py` - synchronous Playwright scraper
- Extracts: title, company, location, salary, description
- Handles: dynamic content, modal dismissal, fallback selectors
- Transport: Headless Chromium with custom user-agent

## Architecture

### Core Components

#### 1. **AI Agent Script** (`ai_linkedin_parser.py`)
- Anthropic API client with tool support
- Integrated MCP tools: Playwright MCP + Code Execution
- Two operational modes:
  - **Discovery Mode**: Explore job page, record actions, document observations
  - **Code Generation Mode**: Convert recorded steps to standalone script

#### 2. **Playwright MCP Integration**
Based on documentation, the system will use:
- `mcp__playwright__browser_navigate` - Navigate to job URLs
- `mcp__playwright__browser_snapshot` - Capture page state (better than screenshots)
- `mcp__playwright__browser_click` - Interact with elements (dismiss modals)
- `mcp__playwright__browser_evaluate` - Extract job data via JavaScript
- `mcp__playwright__browser_wait_for` - Handle dynamic content

#### 3. **Code Execution Tool**
- Python REPL environment for generating and testing scripts
- Converts AI observations → Playwright code patterns
- Validates generated scripts before output

### System Flow

```
┌─────────────────────────────────────────────┐
│  User Input: LinkedIn Job URL               │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  PHASE 1: DISCOVERY MODE                    │
│  ─────────────────────────                  │
│  Anthropic API + Playwright MCP             │
│  • Navigate to URL                          │
│  • Take snapshots at each step              │
│  • Click modals/interact as needed          │
│  • Evaluate selectors for data              │
│  • Document findings in structured format   │
│  Output: JSON log of actions + observations │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  PHASE 2: CODE GENERATION MODE              │
│  ────────────────────────────              │
│  Anthropic API + Code Execution Tool        │
│  • Analyze discovery log                    │
│  • Generate standalone Playwright script    │
│  • Use code execution to validate syntax    │
│  • Apply patterns from existing scraper     │
│  Output: Pure Playwright Python script      │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  Generated Script: linkedin_job_parser.py   │
│  • Self-contained, no AI dependencies       │
│  • Can be version-controlled                │
│  • Reproducible on any environment          │
└─────────────────────────────────────────────┘
```

## Implementation Details

### Tool Definitions for Anthropic API

The system integrates multiple tools via the Anthropic Messages API:

```python
tools = [
    # Playwright MCP tools (bridged via MCP client)
    {
        "name": "browser_navigate",
        "description": "Navigate browser to URL",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_snapshot",
        "description": "Capture accessibility snapshot of current page",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "browser_click",
        "description": "Click element on page",
        "input_schema": {
            "type": "object",
            "properties": {
                "element": {"type": "string", "description": "Human-readable element description"},
                "ref": {"type": "string", "description": "Element reference from snapshot"}
            },
            "required": ["element", "ref"]
        }
    },
    {
        "name": "browser_evaluate",
        "description": "Execute JavaScript on the page",
        "input_schema": {
            "type": "object",
            "properties": {
                "function": {"type": "string", "description": "JavaScript function to execute"}
            },
            "required": ["function"]
        }
    },
    # Code execution tool
    {
        "name": "execute_python",
        "description": "Execute Python code to generate/test scripts",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"}
            },
            "required": ["code"]
        }
    }
]
```

### Discovery Mode System Prompt

```
You are a web scraping expert analyzing a LinkedIn job posting.

Your task: Explore the LinkedIn job page and document every action needed to extract job data.

Available tools:
- browser_navigate: Navigate to URLs
- browser_snapshot: Capture current page state (use this frequently!)
- browser_click: Interact with elements (dismiss modals, expand content)
- browser_evaluate: Execute JavaScript to extract data

Process:
1. Navigate to the provided LinkedIn job URL
2. Take snapshot to understand initial page structure
3. Check for and dismiss any modal dialogs
4. Wait for dynamic content to load
5. Identify selectors for: title, company, location, salary, description
6. Test extraction with browser_evaluate
7. Document ALL findings in structured format

Output format:
{
  "job_id": "extracted from URL",
  "url": "original URL",
  "actions": [
    {
      "step": 1,
      "action": "navigate",
      "details": "navigated to URL",
      "observations": "page loaded, modal present"
    },
    {
      "step": 2,
      "action": "click",
      "element": "dismiss button",
      "selector": "button:has-text('Dismiss')",
      "observations": "modal dismissed successfully"
    },
    ...
  ],
  "data_extraction": {
    "title": {
      "selector": "h1",
      "strategy": "querySelector with textContent",
      "fallback": null
    },
    "company": {
      "selector": "a[data-tracking-control-name*='topcard-org-name']",
      "strategy": "querySelector with textContent.trim()",
      "fallback": "a[data-tracking-control-name*='topcard_org_name']"
    },
    ...
  },
  "edge_cases": [
    "Modal may or may not appear",
    "Salary field is optional",
    "Location parsing requires regex"
  ]
}

Be thorough. Every detail matters for code generation in Phase 2.
```

### Code Generation Mode System Prompt

```
You are a Python developer specializing in Playwright automation.

Your task: Convert the discovery log into a standalone, production-ready Playwright script.

Input: JSON discovery log from Phase 1 containing:
- Actions taken during discovery
- Selectors identified for each data field
- Edge cases and fallback strategies

Output: A complete Python script that:
1. Uses sync_playwright API (not async)
2. Matches the structure of the existing linkedin_job_scraper.py
3. Implements all functions: sanitize_filename, extract_job_id, scrape_linkedin_job, format_job_description, main
4. Includes robust error handling (TimeoutError, missing elements)
5. Uses fallback selectors where provided
6. Saves output to job_descriptions/ directory
7. Can run independently without any AI/MCP dependencies

Requirements:
- Browser: chromium, headless=True
- Viewport: 1920x1080
- User agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
- Timeout: 60000ms for navigation, 15000ms for selectors
- Wait after load: 3 seconds for dynamic content
- Modal handling: Try to dismiss "Dismiss" button if visible

Validation:
- Use execute_python tool to validate syntax before final output
- Ensure all imports are standard (no AI/MCP libraries)
- Test that the script structure matches the original

Output the complete script as a single code block.
```

### MCP Integration Pattern

The system bridges Anthropic API tool calls to MCP Playwright tools:

```python
from anthropic import Anthropic
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

# Initialize MCP client for Playwright
mcp_server_params = StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-playwright"]
)

async def run_discovery_mode(job_url: str):
    """Run Phase 1: Discovery Mode"""

    # Connect to Playwright MCP server
    async with stdio_client(mcp_server_params) as (read, write):
        async with ClientSession(read, write) as mcp_session:
            await mcp_session.initialize()

            # Initialize Anthropic client with streaming
            anthropic_client = Anthropic()

            # System prompt for discovery
            system_prompt = "You are a web scraping expert..."

            # Start conversation with streaming
            messages = [
                {
                    "role": "user",
                    "content": f"Analyze this LinkedIn job posting: {job_url}"
                }
            ]

            # Stream responses and handle tool calls
            with anthropic_client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=tool_definitions
            ) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            # Handle tool call by routing to MCP
                            tool_name = event.content_block.name
                            tool_input = event.content_block.input

                            # Route to appropriate MCP tool
                            result = await execute_mcp_tool(
                                mcp_session,
                                tool_name,
                                tool_input
                            )

                            # Return result to Claude
                            messages.append({
                                "role": "assistant",
                                "content": [event.content_block]
                            })
                            messages.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": event.content_block.id,
                                    "content": str(result)
                                }]
                            })
```

## File Structure

```
linkedin-job-scraper/
├── linkedin_job_scraper.py          # Original (keep as reference)
├── ai_linkedin_parser.py             # NEW: AI agent orchestrator
├── discovery_logs/                   # NEW: Phase 1 outputs
│   └── job_{id}_discovery.json
├── generated_scripts/                # NEW: Phase 2 outputs
│   └── job_{id}_scraper.py
├── job_descriptions/                 # Existing output directory
├── .env                              # API keys
├── requirements.txt                  # Update with new deps
├── ai_linkedin_parser.md             # This document
├── todo.md                           # Development checklist
└── README.md                         # Update with new usage
```

## Dependencies

```txt
# Core
anthropic>=0.40.0         # API client with streaming + tools
playwright>=1.48.0        # Browser automation
pydantic>=2.0.0           # Data validation

# MCP
mcp>=1.1.0                # Model Context Protocol client

# Utilities
python-dotenv>=1.0.0      # Environment variable management
```

## Usage

### Discovery Mode (Phase 1)

```bash
# Discover and document scraping strategy
python ai_linkedin_parser.py discover "https://www.linkedin.com/jobs/view/4300362234"

# Output: discovery_logs/job_4300362234_discovery.json
```

### Code Generation Mode (Phase 2)

```bash
# Generate standalone script from discovery log
python ai_linkedin_parser.py generate discovery_logs/job_4300362234_discovery.json

# Output: generated_scripts/job_4300362234_scraper.py
```

### Run Generated Script

```bash
# Use generated script independently (no AI needed)
python generated_scripts/job_4300362234_scraper.py "https://www.linkedin.com/jobs/view/9876543210"

# Output: job_descriptions/Job-Title-Company-Name.txt
```

### Full Workflow

```bash
# 1. Discover
python ai_linkedin_parser.py discover "https://www.linkedin.com/jobs/view/123"

# 2. Generate
python ai_linkedin_parser.py generate discovery_logs/job_123_discovery.json

# 3. Use generated script
python generated_scripts/job_123_scraper.py "https://www.linkedin.com/jobs/view/456"
```

## Key Advantages

1. **Adaptive**: AI can handle LinkedIn page structure changes automatically
2. **Transparent**: Discovery logs show AI's decision-making process
3. **Portable**: Generated scripts have no AI dependencies, pure Playwright
4. **Maintainable**: Version control generated scripts like regular code
5. **Educational**: Discovery logs serve as documentation and learning resource
6. **Cost-Effective**: Only use AI for discovery/generation, not every scrape
7. **Debugging**: Clear separation between exploration and execution phases

## Security Considerations

- Store `ANTHROPIC_API_KEY` in `.env` file (never commit)
- MCP Playwright server runs locally (no remote access)
- Generated scripts contain no credentials or secrets
- Discovery logs may contain page content (review before sharing)

## Troubleshooting

### MCP Server Connection Issues
```bash
# Test Playwright MCP server manually
npx -y @modelcontextprotocol/server-playwright
```

### Discovery Mode Hangs
- Check Anthropic API key is valid
- Verify Playwright MCP server is running
- Increase timeout values in configuration

### Generated Script Fails
- Review discovery log for incomplete data
- Check if LinkedIn changed page structure
- Re-run discovery mode with updated URL

## Future Enhancements

1. **Multi-page Support**: Extend to scrape job search results
2. **Schema Validation**: Add Pydantic models for job data
3. **Caching**: Cache discovery logs to avoid re-analysis
4. **Testing**: Generate pytest tests alongside scripts
5. **Monitoring**: Track LinkedIn page structure changes
6. **Batch Processing**: Parallel discovery for multiple URLs

---

## Version 1.1 - Multi-Site Support Architecture

### Problem Statement

**Current Limitation (Version 1.0)**:
- System generates **job-specific** scripts: `job_4292996578_scraper.py`, `job_4300362234_scraper.py`
- Each job URL triggers discovery and generation (2 API calls every time)
- LinkedIn structure is **identical for all jobs** - we're creating duplicate scripts
- No reusability: Same scraping logic regenerated for every single job
- API cost scales linearly with number of jobs

**Why This Is Inefficient**:
```
Job 1: https://linkedin.com/jobs/view/123
  → Discovery (AI analysis) → job_123_scraper.py
  → Result: Works for job 123 ONLY

Job 2: https://linkedin.com/jobs/view/456
  → Discovery (AI analysis) → job_456_scraper.py
  → Result: Same logic, different hardcoded URL

Issue: Both scripts are 99% identical, only the job_id differs!
```

### Solution Overview

**Version 1.1 Architecture**:
- Generate **site-specific** scrapers: `linkedin_scraper.py`, `indeed_scraper.py`, `glassdoor_scraper.py`
- Each scraper is **reusable** - accepts any job URL from that site as parameter
- **Try existing scraper first** → Fallback to discovery only if it fails
- API calls only when:
  1. First time scraping a site (no scraper exists)
  2. Existing scraper fails (site structure changed)
- API cost becomes **nearly zero** after initial discovery

**Efficiency Gain**:
```
First Job (LinkedIn): https://linkedin.com/jobs/view/123
  → No existing scraper found
  → Discovery + Generation → linkedin_scraper.py
  → API calls: 2

Second Job (LinkedIn): https://linkedin.com/jobs/view/456
  → Found linkedin_scraper.py
  → Run existing script with new URL
  → API calls: 0 ✓

Third Job (LinkedIn): https://linkedin.com/jobs/view/789
  → Use linkedin_scraper.py
  → API calls: 0 ✓

LinkedIn Changes Structure:
  → Existing scraper fails
  → Auto-fallback to discovery + regenerate
  → API calls: 2 (one-time fix)
```

### New Workflow

#### Primary Command: `scrape` (Automatic)

```bash
# Single command handles everything
python ai_parser.py scrape "https://www.linkedin.com/jobs/view/123"

# What happens internally:
1. Detect site from URL → "linkedin"
2. Check if generated_scripts/linkedin_scraper.py exists
   YES → Try to run it with the URL
     SUCCESS → Save result, done! (0 API calls)
     FAILURE → Continue to step 3
   NO → Continue to step 3
3. Run discovery mode (AI analyzes page structure)
4. Generate linkedin_scraper.py (AI creates reusable script)
5. Validate with code execution tool
6. Run the new scraper with the URL
7. Save result
```

#### Manual Commands (Debugging)

```bash
# Force regeneration (skip trying existing scraper)
python ai_parser.py scrape URL --force-regenerate

# Manual discovery (for debugging site structure)
python ai_parser.py discover URL --site linkedin

# Manual generation from discovery log
python ai_parser.py generate discovery_log.json
```

### Key Architecture Changes

#### 1. Site Detection

**New Component**: `detect_job_site(url: str) -> JobSite`

```python
from enum import Enum
from dataclasses import dataclass

class JobSite(Enum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"

@dataclass
class SiteConfig:
    name: str
    display_name: str
    url_pattern: str  # Regex pattern
    job_id_pattern: str

SITE_CONFIGS = {
    JobSite.LINKEDIN: SiteConfig(
        name="linkedin",
        display_name="LinkedIn",
        url_pattern=r"linkedin\.com/jobs",
        job_id_pattern=r"/jobs/view/(\d+)"  # Path-based
    ),
    JobSite.INDEED: SiteConfig(
        name="indeed",
        display_name="Indeed",
        url_pattern=r"indeed\.com/viewjob",
        job_id_pattern=r"\?jk=([a-f0-9]+)"  # Query param
    ),
    JobSite.GLASSDOOR: SiteConfig(
        name="glassdoor",
        display_name="Glassdoor",
        url_pattern=r"glassdoor\.com/job-listing",
        job_id_pattern=r"-JV_IC(\d+)"  # Mixed pattern
    )
}

def detect_job_site(url: str) -> JobSite:
    """Auto-detect job site from URL"""
    for site, config in SITE_CONFIGS.items():
        if re.search(config.url_pattern, url):
            return site
    raise ValueError(f"Unsupported job site: {url}")
```

#### 2. Generic Scraper Structure

**Generated Scripts Accept URL Parameter**:

```python
# OLD (Version 1.0): Job-specific, hardcoded
def main():
    url = "https://www.linkedin.com/jobs/view/4292996578"  # HARDCODED
    job_id = "4292996578"  # HARDCODED
    scrape_linkedin_job(url)

# NEW (Version 1.1): Site-generic, accepts parameter
def main(job_url: str = None):
    """Scrape any LinkedIn job given its URL"""
    if job_url is None:
        import argparse
        parser = argparse.ArgumentParser(description='Scrape LinkedIn job posting')
        parser.add_argument('url', help='LinkedIn job URL')
        args = parser.parse_args()
        job_url = args.url

    job_id = extract_job_id(job_url)  # DYNAMIC extraction
    scrape_linkedin_job(job_url)

if __name__ == "__main__":
    main()
```

**Usage**:
```bash
# Can accept any LinkedIn job URL
python linkedin_scraper.py "https://www.linkedin.com/jobs/view/123"
python linkedin_scraper.py "https://www.linkedin.com/jobs/view/456"
python linkedin_scraper.py "https://www.linkedin.com/jobs/view/789"
```

#### 3. Execution Strategy

**New Function**: `try_existing_scraper(site: JobSite, job_url: str) -> Optional[Dict]`

```python
def try_existing_scraper(site: JobSite, job_url: str) -> Optional[Dict]:
    """
    Try to run existing site-specific scraper.
    Returns result dict if successful, None if failed/not found.
    """
    script_path = Path(f"generated_scripts/{site.value}_scraper.py")

    # Check if scraper exists
    if not script_path.exists():
        logging.info(f"No existing {site.value} scraper found")
        return None

    # Try to run existing scraper
    try:
        logging.info(f"Trying existing {site.value}_scraper.py...")
        result = subprocess.run(
            [sys.executable, str(script_path), job_url],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0 and "Job description saved to:" in result.stdout:
            logging.info(f"✓ Existing scraper succeeded")
            return parse_scraper_output(result.stdout)
        else:
            logging.warning(f"✗ Existing scraper failed: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        logging.warning(f"✗ Existing scraper timed out")
        return None
    except Exception as e:
        logging.error(f"✗ Error running existing scraper: {e}")
        return None
```

**Fallback Logic**:
```python
async def scrape_job(job_url: str, force_regenerate: bool = False):
    """Main scraping function with fallback logic"""

    # Detect site
    site = detect_job_site(job_url)

    # Try existing scraper (unless forced to regenerate)
    if not force_regenerate:
        result = try_existing_scraper(site, job_url)
        if result is not None:
            return result  # SUCCESS - no API calls needed!

    # Fallback: Run discovery + generation
    logging.info("Falling back to discovery mode...")
    discovery_log = await run_discovery_mode(job_url, site)
    script_path = await run_generation_mode(discovery_log, site)

    # Run the newly generated scraper
    result = try_existing_scraper(site, job_url)
    return result
```

#### 4. CLI Changes

**New Command Structure**:

```python
# Primary interface: scrape (automatic workflow)
parser.add_subparsers(dest='command')

scrape_parser = subparsers.add_parser('scrape',
    help='Scrape a job posting (auto-detects site, tries existing scraper)')
scrape_parser.add_argument('url', help='Job posting URL')
scrape_parser.add_argument('--force-regenerate', action='store_true',
    help='Skip existing scraper, always run discovery')
scrape_parser.add_argument('--site', choices=['linkedin', 'indeed', 'glassdoor'],
    help='Manually specify site (overrides auto-detection)')

# Manual interface: discover + generate (debugging)
discover_parser = subparsers.add_parser('discover',
    help='Run discovery mode only (for debugging)')
discover_parser.add_argument('url', help='Job posting URL')
discover_parser.add_argument('--site', choices=['linkedin', 'indeed', 'glassdoor'])

generate_parser = subparsers.add_parser('generate',
    help='Generate script from discovery log')
generate_parser.add_argument('log_path', help='Path to discovery log JSON')
```

#### 5. Discovery Log Changes

**Naming Convention**:

```python
# OLD (Version 1.0): Job-specific
discovery_logs/job_4292996578_discovery.json
discovery_logs/job_4300362234_discovery.json

# NEW (Version 1.1): Site-specific with timestamp
discovery_logs/linkedin_discovery_2025-09-29T12-00-00.json
discovery_logs/linkedin_discovery_2025-10-01T15-30-00.json
discovery_logs/indeed_discovery_2025-09-29T13-00-00.json
```

**Benefits**:
- Keeps history of site structure changes
- Allows comparison over time
- Easy to find latest discovery for a site

**Helper Function**:
```python
def get_latest_discovery_log(site: JobSite) -> Optional[Path]:
    """Find most recent discovery log for a site"""
    logs = sorted(Path("discovery_logs").glob(f"{site.value}_discovery_*.json"))
    return logs[-1] if logs else None
```

#### 6. Generation Prompt Changes

**OLD System Prompt (Job-Specific)**:
```
You are generating a scraper for this specific LinkedIn job.
The script should scrape job ID 4292996578.
```

**NEW System Prompt (Site-Generic)**:
```
You are generating a REUSABLE scraper for {site_name}.

CRITICAL: This script will be used for MANY different jobs on {site_name}.
It must:
1. Accept job_url as a command-line argument
2. Extract job_id DYNAMICALLY from the provided URL
3. Work for ANY job on {site_name}, not just one specific job
4. Never hardcode job-specific information (IDs, titles, etc.)

Example usage:
  python {site}_scraper.py "https://{site}.com/jobs/view/123"
  python {site}_scraper.py "https://{site}.com/jobs/view/456"

The scraper must handle different jobs with the same logic.
```

#### 7. Validation Changes

**Multi-URL Validation**:

```python
def validate_generated_scraper_multi_url(script_path: Path, test_urls: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that generated scraper works with multiple URLs.
    Ensures reusability.
    """
    issues = []

    for test_url in test_urls:
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), test_url],
                capture_output=True,
                timeout=30
            )

            if result.returncode != 0:
                issues.append(f"Failed for URL: {test_url}")

        except subprocess.TimeoutExpired:
            issues.append(f"Timeout for URL: {test_url}")
        except Exception as e:
            issues.append(f"Error for URL {test_url}: {e}")

    return len(issues) == 0, issues

# Usage in generation mode
test_urls = [
    "https://www.linkedin.com/jobs/view/123",
    "https://www.linkedin.com/jobs/view/456",
    "https://www.linkedin.com/jobs/view/789"
]
is_valid, issues = validate_generated_scraper_multi_url(script_path, test_urls)
```

### File Structure Changes

#### Before (Version 1.0)

```
linkedin-job-scraper/
├── generated_scripts/
│   ├── job_4292996578_scraper.py    ❌ Job-specific, not reusable
│   ├── job_4300362234_scraper.py    ❌ Duplicate logic
│   └── job_4305678901_scraper.py    ❌ More duplication
├── discovery_logs/
│   ├── job_4292996578_discovery.json
│   ├── job_4300362234_discovery.json
│   └── job_4305678901_discovery.json
└── ai_linkedin_parser.py
```

#### After (Version 1.1)

```
linkedin-job-scraper/
├── generated_scripts/
│   ├── linkedin_scraper.py          ✅ Site-specific, reusable for ALL LinkedIn jobs
│   ├── indeed_scraper.py            ✅ Site-specific, reusable for ALL Indeed jobs
│   └── glassdoor_scraper.py         ✅ Site-specific, reusable for ALL Glassdoor jobs
├── discovery_logs/
│   ├── linkedin_discovery_2025-09-29T12-00-00.json    ✅ Timestamped history
│   ├── linkedin_discovery_2025-10-01T15-30-00.json    ✅ Tracks site changes
│   ├── indeed_discovery_2025-09-29T13-00-00.json      ✅ Multi-site support
│   └── glassdoor_discovery_2025-09-29T14-00-00.json
├── job_descriptions/
│   ├── linkedin_job_4292996578_Lead_Data_Architect.txt    ✅ Job-specific results
│   ├── linkedin_job_4300362234_Senior_Engineer.txt
│   ├── indeed_job_abc123_Product_Manager.txt
│   └── glassdoor_job_xyz789_Designer.txt
└── ai_parser.py                     ✅ Renamed (multi-site support)
```

### API Efficiency Comparison

#### Version 1.0 API Usage

```
Job 1: https://linkedin.com/jobs/view/123
  → Discovery API call: 1
  → Generation API call: 1
  → Total: 2 API calls

Job 2: https://linkedin.com/jobs/view/456
  → Discovery API call: 1
  → Generation API call: 1
  → Total: 2 API calls

Job 3: https://linkedin.com/jobs/view/789
  → Discovery API call: 1
  → Generation API call: 1
  → Total: 2 API calls

Total for 100 jobs: 200 API calls
Cost (at $3/million input tokens): ~$0.60 - $1.20
```

#### Version 1.1 API Usage

```
Job 1 (LinkedIn): https://linkedin.com/jobs/view/123
  → No existing scraper found
  → Discovery API call: 1
  → Generation API call: 1
  → Total: 2 API calls

Job 2 (LinkedIn): https://linkedin.com/jobs/view/456
  → Found linkedin_scraper.py
  → Run existing scraper: 0 API calls ✓
  → Total: 0 API calls

Job 3 (LinkedIn): https://linkedin.com/jobs/view/789
  → Use linkedin_scraper.py
  → Total: 0 API calls ✓

... (Jobs 4-99, same as above)

Job 100 (LinkedIn): https://linkedin.com/jobs/view/999
  → Use linkedin_scraper.py
  → Total: 0 API calls ✓

Total for 100 jobs: 2 API calls (first job only)
Cost: ~$0.006 - $0.012

Savings: 99% reduction in API costs! 🎉
```

### Multi-Site Support

**Supported Sites**:

| Site | URL Pattern | Job ID Pattern | Complexity |
|------|-------------|----------------|------------|
| **LinkedIn** | `linkedin.com/jobs/view/{id}` | Path-based: `/jobs/view/(\d+)` | Medium (modals, show-more) |
| **Indeed** | `indeed.com/viewjob?jk={id}` | Query param: `?jk=([a-f0-9]+)` | Low (simple structure) |
| **Glassdoor** | `glassdoor.com/job-listing/...` | Mixed: `-JV_IC(\d+)` | High (login walls) |

**Extensibility**:

Adding a new site is straightforward:

```python
# 1. Add to JobSite enum
class JobSite(Enum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    ZIPRECRUITER = "ziprecruiter"  # NEW

# 2. Add site config
SITE_CONFIGS[JobSite.ZIPRECRUITER] = SiteConfig(
    name="ziprecruiter",
    display_name="ZipRecruiter",
    url_pattern=r"ziprecruiter\.com/jobs",
    job_id_pattern=r"/jobs/[^/]+/(\d+)"
)

# 3. Run discovery once
python ai_parser.py discover "https://www.ziprecruiter.com/jobs/example/123"

# 4. Done! Now scrape any ZipRecruiter job
python ai_parser.py scrape "https://www.ziprecruiter.com/jobs/another/456"
```

### Migration Guide

**For Existing Version 1.0 Users**:

```bash
# Step 1: Rename old scripts to legacy (optional)
mkdir legacy
mv generated_scripts/job_*_scraper.py legacy/

# Step 2: Regenerate as site-specific scraper
python ai_parser.py scrape "https://www.linkedin.com/jobs/view/4292996578"
# This creates linkedin_scraper.py

# Step 3: Use new scraper for all LinkedIn jobs
python ai_parser.py scrape "https://www.linkedin.com/jobs/view/ANY_JOB_ID"
# Reuses linkedin_scraper.py, 0 API calls ✓

# Step 4: Update any automation scripts
# OLD: python generated_scripts/job_123_scraper.py
# NEW: python ai_parser.py scrape "URL"
```

### Benefits Summary

1. **Reusability**: One scraper per site, not per job (90%+ code reduction)
2. **API Efficiency**: 99% fewer API calls after initial discovery
3. **Cost Savings**: ~$1.20 → ~$0.01 per 100 jobs (100x cheaper)
4. **Multi-Site**: Easy to add Indeed, Glassdoor, etc.
5. **Automatic Fallback**: Self-healing when sites change structure
6. **Better Organization**: Site-specific scripts, timestamped discovery logs
7. **Backward Compatible**: Old discovery logs still work
8. **Scalable**: Can scrape thousands of jobs with minimal API usage

### Performance Targets

| Metric | Version 1.0 | Version 1.1 | Improvement |
|--------|-------------|-------------|-------------|
| First job (same site) | ~40s | ~40s | Same |
| Second job (same site) | ~40s | ~5-10s | **4-8x faster** |
| API calls (100 jobs) | 200 | 2-5 | **40-100x fewer** |
| Cost (100 jobs) | $1.20 | $0.01 | **120x cheaper** |
| Scripts generated | 100 | 1-3 | **33-100x fewer** |

### Implementation Status

See `todo.md` **Phase 11: Version 1.1 - Multi-Site Support** for detailed implementation tasks (55 tasks across 8 sub-phases).

**Estimated Implementation Time**: 5-7 hours with comprehensive testing

**Ready to implement**: All architecture decisions finalized ✓

---

## Version 1.2 - Perfect AI-Generated Scrapers

### Problem Statement

**Critical Issue**: AI-generated scrapers have 0% success rate while original scraper has 100% success rate.

#### Comparison

| Aspect | Original Scraper | AI-Generated Scraper | Result |
|--------|------------------|----------------------|--------|
| **Success Rate** | 100% | 0% (timeouts) | ❌ FAILS |
| **Extraction Method** | `page.evaluate()` with JavaScript | `page.wait_for_selector()` with CSS | ❌ FRAGILE |
| **Discovery Testing** | N/A (hardcoded) | Zero live testing | ❌ GUESSING |
| **Validation** | Manual testing | None | ❌ NO FEEDBACK |
| **Evidence Base** | Direct coding | AI guesses selectors | ❌ NO PROOF |

#### Root Cause Analysis

**Why Original Works**:
```python
# Original scraper (linkedin_job_scraper.py:97-149)
job_data = page.evaluate('''() => {
    // Single atomic JavaScript operation in browser context
    const titleElement = document.querySelector('h1');
    const jobTitle = titleElement ? titleElement.textContent.trim() : 'Unknown Job';

    const mainContent = document.querySelector('div.show-more-less-html__markup');
    const jobDescription = mainContent ? mainContent.innerText : '';

    return {
        title: jobTitle,
        description: jobDescription,
        // ... other fields
    };
}''')
```

**Key Success Factors**:
1. **Single atomic operation**: All data extracted in one browser context evaluation
2. **Simple selectors**: `h1`, `div.show-more-less-html__markup` - stable patterns
3. **Direct DOM access**: No race conditions, no round trips
4. **Fallback built-in**: `element ? element.text : 'Unknown'` pattern

**Why AI-Generated Fails**:
```python
# AI-generated scraper (generated_scripts/linkedin_scraper.py:54-76)
for selector in title_selectors:
    try:
        title_element = page.wait_for_selector(selector, timeout=15000)  # Round trip
        if title_element:
            job_data['title'] = title_element.text_content().strip()  # Round trip
            break
    except:
        continue
```

**Failure Modes**:
1. **Multiple round trips**: Each field requires separate Python ↔ browser communication
2. **Guessed selectors**: `.job-details-jobs-unified-top-card__job-title h1` - AI hallucinated without seeing HTML
3. **No evidence**: Discovery sent zero HTML to Claude, just generic prompt
4. **No validation**: Generated → saved → never tested

#### Discovery Mode Gap

**Current Discovery**:
```python
# What Claude receives (ai_parser.py:586-611)
analysis_prompt = f"""Analyze this LinkedIn job posting page.

URL: {job_url}
Site: LinkedIn
Page Title: {page_title}
Modal Dialog Present: {modal_present}

Based on standard LinkedIn job page structure, provide a complete data extraction strategy.
"""
# NO HTML, NO TESTING, NO PROOF
```

**What Claude Needs**:
```python
analysis_prompt = f"""Analyze this LinkedIn job posting.

I have TESTED these extraction strategies and they WORK:

Title extraction results:
[
  {{
    "strategy": "javascript_evaluation",
    "code": "document.querySelector('h1').textContent",
    "success": true,
    "sample": "Engineering Manager, API Product...",
    "confidence": "high"
  }}
]

Description extraction results:
[
  {{
    "strategy": "javascript_evaluation",
    "code": "document.querySelector('div.show-more-less-html__markup').innerText",
    "success": true,
    "sample": "About Anthropic\n\nAnthropic's mission is to create...",
    "length": 2847,
    "confidence": "high"
  }}
]

HTML samples from the page:
Title area: <h1>Engineering Manager, API Product...</h1>
Description area: <div class="show-more-less-html__markup">About Anthropic...</div>

Use EXACTLY these tested strategies that have "confidence": "high".
"""
```

### Solution Architecture

#### Core Principles

1. **Evidence Over Guessing**: Test 10+ strategies during discovery, save what works
2. **JavaScript Over CSS**: Require `page.evaluate()` pattern in generated code
3. **Validation Over Hope**: Test generated scripts immediately, iterate until working
4. **Real HTML Over Generic Prompts**: Send actual DOM snippets to Claude

#### Four-Phase Enhancement

```
┌──────────────────────────────────────────────────────┐
│ Phase 1: Evidence-Based Discovery                   │
│ ────────────────────────────────────                │
│ • Open page with Playwright                          │
│ • Test 10+ extraction strategies per field           │
│ • Test JavaScript evaluation (like original)         │
│ • Test "show more" button clicking                   │
│ • Capture HTML snippets of working elements          │
│ • Send PROOF to Claude: "This JS code WORKS: {...}"  │
│                                                       │
│ Output: Discovery log with tested_strategies,        │
│         html_samples, show_more_strategy             │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│ Phase 2: JavaScript-First Generation                │
│ ────────────────────────────────                    │
│ • Use CODE_GENERATION_SYSTEM_PROMPT_V2               │
│ • REQUIRE: "Script MUST use page.evaluate()"         │
│ • PROVIDE: Exact JavaScript code from discovery      │
│ • TEMPLATE: Single page.evaluate() for all fields    │
│ • VALIDATE: Check for page.evaluate() in code        │
│                                                       │
│ Output: Script using page.evaluate() with            │
│         tested JavaScript from discovery log         │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│ Phase 3: Validation Loop                            │
│ ────────────────────────                            │
│ • Run generated script on test job                   │
│ • Check output: length > 500 chars?                  │
│ • If FAIL: Send error + discovery log to AI          │
│ • Request fix: "Use the working JS: {code}"          │
│ • Retry (max 3 attempts)                             │
│ • Only save when validation passes                   │
│                                                       │
│ Output: Validated, working scraper                   │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│ Phase 4: Multi-Job Validation                       │
│ ────────────────────────                            │
│ • Test scraper with 3 different jobs                 │
│ • Verify: 100% success rate (3/3)                    │
│ • If <100%: Analyze failures, improve discovery      │
│                                                       │
│ Output: Production-ready scraper                     │
└──────────────────────────────────────────────────────┘
```

### Implementation Details

#### Phase 1: Evidence-Based Discovery

**New Function: `test_extraction_strategies()`**

```python
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
            "sample": "Engineering Manager, API Product (Several API Teams Hiring)",
            "length": 57,
            "confidence": "high"
        },
        {
            "strategy": "css_selector",
            "selector": "h1.top-card-layout__title",
            "success": True,
            "sample": "Engineering Manager...",
            "length": 57,
            "confidence": "medium"
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
        except Exception as e:
            logging.debug(f"JS evaluation failed for {field_name}: {e}")

    # Strategy 2: Common CSS selectors (FALLBACK)
    css_selectors = {
        "title": ["h1", "h1.title", "[data-test-id='job-title']"],
        "company": ["a[data-tracking-control-name*='topcard']", ".company-name"],
        "location": [".topcard__flavor", ".location"],
        "description": [".description", ".job-description", "[class*='description']"]
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
        except:
            continue

    # Sort by confidence: high → medium → low
    confidence_order = {"high": 3, "medium": 2, "low": 1}
    results.sort(key=lambda x: confidence_order.get(x.get("confidence", "low"), 0), reverse=True)

    return results
```

**New Function: `test_show_more_button()`**

```python
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
```

**Updated `run_discovery_mode()` Integration**:

```python
async def run_discovery_mode(job_url, config, site, verbose):
    """Enhanced discovery with live testing"""

    # ... existing navigation code ...

    # NEW: Test extraction strategies for all fields
    logging.info("Testing extraction strategies...")
    tested_strategies = {}

    for field in ['title', 'company', 'location', 'description']:
        logging.info(f"Testing {field} extraction...")
        strategies = await test_extraction_strategies(page, field)
        tested_strategies[field] = strategies

        if strategies:
            best = strategies[0]
            logging.info(f"✓ Found working strategy for {field}: {best['strategy']} (confidence: {best['confidence']})")
        else:
            logging.warning(f"✗ No working strategy found for {field}")

    # NEW: Test show more button
    logging.info("Testing show more button...")
    show_more_strategy = await test_show_more_button(page)
    if show_more_strategy.get("needed"):
        logging.info(f"✓ Show more button required: {show_more_strategy['impact']}")

    # NEW: Capture HTML samples
    logging.info("Capturing HTML samples...")
    html_samples = {}
    for field in ['title', 'description']:
        try:
            # Use the working JavaScript from tested_strategies
            if field in tested_strategies and tested_strategies[field]:
                best_strategy = tested_strategies[field][0]
                if best_strategy['strategy'] == 'javascript_evaluation':
                    # Capture element HTML
                    html = await page.evaluate(f"""() => {{
                        const el = document.querySelector('h1');  // Adjust per field
                        return el ? el.outerHTML : null;
                    }}""")
                    html_samples[field] = html[:500] if html else None
        except:
            pass

    # NEW: Enhanced AI prompt with REAL data
    analysis_prompt = f"""Analyze this {site_config.display_name} job posting.

I have TESTED these extraction strategies and they WORK:

Title extraction results:
{json.dumps(tested_strategies.get('title', []), indent=2)}

Description extraction results:
{json.dumps(tested_strategies.get('description', []), indent=2)}

Show more button strategy:
{json.dumps(show_more_strategy, indent=2)}

HTML samples from the page:
Title area: {html_samples.get('title', 'N/A')[:300]}
Description area: {html_samples.get('description', 'N/A')[:300]}

Based on these TESTED and VERIFIED strategies, document the scraping approach.
Prioritize strategies marked with "confidence": "high".
Use the exact JavaScript code provided in the tested strategies.
"""

    # ... rest of discovery code ...

    # Add to discovery log
    discovery_log['tested_strategies'] = tested_strategies
    discovery_log['show_more_strategy'] = show_more_strategy
    discovery_log['html_samples'] = html_samples

    return discovery_log
```

#### Phase 2: JavaScript-First Generation

**New System Prompt: CODE_GENERATION_SYSTEM_PROMPT_V2**

```python
CODE_GENERATION_SYSTEM_PROMPT_V2 = """You are a Python developer specializing in Playwright automation.

CRITICAL REQUIREMENT: Generated scripts MUST use page.evaluate() with JavaScript for data extraction.
DO NOT use page.wait_for_selector() or page.query_selector() for extracting data.

Why JavaScript Evaluation is Mandatory:
1. **10x more reliable**: Single atomic operation vs multiple round trips
2. **No race conditions**: All data extracted in one browser context call
3. **Proven pattern**: Original scraper achieves 100% success rate with this approach
4. **Handles dynamic content**: JavaScript executes after all content loaded

REQUIRED PATTERN:

```python
def scrape_linkedin_job(page, job_url):
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

Output ONLY the complete Python script. No explanations."""
```

**Updated Generation Prompt**:

```python
async def run_generation_mode(discovery_log_path, config, site, verbose):
    """Generate script with tested JavaScript strategies"""

    discovery_log = load_discovery_log(discovery_log_path)
    tested_strategies = discovery_log.get('tested_strategies', {})

    # Extract high-confidence JavaScript code
    js_code_snippets = {}
    for field, strategies in tested_strategies.items():
        for strategy in strategies:
            if strategy.get('strategy') == 'javascript_evaluation' and strategy.get('confidence') == 'high':
                js_code_snippets[field] = strategy['code']
                break

    generation_prompt = f"""Generate a REUSABLE Playwright scraper for {site_config.display_name}.

TESTED JAVASCRIPT STRATEGIES (use these EXACTLY):

Title: {js_code_snippets.get('title', 'N/A')}
Company: {js_code_snippets.get('company', 'N/A')}
Location: {js_code_snippets.get('location', 'N/A')}
Description: {js_code_snippets.get('description', 'N/A')}

Show more button handling:
{json.dumps(discovery_log.get('show_more_strategy', {}), indent=2)}

Generate a script that:
1. Uses page.evaluate() with the EXACT JavaScript above
2. Combines all fields in a single evaluate() call
3. Clicks show more button if needed (before evaluate)
4. Returns all data as dict

Example structure:
```python
job_data = page.evaluate('''() => {{
    const title = {js_code_snippets.get('title', 'document.querySelector("h1").textContent')};
    const description = {js_code_snippets.get('description', 'document.querySelector(".description").innerText')};
    return {{ title, description }};
}}''')
```

Output the complete script."""

    # Generate with V2 prompt
    message = anthropic_client.messages.create(
        model=config.model_name,
        max_tokens=config.max_tokens,
        system=CODE_GENERATION_SYSTEM_PROMPT_V2,
        messages=[{"role": "user", "content": generation_prompt}]
    )

    # ... rest of generation code ...
```

#### Phase 3: Validation Loop

**New Function: `validate_generated_script()`**

```python
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
                with open(script_path, 'w') as f:
                    f.write(fixed_script)
                continue
            else:
                return False, [error_msg]

        # Check exit code
        if result.returncode != 0:
            error_msg = f"Script failed with exit code {result.returncode}: {result.stderr}"
            logging.error(f"❌ {error_msg}")

            if attempt < max_attempts:
                # Request fix
                fixed_script = await request_fix_from_ai(
                    script_path, result.stderr, discovery_log, config
                )
                with open(script_path, 'w') as f:
                    f.write(fixed_script)
                continue
            else:
                return False, [error_msg]

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
                with open(script_path, 'w') as f:
                    f.write(fixed_script)
                continue
            else:
                return False, [error_msg]

        # Validate output content
        with open(output_files[0], 'r') as f:
            content = f.read()

        if len(content) > 500 and ("About" in content or "responsibilities" in content.lower()):
            logging.info(f"✅ Validation passed! Description length: {len(content)} chars")
            return True, []
        else:
            error_msg = f"Output too short ({len(content)} chars) or missing key content"
            logging.warning(f"⚠️  {error_msg}")

            if attempt < max_attempts:
                fixed_script = await request_fix_from_ai(
                    script_path, error_msg, discovery_log, config
                )
                with open(script_path, 'w') as f:
                    f.write(fixed_script)
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
    with open(script_path, 'r') as f:
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
        fixed_script = response_text

    logging.info("💾 Applying fix...")
    return fixed_script
```

### Success Metrics & Targets

#### Before (Current State)
- Discovery accuracy: **0%** (blind guessing)
- First-generation success: **0%** (timeouts)
- Validation pass rate: **N/A** (no validation)
- Multi-job success: **Unknown**

#### After (Target State)
- Discovery accuracy: **95%** (tested strategies)
- First-generation success: **90%** (using tested JS)
- Validation pass rate: **95%** (after fixes)
- Multi-job success: **85%+** (across different jobs)

#### Performance Targets
- Discovery time: <60s (includes live testing)
- Generation time: <30s
- Validation time: <90s per attempt
- Total flow: <3 minutes (discovery + generation + validation)

### Migration Path

#### For Existing Users

1. **No Breaking Changes**: All existing functionality preserved
2. **Opt-In Enhancement**: Use new validation with `--enable-validation` flag
3. **Backward Compatible**: Old discovery logs still work with new generation

#### Implementation Order

1. **Phase 12.1** (Critical): Implement live testing in discovery
2. **Phase 12.2** (Critical): Update generation to use JavaScript
3. **Phase 12.3** (Important): Add validation loop
4. **Phase 12.4** (Important): Multi-job testing
5. **Phase 12.5** (Nice to have): Polish and metrics

### Testing Strategy

#### Unit Tests
- `test_extraction_strategies()` with mock Playwright page
- `test_show_more_button()` with different button types
- `validate_generated_script()` with known good/bad scripts

#### Integration Tests
- Full flow: discover → generate → validate → success
- Fix iteration: discover → generate → validate fail → fix → success
- Multi-job: generate once → test with 3 URLs

#### End-to-End Tests
- Real LinkedIn job: Complete flow from URL to working scraper
- Job with "show more": Verify button clicked and full content extracted
- Multiple jobs: Same scraper works for 3+ different postings

### See Also

- **Implementation Tasks**: See `todo.md` Phase 12 for detailed 45+ task breakdown
- **Original Scraper**: `linkedin_job_scraper.py` (reference implementation)
- **Current AI Parser**: `ai_parser.py` (to be enhanced)