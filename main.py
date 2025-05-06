import requests
from bs4 import BeautifulSoup

# 設定你的 LINE Bot Token 與 User ID
ACCESS_TOKEN = '你的 LINE Channel Access Token'
USER_ID = '你的 LINE User ID'

def fetch_news():
    url = "https://news.google.com/search?q=新光金控"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    articles = soup.select("article h3 a")
    news_list = []

    for article in articles[:5]:
        title = article.text
        link = 'https://news.google.com' + article['href'][1:]
        news_list.append(f"{title}\n{link}")

    return "\n\n".join(news_list)

def push_line_message(message):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }
    payload = {
        "to": USER_ID,
        "messages": [{
            "type": "text",
            "text": message
        }]
    }
    res = requests.post(url, headers=headers, json=payload)
    print(res.status_code, res.text)

if __name__ == "__main__":
    news = fetch_news()
    if news:
        push_line_message("【新光金控 最新新聞】\n\n" + news)
