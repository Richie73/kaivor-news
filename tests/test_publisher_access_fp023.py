from publisher_access import publisher_access_info, publisher_for_url


def test_detects_supported_subscription_publishers():
    cases = [
        ("https://www.nytimes.com/2026/01/01/example.html", "The New York Times"),
        ("https://www.telegraph.co.uk/news/example/", "The Telegraph"),
        ("https://www.independent.co.uk/news/example", "The Independent"),
        ("https://www.theathletic.com/123/example/", "The Athletic"),
    ]
    for url, expected in cases:
        assert publisher_for_url(url)["label"] == expected


def test_rejects_domain_suffix_spoofing():
    assert publisher_for_url("https://nytimes.com.attacker.example/story") is None
    assert publisher_for_url("https://nottelegraph.co.uk.example/story") is None


def test_unknown_and_invalid_urls_are_safe():
    assert publisher_access_info("Publisher", "https://example.com/story") == {
        "supported": False, "publisher": "", "label": "Open original article"
    }
    assert publisher_for_url("not a url") is None
    assert publisher_for_url("") is None


def test_subdomains_are_supported():
    assert publisher_for_url("https://cooking.nytimes.com/recipe") ["label"] == "The New York Times"
