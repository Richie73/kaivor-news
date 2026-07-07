from dataclasses import dataclass


@dataclass
class Article:
    source: str
    title: str
    link: str
    published: str
    summary: str = ""
    category: str = ""
