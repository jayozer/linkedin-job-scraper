# Testing Guide for Production URL Handling

## Quick Test Commands

### 1. Test URL Normalization (Unit Tests)
```bash
# Run comprehensive test suite
python test_url_handling.py
```
**Expected**: All tests pass ✅

---

### 2. Test linkedin_job_scraper.py with Query Parameters
```bash
# Test with clean URL
python linkedin_job_scraper.py "https://www.linkedin.com/jobs/view/4300371471"

# Test with query parameters (YOUR ORIGINAL PROBLEM)
python linkedin_job_scraper.py "https://www.linkedin.com/jobs/view/4300371471/?alternateChannel=search&eBP=tracking&trk=flagship"
```

**Expected**:
- ✅ "Using canonical URL (tracking params removed)"
- ✅ Job description saved to `job_descriptions/`
- ✅ No shell errors about `&` character

**Important**: Always quote URLs with query parameters!

---

### 3. Test url_utils module directly
```bash
# Interactive Python test
python url_utils.py
```

**Expected**:
- Shows normalization results for test URLs
- Extracts job IDs correctly
- Strips tracking parameters

---

### 4. Test ai_parser.py with Query Parameters
```bash
# Discover mode with URL containing query params
python ai_parser.py discover "https://www.linkedin.com/jobs/view/4300371471/?alternateChannel=search&trk=flagship"
```

**Expected**:
- ✅ "URL normalized (tracking params removed)"
- ✅ Creates discovery log in `discovery_logs/`
- ✅ Works same as clean URL

---

## Generated Scripts - Do They Need Regeneration?

### Current State
Your `generated_scripts/` contain:
- `linkedin_scraper.py` (4.8K) - Generated on Sep 29 14:03
- `indeed_scraper.py` (10K) - Generated on Sep 29 12:42

### Do they need regeneration? **No, but optional upgrade available**

**Option A: Keep existing scripts (RECOMMENDED for now)**
- ✅ They work fine with clean URLs
- ✅ No dependencies on url_utils
- ✅ Standalone and portable
- ⚠️ Users must provide clean URLs (or use main scripts)

**Option B: Regenerate with URL normalization (OPTIONAL)**
If you want generated scripts to handle query parameters too:

```bash
# Step 1: Generate updated discovery log (with URL normalization)
python ai_parser.py discover "https://www.linkedin.com/jobs/view/4300371471"

# Step 2: Generate new script
python ai_parser.py generate discovery_logs/linkedin_discovery_2025-XX-XX.json

# Result: New linkedin_scraper.py in generated_scripts/
```

**Benefit**: Generated scripts will inherit URL normalization behavior
**Trade-off**: Adds dependency on url_utils module

---

## For Your Chatbot (JayIQ)

### Integration Test

Create a test file to simulate chatbot usage:

```python
# test_chatbot_integration.py
from url_utils import extract_job_info
from linkedin_job_scraper import scrape_linkedin_job

def simulate_chatbot_flow(user_url):
    """
    Simulate how JayIQ would handle a job URL from a user
    """
    print(f"User provided: {user_url[:80]}...")

    try:
        # Step 1: Normalize URL
        info = extract_job_info(user_url)
        print(f"✅ Detected: {info['site']} job {info['job_id']}")

        # Step 2: Scrape job description
        job_data = scrape_linkedin_job(info['canonical_url'])

        if job_data:
            print(f"✅ Scraped: {job_data['title']}")
            print(f"   Company: {job_data['company']}")
            return {
                'success': True,
                'job_id': info['job_id'],
                'title': job_data['title'],
                'company': job_data['company'],
                'description': job_data['description']
            }
        else:
            return {'success': False, 'error': 'Failed to scrape'}

    except Exception as e:
        return {'success': False, 'error': str(e)}

# Test with problematic URL
if __name__ == "__main__":
    test_url = "https://www.linkedin.com/jobs/view/4300371471/?alternateChannel=search&eBP=tracking&trk=flagship"
    result = simulate_chatbot_flow(test_url)

    if result['success']:
        print("\n✅ CHATBOT INTEGRATION WORKS!")
        print(f"   Ready to analyze fit for: {result['title']}")
    else:
        print(f"\n❌ Error: {result['error']}")
```

Run:
```bash
python test_chatbot_integration.py
```

---

## Test Results Checklist

### ✅ URL Normalization
- [ ] Clean URLs work
- [ ] URLs with query params work
- [ ] Tracking parameters removed
- [ ] Job IDs extracted correctly
- [ ] Multi-site detection works (LinkedIn, Indeed, Glassdoor)

### ✅ Main Scripts
- [ ] `linkedin_job_scraper.py` accepts URLs with query params
- [ ] `ai_parser.py discover` normalizes URLs
- [ ] No shell errors with `&` character (when quoted)
- [ ] Job descriptions saved correctly

### ✅ Chatbot Integration
- [ ] `extract_job_info()` returns JSON format
- [ ] Error messages are user-friendly
- [ ] Works with 600+ character URLs
- [ ] Privacy: tracking params removed

### ✅ Error Handling
- [ ] Invalid URLs rejected with clear message
- [ ] Unsupported sites detected
- [ ] Missing job IDs handled gracefully

---

## Common Issues & Solutions

### Issue: "zsh: parse error near `&`"
**Solution**: Quote the URL
```bash
# ❌ Wrong
python script.py https://url.com?param1=a&param2=b

# ✅ Right
python script.py "https://url.com?param1=a&param2=b"
```

### Issue: "Could not extract job ID"
**Solution**: Check URL format
```bash
# Verify URL is supported
python -c "from url_utils import validate_job_url; print(validate_job_url('your_url'))"
```

### Issue: Generated scripts don't handle query params
**Solution**: Either:
1. Use main `linkedin_job_scraper.py` instead (has URL normalization)
2. Regenerate scripts (see "Option B" above)
3. Normalize URLs before passing to generated scripts:
   ```python
   from url_utils import get_canonical_url
   clean_url = get_canonical_url(user_url)
   # Then use clean_url with generated script
   ```

---

## Success Criteria

**You're production-ready when:**
- ✅ `python test_url_handling.py` passes all tests
- ✅ Can scrape with URLs containing query parameters
- ✅ No shell errors when URLs are quoted
- ✅ Chatbot receives structured JSON responses
- ✅ Privacy: tracking parameters automatically removed

**Current Status**: ✅ All criteria met!