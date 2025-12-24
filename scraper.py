import asyncio
import aiohttp
import csv
import json
import signal
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set
import logging
from datetime import datetime
import re
from urllib.parse import urljoin
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AratapScraper:
    def __init__(
        self,
        category_url: str = "https://aratap.az/dasinmaz-emlak",
        start_page: int = 1,
        end_page: Optional[int] = None,
        max_concurrent: int = 10,
        fetch_details: bool = True,
        max_retries: int = 3,
        auto_save_interval: int = 50,
        resume: bool = True
    ):
        """
        Initialize the crash-proof scraper

        Args:
            category_url: Base category URL
            start_page: First page to scrape
            end_page: Last page to scrape (None = auto-detect)
            max_concurrent: Maximum concurrent requests
            fetch_details: Whether to fetch individual listing details
            max_retries: Number of retries for failed requests
            auto_save_interval: Save progress every N listings
            resume: Whether to resume from checkpoint if exists
        """
        self.category_url = category_url.rstrip('/')
        self.start_page = start_page
        self.end_page = end_page
        self.max_concurrent = max_concurrent
        self.fetch_details = fetch_details
        self.base_url = "https://aratap.az"
        self.max_retries = max_retries
        self.auto_save_interval = auto_save_interval
        self.resume = resume

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': 'https://aratap.az/',
            'DNT': '1',
            'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-requested-with': 'XMLHttpRequest'
        }

        self.all_listings = []
        self.failed_urls = []
        self.processed_urls: Set[str] = set()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.shutdown_requested = False

        # Setup checkpoint and output files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        category_name = self.category_url.split('/')[-1] or 'aratap'
        self.checkpoint_file = f'{category_name}_checkpoint.json'
        self.output_file = f'{category_name}_listings_{timestamp}.csv'
        self.failed_urls_file = f'{category_name}_failed_urls_{timestamp}.txt'

        # Load checkpoint if resuming
        if self.resume:
            self._load_checkpoint()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.warning(f"\n{'='*50}")
        logger.warning("Shutdown signal received! Saving progress...")
        logger.warning(f"{'='*50}")
        self.shutdown_requested = True
        self._save_checkpoint()
        self._save_progress()
        logger.info(f"Progress saved. Safe to exit.")
        sys.exit(0)

    def _load_checkpoint(self):
        """Load checkpoint from previous run"""
        try:
            if Path(self.checkpoint_file).exists():
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                    self.processed_urls = set(checkpoint.get('processed_urls', []))
                    self.all_listings = checkpoint.get('listings', [])
                    self.failed_urls = checkpoint.get('failed_urls', [])
                    logger.info(f"Resumed from checkpoint: {len(self.all_listings)} listings, {len(self.processed_urls)} URLs processed")
        except Exception as e:
            logger.error(f"Error loading checkpoint: {str(e)}")

    def _save_checkpoint(self):
        """Save current progress to checkpoint file"""
        try:
            checkpoint = {
                'processed_urls': list(self.processed_urls),
                'listings': self.all_listings,
                'failed_urls': self.failed_urls,
                'timestamp': datetime.now().isoformat(),
                'category_url': self.category_url
            }
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)
            logger.debug(f"Checkpoint saved: {len(self.all_listings)} listings")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {str(e)}")

    def _save_progress(self):
        """Save current data to CSV"""
        if self.all_listings:
            self.save_to_csv(self.output_file)
        if self.failed_urls:
            self._save_failed_urls()

    def _save_failed_urls(self):
        """Save failed URLs to file"""
        try:
            with open(self.failed_urls_file, 'w', encoding='utf-8') as f:
                for url in self.failed_urls:
                    f.write(f"{url}\n")
            logger.info(f"Saved {len(self.failed_urls)} failed URLs to {self.failed_urls_file}")
        except Exception as e:
            logger.error(f"Error saving failed URLs: {str(e)}")

    def get_page_url(self, page: int) -> str:
        """Generate URL for a specific page"""
        if page == 1:
            return self.category_url
        return f"{self.category_url}/page/{page}/"

    async def fetch_page(
        self,
        session: aiohttp.ClientSession,
        url: str,
        page_num: Optional[int] = None,
        retry_count: int = 0
    ) -> Optional[str]:
        """Fetch a single page with retry logic"""
        if self.shutdown_requested:
            return None

        async with self.semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with session.get(url, headers=self.headers, timeout=timeout) as response:
                    if response.status == 200:
                        content = await response.text()
                        log_msg = f"Successfully fetched: {url}"
                        if page_num:
                            log_msg = f"Successfully fetched page {page_num}"
                        logger.info(log_msg)
                        return content
                    else:
                        logger.warning(f"{url} returned status {response.status}")
                        if retry_count < self.max_retries:
                            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                            return await self.fetch_page(session, url, page_num, retry_count + 1)
                        return None
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching {url}")
                if retry_count < self.max_retries:
                    await asyncio.sleep(2 ** retry_count)
                    return await self.fetch_page(session, url, page_num, retry_count + 1)
                self.failed_urls.append(url)
                return None
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}")
                if retry_count < self.max_retries:
                    await asyncio.sleep(2 ** retry_count)
                    return await self.fetch_page(session, url, page_num, retry_count + 1)
                self.failed_urls.append(url)
                return None

    def parse_listing_card(self, card_element) -> Optional[Dict]:
        """Parse a listing card from category page"""
        try:
            data = {}

            # Extract link and title
            link_elem = card_element.find('a', class_='products-link')
            if link_elem:
                data['url'] = urljoin(self.base_url, link_elem.get('href', ''))

                # Skip if already processed
                if data['url'] in self.processed_urls:
                    return None

                # Extract title
                title_elem = link_elem.find('div', class_='products-name')
                data['title'] = title_elem.get_text(strip=True) if title_elem else ''

                # Extract image
                img_elem = link_elem.find('img')
                if img_elem:
                    data['thumbnail'] = img_elem.get('src', '')

                # Extract price
                price_container = link_elem.find('div', class_='products-price')
                if price_container:
                    price_val = price_container.find('span', class_='price-val')
                    price_cur = price_container.find('span', class_='price-cur')
                    data['price_value'] = price_val.get_text(strip=True) if price_val else ''
                    data['price_currency'] = price_cur.get_text(strip=True) if price_cur else ''
                    data['price'] = f"{data['price_value']} {data['price_currency']}"

                # Extract date
                date_elem = link_elem.find('div', class_='products-created')
                data['listing_date'] = date_elem.get_text(strip=True) if date_elem else ''

            # Extract listing ID from bookmark
            bookmark = card_element.find('a', class_='add_bookmark')
            if bookmark:
                data['listing_id'] = bookmark.get('data-id', '')

            return data if data.get('url') else None

        except Exception as e:
            logger.error(f"Error parsing listing card: {str(e)}", exc_info=True)
            return None

    def parse_listing_cards(self, html: str) -> List[Dict]:
        """Parse all listing cards from a category page"""
        if not html:
            return []

        try:
            soup = BeautifulSoup(html, 'html.parser')
            listings = []

            # Find all listing cards
            cards = soup.find_all('div', class_='products-i')
            logger.info(f"Found {len(cards)} listing cards")

            for card in cards:
                try:
                    listing_data = self.parse_listing_card(card)
                    if listing_data and listing_data.get('url'):
                        listings.append(listing_data)
                except Exception as e:
                    logger.error(f"Error parsing individual card: {str(e)}")
                    continue

            return listings
        except Exception as e:
            logger.error(f"Error parsing listing cards: {str(e)}", exc_info=True)
            return []

    def parse_detail_page(self, html: str, url: str) -> Dict:
        """Parse detailed information from individual listing page"""
        if not html:
            return {}

        try:
            soup = BeautifulSoup(html, 'html.parser')
            data = {'detail_url': url}

            # Extract price from detail page
            try:
                price_section = soup.find('div', class_='product-price')
                if price_section:
                    price_val = price_section.find('span', class_='price-val')
                    price_cur = price_section.find('span', class_='price-cur')
                    if price_val:
                        data['detail_price_value'] = price_val.get_text(strip=True)
                    if price_cur:
                        data['detail_price_currency'] = price_cur.get_text(strip=True)
            except Exception as e:
                logger.debug(f"Error extracting price: {str(e)}")

            # Extract all properties
            try:
                properties = soup.find_all('div', class_='product-properties__i')
                for prop in properties:
                    try:
                        label_elem = prop.find('label', class_='product-properties__i-name')
                        value_elem = prop.find('span', class_='product-properties__i-value')

                        if label_elem and value_elem:
                            label = label_elem.get_text(strip=True).replace(':', '').strip()
                            value = value_elem.get_text(strip=True)

                            # Map Azerbaijani labels to English keys
                            label_mapping = {
                                'Şəhər': 'city',
                                'Əmlakın növü': 'property_type',
                                'Elanın tipi': 'listing_type',
                                'Yerləşdirmə yeri': 'location',
                                'Yerləşmə yeri': 'location',
                                'Binanın tipi': 'building_type',
                                'Sahə, m²': 'area_sqm',
                                'Sahə': 'area_sqm',
                                'Otaq sayı': 'rooms',
                                'Mərtəbə': 'floor',
                                'Mərtəbələrin sayı': 'total_floors',
                                'Tikinti ili': 'construction_year',
                                'Torpaq sahəsi': 'land_area',
                                'Otaqların sayı': 'room_count',
                                'Çıxarış': 'deed_type'
                            }

                            key = label_mapping.get(label, label.lower().replace(' ', '_'))
                            data[key] = value
                    except Exception as e:
                        logger.debug(f"Error extracting property: {str(e)}")
                        continue
            except Exception as e:
                logger.debug(f"Error extracting properties: {str(e)}")

            # Extract description
            try:
                desc_container = soup.find('div', class_='product-description__content')
                if desc_container:
                    desc_elem = desc_container.find('div', style='white-space: pre-wrap;')
                    data['description'] = desc_elem.get_text(strip=True) if desc_elem else ''
            except Exception as e:
                logger.debug(f"Error extracting description: {str(e)}")

            # Extract all images from gallery
            try:
                image_gallery = soup.find('ul', class_='xfieldimagegallery')
                if image_gallery:
                    images = []
                    for img in image_gallery.find_all('img'):
                        img_src = img.get('src', '')
                        if img_src:
                            images.append(img_src)
                    if images:
                        data['all_images'] = '|'.join(images)
                        data['image_count'] = len(images)
            except Exception as e:
                logger.debug(f"Error extracting images: {str(e)}")

            # Extract statistics
            try:
                stats_section = soup.find('div', class_='product-info__statistics')
                if stats_section:
                    stats_items = stats_section.find_all('div', class_='product-info__statistics__i')
                    for item in stats_items:
                        text = item.get_text(strip=True)

                        # Extract listing number
                        if '№' in text:
                            data['listing_number'] = text.replace('№', '').strip()

                        # Extract date posted
                        elif any(month in text for month in ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                                                              'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']):
                            data['posted_date'] = text

                        # Extract views
                        elif 'Baxışların sayı' in text or 'sayı' in text:
                            views_match = re.search(r'(\d[\d\s]*)', text)
                            if views_match:
                                data['views'] = views_match.group(1).replace(' ', '')
            except Exception as e:
                logger.debug(f"Error extracting statistics: {str(e)}")

            # Extract owner information
            try:
                owner_section = soup.find('div', class_='product-owner__info')
                if owner_section:
                    owner_name = owner_section.find('div', class_='product-owner__info-name')
                    if owner_name:
                        data['owner_name'] = owner_name.get_text(strip=True)
            except Exception as e:
                logger.debug(f"Error extracting owner info: {str(e)}")

            # Extract phone number (even if masked)
            try:
                phone_elem = soup.find('span', class_='phone_number')
                if phone_elem:
                    data['phone'] = phone_elem.get_text(strip=True)
            except Exception as e:
                logger.debug(f"Error extracting phone: {str(e)}")

            return data

        except Exception as e:
            logger.error(f"Error parsing detail page {url}: {str(e)}", exc_info=True)
            return {}

    async def fetch_listing_details(self, session: aiohttp.ClientSession, listing: Dict) -> Dict:
        """Fetch detailed information for a single listing"""
        url = listing.get('url')
        if not url:
            return listing

        if self.shutdown_requested:
            return listing

        try:
            html = await self.fetch_page(session, url)
            if html:
                details = self.parse_detail_page(html, url)
                # Merge with existing data
                merged = {**listing, **details}
                self.processed_urls.add(url)
                return merged
            else:
                self.failed_urls.append(url)
                return listing
        except Exception as e:
            logger.error(f"Error fetching details for {url}: {str(e)}")
            self.failed_urls.append(url)
            return listing

    async def detect_last_page(self, session: aiohttp.ClientSession) -> int:
        """Detect the last page by checking pagination"""
        logger.info("Detecting last page...")

        try:
            # Fetch first page
            url = self.get_page_url(1)
            html = await self.fetch_page(session, url, 1)

            if html:
                soup = BeautifulSoup(html, 'html.parser')

                # Look for pagination
                pagination = soup.find('div', class_='navigation') or soup.find('ul', class_='pagination')
                if pagination:
                    page_links = pagination.find_all('a')
                    max_page = 1
                    for link in page_links:
                        text = link.get_text(strip=True)
                        if text.isdigit():
                            max_page = max(max_page, int(text))

                        # Check href for page numbers
                        href = link.get('href', '')
                        page_match = re.search(r'/page/(\d+)/', href)
                        if page_match:
                            max_page = max(max_page, int(page_match.group(1)))

                    if max_page > 1:
                        logger.info(f"Detected last page from pagination: {max_page}")
                        return max_page
        except Exception as e:
            logger.error(f"Error detecting last page: {str(e)}")

        # Default to checking up to 100 pages
        logger.info("Could not detect pagination, will check pages until empty")
        return 100

    async def scrape_all_pages(self):
        """Scrape all category pages and optionally fetch details"""
        try:
            connector = aiohttp.TCPConnector(limit=self.max_concurrent, force_close=True)
            timeout = aiohttp.ClientTimeout(total=None, connect=30, sock_read=30)

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # Auto-detect end page if not specified
                if self.end_page is None:
                    self.end_page = await self.detect_last_page(session)
                    logger.info(f"Auto-detected end page: {self.end_page}")

                logger.info(f"Starting scrape from page {self.start_page} to {self.end_page}")
                logger.info(f"Category: {self.category_url}")
                logger.info(f"Fetch details: {self.fetch_details}")

                # Fetch all category pages
                tasks = []
                for page in range(self.start_page, self.end_page + 1):
                    if self.shutdown_requested:
                        break
                    url = self.get_page_url(page)
                    task = self.fetch_page(session, url, page)
                    tasks.append((page, task))

                # Parse category pages
                all_listing_cards = []
                htmls = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

                for (page_num, _), html in zip(tasks, htmls):
                    if self.shutdown_requested:
                        break

                    if isinstance(html, Exception):
                        logger.error(f"Error fetching page {page_num}: {str(html)}")
                        continue

                    if html:
                        listings = self.parse_listing_cards(html)
                        if listings:
                            logger.info(f"Extracted {len(listings)} listings from page {page_num}")
                            all_listing_cards.extend(listings)
                        else:
                            logger.warning(f"No listings found on page {page_num}")
                            # Stop if we hit an empty page
                            if page_num > self.start_page:
                                logger.info(f"Stopping at page {page_num} (empty page)")
                                break

                logger.info(f"Total listing cards extracted: {len(all_listing_cards)}")

                # Fetch details for each listing
                if self.fetch_details and all_listing_cards and not self.shutdown_requested:
                    logger.info("Fetching detailed information for each listing...")

                    for i, listing in enumerate(all_listing_cards):
                        if self.shutdown_requested:
                            break

                        try:
                            # Skip if already processed
                            if listing.get('url') in self.processed_urls:
                                continue

                            detailed_listing = await self.fetch_listing_details(session, listing)
                            self.all_listings.append(detailed_listing)

                            # Auto-save every N listings
                            if (i + 1) % self.auto_save_interval == 0:
                                self._save_checkpoint()
                                self._save_progress()
                                logger.info(f"Auto-saved progress: {len(self.all_listings)} listings")

                            # Progress update
                            if (i + 1) % 10 == 0:
                                logger.info(f"Processed {i + 1}/{len(all_listing_cards)} listings")

                        except Exception as e:
                            logger.error(f"Error processing listing {i}: {str(e)}")
                            continue
                else:
                    self.all_listings.extend(all_listing_cards)

                # Final save
                self._save_checkpoint()
                self._save_progress()

                logger.info(f"Total listings with details: {len(self.all_listings)}")

        except Exception as e:
            logger.error(f"Critical error in scrape_all_pages: {str(e)}", exc_info=True)
            # Save what we have
            self._save_checkpoint()
            self._save_progress()
            raise

    def save_to_csv(self, filename: str = None):
        """Save all listings to CSV"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            category_name = self.category_url.split('/')[-1] or 'aratap'
            filename = f'{category_name}_listings_{timestamp}.csv'

        if not self.all_listings:
            logger.warning("No listings to save")
            return None

        try:
            # Get all unique fields
            fieldnames = set()
            for listing in self.all_listings:
                fieldnames.update(listing.keys())

            # Define preferred field order
            priority_fields = [
                'listing_id', 'listing_number', 'title', 'price', 'price_value', 'price_currency',
                'city', 'location', 'property_type', 'listing_type', 'building_type',
                'area_sqm', 'rooms', 'room_count', 'floor', 'total_floors',
                'description', 'owner_name', 'phone', 'url', 'listing_date', 'posted_date',
                'views', 'image_count', 'thumbnail', 'all_images'
            ]

            # Order fields: priority first, then alphabetically
            ordered_fields = []
            for field in priority_fields:
                if field in fieldnames:
                    ordered_fields.append(field)
                    fieldnames.remove(field)
            ordered_fields.extend(sorted(fieldnames))

            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=ordered_fields)
                writer.writeheader()
                writer.writerows(self.all_listings)

            logger.info(f"Successfully saved {len(self.all_listings)} listings to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}", exc_info=True)
            # Try to save as JSON backup
            try:
                json_file = filename.replace('.csv', '_backup.json')
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(self.all_listings, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved backup to {json_file}")
            except Exception as e2:
                logger.error(f"Error saving backup: {str(e2)}")
            return None


async def main():
    """Main function"""
    try:
        # Configure these parameters
        CATEGORY_URL = "https://aratap.az/dasinmaz-emlak"  # Change to any category
        START_PAGE = 1
        END_PAGE = None  # None = auto-detect all pages
        MAX_CONCURRENT = 5  # Be respectful to the server
        FETCH_DETAILS = True  # Set to False to only get listing cards without visiting each page
        AUTO_SAVE_INTERVAL = 50  # Save progress every N listings
        RESUME = True  # Resume from checkpoint if exists

        scraper = AratapScraper(
            category_url=CATEGORY_URL,
            start_page=START_PAGE,
            end_page=END_PAGE,
            max_concurrent=MAX_CONCURRENT,
            fetch_details=FETCH_DETAILS,
            auto_save_interval=AUTO_SAVE_INTERVAL,
            resume=RESUME
        )

        # Scrape all pages
        await scraper.scrape_all_pages()

        # Save to CSV
        output_file = scraper.save_to_csv()

        if output_file:
            print(f"\n{'='*50}")
            print(f"Scraping complete!")
            print(f"{'='*50}")
            print(f"Category: {CATEGORY_URL}")
            print(f"Total listings: {len(scraper.all_listings)}")
            print(f"Output file: {output_file}")
            if scraper.failed_urls:
                print(f"Failed URLs: {len(scraper.failed_urls)} (saved to {scraper.failed_urls_file})")
            print(f"{'='*50}")
        else:
            print("\nScraping completed but no data was saved")

    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user. Progress has been saved.")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
