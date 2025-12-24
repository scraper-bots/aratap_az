# 🚀 Quick Start Guide

## 📦 Installation

```bash
pip install -r requirements.txt
```

## 🎯 Complete Workflow

### Step 1: Scrape Data
```bash
python scraper.py
```

**What happens:**
- Scrapes all real estate listings from aratap.az
- Saves to: `dasinmaz-emlak_listings_YYYYMMDD_HHMMSS.csv`
- Creates checkpoint: `dasinmaz-emlak_checkpoint.json`
- Generates log: `scraper.log`

**Features:**
- ✅ Auto-resume if interrupted (just run again!)
- ✅ Saves every 50 listings automatically
- ✅ Press Ctrl+C anytime - no data loss

### Step 2: Analyze & Visualize
```bash
python generate_charts.py
```

**What happens:**
- Analyzes the latest CSV file automatically
- Generates 8 professional charts in `charts/` folder
- Creates insights summary: `charts/insights_summary.txt`

**Charts Generated:**
1. `01_price_distribution.png` - Price ranges and outliers
2. `02_location_analysis.png` - Top cities and pricing
3. `03_property_types.png` - Property type breakdown
4. `04_listing_types.png` - Sale vs Rental
5. `05_area_analysis.png` - Size distribution and correlation
6. `06_room_analysis.png` - Room count analysis
7. `07_price_per_sqm.png` - Value analysis by location
8. `08_popularity_analysis.png` - Most viewed listings

### Step 3: Review Results

**View Charts:**
```bash
open charts/
```

**Read Summary:**
```bash
cat charts/insights_summary.txt
```

**Open CSV:**
```bash
open dasinmaz-emlak_listings_*.csv
```

## ⚙️ Configuration

Edit `scraper.py` main() function:

```python
CATEGORY_URL = "https://aratap.az/dasinmaz-emlak"  # Category
START_PAGE = 1                                      # Start
END_PAGE = None                                     # Auto-detect all
MAX_CONCURRENT = 5                                  # Speed
FETCH_DETAILS = True                                # Full data
AUTO_SAVE_INTERVAL = 50                             # Save frequency
RESUME = True                                       # Auto-resume
```

## 🔄 Common Scenarios

### Resume After Interruption
```bash
# Just run again - it will resume automatically!
python scraper.py
```

### Start Fresh
```bash
# Delete checkpoint to start over
rm dasinmaz-emlak_checkpoint.json
python scraper.py
```

### Analyze Different Category
Edit `scraper.py`:
```python
CATEGORY_URL = "https://aratap.az/elektronika"  # Electronics
# or
CATEGORY_URL = "https://aratap.az/neqliyyat"    # Vehicles
```

### Quick Test (First 5 Pages)
Edit `scraper.py`:
```python
END_PAGE = 5
```

## 📊 Output Files

**After Scraping:**
- `dasinmaz-emlak_listings_TIMESTAMP.csv` - Your data!
- `dasinmaz-emlak_checkpoint.json` - Resume point
- `scraper.log` - Execution log

**After Analysis:**
- `charts/01_price_distribution.png`
- `charts/02_location_analysis.png`
- ... (8 charts total)
- `charts/insights_summary.txt`

## 🆘 Troubleshooting

**Scraper stops unexpectedly?**
→ Just run `python scraper.py` again - it resumes!

**Want to see what's happening?**
→ Check `scraper.log` for detailed logs

**Charts not generating?**
→ Make sure you ran `python scraper.py` first

**Need different data?**
→ Change `CATEGORY_URL` and run scraper again

## 💡 Pro Tips

1. **Run overnight** for large datasets
2. **Check logs** if something seems wrong: `tail -f scraper.log`
3. **Save different categories** to different folders
4. **Re-run analysis** anytime with `python generate_charts.py`
5. **Update data regularly** to track market trends

## 🎯 One-Liner

```bash
python scraper.py && python generate_charts.py && open charts/
```

This will:
1. Scrape all data
2. Generate all charts
3. Open charts folder

---

**Questions?** Check `README.md` for full documentation!
