
import random
from typing import Dict

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.2420.65 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.57 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-A528B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
]

# accept_languages = [ # Can be used to randomize through.
#     "en-US,en;q=0.9",
#     "en-GB,en;q=0.8",
#     "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
#     "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
#     "es-ES,es;q=0.9,en;q=0.8",
#     "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
#     "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
#     "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
#     "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
#     "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
#     "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
#     "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
#     "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
#     "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
#     "sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7"
# ]


def headers_randomizer(domain: str) -> Dict[str, str]:
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "image/avif,image/jpeg,image/jpg,image/png,image/apng,image/gif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Referer": f"https://www.google.com/search?q={domain}",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-control": "max-age=0"
    }
