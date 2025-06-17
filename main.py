import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import email.utils
from datetime import datetime, timedelta, timezone
import re
import os

# 從環境變數讀取設定（推薦用於 GitHub Actions）
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN', '你的 LINE Channel Access Token')
USER_ID = os.getenv('USER_ID', '你的 LINE User ID')

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除不需要的標籤
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
            tag.decompose()
        
        # 尋找文章內容的常見標籤
        content_selectors = [
            'article p', '.content p', '.article-content p', 
            '.news-content p', '.post-content p', 'main p',
            '.entry-content p', '.story-content p', '.article-body p'
        ]
        
        content_text = ""
        for selector in content_selectors:
            paragraphs = soup.select(selector)
            if paragraphs and len(paragraphs) > 0:
                # 取前3段，過濾掉太短的段落
                valid_paragraphs = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20]
                if valid_paragraphs:
                    content_text = " ".join(valid_paragraphs[:2])
                    break
        
        # 如果找不到特定選擇器，嘗試所有 p 標籤
        if not content_text:
            paragraphs = soup.find_all('p')
            valid_paragraphs = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20]
            if valid_paragraphs:
                content_text = " ".join(valid_paragraphs[:2])
        
        # 清理文本
        content_text = re.sub(r'\s+', ' ', content_text)
        content_text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？；：「」『』（）]', '', content_text)
        content_text = content_text.strip()
        
        # 截取指定字數
        if len(content_text) > max_chars:
            content_text = content_text[:max_chars] + "..."
        
        return content_text if content_text else "無法獲取摘要"
        
    except Exception as e:
        print(f"獲取摘要失敗 ({url}): {e}")
        return "無法獲取摘要"

