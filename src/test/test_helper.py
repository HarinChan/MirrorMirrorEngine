import pytest
from datetime import datetime, timezone
from types import SimpleNamespace

from ..app.helper import PenpalsHelper

@pytest.mark.unit
@pytest.mark.parametrize(
    "email,expected",
    [
        ("teacher@example.com", True),
        ("teacher.name+class@school.co.uk", True),
        ("invalid-email", False),
        ("missing-at.com", False),
        ("@no-local-part.com", False),
        ("", False),
        (None, False),
    ],
)
def test_validate_email(email, expected):
    assert PenpalsHelper.validate_email(email) is expected

@pytest.mark.unit
@pytest.mark.parametrize(
    "lat,lng,expected",
    [
        ("51.5074", "-0.1278", True),
        ("-90", "180", True),
        ("90", "-180", True),
        ("91", "0", False),
        ("0", "181", False),
        ("not-a-number", "0", False),
        ("0", "not-a-number", False),
        (None, "0", True),
        ("0", None, True),
        ("", "", True),
    ],
)
def test_validate_coordinates(lat, lng, expected):
    assert PenpalsHelper.validate_coordinates(lat, lng) is expected

@pytest.mark.unit
def test_sanitize_interests_normalizes_deduplicates_and_limits():
    raw = [
        "  Coding  ",
        "coding",
        " Machine   Learning ",
        "",
        " " * 3,
        123,
        "A" * 51,
        "Design",
        "music",
        "history",
        "science",
        "math",
        "physics",
        "chemistry",
        "biology",
        "art",
        "geography",
    ]

    result = PenpalsHelper.sanitize_interests(raw)

    assert result == [
        "coding",
        "machine learning",
        "design",
        "music",
        "history",
        "science",
        "math",
        "physics",
        "chemistry",
        "biology",
    ]
    assert len(result) == 10

@pytest.mark.unit
@pytest.mark.parametrize("value", [None, "not-a-list", 123, {"interest": "coding"}])
def test_sanitize_interests_invalid_input_returns_empty_list(value):
    assert PenpalsHelper.sanitize_interests(value) == []

@pytest.mark.unit
def test_format_profile_response_without_friends():
    created_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    classroom = SimpleNamespace(
        id=1,
        name="Year 2A",
        location="London",
        lattitude=51.5,
        longitude=-0.12,
        class_size=30,
        availability=[{"day": "monday", "time": "09:00-11:00"}],
        interests=["coding", "math"],
        account=SimpleNamespace(created_at=created_at),
        sent_relations=[],
    )

    response = PenpalsHelper.format_profile_response(classroom, include_friends=False)

    assert response["id"] == 1
    assert response["name"] == "Year 2A"
    assert response["location"] == "London"
    assert response["latitude"] == 51.5
    assert response["longitude"] == -0.12
    assert response["class_size"] == 30
    assert response["availability"] == [{"day": "monday", "time": "09:00-11:00"}]
    assert response["interests"] == ["coding", "math"]
    assert response["created_at"] == created_at.isoformat()
    assert "friends" not in response
    assert "friends_count" not in response

@pytest.mark.unit
def test_format_profile_response_with_friends():
    relation_created_at = datetime(2026, 2, 1, 8, 30, tzinfo=timezone.utc)

    friend = SimpleNamespace(
        id=9,
        name="Year 2B",
        location="Paris",
        interests=["art", "science"],
    )
    relation = SimpleNamespace(to_profile=friend, created_at=relation_created_at)

    classroom = SimpleNamespace(
        id=1,
        name="Year 2A",
        location="London",
        lattitude=51.5,
        longitude=-0.12,
        class_size=30,
        availability=[],
        interests=["coding"],
        account=SimpleNamespace(created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
        sent_relations=[relation],
    )

    response = PenpalsHelper.format_profile_response(classroom, include_friends=True)

    assert response["friends_count"] == 1
    assert response["friends"] == [
        {
            "id": 9,
            "name": "Year 2B",
            "location": "Paris",
            "interests": ["art", "science"],
            "friends_since": relation_created_at.isoformat(),
        }
    ]

@pytest.mark.unit
def test_format_profile_response_handles_missing_account():
    classroom = SimpleNamespace(
        id=2,
        name="No Account Class",
        location="Berlin",
        lattitude=52.52,
        longitude=13.405,
        class_size=25,
        availability=[],
        interests=[],
        sent_relations=[],
    )

    response = PenpalsHelper.format_profile_response(classroom)

    assert response["created_at"] is None

@pytest.mark.unit
@pytest.mark.parametrize(
    "interests1,interests2,expected",
    [
        (["coding", "math"], ["coding", "science"], 1 / 3),
        (["  Coding  ", "Math"], ["coding", "math"], 1.0),
        (["a"], ["b"], 0.0),
        ([], ["coding"], 0.0),
        (["coding"], [], 0.0),
        (None, ["coding"], 0.0),
        (["coding"], None, 0.0),
    ],
)
def test_calculate_interest_similarity(interests1, interests2, expected):
    result = PenpalsHelper.calculate_interest_similarity(interests1, interests2)
    assert result == pytest.approx(expected)

@pytest.mark.unit
def test_get_current_utc_timestamp_returns_timezone_aware_utc_datetime():
    ts = PenpalsHelper.get_current_utc_timestamp()

    assert isinstance(ts, datetime)
    assert ts.tzinfo is not None
    assert ts.tzinfo == timezone.utc

@pytest.mark.unit
@pytest.mark.parametrize(
    "availability,expected",
    [
        (None, True),
        ([], True),
        ([{"day": "monday", "time": "09:00-11:00"}], True),
        (
            [
                {"day": "tuesday", "time": "14:00-16:00"},
                {"day": "friday", "time": "10:00-12:00"},
            ],
            True,
        ),
        ("not-a-list", False),
        ([1, 2, 3], False),
        ([{"day": "monday"}], False),
        ([{"time": "09:00-11:00"}], False),
        ([{"day": "monday", "time": "09:00-11:00"}, {"day": "tuesday"}], False),
    ],
)
def test_validate_availability_format(availability, expected):
    assert PenpalsHelper.validate_availability_format(availability) is expected