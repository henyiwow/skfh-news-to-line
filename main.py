import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import email.utils
from urllib.parse import quote
import requests
import re
from bs4 import BeautifulSoup

ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
print("✅ Access Token 前 10 碼：", ACCESS_TOKEN[:10] if ACCESS_TOKEN else "未設定")

CATEGORY_KEYWORDS = {
    "新光金控": ["新光金", "新光人壽", "新壽", "吳東進"],
    "台新金控": ["台新金", "台新人壽", "台新壽", "吳東亮"],
    "金控": ["金控", "金融控股", "中信金", "玉山金", "永豐金", "國泰金", "富邦金", "台灣金"],
    "保險": ["保險", "壽險", "健康險", "意外險", "人壽"],
    "其他": []
}

EXCLUDED_KEYWORDS = ['保險套', '避孕套', '保險套使用', '太陽人壽', '大西部人壽', '美國海岸保險']

TW_TZ = timezone(timedelta(hours=8))
now = datetime.now(TW_TZ)
today = now.date()

# ✅ 標題正規化
def normalize_title(title):
    title = re.sub(r'[｜|‧\-－–—~～].*$', '', title)  # 移除媒體後綴
    title = re.sub(r'<[^>]+>', '', title)            # 移除 HTML 標籤
    title = re.sub(r'[^\w\u4e00-\u9fff\s]', '', title)  # 移除非文字符號
    title = re.sub(r'\s+', ' ', title)               # 多餘空白
    return title.strip().lower()

def get_article_summary(url, max_chars=100):
    """獲取文章摘要（改良版）"""
    try:
        # 先檢查是否為 Google News 網址
        if 'news.google.com' in url:
            print(f"    ⚠️ Google News 網址，可能無法獲取摘要: {url[:60]}...")
            return "Google News 連結，請點擊查看完整內容"
        
        # 更完整的 headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }
        
        print(f"    🔍 嘗試獲取摘要: {url[:60]}...")
        response = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
        
        # 檢查最終 URL
        final_url = response.url
        print(f"    📍 最終 URL: {final_url[:60]}...")
        
        # 檢查是否成功獲取內容
        if response.status_code != 200:
            print(f"    ❌ HTTP 狀態碼: {response.status_code}")
            return f"無法獲取摘要（狀態碼：{response.status_code}）"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 先嘗試取 meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content_text = meta_desc.get('content').strip()
            print(f"    ✅ 從 meta description 獲取: {content_text[:50]}...")
        else:
            # 嘗試 og:description
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                content_text = og_desc.get('content').strip()
                print(f"    ✅ 從 og:description 獲取: {content_text[:50]}...")
            else:
                print(f"    ⚠️ 無法從 meta 標籤獲取摘要，嘗試解析內容...")
                
                # 移除不需要的標籤
                for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'form', 'button']):
                    tag.decompose()
                
                # 嘗試找到文章內容
                content_selectors = [
                    'article p', '.content p', '.article-content p', 
                    '.news-content p', '.post-content p', 'main p',
                    '.entry-content p', '.story-content p', '.article-body p'
                ]
                
                content_text = ""
                for selector in content_selectors:
                    try:
                        paragraphs = soup.select(selector)
                        if paragraphs:
                            valid_paragraphs = []
                            for p in paragraphs[:3]:
                                text = p.get_text().strip()
                                if len(text) > 30 and '點擊' not in text and '更多' not in text:
                                    valid_paragraphs.append(text)
                            
                            if valid_paragraphs:
                                content_text = " ".join(valid_paragraphs[:1])  # 只取第一段
                                print(f"    ✅ 從內容解析獲取: {content_text[:50]}...")
                                break
                    except:
                        continue
                
                if not content_text:
                    print(f"    ❌ 無法解析文章內容")
                    return "無法獲取文章摘要"
        
        # 清理和截取文本
        if content_text:
            # 移除多餘的空白和特殊字符
            content_text = re.sub(r'\s+', ' ', content_text)
            content_text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？；：「」『』（）、]', '', content_text)
            content_text = content_text.strip()
            
            # 截取指定字數
            if len(content_text) > max_chars:
                content_text = content_text[:max_chars] + "..."
            
            return content_text if content_text else "無法獲取摘要"
        
        return "無法獲取摘要"
        
    except requests.exceptions.Timeout:
        print(f"    ⏰ 請求超時")
        return "網站回應超時"
    except requests.exceptions.ConnectionError:
        print(f"    🔌 連線錯誤")
        return "網路連線錯誤"
    except Exception as e:
        print(f"    ❌ 其他錯誤: {str(e)[:50]}")
        return f"獲取摘要失敗"

