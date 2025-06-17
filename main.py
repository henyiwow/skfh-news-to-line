import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import email.utils
from datetime import datetime, timedelta, timezone
import re

# 設定你的 LINE Bot Token 與 User ID
ACCESS_TOKEN = '你的 LINE Channel Access Token'
USER_ID = '你的 LINE User ID'

# 台灣時區
TW_TZ = timezone(timedelta(hours=8))

# 關鍵字定義
KEYWORDS = {
    "新光金控": ["新光金控", "新光人壽", "新壽", "吳東進"],
    "台新金控": ["台新金控", "台新人壽", "台新壽", "吳東亮"],
    "保險相關": ["保險", "壽險", "健康險", "意外險", "人壽保險", "產險"]
}

# 排除關鍵字
EXCLUDED_KEYWORDS = ['保險套', '避孕套', '太陽人壽', '大西部人壽']

def classify_news(title, content):
    """新聞分類函數"""
    text = (title + " " + content).lower()
    
    for category, keywords in KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            return category
    return None

def get_article_summary(url, max_chars=100):
    """獲取文章摘要"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除不需要的標籤
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        
        # 尋找文章內容的常見標籤
        content_selectors = [
            'article p', '.content p', '.article-content p', 
            '.news-content p', '.post-content p', 'main p',
            '.entry-content p', '.story-content p'
        ]
        
        content_text = ""
        for selector in content_selectors:
            paragraphs = soup.select(selector)
            if paragraphs:
                content_text = " ".join([p.get_text().strip() for p in paragraphs[:3]])
                break
        
        # 如果找不到特定選擇器，嘗試所有 p 標籤
        if not content_text:
            paragraphs = soup.find_all('p')
            content_text = " ".join([p.get_text().strip() for p in paragraphs[:3]])
        
        # 清理文本
        content_text = re.sub(r'\s+', ' ', content_text)
        content_text = content_text.strip()
        
        # 截取指定字數
        if len(content_text) > max_chars:
            content_text = content_text[:max_chars] + "..."
        
        return content_text if content_text else "無法獲取摘要"
        
    except Exception as e:
        print(f"獲取摘要失敗: {e}")
        return "無法獲取摘要"

def fetch_news():
    """從 RSS 獲取新聞"""
    rss_urls = [
        "https://news.google.com/rss/search?q=新光金控+OR+新光人壽+OR+新壽+OR+吳東進&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "https://news.google.com/rss/search?q=台新金控+OR+台新人壽+OR+台新壽+OR+吳東亮&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        "https://news.google.com/rss/search?q=壽險+OR+保險+OR+人壽保險&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    ]
    
    news_by_category = {category: [] for category in KEYWORDS.keys()}
    processed_titles = set()
    
    for rss_url in rss_urls:
        try:
            print(f"正在抓取: {rss_url}")
            response = requests.get(rss_url, timeout=10)
            
            if response.status_code != 200:
                continue
                
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            print(f"找到 {len(items)} 則新聞")
            
            for item in items:
                try:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pubDate_elem = item.find('pubDate')
                    
                    if not all([title_elem, link_elem, pubDate_elem]):
                        continue
                    
                    title = title_elem.text.strip()
                    link = link_elem.text.strip()
                    pubDate_str = pubDate_elem.text.strip()
                    
                    # 跳過無效標題
                    if not title or title.startswith("Google"):
                        continue
                    
                    # 檢查是否為重複新聞
                    if title in processed_titles:
                        continue
                    
                    # 檢查排除關鍵字
                    if any(excluded in title for excluded in EXCLUDED_KEYWORDS):
                        continue
                    
                    # 檢查發布時間（24小時內）
                    try:
                        pub_datetime = email.utils.parsedate_to_datetime(pubDate_str).astimezone(TW_TZ)
                        now = datetime.now(TW_TZ)
                        if now - pub_datetime > timedelta(hours=24):
                            continue
                    except:
                        continue
                    
                    # 獲取文章摘要
                    print(f"正在獲取摘要: {title[:30]}...")
                    summary = get_article_summary(link)
                    
                    # 分類新聞
                    category = classify_news(title, summary)
                    
                    if category:
                        news_item = f"📰 {title}\n📝 {summary}\n🔗 {link}"
                        news_by_category[category].append(news_item)
                        processed_titles.add(title)
                        print(f"✅ 已分類到 [{category}]: {title[:30]}...")
                    
                except Exception as e:
                    print(f"處理新聞項目時發生錯誤: {e}")
                    continue
                    
        except Exception as e:
            print(f"處理 RSS 時發生錯誤: {e}")
            continue
    
    return news_by_category

def push_line_message(message):
    """發送 LINE 訊息"""
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }
    
    # 如果訊息太長，分段發送
    max_length = 4000
    if len(message) > max_length:
        parts = [message[i:i+max_length] for i in range(0, len(message), max_length)]
        for part in parts:
            payload = {
                "to": USER_ID,
                "messages": [{
                    "type": "text",
                    "text": part
                }]
            }
            response = requests.post(url, headers=headers, json=payload)
            print(f"發送狀態: {response.status_code}")
    else:
        payload = {
            "to": USER_ID,
            "messages": [{
                "type": "text",
                "text": message
            }]
        }
        response = requests.post(url, headers=headers, json=payload)
        print(f"發送狀態: {response.status_code}, 回應: {response.text}")

if __name__ == "__main__":
    print("開始抓取金控和保險相關新聞...")
    news_by_category = fetch_news()
    
    if any(news_by_category.values()):
        today = datetime.now(TW_TZ).strftime("%Y-%m-%d")
        
        for category, news_list in news_by_category.items():
            if news_list:
                message = f"【{today} {category}新聞整理】\n共 {len(news_list)} 則新聞\n\n"
                message += "\n\n".join(news_list)
                push_line_message(message)
                print(f"✅ 已發送 {category} 新聞 ({len(news_list)} 則)")
        
        print("新聞發送完成！")
    else:
        print("今日無符合條件的新聞")
        push_line_message("【今日新聞】\n暫無新光金控、台新金控或保險相關新聞")
