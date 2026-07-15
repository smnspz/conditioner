CREATE TABLE equipment (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

INSERT INTO equipment (id, name) VALUES
    ('none', 'No equipment (bodyweight only)'),
    ('dumbbells', 'Dumbbells'),
    ('barbell', 'Barbell'),
    ('kettlebell', 'Kettlebell'),
    ('resistance_bands', 'Resistance/Elastic Bands'),
    ('pull_up_bar', 'Pull-Up Bar'),
    ('bench', 'Bench'),
    ('medicine_ball', 'Medicine Ball'),
    ('jump_rope', 'Jump Rope'),
    ('foam_roller', 'Foam Roller'),
    ('yoga_mat', 'Yoga Mat'),
    ('plyo_box', 'Plyo Box'),
    ('battle_ropes', 'Battle Ropes'),
    ('suspension_trainer', 'Suspension Trainer (TRX)');
