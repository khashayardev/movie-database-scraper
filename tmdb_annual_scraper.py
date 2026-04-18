# tmdb_annual_scraper.py
import requests
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import time

class TMDBAnnualScraper:
    def __init__(self, api_key: str, access_token: str):
        """
        اسکرپر تعاملی TMDB برای دریافت محتوای یک سال خاص
        
        Args:
            api_key: کلید API TMDB
            access_token: توکن دسترسی خواندن
        """
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = "https://api.themoviedb.org/3"
        
        # هدرهای احراز هویت
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json;charset=utf-8"
        }
        
        self.results = []
        
    def get_user_input(self) -> tuple:
        """گرفتن ورودی از کاربر"""
        print("\n" + "="*60)
        print("🎬 اسکریپت دریافت محتوای سالانه از TMDB")
        print("="*60)
        
        # دریافت سال
        while True:
            try:
                year = input("\n📅 سال مورد نظر را وارد کنید (مثال: 2025): ").strip()
                year = int(year)
                if 1900 <= year <= 2030:
                    break
                else:
                    print("❌ سال باید بین 1900 تا 2030 باشد!")
            except ValueError:
                print("❌ لطفاً یک عدد معتبر وارد کنید!")
        
        # دریافت نوع محتوا
        while True:
            content_type = input("\n🎯 نوع محتوا را انتخاب کنید (Movie / Series): ").strip().lower()
            if content_type in ['movie', 'series', 'm', 's']:
                if content_type in ['m', 'movie']:
                    content_type = 'movie'
                else:
                    content_type = 'tv'
                break
            else:
                print("❌ لطفاً 'Movie' یا 'Series' را وارد کنید!")
        
        print(f"\n✅ شروع دریافت {content_type.upper()}های سال {year}...")
        return year, content_type
    
    def fetch_with_pagination(self, endpoint: str, params: Dict) -> List[Dict]:
        """
        دریافت داده‌ها با مدیریت pagination (صفحه‌بندی)
        """
        all_results = []
        page = 1
        total_pages = 1
        
        while page <= total_pages:
            params['page'] = page
            
            try:
                response = requests.get(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    all_results.extend(results)
                    
                    total_pages = data.get('total_pages', 1)
                    print(f"   📄 صفحه {page}/{total_pages} - {len(results)} آیتم دریافت شد")
                    
                    page += 1
                    time.sleep(0.2)  # تاخیر جزئی برای جلوگیری از rate limiting
                    
                elif response.status_code == 429:
                    print(f"   ⚠️ درخواست زیاد! 5 ثانیه صبر کنید...")
                    time.sleep(5)
                    
                else:
                    print(f"   ❌ خطا {response.status_code}: {response.text[:100]}")
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ خطای شبکه: {e}")
                break
        
        print(f"   ✅ مجموع: {len(all_results)} آیتم دریافت شد")
        return all_results
    
    def fetch_movies_by_year(self, year: int) -> List[Dict]:
        """دریافت فیلم‌های یک سال خاص"""
        print(f"\n🎬 دریافت فیلم‌های سال {year}...")
        
        # روش اول: استفاده از discover/movie
        params = {
            "primary_release_year": year,
            "sort_by": "popularity.desc",
            "language": "fa-IR",  # ترجیحاً به فارسی
            "include_adult": False
        }
        
        movies = self.fetch_with_pagination("/discover/movie", params)
        
        # برای هر فیلم، اطلاعات بیشتری دریافت کن
        enriched_movies = []
        for i, movie in enumerate(movies, 1):
            print(f"   🔄 دریافت جزئیات فیلم {i}/{len(movies)}: {movie.get('title', 'Unknown')}")
            details = self.get_movie_details(movie['id'])
            enriched_movies.append(details)
            time.sleep(0.1)
        
        return enriched_movies
    
    def fetch_series_by_year(self, year: int) -> List[Dict]:
        """دریافت سریال‌های یک سال خاص"""
        print(f"\n📺 دریافت سریال‌های سال {year}...")
        
        # روش اول: استفاده از discover/tv
        params = {
            "first_air_date_year": year,
            "sort_by": "popularity.desc",
            "language": "fa-IR",
            "include_adult": False
        }
        
        series_list = self.fetch_with_pagination("/discover/tv", params)
        
        # برای هر سریال، اطلاعات بیشتری دریافت کن
        enriched_series = []
        for i, series in enumerate(series_list, 1):
            print(f"   🔄 دریافت جزئیات سریال {i}/{len(series_list)}: {series.get('name', 'Unknown')}")
            details = self.get_tv_details(series['id'])
            enriched_series.append(details)
            time.sleep(0.1)
        
        return enriched_series
    
    def get_movie_details(self, movie_id: int) -> Dict:
        """دریافت جزئیات کامل یک فیلم"""
        try:
            response = requests.get(
                f"{self.base_url}/movie/{movie_id}",
                headers=self.headers,
                params={
                    "language": "fa-IR",
                    "append_to_response": "credits,keywords,similar,recommendations"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # اضافه کردن لینک پوستر کامل
                if data.get('poster_path'):
                    data['poster_url'] = f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
                if data.get('backdrop_path'):
                    data['backdrop_url'] = f"https://image.tmdb.org/t/p/w1280{data['backdrop_path']}"
                return data
            else:
                return {'id': movie_id, 'error': f"خطا {response.status_code}"}
                
        except Exception as e:
            return {'id': movie_id, 'error': str(e)}
    
    def get_tv_details(self, tv_id: int) -> Dict:
        """دریافت جزئیات کامل یک سریال"""
        try:
            response = requests.get(
                f"{self.base_url}/tv/{tv_id}",
                headers=self.headers,
                params={
                    "language": "fa-IR",
                    "append_to_response": "credits,keywords,similar,recommendations"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('poster_path'):
                    data['poster_url'] = f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
                if data.get('backdrop_path'):
                    data['backdrop_url'] = f"https://image.tmdb.org/t/p/w1280{data['backdrop_path']}"
                return data
            else:
                return {'id': tv_id, 'error': f"خطا {response.status_code}"}
                
        except Exception as e:
            return {'id': tv_id, 'error': str(e)}
    
    def save_results(self, year: int, content_type: str, data: List[Dict]):
        """ذخیره نتایج در فایل JSON"""
        # نام فایل
        filename = f"tmdb_{content_type}_{year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # اطلاعات کامل
        output_data = {
            'metadata': {
                'year': year,
                'content_type': content_type,
                'total_count': len(data),
                'extraction_date': datetime.now().isoformat(),
                'api_version': '3'
            },
            'results': data
        }
        
        # ذخیره فایل اصلی
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 فایل ذخیره شد: {filename}")
        
        # ذخیره نسخه ساده (فقط اطلاعات پایه)
        simple_filename = filename.replace('.json', '_simple.json')
        simple_data = []
        for item in data:
            if content_type == 'movie':
                simple_data.append({
                    'id': item.get('id'),
                    'title': item.get('title'),
                    'original_title': item.get('original_title'),
                    'release_date': item.get('release_date'),
                    'vote_average': item.get('vote_average'),
                    'vote_count': item.get('vote_count'),
                    'popularity': item.get('popularity'),
                    'overview': item.get('overview'),
                    'poster_url': item.get('poster_url')
                })
            else:
                simple_data.append({
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'original_name': item.get('original_name'),
                    'first_air_date': item.get('first_air_date'),
                    'vote_average': item.get('vote_average'),
                    'vote_count': item.get('vote_count'),
                    'popularity': item.get('popularity'),
                    'overview': item.get('overview'),
                    'poster_url': item.get('poster_url')
                })
        
        with open(simple_filename, 'w', encoding='utf-8') as f:
            json.dump(simple_data, f, ensure_ascii=False, indent=2)
        
        print(f"📁 نسخه ساده: {simple_filename}")
        
        # نمایش آمار
        self.show_statistics(simple_data, content_type)
    
    def show_statistics(self, data: List[Dict], content_type: str):
        """نمایش آمار ساده از داده‌های دریافت شده"""
        if not data:
            print("\n⚠️ هیچ داده‌ای دریافت نشد!")
            return
        
        print("\n" + "="*60)
        print("📊 آمار دریافت شده:")
        print("="*60)
        print(f"تعداد کل: {len(data)}")
        
        if content_type == 'movie':
            titles = [item.get('title', 'N/A') for item in data[:10]]
            avg_rating = sum(item.get('vote_average', 0) for item in data if item.get('vote_average')) / len(data)
            print(f"میانگین امتیاز: {avg_rating:.2f}/10")
            print(f"\n۱۰ فیلم اول:")
            for i, title in enumerate(titles, 1):
                print(f"  {i}. {title}")
        else:
            titles = [item.get('name', 'N/A') for item in data[:10]]
            avg_rating = sum(item.get('vote_average', 0) for item in data if item.get('vote_average')) / len(data)
            print(f"میانگین امتیاز: {avg_rating:.2f}/10")
            print(f"\n۱۰ سریال اول:")
            for i, title in enumerate(titles, 1):
                print(f"  {i}. {title}")
        
        print("="*60)


def check_internet_connection():
    """بررسی اتصال به اینترنت (بین‌الملل)"""
    import socket
    try:
        socket.create_connection(("api.themoviedb.org", 443), timeout=5)
        return True
    except OSError:
        return False


def main():
    # اطلاعات API شما
    API_KEY = "de8661ab534e482cc27a11a3d249465a"
    ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJkZTg2NjFhYjUzNGU0ODJjYzI3YTExYTNkMjQ5NDY1YSIsIm5iZiI6MTc3NjU0NDMzMC4yNTQwMDAyLCJzdWIiOiI2OWUzZWE0YTEwYjkwODJiNTM1ZTczMTgiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.4dFTDQvwo-NlUG2TVODypgZ_2rAgCDlhlutPEIBXYPo"
    
    # بررسی اتصال به اینترنت
    print("\n🌐 در حال بررسی اتصال به API TMDB...")
    if not check_internet_connection():
        print("⚠️ هشدار: به نظر می‌رسد دسترسی به اینترنت بین‌الملل ندارید!")
        print("⚠️ اگر API TMDB مسدود باشد، اسکریپت کار نخواهد کرد.")
        print("   ممکن است نیاز به استفاده از VPN یا پروکسی داشته باشید.\n")
        
        continue_anyway = input("آیا می‌خواهید ادامه دهید؟ (y/n): ").strip().lower()
        if continue_anyway != 'y':
            print("❌ اسکریپت متوقف شد.")
            return
    
    # ایجاد نمونه از اسکرپر
    scraper = TMDBAnnualScraper(API_KEY, ACCESS_TOKEN)
    
    # گرفتن ورودی از کاربر
    year, content_type = scraper.get_user_input()
    
    # دریافت داده‌ها
    print("\n" + "="*60)
    print("⏳ در حال دریافت اطلاعات از API TMDB...")
    print("⚠️ این عملیات ممکن است چند دقیقه طول بکشد.")
    print("="*60)
    
    if content_type == 'movie':
        results = scraper.fetch_movies_by_year(year)
    else:
        results = scraper.fetch_series_by_year(year)
    
    # ذخیره نتایج
    if results:
        scraper.save_results(year, content_type, results)
        print(f"\n✅ عملیات با موفقیت کامل شد! {len(results)} آیتم ذخیره شد.")
    else:
        print("\n❌ هیچ داده‌ای دریافت نشد!")
        print("ممکن است:")
        print("  ۱. سال وارد شده اشتباه باشد")
        print("  ۲. دسترسی به اینترنت بین‌الملل وجود ندارد")
        print("  ۳. API Key معتبر نیست")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ اسکریپت توسط کاربر متوقف شد.")
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
        import traceback
        traceback.print_exc()