def shorten_url(long_url):
    try:
        encoded_url = quote(long_url, safe='')
        api_url = f"http://tinyurl.com/api-create.php?url={encoded_url}"
        res = requests.get(api_url, timeout=5)
        if res.status_code == 200:
            return res.text.strip()
    except Exception as e:
        print("⚠️ 短網址失敗：", e)
    return long_url

def classify_news(title):
    title = normalize_title(title)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw.lower() in title for kw in keywords):
            return category
    return "其他"

def is_taiwan_news(source_name, link):
    taiwan_sources = [
        '工商時報', '中國時報', '經濟日報', '三立新聞網', '自由時報', '聯合新聞網',
        '鏡週刊', '台灣雅虎', '鉅亨網', '中時新聞網','Ettoday新聞雲',
        '天下雜誌', '奇摩新聞', '《現代保險》雜誌','遠見雜誌'
    ]
    if any(taiwan_source in source_name for taiwan_source in taiwan_sources) and "香港經濟日報" not in source_name:
        return True
    if '.tw' in link:
        return True
    return False

def is_similar_simple(title, known_titles):
    """簡化版相似度檢測（不使用語意模型）"""
    norm_title = normalize_title(title)
    
    for known_title in known_titles:
        # 計算字符重疊率
        title_set = set(norm_title)
        known_set = set(known_title)
        
        if len(title_set) == 0 or len(known_set) == 0:
            continue
            
        intersection = title_set.intersection(known_set)
        union = title_set.union(known_set)
        
        # 如果重疊率超過 80%，認為是重複
        if len(union) > 0:
            similarity = len(intersection) / len(union)
            if similarity > 0.8:
                return True
    
    return False