def is_taiwan_news(source_name, link):
    """判斷是否為台灣新聞"""
    taiwan_sources = [
        '工商時報', '中國時報', '經濟日報', '三立新聞網', '自由時報', '聯合新聞網',
        '鏡週刊', '台灣雅虎', '鉅亨網', '中時新聞網', 'Ettoday新聞雲',
        '天下雜誌', '奇摩新聞', '現代保險', '遠見雜誌', '財訊', '商業周刊'
    ]
    
    if any(taiwan_source in source_name for taiwan_source in taiwan_sources):
        return True
    if '.tw' in link:
        return True
    return False

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
            response = requests.get(rss_url, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ RSS 請求失敗: {response.status_code}")
                continue
                
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            print(f"找到 {len(items)} 則新聞")
            
            for item in items:
                try:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pubDate_elem = item.find('pubDate')
                    source_elem = item.find('source')
                    
                    if not all([title_elem, link_elem, pubDate_elem]):
                        continue
                    
                    title = title_elem.text.strip()
                    link = link_elem.text.strip()
                    pubDate_str = pubDate_elem.text.strip()
                    source_name = source_elem.text.strip() if source_elem is not None else "未知來源"
                    
                    # 跳過無效標題
                    if not title or title.startswith("Google") or len(title) < 10:
                        continue
                    
                    # 檢查是否為重複新聞（簡化標題比對）
                    title_normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', title.lower())
                    if title_normalized in processed_titles:
                        continue
                    
                    # 檢查排除關鍵字
                    if any(excluded in title for excluded in EXCLUDED_KEYWORDS):
                        continue
                    
                    # 檢查是否為台灣新聞
                    if not is_taiwan_news(source_name, link):
                        continue
                    
                    # 檢查發布時間（24小時內）
                    try:
                        pub_datetime = email.utils.parsedate_to_datetime(pubDate_str).astimezone(TW_TZ)
                        now = datetime.now(TW_TZ)
                        if now - pub_datetime > timedelta(hours=24):
                            continue
                    except:
                        # 如果時間解析失敗，跳過時間檢查
                        pass
                    
                    # 獲取文章摘要
                    print(f"正在獲取摘要: {title[:40]}...")
                    summary = get_article_summary(link)
                    
                    # 分類新聞
                    category = classify_news(title, summary)
                    
                    if category:
                        news_item = f"📰 {title}\n📝 {summary}\n🔗 {link}\n📌 來源：{source_name}"
                        news_by_category[category].append(news_item)
                        processed_titles.add(title_normalized)
                        print(f"✅ 已分類到 [{category}]: {title[:40]}...")
                    else:
                        print(f"⚠️ 未符合分類條件: {title[:40]}...")
                    
                except Exception as e:
                    print(f"處理新聞項目時發生錯誤: {e}")
                    continue
                    
        except Exception as e:
            print(f"處理 RSS 時發生錯誤: {e}")
            continue
    
    return news_by_category

def push_line_message(message):
    """發送 LINE 訊息"""
    # 檢查 ACCESS_TOKEN 是否設定
    if not ACCESS_TOKEN or ACCESS_TOKEN == '你的 LINE Channel Access Token':
        print("⚠️ ACCESS_TOKEN 未正確設定，跳過 LINE 訊息發送")
        print(f"📝 預覽訊息內容:\n{message}")
        return
    
    # 檢查 USER_ID 是否設定
    if not USER_ID or USER_ID == '你的 LINE User ID':
        print("⚠️ USER_ID 未正確設定，跳過 LINE 訊息發送")
        print(f"📝 預覽訊息內容:\n{message}")
        return
    
    url = 'https://api.line.me/v2/bot/message/push'
    
    # 確保 ACCESS_TOKEN 為純 ASCII 字符
    try:
        token = ACCESS_TOKEN.encode('ascii').decode('ascii')
    except UnicodeEncodeError:
        print("⚠️ ACCESS_TOKEN 包含非 ASCII 字符，請檢查 token 設定")
        return
    
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Authorization': f'Bearer {token}'
    }
    
    try:
        # 如果訊息太長，分段發送
        max_length = 4000
        if len(message) > max_length:
            parts = [message[i:i+max_length] for i in range(0, len(message), max_length)]
            for i, part in enumerate(parts):
                payload = {
                    "to": USER_ID,
                    "messages": [{
                        "type": "text",
                        "text": part
                    }]
                }
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                print(f"發送第 {i+1} 段狀態: {response.status_code}")
                if response.status_code != 200:
                    print(f"發送失敗: {response.text}")
        else:
            payload = {
                "to": USER_ID,
                "messages": [{
                    "type": "text",
                    "text": message
                }]
            }
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            print(f"發送狀態: {response.status_code}")
            if response.status_code != 200:
                print(f"發送失敗: {response.text}")
            else:
                print("✅ 訊息發送成功")
                
    except Exception as e:
        print(f"❌ 發送 LINE 訊息時發生錯誤: {e}")

if __name__ == "__main__":
    print("開始抓取金控和保險相關新聞...")
    print(f"ACCESS_TOKEN 設定狀態: {'✅ 已設定' if ACCESS_TOKEN and ACCESS_TOKEN != '你的 LINE Channel Access Token' else '❌ 未設定'}")
    print(f"USER_ID 設定狀態: {'✅ 已設定' if USER_ID and USER_ID != '你的 LINE User ID' else '❌ 未設定'}")
    
    news_by_category = fetch_news()
    
    # 統計總新聞數量
    total_news = sum(len(news_list) for news_list in news_by_category.values())
    print(f"\n📊 總共找到 {total_news} 則符合條件的新聞")
    
    if total_news > 0:
        today = datetime.now(TW_TZ).strftime("%Y-%m-%d")
        
        for category, news_list in news_by_category.items():
            if news_list:
                message = f"【{today} {category}新聞整理】\n共 {len(news_list)} 則新聞\n\n"
                message += "\n\n".join(news_list)
                push_line_message(message)
                print(f"✅ 已處理 {category} 新聞 ({len(news_list)} 則)")
        
        print("新聞處理完成！")
    else:
        no_news_message = f"【{datetime.now(TW_TZ).strftime('%Y-%m-%d')} 今日新聞】\n暫無新光金控、台新金控或保險相關新聞"
        push_line_message(no_news_message)
        print("今日無符合條件的新聞")
