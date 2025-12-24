# AraTap.az Scraper - Crash-Proof Edition

**Production-ready** async web scraper for aratap.az with comprehensive crash recovery, checkpointing, and data preservation features.

## Key Features

### Crash-Proof & Data Safety
- **Auto-save checkpoints** - Progress saved every N listings (configurable)
- **Resume capability** - Automatically resumes from last checkpoint
- **Graceful shutdown** - Handles Ctrl+C and signals without data loss
- **Failed URL tracking** - Saves URLs that failed to scrape
- **Deduplication** - Skips already-processed URLs
- **JSON backup** - Creates JSON backup if CSV export fails
- **Comprehensive logging** - All activities logged to file and console

### Scraping Features
- Asynchronous scraping using aiohttp for fast parallel requests
- Two-phase scraping:
  1. Extract listing cards from category pages
  2. Visit each individual listing page for detailed information
- Automatic pagination detection
- **Retry logic with exponential backoff** (configurable retries)
- Connection timeout handling
- Comprehensive data extraction

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python scraper.py
```

If interrupted (Ctrl+C) or crashed, simply run again - it will resume from where it left off.

### Configuration

Edit the following parameters in `scraper.py` main() function:

```python
CATEGORY_URL = "https://aratap.az/dasinmaz-emlak"  # Category to scrape
START_PAGE = 1                                      # First page number
END_PAGE = None                                     # None = auto-detect all pages
MAX_CONCURRENT = 5                                  # Concurrent requests (be respectful!)
FETCH_DETAILS = True                                # True = visit each listing for details
AUTO_SAVE_INTERVAL = 50                             # Save progress every N listings
RESUME = True                                       # Resume from checkpoint if exists
```

### Advanced Configuration

```python
scraper = AratapScraper(
    category_url="https://aratap.az/dasinmaz-emlak",
    start_page=1,
    end_page=None,
    max_concurrent=5,
    fetch_details=True,
    max_retries=3,           # Number of retries for failed requests
    auto_save_interval=50,   # Save every 50 listings
    resume=True              # Resume from checkpoint
)
```

### Available Categories

You can scrape any category by changing the `CATEGORY_URL`:

- Real Estate: `https://aratap.az/dasinmaz-emlak`
- Electronics: `https://aratap.az/elektronika`
- Vehicles: `https://aratap.az/neqliyyat`
- Services: `https://aratap.az/xidmetler-ve-biznes`
- And more...

## Data Extracted

### From Listing Cards (Category Pages)

- Listing ID
- Title
- Price (value and currency)
- Thumbnail image
- Listing date
- URL to detail page

### From Individual Listing Pages

- Complete image gallery (all images)
- Detailed description
- Property details:
  - City
  - Location
  - Property type
  - Listing type (sale/rent)
  - Building type
  - Area (square meters)
  - Number of rooms
  - Floor information
  - Construction year
  - Land area
  - Deed type
- Owner information:
  - Owner name
  - Phone number (may be masked)
- Statistics:
  - Listing number
  - Posted date
  - View count

## Output Files

### Main Output
- **CSV file**: `{category}_listings_{timestamp}.csv` - All scraped data

### Checkpoint & Recovery Files
- **Checkpoint**: `{category}_checkpoint.json` - Resume point (auto-created)
- **Failed URLs**: `{category}_failed_urls_{timestamp}.txt` - URLs that failed to scrape
- **Log file**: `scraper.log` - Detailed execution log
- **JSON backup**: `{category}_listings_{timestamp}_backup.json` - Created if CSV fails

## Crash Recovery

### How It Works

1. **During Scraping**: Progress is saved every N listings (default: 50)
2. **On Interrupt/Crash**: All current data is immediately saved
3. **On Restart**: Automatically detects and loads checkpoint
4. **Deduplication**: Skips URLs already processed in previous run

### Example Workflow

