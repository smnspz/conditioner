import pytest

from conditioner.core.domain.readiness.readiness import ReadinessZone


@pytest.mark.parametrize(
    ("score", "expected_zone"),
    [
        (100, ReadinessZone.PEAK),
        (80, ReadinessZone.PEAK),
        (79, ReadinessZone.GOOD),
        (65, ReadinessZone.GOOD),
        (64, ReadinessZone.MODERATE),
        (50, ReadinessZone.MODERATE),
        (49, ReadinessZone.LIGHT),
        (35, ReadinessZone.LIGHT),
        (34, ReadinessZone.REST),
        (0, ReadinessZone.REST),
    ],
)
def test_from_score_maps_to_expected_zone(score: int, expected_zone: ReadinessZone) -> None:
    assert ReadinessZone.from_score(score) is expected_zone
