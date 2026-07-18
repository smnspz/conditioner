import json

from yoyo import step

_CREATE = """
CREATE TABLE exercise_catalog (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    modality TEXT NOT NULL,
    required_gear_json TEXT NOT NULL DEFAULT '[]',
    optional_gear_json TEXT NOT NULL DEFAULT '[]',
    difficulty INTEGER NOT NULL DEFAULT 1,
    primary_muscles_json TEXT NOT NULL DEFAULT '[]',
    movement_pattern TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]'
)
"""

# Each entry: (id, name, modality, required_gear, optional_gear,
#              difficulty, primary_muscles, movement_pattern, tags)
# required_gear=[] means bodyweight-only (always available).
# difficulty: 1=beginner, 2=intermediate, 3=advanced.
_EXERCISES = [
    # --- Bodyweight — push ---
    ("bw_push_up", "Push-Up", "strength", [], [], 1, ["chest", "triceps", "shoulders"], "push", ["compound", "upper_body"]),
    ("bw_pike_push_up", "Pike Push-Up", "strength", [], [], 2, ["shoulders", "triceps"], "push", ["compound", "upper_body"]),
    ("bw_diamond_push_up", "Diamond Push-Up", "strength", [], [], 2, ["triceps", "chest"], "push", ["isolation", "upper_body"]),
    ("bw_handstand_push_up", "Handstand Push-Up", "strength", [], [], 3, ["shoulders", "triceps"], "push", ["compound", "upper_body", "skill"]),
    # --- Bodyweight — pull ---
    ("bw_inverted_row", "Inverted Row", "strength", [], [], 1, ["lats", "biceps", "upper_back"], "pull", ["compound", "upper_body"]),
    ("bw_chin_up", "Chin-Up", "strength", ["pull_up_bar"], [], 1, ["lats", "biceps"], "pull", ["compound", "upper_body"]),
    ("bw_pull_up", "Pull-Up", "strength", ["pull_up_bar"], [], 2, ["lats", "upper_back"], "pull", ["compound", "upper_body"]),
    ("bw_commando_pull_up", "Commando Pull-Up", "strength", ["pull_up_bar"], [], 3, ["lats", "obliques"], "pull", ["compound", "upper_body", "core"]),
    # --- Bodyweight — hinge ---
    ("bw_good_morning", "Bodyweight Good Morning", "strength", [], [], 1, ["hamstrings", "glutes", "lower_back"], "hinge", ["compound", "lower_body"]),
    ("bw_single_leg_rdl", "Single-Leg Romanian Deadlift", "strength", [], [], 2, ["hamstrings", "glutes", "balance"], "hinge", ["compound", "lower_body", "balance"]),
    # --- Bodyweight — squat ---
    ("bw_squat", "Bodyweight Squat", "strength", [], [], 1, ["quads", "glutes"], "squat", ["compound", "lower_body"]),
    ("bw_lunge", "Reverse Lunge", "strength", [], [], 1, ["quads", "glutes", "hamstrings"], "squat", ["compound", "lower_body"]),
    ("bw_bulgarian_split_squat", "Bulgarian Split Squat", "strength", [], [], 2, ["quads", "glutes"], "squat", ["compound", "lower_body", "balance"]),
    ("bw_jump_squat", "Jump Squat", "strength", [], [], 2, ["quads", "glutes", "calves"], "squat", ["compound", "lower_body", "explosive"]),
    ("bw_pistol_squat", "Pistol Squat", "strength", [], [], 3, ["quads", "glutes", "balance"], "squat", ["compound", "lower_body", "skill"]),
    # --- Bodyweight — core ---
    ("bw_plank", "Plank", "strength", [], [], 1, ["core", "shoulders"], "core", ["isometric", "core"]),
    ("bw_side_plank", "Side Plank", "strength", [], [], 1, ["obliques", "core"], "core", ["isometric", "core"]),
    ("bw_hollow_hold", "Hollow Body Hold", "strength", [], [], 2, ["core", "hip_flexors"], "core", ["isometric", "core"]),
    ("bw_dead_bug", "Dead Bug", "strength", [], [], 1, ["core", "hip_flexors"], "core", ["core", "stability"]),
    ("bw_v_up", "V-Up", "strength", [], [], 2, ["core", "hip_flexors"], "core", ["core"]),
    # --- Bodyweight — cardio ---
    ("bw_burpee", "Burpee", "cardio", [], [], 2, ["full_body"], "cardio", ["metabolic", "full_body"]),
    ("bw_jumping_jack", "Jumping Jack", "cardio", [], [], 1, ["full_body"], "cardio", ["low_impact", "warmup"]),
    ("bw_mountain_climber", "Mountain Climber", "cardio", [], [], 2, ["core", "shoulders", "hip_flexors"], "cardio", ["metabolic", "core"]),
    ("bw_high_knee", "High Knees", "cardio", [], [], 1, ["hip_flexors", "quads"], "cardio", ["metabolic", "lower_body"]),
    ("bw_sprawl", "Sprawl", "cardio", [], [], 2, ["full_body"], "cardio", ["mma", "metabolic"]),
    ("bw_shadow_box", "Shadow Boxing", "cardio", [], [], 1, ["shoulders", "core"], "cardio", ["mma", "low_impact"]),
    # --- Bodyweight — mobility ---
    ("mob_hip_circle", "Hip Circle", "mobility", [], [], 1, ["hips", "glutes"], "mobility", ["warmup", "hip_mobility"]),
    ("mob_leg_swing", "Leg Swing", "mobility", [], [], 1, ["hip_flexors", "hamstrings"], "mobility", ["warmup", "hip_mobility"]),
    ("mob_thoracic_rotation", "Thoracic Rotation", "mobility", [], [], 1, ["upper_back", "core"], "mobility", ["warmup", "spine_mobility"]),
    ("mob_world_greatest_stretch", "World's Greatest Stretch", "mobility", [], [], 2, ["hips", "thoracic", "hamstrings"], "mobility", ["full_body", "warmup"]),
    # --- Resistance bands ---
    ("rb_row", "Resistance Band Row", "strength", ["resistance_bands"], [], 1, ["lats", "upper_back", "biceps"], "pull", ["compound", "upper_body"]),
    ("rb_chest_press", "Resistance Band Chest Press", "strength", ["resistance_bands"], [], 1, ["chest", "triceps", "shoulders"], "push", ["compound", "upper_body"]),
    ("rb_shoulder_press", "Resistance Band Shoulder Press", "strength", ["resistance_bands"], [], 1, ["shoulders", "triceps"], "push", ["compound", "upper_body"]),
    ("rb_bicep_curl", "Resistance Band Bicep Curl", "strength", ["resistance_bands"], [], 1, ["biceps"], "pull", ["isolation", "upper_body"]),
    ("rb_tricep_extension", "Resistance Band Tricep Extension", "strength", ["resistance_bands"], [], 1, ["triceps"], "push", ["isolation", "upper_body"]),
    ("rb_lateral_raise", "Resistance Band Lateral Raise", "strength", ["resistance_bands"], [], 1, ["shoulders"], "push", ["isolation", "upper_body"]),
    ("rb_pull_apart", "Resistance Band Pull-Apart", "strength", ["resistance_bands"], [], 1, ["rear_delt", "upper_back"], "pull", ["isolation", "upper_body", "warmup"]),
    ("rb_face_pull", "Resistance Band Face Pull", "strength", ["resistance_bands"], [], 1, ["rear_delt", "upper_back", "external_rotators"], "pull", ["isolation", "upper_body"]),
    ("rb_squat", "Resistance Band Squat", "strength", ["resistance_bands"], [], 1, ["quads", "glutes"], "squat", ["compound", "lower_body"]),
    ("rb_deadlift", "Resistance Band Deadlift", "strength", ["resistance_bands"], [], 1, ["hamstrings", "glutes", "lower_back"], "hinge", ["compound", "lower_body"]),
    ("rb_romanian_deadlift", "Resistance Band Romanian Deadlift", "strength", ["resistance_bands"], [], 2, ["hamstrings", "glutes"], "hinge", ["compound", "lower_body"]),
    ("rb_hip_thrust", "Resistance Band Hip Thrust", "strength", ["resistance_bands"], [], 1, ["glutes", "hamstrings"], "hinge", ["compound", "lower_body"]),
    ("rb_woodchop", "Resistance Band Woodchop", "strength", ["resistance_bands"], [], 2, ["core", "obliques", "shoulders"], "core", ["rotational", "core", "mma"]),
    ("rb_pallof_press", "Resistance Band Pallof Press", "strength", ["resistance_bands"], [], 2, ["core", "obliques"], "core", ["anti_rotation", "core", "mma"]),
    # --- Dumbbells ---
    ("db_goblet_squat", "Goblet Squat", "strength", ["dumbbells"], [], 1, ["quads", "glutes", "core"], "squat", ["compound", "lower_body"]),
    ("db_rdl", "Dumbbell Romanian Deadlift", "strength", ["dumbbells"], [], 2, ["hamstrings", "glutes"], "hinge", ["compound", "lower_body"]),
    ("db_bent_over_row", "Dumbbell Bent-Over Row", "strength", ["dumbbells"], [], 2, ["lats", "upper_back", "biceps"], "pull", ["compound", "upper_body"]),
    ("db_shoulder_press", "Dumbbell Shoulder Press", "strength", ["dumbbells"], [], 2, ["shoulders", "triceps"], "push", ["compound", "upper_body"]),
    ("db_farmers_carry", "Farmers Carry", "strength", ["dumbbells"], [], 1, ["core", "grip", "traps"], "carry", ["full_body", "mma"]),
    ("db_thruster", "Dumbbell Thruster", "strength", ["dumbbells"], [], 2, ["quads", "shoulders", "full_body"], "squat", ["compound", "full_body", "metabolic"]),
    # --- Kettlebell ---
    ("kb_swing", "Kettlebell Swing", "strength", ["kettlebell"], [], 2, ["glutes", "hamstrings", "core"], "hinge", ["compound", "lower_body", "mma", "explosive"]),
    ("kb_goblet_squat", "Kettlebell Goblet Squat", "strength", ["kettlebell"], [], 1, ["quads", "glutes"], "squat", ["compound", "lower_body"]),
    ("kb_clean", "Kettlebell Clean", "strength", ["kettlebell"], [], 3, ["full_body", "power"], "hinge", ["compound", "full_body", "mma", "skill"]),
    ("kb_turkish_get_up", "Turkish Get-Up", "strength", ["kettlebell"], [], 3, ["full_body", "shoulders", "core"], "core", ["full_body", "mma", "skill"]),
    # --- Jump rope ---
    ("jr_jump_rope", "Jump Rope", "cardio", ["jump_rope"], [], 1, ["calves", "cardio"], "cardio", ["low_impact", "mma", "coordination"]),
    ("jr_double_under", "Double Under", "cardio", ["jump_rope"], [], 3, ["calves", "cardio", "coordination"], "cardio", ["mma", "coordination", "explosive"]),
    # --- Plyo box ---
    ("pb_box_jump", "Box Jump", "strength", ["plyo_box"], [], 2, ["quads", "glutes", "calves"], "squat", ["explosive", "lower_body", "mma"]),
    ("pb_step_up", "Step-Up", "strength", ["plyo_box"], [], 1, ["quads", "glutes"], "squat", ["compound", "lower_body", "balance"]),
    ("pb_box_lateral_jump", "Lateral Box Jump", "strength", ["plyo_box"], [], 3, ["quads", "glutes", "abductors"], "squat", ["explosive", "lower_body", "mma", "agility"]),
    # --- Battle ropes ---
    ("br_alternating_wave", "Battle Rope Alternating Wave", "cardio", ["battle_ropes"], [], 2, ["shoulders", "core", "cardio"], "cardio", ["metabolic", "upper_body", "mma"]),
    ("br_slam", "Battle Rope Slam", "cardio", ["battle_ropes"], [], 2, ["full_body", "core", "power"], "cardio", ["metabolic", "mma", "explosive"]),
    # --- Suspension trainer ---
    ("trx_row", "TRX Row", "strength", ["suspension_trainer"], [], 1, ["lats", "upper_back", "biceps"], "pull", ["compound", "upper_body"]),
    ("trx_push_up", "TRX Push-Up", "strength", ["suspension_trainer"], [], 2, ["chest", "triceps", "core"], "push", ["compound", "upper_body", "core"]),
    ("trx_pike", "TRX Pike", "strength", ["suspension_trainer"], [], 2, ["core", "shoulders"], "core", ["core", "skill"]),
    ("trx_single_leg_squat", "TRX Single-Leg Squat", "strength", ["suspension_trainer"], [], 2, ["quads", "glutes", "balance"], "squat", ["compound", "lower_body", "balance"]),
    # --- Bench ---
    ("bench_dip", "Bench Dip", "strength", ["bench"], [], 1, ["triceps", "chest", "shoulders"], "push", ["compound", "upper_body"]),
    ("bench_step_up", "Bench Step-Up", "strength", ["bench"], [], 1, ["quads", "glutes"], "squat", ["compound", "lower_body"]),
    # --- Medicine ball ---
    ("mb_slam", "Medicine Ball Slam", "strength", ["medicine_ball"], [], 2, ["core", "shoulders", "full_body"], "core", ["explosive", "mma", "full_body"]),
    ("mb_rotational_throw", "Medicine Ball Rotational Throw", "strength", ["medicine_ball"], [], 2, ["core", "obliques", "shoulders"], "core", ["rotational", "mma", "explosive"]),
]


def _row(entry: tuple) -> tuple:
    """Serialise list fields to JSON for insertion."""
    id_, name, modality, req, opt, diff, muscles, pattern, tags = entry
    return (id_, name, modality, json.dumps(req), json.dumps(opt), diff, json.dumps(muscles), pattern, json.dumps(tags))


steps = [
    step(_CREATE, "DROP TABLE exercise_catalog"),
    step(
        lambda conn: conn.executemany(
            """
            INSERT INTO exercise_catalog
                (id, name, modality, required_gear_json, optional_gear_json,
                 difficulty, primary_muscles_json, movement_pattern, tags_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [_row(e) for e in _EXERCISES],
        ),
    ),
]
