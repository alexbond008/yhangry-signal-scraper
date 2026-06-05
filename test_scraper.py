from scraper import scrape_website
url = "https://northerngroup.co.uk"
text = scrape_website(url)
print(text[-2000:])