```bash
# Start scraping
python scraper.py
# ... 500 listings scraped ...
# Press Ctrl+C or connection lost
# -> Data saved automatically

# Resume (processes remaining listings only)
python scraper.py
# -> Resumes from listing 501
```

### Manual Checkpoint Management

To start fresh (ignore checkpoint):
```python
RESUME = False  # In main() function
```

Or delete the checkpoint file:
```bash
rm dasinmaz-emlak_checkpoint.json
```

## Error Handling

### Automatic Recovery
- **Network errors**: Retried 3 times with exponential backoff
- **Timeouts**: 30-second timeout, retried if failed
- **Parse errors**: Logged but don't stop scraping
- **Critical errors**: Save all data before exiting

### Failed URLs
Failed URLs are saved to `{category}_failed_urls_{timestamp}.txt` for manual review or retry.

## Logging

The scraper provides detailed logging to both console and `scraper.log`:

```
2024-12-24 15:30:45 - INFO - Successfully fetched page 5
2024-12-24 15:30:46 - INFO - Found 24 listing cards
2024-12-24 15:30:47 - INFO - Extracted 24 listings from page 5
2024-12-24 15:31:15 - INFO - Processed 50/500 listings
2024-12-24 15:31:15 - INFO - Auto-saved progress: 50 listings
```

## Performance & Safety

### Performance Notes
- Default concurrency: 5 (respectful to server)
- Fetching details takes significantly longer than listing cards only
- Auto-save every 50 listings minimizes re-scraping on crash
- Exponential backoff prevents overwhelming the server

### Safety Features
- Signal handlers (SIGINT, SIGTERM) for clean shutdown
- Connection pooling with proper cleanup
- Timeout handling prevents infinite waits
- Exception handling at every level
- Data never lost - always saved before exit

## Troubleshooting

### Resume Not Working
- Check if `{category}_checkpoint.json` exists
- Ensure `RESUME = True` in configuration
- Check log file for errors

### Too Many Failed URLs
- Increase `max_retries` (default: 3)
- Reduce `max_concurrent` (less load on server)
- Check network connection

### Out of Memory
- Reduce `auto_save_interval` to save more frequently
- Process in smaller page ranges (set `END_PAGE`)
- Set `FETCH_DETAILS = False` for listing cards only

## Example Workflows

### 1. Quick Scan (Listing Cards Only)
```python
FETCH_DETAILS = False  # Fast - just listing cards
END_PAGE = 10          # First 10 pages only
```

### 2. Complete Scrape (All Details)
```python
FETCH_DETAILS = True   # Get full details
END_PAGE = None        # Auto-detect all pages
AUTO_SAVE_INTERVAL = 25  # Save more frequently
```

### 3. Resume After Crash
```python
RESUME = True          # Resume from checkpoint
# Just run - it will continue from where it stopped
```

### 4. Specific Page Range
```python
START_PAGE = 5
END_PAGE = 15
FETCH_DETAILS = True
```

## CSV Columns (in order)

- listing_id, listing_number
- title, price, price_value, price_currency
- city, location
- property_type, listing_type, building_type
- area_sqm, rooms, room_count, floor, total_floors
- description
- owner_name, phone
- url, listing_date, posted_date
- views, image_count
- thumbnail, all_images (pipe-separated)
- Additional fields as discovered

## Legal & Ethical Considerations

- Be respectful to the server - don't set concurrency too high
- Use reasonable delays between requests (built-in)
- Ensure compliance with the website's robots.txt and terms of service
- Use scraped data responsibly
- Respect privacy - phone numbers may be masked

## Technical Details

- **Language**: Python 3.7+
- **Async Framework**: asyncio, aiohttp
- **HTML Parser**: BeautifulSoup4
- **Data Format**: CSV (UTF-8 with BOM for Excel), JSON (backup)
- **Checkpoint Format**: JSON
- **Encoding**: UTF-8 throughout
