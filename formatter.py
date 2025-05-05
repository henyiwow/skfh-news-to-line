from datetime import datetime

def format_message(classified):
    message = f"📢 新光金控 - 今日新聞摘要（{datetime.today().strftime('%Y/%m/%d')}）\n\n"
    for category, items in classified.items():
        if items:
            message += f"{category}\n"
            for news in items:
                message += f"- {news['title']}\n  🔗 {news['link']}\n"
            message += "\n"
    return message.strip()
