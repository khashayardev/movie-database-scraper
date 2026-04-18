# tmdb_complete_scraper.py
import requests
import json
import time
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

class TMDBCompleteScraper:
    def __init__(self, access_token: str):
        self.base_url = "https://api.themoviedb.org/3"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json;charset=utf-8"
        }
        # لیست همه چیزهایی که می‌خواهیم از API بگیریم
        # مستندات: https://developer.themoviedb.org/docs/append-to-response [citation:3]
        self.append_to_response = "videos,images,credits,keywords,recommendations,similar,external_ids,release_dates,translations"
        
        self.stats = {'total_movies': 0, 'years_processed': 0, 'api_calls': 0}

    def fetch_movies_by_year(self, year: int, min_votes: int = 100, min_rating: float = 7.0, limit: int = 500) -> List[Dict]:
        """دریافت لیست فیلم‌های یک سال با فیلتر امتیاز"""
        params = {
            "primary_release_year": year,
            "sort_by": "vote_average.desc",
            "vote_count.gte": min_votes,
            "vote_average.gte": min_rating,
            "include_adult": False
        }
        
        print(f"   🔍 سال {year}: حداقل {min_votes} رای | امتیاز >= {min_rating}")
        
        all_movies = []
        page = 1
        max_pages = 25
        
        while page <= max_pages and len(all_movies) < limit:
            params['page'] = page
            try:
                resp = requests.get(f"{self.base_url}/discover/movie", headers=self.headers, params=params, timeout=15)
                self.stats['api_calls'] += 1
                
                if resp.status_code == 200:
                    data = resp.json()
                    movies = data.get('results', [])
                    if not movies: break
                    all_movies.extend(movies)
                    total_pages = min(data.get('total_pages', 1), max_pages)
                    print(f"      📄 صفحه {page}/{total_pages} - {len(movies)} فیلم (مجموع: {len(all_movies)})")
                    page += 1
                    time.sleep(0.1)
                elif resp.status_code == 429:
                    print(f"      ⚠️ Rate limit! 2 ثانیه صبر...")
                    time.sleep(2)
                else:
                    print(f"      ⚠️ خطا {resp.status_code}")
                    break
            except Exception as e:
                print(f"      ❌ خطا: {e}")
                break
        
        # حذف تکراری‌ها و محدود کردن به خروجی
        unique_movies = {m['id']: m for m in all_movies}.values()
        result = sorted(list(unique_movies), key=lambda x: x.get('vote_average', 0), reverse=True)[:limit]
        print(f"      ✅ {len(result)} فیلم با امتیاز >= {min_rating} برای سال {year}")
        return result

    def get_complete_movie_details(self, movie_id: int) -> Dict:
        """
        دریافت کامل‌ترین اطلاعات ممکن برای یک فیلم با استفاده از append_to_response
        این متد همه چیز را در یک درخواست دریافت می‌کند [citation:3]
        """
        params = {
            "append_to_response": self.append_to_response,
            "language": "fa-IR"  # اولویت با زبان فارسی
        }
        
        try:
            resp = requests.get(
                f"{self.base_url}/movie/{movie_id}",
                headers=self.headers,
                params=params,
                timeout=30
            )
            self.stats['api_calls'] += 1
            
            if resp.status_code == 200:
                data = resp.json()
                
                # ----- اضافه کردن لینک‌های کامل تصاویر -----
                if data.get('poster_path'):
                    data['poster_url'] = f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
                if data.get('backdrop_path'):
                    data['backdrop_url'] = f"https://image.tmdb.org/t/p/w1280{data['backdrop_path']}"
                
                # تمیز کردن و خلاصه‌سازی اطلاعات اضافی برای خوانایی بهتر
                
                # 1. اطلاعات بازیگران و عوامل (credits)
                if data.get('credits'):
                    # استخراج کارگردان از بین عوامل
                    director = next((c['name'] for c in data['credits'].get('crew', []) if c['job'] == 'Director'), None)
                    # استخراج نویسنده
                    writer = next((c['name'] for c in data['credits'].get('crew', []) if c['job'] == 'Screenplay'), None)
                    # لیست 10 بازیگر اصلی
                    main_cast = [{'name': c['name'], 'character': c['character']} for c in data['credits'].get('cast', [])[:10]]
                    
                    data['credits_summary'] = {
                        'director': director,
                        'writer': writer,
                        'cast': main_cast,
                        'total_cast': len(data['credits'].get('cast', [])),
                        'total_crew': len(data['credits'].get('crew', []))
                    }
                    # حذف داده خام credits برای کاهش حجم (اختیاری)
                    # del data['credits']
                
                # 2. اطلاعات ویدیوها (trailers, teasers)
                if data.get('videos') and data.get('videos', {}).get('results'):
                    data['videos_summary'] = [
                        {'name': v['name'], 'key': v['key'], 'type': v['type'], 'site': v['site']}
                        for v in data['videos']['results'] if v['site'] == 'YouTube'
                    ][:5]  # فقط  تا ۵ ویدیو
                
                # 3. اطلاعات تصاویر (posters, backdrops)
                if data.get('images') and data.get('images', {}).get('posters'):
                    data['posters_url'] = [
                        f"https://image.tmdb.org/t/p/w342{p['file_path']}" 
                        for p in data['images']['posters'][:10]
                    ]
                
                # 4. اطلاعات کلیدی (keywords)
                if data.get('keywords') and data.get('keywords', {}).get('keywords'):
                    data['keywords_summary'] = [k['name'] for k in data['keywords']['keywords'][:15]]
                
                # 5. اطلاعات کشورها و تاریخ اکران (release_dates)
                if data.get('release_dates') and data.get('release_dates', {}).get('results'):
                    us_release = next((r for r in data['release_dates']['results'] if r['iso_3166_1'] == 'US'), None)
                    if us_release and us_release.get('release_dates'):
                        data['us_certification'] = us_release['release_dates'][0].get('certification')
                
                # 6. اطلاعات شبکه‌های پخش (watch providers)
                if data.get('watch/providers') and data.get('watch/providers', {}).get('results'):
                    us_providers = data['watch/providers']['results'].get('US', {})
                    if us_providers:
                        data['streaming_services'] = {
                            'flatrate': [p['provider_name'] for p in us_providers.get('flatrate', [])],
                            'rent': [p['provider_name'] for p in us_providers.get('rent', [])],
                            'buy': [p['provider_name'] for p in us_providers.get('buy', [])]
                        }
                
                return data
            return {}
        except Exception as e:
            print(f"      ❌ خطا در دریافت جزئیات فیلم {movie_id}: {e}")
            return {}

    def scrape_yearly_archive(self, start_year: int, end_year: int, min_rating: float = 7.0):
        """اجرای اصلی اسکرپینگ"""
        print(f"\n🎬 شروع ساخت آرشیو کامل از {start_year} تا {end_year}")
        print(f"⭐ فیلتر: فیلم‌های با امتیاز >= {min_rating}")
        print("="*60)
        
        archive = {
            'metadata': {
                'start_year': start_year,
                'end_year': end_year,
                'total_years': end_year - start_year + 1,
                'min_rating': min_rating,
                'min_votes': 100,
                'extraction_date': datetime.now().isoformat(),
                'description': 'آرشیو کامل فیلم‌ها با تمام اطلاعات (بازیگران، ویدیوها، تصاویر، عوامل پشت صحنه و...)'
            },
            'movies': []
        }
        
        for year in range(start_year, end_year + 1):
            print(f"\n📅 سال {year}:")
            
            # مرحله 1: دریافت لیست فیلم‌های سال
            movies = self.fetch_movies_by_year(year, min_votes=100, min_rating=min_rating, limit=500)
            
            # مرحله 2: دریافت جزئیات کامل برای هر فیلم
            detailed_movies = []
            total = len(movies)
            for i, movie in enumerate(movies, 1):
                print(f"      🔄 [{i}/{total}] دریافت اطلاعات کامل: {movie.get('title', 'Unknown')[:45]}...")
                details = self.get_complete_movie_details(movie['id'])
                if details:
                    detailed_movies.append(details)
                time.sleep(0.1)  # تاخیر برای جلوگیری از overload
            
            archive['movies'].extend(detailed_movies)
            self.stats['total_movies'] += len(detailed_movies)
            self.stats['years_processed'] += 1
            print(f"   ✅ {len(detailed_movies)} فیلم کامل برای سال {year} ذخیره شد")
        
        archive['metadata']['statistics'] = self.stats
        self.save_archive(archive)
        return archive

    def save_archive(self, archive: Dict):
        """ذخیره آرشیو نهایی"""
        filename = f"complete_movies_archive_{archive['metadata']['start_year']}_{archive['metadata']['end_year']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 آرشیو نهایی در فایل {filename} ذخیره شد.")
        print(f"\n📊 آمار نهایی:")
        print(f"   📅 سال‌های پردازش شده: {archive['metadata']['total_years']}")
        print(f"   🎬 تعداد کل فیلم‌ها: {archive['metadata']['statistics']['total_movies']}")
        print(f"   🌐 تعداد درخواست‌های API: {archive['metadata']['statistics']['api_calls']}")
        print(f"   ⭐ حداقل امتیاز: {archive['metadata']['min_rating']}")
        return filename


def main():
    ACCESS_TOKEN = os.environ.get('TMDB_ACCESS_TOKEN')
    
    if not ACCESS_TOKEN:
        print("❌ خطا: TMDB_ACCESS_TOKEN پیدا نشد!")
        sys.exit(1)
    
    # دریافت سال‌ها از آرگومان‌ها
    if len(sys.argv) >= 3:
        start_year = int(sys.argv[1])
        end_year = int(sys.argv[2])
    else:
        start_year = 2000
        end_year = 2026
    
    min_rating = 7.0
    if len(sys.argv) >= 4:
        min_rating = float(sys.argv[3])
    
    scraper = TMDBCompleteScraper(ACCESS_TOKEN)
    scraper.scrape_yearly_archive(start_year, end_year, min_rating)
    print("\n✅ فرآیند کامل شد! فایل JSON آماده دانلود است.")


if __name__ == "__main__":
    main()
