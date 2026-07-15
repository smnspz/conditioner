from yoyo import step

_SEED = [
    ("none", "No equipment (bodyweight only)"),
    ("dumbbells", "Dumbbells"),
    ("barbell", "Barbell"),
    ("kettlebell", "Kettlebell"),
    ("resistance_bands", "Resistance/Elastic Bands"),
    ("pull_up_bar", "Pull-Up Bar"),
    ("bench", "Bench"),
    ("medicine_ball", "Medicine Ball"),
    ("jump_rope", "Jump Rope"),
    ("foam_roller", "Foam Roller"),
    ("yoga_mat", "Yoga Mat"),
    ("plyo_box", "Plyo Box"),
    ("battle_ropes", "Battle Ropes"),
    ("suspension_trainer", "Suspension Trainer (TRX)"),
]

_VALUES = ", ".join(f"('{id_}', '{name}')" for id_, name in _SEED)

steps = [
    step(
        """
        CREATE TABLE equipment (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
        """,
        "DROP TABLE equipment",
    ),
    step(f"INSERT INTO equipment (id, name) VALUES {_VALUES}", "DELETE FROM equipment"),
]