def fetch_news():
    rss_urls = [
        "https://news.google.com/rss/search?q=新光金控+OR+新光人壽+OR+台新金控+OR+台新人壽+OR+壽險+OR+金控+OR+人壽+OR+新壽+OR+台新壽+OR+吳東進+OR+吳東亮&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "https://news.google.com/rss/search?q=新光金控+OR+新光人壽+OR+新壽+OR+吳東進&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "https://news.google.com/rss/search?q=台新金控+OR+台新人壽+OR+台新壽+OR+吳東亮&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "https://news.google.com/rss/search?q=壽險+OR+健康險+OR+意外險+OR+人壽&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "https://news.google.com/rss/search?q=金控+OR+金融控股&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    ]

    classified_news = {cat: [] for cat in CATEGORY_KEYWORDS}
    known_titles = []  # 使用簡單的字符串列表

    for rss_url in rss_urls:
        res = requests.get(rss_url)
        print(f"✅ 來源: {rss_url} 回應狀態：{res.status_code}")
        if res.status_code != 200:
            continue

        root = ET.fromstring(res.content)
        items = root.findall(".//item")
        print(f"✅ 從 {rss_url} 抓到 {len(items)} 筆新聞")

        for item in items:
            title_elem = item.find('title')
            link_elem = item.find('link')
            pubDate_elem = item.find('pubDate')
            if title_elem is None or link_elem is None or pubDate_elem is None:
                continue

            title = title_elem.text.strip()
            link = link_elem.text.strip()
            pubDate_str = pubDate_elem.text.strip()
            if not title or title.startswith("Google ニュース"):
                continue

            source_elem = item.find('source')
            source_name = source_elem.text.strip() if source_elem is not None else "未標示"
            pub_datetime = email.utils.parsedate_to_datetime(pubDate_str).astimezone(TW_TZ)

            if now - pub_datetime > timedelta(hours=24):
                continue
            if any(bad_kw in title for bad_kw in EXCLUDED_KEYWORDS):
                continue
            if not is_taiwan_news(source_name, link):
                continue
            if is_similar_simple(title, known_titles):  # 使用簡化版相似度檢測
                continue

            # ✅ 獲取文章摘要
            print(f"📰 正在處理: {title[:40]}...")
            summary = get_article_summary(link)
            
            short_link = shorten_url(link)
            category = classify_news(title)
            
            # ✅ 修改格式，加入摘要
            formatted = f"📰 {title}\n📝 {summary}\n📌 來源：{source_name}\n🔗 {short_link}"
            classified_news[category].append(formatted)

            # ✅ 新增標題到已知列表（用正規化後標題）
            norm_title = normalize_title(title)
            known_titles.append(norm_title)

    return classified_news

def send_message_by_category(news_by_category):
    max_length = 4000
    
    # 收集所有有新聞的分類
    categories_with_news = []
    categories_without_news = []
    
    for category, messages in news_by_category.items():
        if messages:
            categories_with_news.append((category, messages))
        else:
            categories_without_news.append(category)
    
    # 構建完整訊息
    full_message = ""
    
    # 先加入有新聞的分類
    for category, messages in categories_with_news:
        category_section = f"【{today} 業企部 今日【{category}】重點新聞整理】 共{len(messages)}則新聞\n\n"
        category_content = "\n\n".join(messages)
        category_section += category_content + "\n\n"
        
        # 檢查是否會超過長度限制
        if len(full_message + category_section) > max_length:
            # 如果會超過，就截斷並結束
            remaining_space = max_length - len(full_message) - 50  # 保留空間給截斷提示
            if remaining_space > 100:  # 如果還有足夠空間
                truncated_section = category_section[:remaining_space] + "...\n\n📝 訊息已截斷，更多新聞請查看後續通知"
                full_message += truncated_section
            else:
                full_message += "📝 更多新聞因字數限制已省略"
            break
        else:
            full_message += category_section
    
    # 如果還有空間，加入無新聞的分類
    if categories_without_news and len(full_message) < max_length - 200:
        no_news_section = f"【{today} 業企部 今日無相關新聞分類整理】\n"
        no_news_content = "\n".join(f"📂【{cat}】無相關新聞" for cat in categories_without_news)
        no_news_section += no_news_content
        
        if len(full_message + no_news_section) <= max_length:
            full_message += no_news_section
    
    # 🆕 先顯示訊息內容
    print("\n" + "="*60)
    print("📱 完整訊息內容預覽：")
    print("="*60)
    print(full_message)
    print("="*60 + "\n")
    
    # 發送單一訊息
    if full_message.strip():
        broadcast_message(full_message.strip())
    else:
        # 如果沒有任何內容，發送簡單訊息
        simple_message = f"【{today} 業企部 今日新聞整理】\n暫無相關新聞"
        print("\n" + "="*60)
        print("📱 簡單訊息內容：")
        print("="*60)
        print(simple_message)
        print("="*60 + "\n")
        broadcast_message(simple_message)

def broadcast_message(message):
    if not ACCESS_TOKEN or ACCESS_TOKEN == "未設定":
        print("⚠️ ACCESS_TOKEN 未設定，僅顯示訊息內容：")
        print("=" * 50)
        print(message)
        print("=" * 50)
        return
    
    url = 'https://api.line.me/v2/bot/message/broadcast'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }

    data = {
        "messages": [{
            "type": "text",
            "text": message
        }]
    }

    print(f"📤 發送訊息總長：{len(message)} 字元")
    res = requests.post(url, headers=headers, json=data)
    print(f"📤 LINE 回傳狀態碼：{res.status_code}")
    print("📤 LINE 回傳內容：", res.text)

if __name__ == "__main__":
    print("🚀 開始抓取金控和保險相關新聞...")
    news = fetch_news()
    if news:
        send_message_by_category(news)
    else:
        print("⚠️ 沒有符合條件的新聞，不發送。")
