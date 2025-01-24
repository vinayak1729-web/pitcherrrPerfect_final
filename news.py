from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Function to scrape the latest news
def fetch_latest_news():
    url = "https://www.mlb.com/news/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the news articles (modify selectors based on website structure)
    articles = soup.find_all('article', class_='article-item', limit=4)
    news_list = []

    for article in articles:
        title = article.find('h1', class_='article-item__headline').get_text(strip=True)
        link = article.find('a', href=True)['href']
        
    
        news_list.append({
            'title': title,
            'link': f"https://www.mlb.com/news/",
          
        })

    return news_list

@app.route('/')
def home():
    news = fetch_latest_news()
    return render_template('news.html', news=news)

if __name__ == '__main__':
    app.run(debug=True)
