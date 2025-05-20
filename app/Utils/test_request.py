import requests 
from bs4 import BeautifulSoup

def request():
    link = "https://www.greatplacetowork.com.bo/"
    try:
        req = requests.get(link)
        print(req.text)
    except Exception as err:
        print(f"Exception! {err}")
request()