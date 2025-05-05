def classify_news(news_list):
    categories = {
        "📈 業績 / 財報": ["財報", "獲利", "盈餘", "收入", "營收"],
        "🏛️ 政策 / 法規": ["金管會", "規範", "法令", "監理"],
        "👥 人事異動": ["總經理", "董事長", "辭職", "接任", "人事"],
        "📰 媒體評論": ["專欄", "分析", "觀點", "評論"],
    }
    result = {key: [] for key in categories}
    for item in news_list:
        categorized = False
        for cat, keywords in categories.items():
            if any(k in item["title"] for k in keywords):
                result[cat].append(item)
                categorized = True
                break
        if not categorized:
            result.setdefault("📌 其他", []).append(item)
    return result
