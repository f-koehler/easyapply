from easyapply.themes import filters
import datetime
import pytest


def test_strip_url():
    assert filters.strip_url_protocol("http://google.com") == "google.com"
    assert filters.strip_url_protocol("file:///home/user/test") == "/home/user/test"
    with pytest.raises(ValueError):
        filters.strip_url_protocol("google.com")


def test_get_github_username():
    assert (
        filters.get_github_username("https://github.com/torvalds/linux") == "torvalds"
    )
    assert filters.get_github_username("https://github.com/f-koehler") == "f-koehler"
    assert filters.get_github_username("https://github.com/f-koehler/") == "f-koehler"

    with pytest.raises(ValueError):
        filters.get_github_username("github.com/torvalds/linux") == "torvalds"

    with pytest.raises(ValueError):
        filters.get_github_username("github.com/f-koehler") == "f-koehler"

    with pytest.raises(ValueError):
        filters.get_github_username("github.com/f-koehler/") == "f-koehler"


def test_parse_date():
    assert filters.parse_date("2022-01-01") == datetime.datetime(2022, 1, 1)
    assert filters.parse_date("2022-01") == datetime.datetime(2022, 1, 1)
    assert filters.parse_date("2022") == datetime.datetime(2022, 1, 1)
    
    with pytest.raises(ValueError):
        assert filters.parse_date("2022-01-01:01:14")


def test_day_suffix():
    expectation = (
        ["st", "nd", "rd"] + (["th"] * 17) + ["st", "nd", "rd"] + (["th"] * 7) + ["st"]
    )
    for i in range(1, 32):
        assert filters.day_suffix(datetime.datetime(2022, 1, i)) == expectation[i - 1]
