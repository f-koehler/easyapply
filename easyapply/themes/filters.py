import re

RE_URL_PROTO = re.compile(r"^\w+://(.+)")
RE_GITHUB_USERNAME = re.compile(r"^github\.com/([\w\d\-]+)(?:$|/.*)")


def strip_url_protocol(url: str) -> str:
    m = RE_URL_PROTO.match(url)
    if m:
        return m.group(1)

    raise ValueError(f"Invalid URL: {url}")


def get_github_username(url: str) -> str:
    url = strip_url_protocol(url)
    m = RE_GITHUB_USERNAME.match(url)
    if m:
        return m.group(1)

    raise ValueError(f"Invalid GitHub URL: {url}")
