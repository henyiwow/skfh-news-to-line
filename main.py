from news_fetcher import fetch_news
from classifier import classify_news
from line_push import push_to_line
from formatter import format_message

news = fetch_news("新光金控")
classified = classify_news(news)
message = format_message(classified)

if message:
    status_code, res_text = push_to_line(message)
    print("Message sent:", status_code)
    print(res_text)
else:
    print("No news to send.")
