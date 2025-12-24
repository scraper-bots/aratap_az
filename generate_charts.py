import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import glob
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set style for professional-looking charts
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

class RealEstateAnalyzer:
    def __init__(self, csv_file=None):
        """Initialize analyzer with CSV file"""
        self.df = None
        self.insights = []
        self.charts_dir = Path('charts')
        self.charts_dir.mkdir(exist_ok=True)

        if csv_file:
            self.load_data(csv_file)
        else:
            # Auto-detect latest CSV file
            csv_files = glob.glob('*_listings_*.csv')
            if csv_files:
                latest_file = max(csv_files, key=lambda x: Path(x).stat().st_mtime)
                self.load_data(latest_file)
                print(f"Auto-detected file: {latest_file}")
            else:
                print("No CSV files found. Please run scraper first.")

    def load_data(self, csv_file):
        """Load and prepare data"""
        print(f"Loading data from {csv_file}...")
        self.df = pd.read_csv(csv_file, encoding='utf-8-sig')
        self.csv_file = csv_file
        print(f"Loaded {len(self.df)} listings")
        self._prepare_data()

    def _prepare_data(self):
        """Clean and prepare data for analysis"""
        # Convert price to numeric
        if 'price_value' in self.df.columns:
            self.df['price_numeric'] = pd.to_numeric(self.df['price_value'], errors='coerce')

        # Convert area to numeric
        if 'area_sqm' in self.df.columns:
            self.df['area_numeric'] = pd.to_numeric(self.df['area_sqm'], errors='coerce')

        # Calculate price per sqm
        if 'price_numeric' in self.df.columns and 'area_numeric' in self.df.columns:
            self.df['price_per_sqm'] = self.df['price_numeric'] / self.df['area_numeric']

        # Extract room count
        if 'rooms' in self.df.columns:
            self.df['room_count'] = self.df['rooms'].str.extract('(\d+)').astype(float)

        # Convert views to numeric
        if 'views' in self.df.columns:
            self.df['views_numeric'] = pd.to_numeric(self.df['views'], errors='coerce')

        print("Data prepared successfully")

    def generate_overview_stats(self):
        """Generate overview statistics"""
        print("\n" + "="*60)
        print("MARKET OVERVIEW")
        print("="*60)

        stats = {
            'total_listings': len(self.df),
            'avg_price': self.df['price_numeric'].mean() if 'price_numeric' in self.df.columns else 0,
            'median_price': self.df['price_numeric'].median() if 'price_numeric' in self.df.columns else 0,
            'min_price': self.df['price_numeric'].min() if 'price_numeric' in self.df.columns else 0,
            'max_price': self.df['price_numeric'].max() if 'price_numeric' in self.df.columns else 0,
            'avg_area': self.df['area_numeric'].mean() if 'area_numeric' in self.df.columns else 0,
            'avg_price_per_sqm': self.df['price_per_sqm'].mean() if 'price_per_sqm' in self.df.columns else 0,
            'total_views': self.df['views_numeric'].sum() if 'views_numeric' in self.df.columns else 0,
        }

        print(f"\n📊 Total Listings: {stats['total_listings']:,}")
        print(f"💰 Average Price: {stats['avg_price']:,.0f} AZN")
        print(f"💰 Median Price: {stats['median_price']:,.0f} AZN")
        print(f"💰 Price Range: {stats['min_price']:,.0f} - {stats['max_price']:,.0f} AZN")
        print(f"📐 Average Area: {stats['avg_area']:.1f} m²")
        print(f"💵 Avg Price/m²: {stats['avg_price_per_sqm']:,.0f} AZN")
        print(f"👁️  Total Views: {stats['total_views']:,.0f}")

        self.insights.append({
            'title': 'Market Overview',
            'stats': stats
        })

        return stats

    def plot_price_distribution(self):
        """Plot price distribution"""
        if 'price_numeric' not in self.df.columns:
            return

        fig, axes = plt.subplots(1, 2, figsize=(15, 5))

        # Histogram
        prices = self.df['price_numeric'].dropna()
        axes[0].hist(prices, bins=50, edgecolor='black', alpha=0.7, color='#2E86AB')
        axes[0].set_xlabel('Price (AZN)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Price Distribution', fontweight='bold', fontsize=14)
        axes[0].axvline(prices.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {prices.mean():,.0f} AZN')
        axes[0].axvline(prices.median(), color='green', linestyle='--', linewidth=2, label=f'Median: {prices.median():,.0f} AZN')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Box plot
        axes[1].boxplot(prices, vert=True)
        axes[1].set_ylabel('Price (AZN)')
        axes[1].set_title('Price Range & Outliers', fontweight='bold', fontsize=14)
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.charts_dir / '01_price_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()

        print("✓ Generated: Price Distribution chart")

    def plot_location_analysis(self):
        """Analyze and plot by location"""
        if 'city' not in self.df.columns:
            return

        city_counts = self.df['city'].value_counts().head(10)

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))

        # City distribution
        axes[0].barh(city_counts.index, city_counts.values, color='#A23B72')
        axes[0].set_xlabel('Number of Listings')
        axes[0].set_title('Top 10 Cities by Listings', fontweight='bold', fontsize=14)
        axes[0].grid(True, alpha=0.3, axis='x')

        # Add value labels
        for i, v in enumerate(city_counts.values):
            axes[0].text(v, i, f' {v:,}', va='center')

        # Average price by city
        if 'price_numeric' in self.df.columns:
            city_prices = self.df.groupby('city')['price_numeric'].mean().sort_values(ascending=False).head(10)
            axes[1].barh(city_prices.index, city_prices.values, color='#F18F01')
            axes[1].set_xlabel('Average Price (AZN)')
            axes[1].set_title('Top 10 Cities by Average Price', fontweight='bold', fontsize=14)
            axes[1].grid(True, alpha=0.3, axis='x')

            for i, v in enumerate(city_prices.values):
                axes[1].text(v, i, f' {v:,.0f}', va='center')

        plt.tight_layout()
        plt.savefig(self.charts_dir / '02_location_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

        print("✓ Generated: Location Analysis chart")

        self.insights.append({
            'title': 'Top Cities',
            'data': city_counts.head(5).to_dict()
        })

    def plot_property_types(self):
        """Analyze property types"""
        if 'property_type' not in self.df.columns:
            return

        prop_counts = self.df['property_type'].value_counts().head(10)

        fig, ax = plt.subplots(figsize=(12, 6))

        colors = plt.cm.Set3(np.linspace(0, 1, len(prop_counts)))
        bars = ax.bar(range(len(prop_counts)), prop_counts.values, color=colors, edgecolor='black', linewidth=1.2)

        ax.set_xticks(range(len(prop_counts)))
        ax.set_xticklabels(prop_counts.index, rotation=45, ha='right')
        ax.set_ylabel('Number of Listings')
        ax.set_title('Property Types Distribution', fontweight='bold', fontsize=14)
        ax.grid(True, alpha=0.3, axis='y')

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height):,}',
                   ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        plt.savefig(self.charts_dir / '03_property_types.png', dpi=300, bbox_inches='tight')
        plt.close()

        print("✓ Generated: Property Types chart")

    def plot_listing_type_analysis(self):
        """Analyze listing types (sale vs rent)"""
        if 'listing_type' not in self.df.columns:
            return

        listing_counts = self.df['listing_type'].value_counts()

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Pie chart
        colors = ['#06A77D', '#D4B483', '#C73E1D', '#6A4C93']
        axes[0].pie(listing_counts.values, labels=listing_counts.index, autopct='%1.1f%%',
                    startangle=90, colors=colors[:len(listing_counts)],
                    textprops={'fontweight': 'bold', 'fontsize': 11})
        axes[0].set_title('Listing Types Distribution', fontweight='bold', fontsize=14)

        # Bar chart with prices
        if 'price_numeric' in self.df.columns:
            listing_prices = self.df.groupby('listing_type')['price_numeric'].agg(['mean', 'median'])
            x = np.arange(len(listing_prices))
            width = 0.35

            bars1 = axes[1].bar(x - width/2, listing_prices['mean'], width, label='Mean', color='#06A77D', alpha=0.8)
            bars2 = axes[1].bar(x + width/2, listing_prices['median'], width, label='Median', color='#C73E1D', alpha=0.8)

            axes[1].set_ylabel('Price (AZN)')
            axes[1].set_title('Average Price by Listing Type', fontweight='bold', fontsize=14)
            axes[1].set_xticks(x)
            axes[1].set_xticklabels(listing_prices.index, rotation=45, ha='right')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3, axis='y')

            # Add value labels
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    axes[1].text(bar.get_x() + bar.get_width()/2., height,
                               f'{int(height):,}',
                               ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        plt.savefig(self.charts_dir / '04_listing_types.png', dpi=300, bbox_inches='tight')
        plt.close()

        print("✓ Generated: Listing Types chart")

    def plot_area_analysis(self):
        """Analyze property area"""
        if 'area_numeric' not in self.df.columns:
            return

        areas = self.df['area_numeric'].dropna()

        fig, axes = plt.subplots(1, 2, figsize=(15, 5))

        # Histogram
        axes[0].hist(areas, bins=50, edgecolor='black', alpha=0.7, color='#6A4C93')
        axes[0].set_xlabel('Area (m²)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Area Distribution', fontweight='bold', fontsize=14)
        axes[0].axvline(areas.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {areas.mean():.1f} m²')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Price vs Area scatter plot
        if 'price_numeric' in self.df.columns:
            valid_data = self.df.dropna(subset=['area_numeric', 'price_numeric'])
            if len(valid_data) > 0:
                axes[1].scatter(valid_data['area_numeric'], valid_data['price_numeric'],
                              alpha=0.5, s=30, color='#E63946')
                axes[1].set_xlabel('Area (m²)')
                axes[1].set_ylabel('Price (AZN)')
                axes[1].set_title('Price vs Area', fontweight='bold', fontsize=14)
                axes[1].grid(True, alpha=0.3)

                # Add trend line
                z = np.polyfit(valid_data['area_numeric'], valid_data['price_numeric'], 1)
                p = np.poly1d(z)
                axes[1].plot(valid_data['area_numeric'].sort_values(),
                           p(valid_data['area_numeric'].sort_values()),
                           "g--", linewidth=2, label='Trend')
                axes[1].legend()

        plt.tight_layout()
        plt.savefig(self.charts_dir / '05_area_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

        print("✓ Generated: Area Analysis chart")

    def plot_room_analysis(self):
        """Analyze by number of rooms"""
        if 'room_count' not in self.df.columns:
            return

        room_counts = self.df['room_count'].value_counts().sort_index()

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))

        # Room distribution
        axes[0].bar(room_counts.index, room_counts.values, color='#457B9D', edgecolor='black', linewidth=1.2)
        axes[0].set_xlabel('Number of Rooms')
        axes[0].set_ylabel('Number of Listings')
        axes[0].set_title('Distribution by Room Count', fontweight='bold', fontsize=14)
        axes[0].grid(True, alpha=0.3, axis='y')

        for i, (idx, val) in enumerate(room_counts.items()):
            axes[0].text(idx, val, f'{int(val):,}', ha='center', va='bottom', fontweight='bold')

        # Average price by room count
        if 'price_numeric' in self.df.columns:
            room_prices = self.df.groupby('room_count')['price_numeric'].mean().sort_index()
            axes[1].plot(room_prices.index, room_prices.values, marker='o', linewidth=3,
                        markersize=10, color='#F77F00')
            axes[1].set_xlabel('Number of Rooms')
            axes[1].set_ylabel('Average Price (AZN)')
            axes[1].set_title('Average Price by Room Count', fontweight='bold', fontsize=14)
            axes[1].grid(True, alpha=0.3)

            for idx, val in room_prices.items():
                axes[1].annotate(f'{val:,.0f}', (idx, val), textcoords="offset points",
                               xytext=(0,10), ha='center', fontweight='bold')

        plt.tight_layout()
        plt.savefig(self.charts_dir / '06_room_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

        print("✓ Generated: Room Analysis chart")

    def plot_price_per_sqm(self):
        """Analyze price per square meter"""
        if 'price_per_sqm' not in self.df.columns:
            return

        valid_data = self.df[self.df['price_per_sqm'] < self.df['price_per_sqm'].quantile(0.95)].dropna(subset=['price_per_sqm'])

        if len(valid_data) == 0:
            return

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))

        # Distribution
        axes[0].hist(valid_data['price_per_sqm'], bins=50, edgecolor='black', alpha=0.7, color='#06A77D')
        axes[0].set_xlabel('Price per m² (AZN)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Price per Square Meter Distribution', fontweight='bold', fontsize=14)
        axes[0].axvline(valid_data['price_per_sqm'].mean(), color='red', linestyle='--',
                       linewidth=2, label=f'Mean: {valid_data["price_per_sqm"].mean():,.0f} AZN/m²')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # By city
        if 'city' in self.df.columns:
            city_price_sqm = self.df.groupby('city')['price_per_sqm'].mean().sort_values(ascending=False).head(10)
            axes[1].barh(city_price_sqm.index, city_price_sqm.values, color='#D62828')
            axes[1].set_xlabel('Average Price per m² (AZN)')
            axes[1].set_title('Top 10 Cities by Price/m²', fontweight='bold', fontsize=14)
            axes[1].grid(True, alpha=0.3, axis='x')

            for i, v in enumerate(city_price_sqm.values):
                axes[1].text(v, i, f' {v:,.0f}', va='center', fontweight='bold')

        plt.tight_layout()
        plt.savefig(self.charts_dir / '07_price_per_sqm.png', dpi=300, bbox_inches='tight')
        plt.close()

        print("✓ Generated: Price per m² Analysis chart")

    def plot_popularity_analysis(self):
        """Analyze listing popularity by views"""
        if 'views_numeric' not in self.df.columns:
            return

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))

        # Top viewed listings
        top_viewed = self.df.nlargest(15, 'views_numeric')[['title', 'views_numeric', 'price_numeric']]

        axes[0].barh(range(len(top_viewed)), top_viewed['views_numeric'].values, color='#780116')
        axes[0].set_yticks(range(len(top_viewed)))
        axes[0].set_yticklabels([title[:40] + '...' if len(str(title)) > 40 else title
                                 for title in top_viewed['title']], fontsize=9)
        axes[0].set_xlabel('Views')
        axes[0].set_title('Top 15 Most Viewed Listings', fontweight='bold', fontsize=14)
        axes[0].grid(True, alpha=0.3, axis='x')

        # Views vs Price correlation
        if 'price_numeric' in self.df.columns:
            valid_data = self.df.dropna(subset=['views_numeric', 'price_numeric'])
            if len(valid_data) > 0:
                axes[1].scatter(valid_data['price_numeric'], valid_data['views_numeric'],
                              alpha=0.5, s=30, color='#F77F00')
                axes[1].set_xlabel('Price (AZN)')
                axes[1].set_ylabel('Views')
                axes[1].set_title('Views vs Price Correlation', fontweight='bold', fontsize=14)
                axes[1].grid(True, alpha=0.3)

                # Calculate correlation
                corr = valid_data[['price_numeric', 'views_numeric']].corr().iloc[0, 1]
                axes[1].text(0.05, 0.95, f'Correlation: {corr:.3f}',
                           transform=axes[1].transAxes, fontsize=12,
                           verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        plt.savefig(self.charts_dir / '08_popularity_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

        print("✓ Generated: Popularity Analysis chart")

    def generate_insights_summary(self):
        """Generate text summary of insights"""
        summary_file = self.charts_dir / 'insights_summary.txt'

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("REAL ESTATE MARKET INSIGHTS SUMMARY\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Data Source: {self.csv_file}\n")
            f.write(f"Total Listings Analyzed: {len(self.df):,}\n\n")

            # Market Overview
            if 'price_numeric' in self.df.columns:
                f.write("MARKET OVERVIEW\n")
                f.write("-" * 70 + "\n")
                f.write(f"Average Price: {self.df['price_numeric'].mean():,.0f} AZN\n")
                f.write(f"Median Price: {self.df['price_numeric'].median():,.0f} AZN\n")
                f.write(f"Price Range: {self.df['price_numeric'].min():,.0f} - {self.df['price_numeric'].max():,.0f} AZN\n\n")

            # Top Cities
            if 'city' in self.df.columns:
                f.write("TOP 5 CITIES BY LISTINGS\n")
                f.write("-" * 70 + "\n")
                city_counts = self.df['city'].value_counts().head(5)
                for i, (city, count) in enumerate(city_counts.items(), 1):
                    f.write(f"{i}. {city}: {count:,} listings\n")
                f.write("\n")

            # Property Types
            if 'property_type' in self.df.columns:
                f.write("TOP PROPERTY TYPES\n")
                f.write("-" * 70 + "\n")
                prop_counts = self.df['property_type'].value_counts().head(5)
                for i, (prop, count) in enumerate(prop_counts.items(), 1):
                    f.write(f"{i}. {prop}: {count:,} listings\n")
                f.write("\n")

            # Price per m²
            if 'price_per_sqm' in self.df.columns:
                valid_sqm = self.df[self.df['price_per_sqm'] < self.df['price_per_sqm'].quantile(0.95)]['price_per_sqm']
                f.write("PRICE PER SQUARE METER\n")
                f.write("-" * 70 + "\n")
                f.write(f"Average: {valid_sqm.mean():,.0f} AZN/m²\n")
                f.write(f"Median: {valid_sqm.median():,.0f} AZN/m²\n\n")

            # Most popular
            if 'views_numeric' in self.df.columns:
                f.write("MOST POPULAR LISTINGS (by views)\n")
                f.write("-" * 70 + "\n")
                top_viewed = self.df.nlargest(5, 'views_numeric')[['title', 'views_numeric', 'price_numeric']]
                for i, row in enumerate(top_viewed.itertuples(), 1):
                    title = row.title[:60] if len(str(row.title)) > 60 else row.title
                    f.write(f"{i}. {title}\n")
                    f.write(f"   Views: {row.views_numeric:,} | Price: {row.price_numeric:,.0f} AZN\n\n")

            f.write("=" * 70 + "\n")
            f.write("END OF SUMMARY\n")
            f.write("=" * 70 + "\n")

        print(f"✓ Generated: Insights Summary (saved to {summary_file})")

    def generate_all_charts(self):
        """Generate all charts and insights"""
        if self.df is None:
            print("Error: No data loaded")
            return

        print("\n" + "="*60)
        print("GENERATING CHARTS AND INSIGHTS")
        print("="*60 + "\n")

        self.generate_overview_stats()
        self.plot_price_distribution()
        self.plot_location_analysis()
        self.plot_property_types()
        self.plot_listing_type_analysis()
        self.plot_area_analysis()
        self.plot_room_analysis()
        self.plot_price_per_sqm()
        self.plot_popularity_analysis()
        self.generate_insights_summary()

        print("\n" + "="*60)
        print("✅ ALL CHARTS GENERATED SUCCESSFULLY")
        print("="*60)
        print(f"\nCharts saved to: {self.charts_dir.absolute()}")
        print(f"Total charts: {len(list(self.charts_dir.glob('*.png')))}")
        print(f"Insights summary: {self.charts_dir / 'insights_summary.txt'}")


def main():
    """Main execution"""
    print("\n" + "="*60)
    print("REAL ESTATE DATA ANALYSIS TOOL")
    print("="*60 + "\n")

    # Check for CSV files
    csv_files = glob.glob('*_listings_*.csv')

    if not csv_files:
        print("❌ No CSV files found!")
        print("Please run the scraper first: python scraper.py")
        return

    # Initialize analyzer (auto-detects latest CSV)
    analyzer = RealEstateAnalyzer()

    if analyzer.df is not None:
        # Generate all charts
        analyzer.generate_all_charts()
    else:
        print("❌ Failed to load data")


if __name__ == "__main__":
    main()
