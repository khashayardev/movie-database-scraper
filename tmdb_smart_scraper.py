# tmdb_smart_scraper.py
import requests
import json
import time
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

class TMDBIranScraper:
    def __init__(self, access_token: str):
        self.base_url = "https://api.themoviedb.org/3"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json;charset=utf-8"
        }
        # لیست ID ژانرهای محبوب نزد مخاطب ایرانی
        self.popular_genres = [28, 12, 35, 18, 53, 878, 10749, 16, 80]

    def _get_genre_names(self) -> Dict[int, str]:
        """دریافت لیست اسامی ژانرها از API"""
        try:
            resp = requests.get(f"{self.base_url}/genre/movie/list", headers=self.headers, timeout=10)
            if resp.status_code == 200:
                return {g['id']: g['name'] for g in resp.json().get('genres', [])}
        except:
            pass
        return {}

    def fetch_movies(self, year: int, min_votes: int, min_rating: float, limit: int = 100) -> List[Dict]:
        """دریافت فیلم‌های یک سال با فیلترهای مشخص"""
        params = {
            "primary_release_year": year,
            "sort_by": "vote_average.desc",
            "vote_count.gte": min_votes,
            "vote_average.gte": min_rating,
            "with_genres": ",".join(map(str, self.popular_genres)),
            "include_adult": False
        }
        
        print(f"   🔍 فیلترها: حداقل {min_votes} رای | امتیاز >= {min_rating}")
        all_movies = []
        page, pages = 1, 1
        
        while page <= pages and len(all_movies) < limit:
            params['page'] = page
            try:
                resp = requests.get(f"{self.base_url}/discover/movie", headers=self.headers, params=params, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    all_movies.extend(data['results'])
                    pages = min(data.get('total_pages', 1), 10)
                    page += 1
                    time.sleep(0.1)
                else:
                    break
            except Exception as e:
                print(f"      خطا: {e}")
                break
        
        unique_movies = {m['id']: m for m in all_movies}.values()
        return sorted(list(unique_movies), key=lambda x: x.get('vote_average', 0), reverse=True)[:limit]

    def fetch_iranian_movies(self, year: int, min_votes: int = 100, limit: int = 20) -> List[Dict]:
        """دریافت فیلم‌های ایرانی یک سال"""
        params = {
            "primary_release_year": year,
            "with_origin_country": "IR",
            "sort_by": "vote_average.desc",
            "vote_count.gte": min_votes,
            "include_adult": False
        }
        
        print(f"   🇮🇷 فیلتر ایرانی: حداقل {min_votes} رای")
        all_movies = []
        page, pages = 1, 1
        
        while page <= pages and len(all_movies) < limit:
            params['page'] = page
            try:
                resp = requests.get(f"{self.base_url}/discover/movie", headers=self.headers, params=params, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    all_movies.extend(data['results'])
                    pages = min(data.get('total_pages', 1), 5)
                    page += 1
                    time.sleep(0.1)
                else:
                    break
            except Exception as e:
                print(f"      خطا: {e}")
                break
        
        unique_movies = {m['id']: m for m in all_movies}.values()
        return sorted(list(unique_movies), key=lambda x: x.get('vote_average', 0), reverse=True)[:limit]

    def get_movie_details(self, movie_id: int) -> Dict:
        """دریافت جزئیات کامل یک فیلم"""
        try:
            resp = requests.get(
                f"{self.base_url}/movie/{movie_id}",
                headers=self.headers,
                params={"append_to_response": "credits", "language": "fa-IR"},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get('poster_path'):
                    data['poster_url'] = f"https://image.tmdb.org/t/p/w342{data['poster_path']}"
                if data.get('credits'):
                    data['credits'] = {
                        'director': next((c['name'] for c in data['credits']['crew'] if c['job'] == 'Director'), None),
                        'cast': [c['name'] for c in data['credits']['cast'][:5]]
                    }
                return data
            return {}
        except:
            return {}

    def scrape_yearly_archive(self, start_year: int, end_year: int):
        """اسکرپ سال‌های مورد نظر"""
        print(f"\n🎬 شروع ساخت آرشیو هوشمند از {start_year} تا {end_year}")
        print("="*60)
        
        archive = {
            'metadata': {
                'start_year': start_year,
                'end_year': end_year,
                'total_years': end_year - start_year + 1,
                'extraction_date': datetime.now().isoformat(),
            },
            'movies': []
        }
        
        for year in range(start_year, end_year + 1):
            print(f"\n📅 سال {year}:")
            
            print("   🌍 فیلم‌های بین‌المللی...")
            world_movies = self.fetch_movies(year, min_votes=500, min_rating=6.5, limit=100)
            
            print("   🇮🇷 فیلم‌های ایرانی...")
            iranian_movies = self.fetch_iranian_movies(year, min_votes=100, limit=20)
            
            all_movies = {m['id']: m for m in world_movies + iranian_movies}.values()
            
            detailed_movies = []
            for movie in list(all_movies):
                print(f"      🔄 {movie.get('title', 'Unknown')[:40]}...")
                details = self.get_movie_details(movie['id'])
                if details:
                    details['is_iranian'] = movie['id'] in [m['id'] for m in iranian_movies]
                    detailed_movies.append(details)
                time.sleep(0.05)
            
            archive['movies'].extend(detailed_movies)
            print(f"   ✅ {len(detailed_movies)} فیلم برای سال {year}")
        
        self.save_archive(archive)
        return archive

    def save_archive(self, archive: Dict):
        filename = f"iran_smart_archive_{archive['metadata']['start_year']}_{archive['metadata']['end_year']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)
        print(f"\n💾 آرشیو در {filename} ذخیره شد")
        return filename


def main():
    ACCESS_TOKEN = os.environ.get('TMDB_ACCESS_TOKEN')
    
    if not ACCESS_TOKEN:
        print("❌ خطا: TMDB_ACCESS_TOKEN پیدا نشد!")
        print("لطفاً Secret را در GitHub تنظیم کنید.")
        sys.exit(1)
    
    scraper = TMDBIranScraper(ACCESS_TOKEN)
    
    # دریافت سال‌ها از آرگومان‌های خط فرمان یا ورودی
    if len(sys.argv) > 2:
        start_year = int(sys.argv[1])
        end_year = int(sys.argv[2])
    else:
        start_year = 2000
        end_year = 2026
    
    print(f"\n🔥 شروع اسکرپینگ {start_year} تا {end_year}")
    scraper.scrape_yearly_archive(start_year, end_year)
    print("\n✅ فرآیند کامل شد!")


if __name__ == "__main__":
    main()
