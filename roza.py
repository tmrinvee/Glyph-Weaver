from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import random


GRID_N = 8
CUBE_SIZE = 50
CELL_SPACING = 70
WINDOW_W, WINDOW_H = 1000, 800
COLORS = [
    (0.1, 0.1, 0.1),
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
    (1.0, 1.0, 0.0)
]
CURSOR_COLOR = (1.0, 1.0, 1.0)
MISTAKE_COLOR = (1.0, 0.0, 1.0)
TEXT_COLOR = (1.0, 1.0, 1.0)
GRID_LINE_COLOR = (0.4, 0.4, 0.4)


player_pattern = []
goal_pattern = []
cursor = [GRID_N // 2, GRID_N // 2]
current_color = 1
current_rot = 0
move_count = 0
score = 0
show_goal = False
mirror_mode = False
mistake_highlight = False
match_status = None
replay_actions = []
is_replaying = False
replay_index = 0
current_level = 0


level_difficulties = [
    {'name': 'Easy'},
    {'name': 'Mild'},
    {'name': 'Hard'}
]


fovY = 60
camera_pos = (0.0, GRID_N * CELL_SPACING * 0.9, -GRID_N * CELL_SPACING * 0.9)


def reset_player_state():
    global player_pattern, cursor, current_color, current_rot, match_status, move_count, score
    player_pattern = generate_empty_grid()
    cursor[:] = [GRID_N // 2, GRID_N // 2]
    current_color = 1
    current_rot = 0
    match_status = None
    move_count = 0
    score = 0


def generate_empty_grid():
    return [[{'color': 0, 'rot': 0} for _ in range(GRID_N)] for _ in range(GRID_N)]


def generate_easy_goal():
    new_goal = generate_empty_grid()
    num_cubes = random.randint(1, 2)
    attempts = cubes_placed = 0
    while cubes_placed < num_cubes and attempts < 20:
        r = random.randint(0, GRID_N - 1)
        c = random.randint(0, GRID_N - 1)
        attempts += 1
        if new_goal[r][c]['color'] == 0:
            new_goal[r][c] = {'color': random.randint(1, len(COLORS) - 1),
                              'rot': random.choice([0, 90, 180, 270])}
            cubes_placed += 1
    print(f"Generated Easy goal with {cubes_placed} cube(s).")
    return new_goal


def generate_mild_goal():
    new_goal = generate_empty_grid()
    num_cubes = random.randint(4, 8)
    attempts = cubes_placed = 0
    while cubes_placed < num_cubes and attempts < GRID_N * GRID_N:
        r = random.randint(0, GRID_N - 1)
        c = random.randint(0, GRID_N - 1)
        attempts += 1
        if new_goal[r][c]['color'] == 0:
            new_goal[r][c] = {'color': random.randint(1, len(COLORS) - 1),
                              'rot': random.choice([0, 90, 180, 270])}
            cubes_placed += 1
    print(f"Generated Mild goal with {cubes_placed} cube(s).")
    return new_goal


def generate_hard_goal():
    new_goal = generate_empty_grid()
    num_cubes = random.randint(10, 16)
    attempts = cubes_placed = 0
    while cubes_placed < num_cubes and attempts < GRID_N * GRID_N * 2:
        r = random.randint(0, GRID_N - 1)
        c = random.randint(0, GRID_N - 1)
        attempts += 1
        if new_goal[r][c]['color'] == 0:
            new_goal[r][c] = {'color': random.randint(1, len(COLORS) - 1),
                              'rot': random.choice([0, 90, 180, 270])}
            cubes_placed += 1
    print(f"Generated Hard goal with {cubes_placed} cube(s).")
    return new_goal


def load_level(idx):
    global current_level, goal_pattern, is_replaying, replay_actions, replay_index
    current_level = idx % len(level_difficulties)
    if current_level == 0:
        goal_pattern = generate_easy_goal()
    elif current_level == 1:
        goal_pattern = generate_mild_goal()
    else:
        goal_pattern = generate_hard_goal()
    reset_player_state()
    is_replaying = False
    replay_actions.clear()
    replay_index = 0
    print(f"Loaded Level {current_level + 1}: Difficulty {level_difficulties[current_level]['name']}")
    glutPostRedisplay()


def grid_to_world(r, c):
    offset = -(GRID_N - 1) * CELL_SPACING / 2.0
    x = offset + c * CELL_SPACING
    z = offset + r * CELL_SPACING
    return x, 0.0, z


def check_match():
    global score
    if not goal_pattern or not player_pattern:
        return False
    match = True
    current_score = total_goal_cubes = 0
    for r in range(GRID_N):
        for c in range(GRID_N):
            player_cell = player_pattern[r][c]
            goal_cell = goal_pattern[r][c]
            if goal_cell['color'] != 0:
                total_goal_cubes += 1
                if (player_cell['color'], player_cell['rot']) == (goal_cell['color'], goal_cell['rot']):
                    current_score += 1
                else:
                    match = False
            elif player_cell['color'] != 0:
                match = False
    score = current_score
    num_player_cubes = sum(1 for row in player_pattern for cell in row if cell['color'] != 0)
    if total_goal_cubes == 0 and num_player_cubes == 0:
        match = True
    elif total_goal_cubes != num_player_cubes:
        match = False
    return match


def apply_action(action):
    global cursor, current_color, current_rot
    typ, data = action
    if typ == 'move':
        dr, dc = data
        cursor[0] = max(0, min(GRID_N - 1, cursor[0] + dr))
        cursor[1] = max(0, min(GRID_N - 1, cursor[1] + dc))
    elif typ == 'color':
        current_color = data
    elif typ == 'rotate':
        current_rot = (current_rot + data) % 360
    elif typ == 'paint':
        r, c = cursor
        player_pattern[r][c] = {'color': current_color, 'rot': current_rot}
        if mirror_mode and c != GRID_N - 1 - c:
            player_pattern[r][GRID_N - 1 - c] = {'color': current_color, 'rot': current_rot}


def record_and_apply(action):
    global replay_actions, move_count, is_replaying
    if not is_replaying:
        recorded = action
        if action[0] == 'paint':
            recorded = ('paint', (current_color, current_rot))
            r, c = cursor
            if player_pattern[r][c]['color'] != current_color or player_pattern[r][c]['rot'] != current_rot:
                move_count += 1
        replay_actions.append(recorded)
        apply_action(recorded)
    else:
        print("In replay mode, actions ignored.")


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3fv(TEXT_COLOR)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    win_w = glutGet(GLUT_WINDOW_WIDTH)
    win_h = glutGet(GLUT_WINDOW_HEIGHT)
    if win_h > 0:
        gluOrtho2D(0, win_w, 0, win_h)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_grid_lines():
    glColor3fv(GRID_LINE_COLOR)
    glBegin(GL_LINES)
    half = (GRID_N - 1) * CELL_SPACING / 2.0
    low = -half - CELL_SPACING / 2.0
    high = half + CELL_SPACING / 2.0
    for i in range(GRID_N + 1):
        pos = low + i * CELL_SPACING
        glVertex3f(low, 0.0, pos)
        glVertex3f(high, 0.0, pos)
        glVertex3f(pos, 0.0, low)
        glVertex3f(pos, 0.0, high)
    glEnd()


def draw_cube_outline(x, y, z, color):
    glColor3fv(color)
    glPushMatrix()
    glTranslatef(x, y + 0.02, z)
    glScale(1.05, 1.05, 1.05)
    s = CUBE_SIZE / 2.0
    glBegin(GL_LINES)
    edges = [(-s,-s, s),( s,-s, s),( s,-s,-s),(-s,-s,-s),
             (-s, s, s),( s, s, s),( s, s,-s),(-s, s,-s)]
    wire = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    for a,b in wire:
        glVertex3f(*edges[a]); glVertex3f(*edges[b])
    glEnd()
    glPopMatrix()
    
def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Glyph Weaver")
    glClearColor(0.15, 0.15, 0.2, 1.0)
    load_level(0)
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMainLoop()

if __name__ == "__main__":
    main()