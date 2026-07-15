from conditioner.core.domain.workout.constraints import TrainingGoal, WorkoutConstraints


def test_defaults_to_empty_available_minutes() -> None:
    constraints = WorkoutConstraints(
        user_id="user-1", equipment=["dumbbells"], goal=TrainingGoal.MMA_CONDITIONING
    )

    assert constraints.available_minutes_by_weekday == {}
