#!/usr/bin/env python3
"""
Classic Snake Game for macOS Terminal
Written in Python using standard `curses` library.
"""

import curses
import json
import os
import random
import time
from datetime import datetime

HIGH_SCORES_FILE = "high_scores.json"
GRID_WIDTH = 40
GRID_HEIGHT = 40

# Emoji icons (Note: emojis take 2 column widths in terminal)
SNAKE_HEAD = "🐍"
SNAKE_BODY = "🟩"
FOOD_ICON = "🍎"
OBSTACLE_ICON = "🪨"
EMPTY_ICON = "  "

DIFFICULTIES = {
    "1": {"name": "Easy", "speed": 0.15, "obstacle_rate": 0.05, "dynamic": False},
    "2": {"name": "Medium", "speed": 0.10, "obstacle_rate": 0.10, "dynamic": False},
    "3": {"name": "Hardcore", "speed": 0.05, "obstacle_rate": 0.20, "dynamic": False},
    "4": {"name": "Dynamic", "speed": 0.12, "obstacle_rate": 0.10, "dynamic": True},
}


def load_high_scores():
    if not os.path.exists(HIGH_SCORES_FILE):
        return []
    try:
        with open(HIGH_SCORES_FILE, "r", encoding="utf-8") as f:
            scores = json.load(f)
            return sorted(scores, key=lambda x: x.get("score", 0), reverse=True)[:10]
    except Exception:
        return []


def save_high_score(name, score, difficulty):
    scores = load_high_scores()
    new_entry = {
        "name": name if name.strip() else "Anonymous",
        "score": score,
        "difficulty": difficulty,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    scores.append(new_entry)
    scores = sorted(scores, key=lambda x: x.get("score", 0), reverse=True)[:10]
    try:
        with open(HIGH_SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def safe_addstr(stdscr, y, x, text, attr=curses.A_NORMAL):
    """Safely write string to curses window without throwing error if out of bounds."""
    max_y, max_x = stdscr.getmaxyx()
    if 0 <= y < max_y and 0 <= x < max_x:
        try:
            # Truncate text if it exceeds screen width
            available = max_x - x
            if len(text) > available:
                text = text[:available]
            stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass


def draw_box(stdscr, top, left, height, width, title=""):
    """Draw a border box around an area safely."""
    max_y, max_x = stdscr.getmaxyx()
    if top < 0 or left < 0 or top + height > max_y or left + width > max_x:
        return

    attr = curses.color_pair(1) if curses.has_colors() else curses.A_NORMAL

    safe_addstr(stdscr, top, left, "┌" + "─" * (width - 2) + "┐", attr)
    for y in range(1, height - 1):
        safe_addstr(stdscr, top + y, left, "│", attr)
        safe_addstr(stdscr, top + y, left + width - 1, "│", attr)
    safe_addstr(stdscr, top + height - 1, left, "└" + "─" * (width - 2) + "┘", attr)

    if title:
        title_x = left + max(2, (width - len(title)) // 2)
        safe_addstr(stdscr, top, title_x, f" {title} ", attr)


def prompt_string(stdscr, y, x, prompt):
    """Prompt the user for text input in curses reliably without echoing issues."""
    curses.noecho()  # We handle string drawing manually
    curses.curs_set(1)

    buf = []
    while True:
        safe_addstr(stdscr, y, x, prompt + "".join(buf) + " ")
        stdscr.move(y, x + len(prompt) + len(buf))
        stdscr.refresh()

        ch = stdscr.getch()
        if ch in (10, 13):  # Enter key
            break
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            if buf:
                buf.pop()
        elif 32 <= ch <= 126 and len(buf) < 15:
            buf.append(chr(ch))

    curses.curs_set(0)
    return "".join(buf).strip()


def check_min_dimensions(stdscr, min_w=84, min_h=44):
    """Checks if terminal size is sufficient, prompts user to resize if needed."""
    while True:
        h, w = stdscr.getmaxyx()
        if h >= min_h and w >= min_w:
            break
        stdscr.clear()
        safe_addstr(stdscr, 1, 1, f"Окно слишком мало! Размер сейчас: {w}x{h}. Требуется: {min_w}x{min_h}.")
        safe_addstr(stdscr, 3, 1, "Разверните окно терминала и нажмите любую клавишу...")
        stdscr.refresh()
        stdscr.getch()


def show_menu(stdscr, player_name):
    """Main menu screen to select difficulty or view leaderboard."""
    stdscr.nodelay(False)
    while True:
        check_min_dimensions(stdscr, min_w=84, min_h=30)
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        title = "🐍 T E R M I N A L   S N A K E 🐍"
        safe_addstr(stdscr, 1, max(0, (w - len(title)) // 2), title, curses.A_BOLD | curses.color_pair(2))

        greeting = f"Игрок: {player_name}"
        safe_addstr(stdscr, 3, max(0, (w - len(greeting)) // 2), greeting, curses.color_pair(3))

        options = [
            "1. Легкий (Easy)",
            "2. Средний (Medium)",
            "3. Хардкор (Hardcore)",
            "4. Динамический (Dynamic)",
            "5. Изменить имя игрока",
            "Q. Выход"
        ]

        safe_addstr(stdscr, 5, max(0, (w - 20) // 2), "Выберите сложность:", curses.A_UNDERLINE)
        for idx, opt in enumerate(options):
            safe_addstr(stdscr, 7 + idx, max(0, (w - len(opt)) // 2), opt)

        # Draw Leaderboard below menu
        scores = load_high_scores()
        lb_top = 14
        safe_addstr(stdscr, lb_top, max(0, (w - 25) // 2), "🏆 ТОП-10 РЕКОРДОВ 🏆", curses.A_BOLD | curses.color_pair(2))
        safe_addstr(stdscr, lb_top + 1, max(0, (w - 40) // 2), "─" * 40)

        if not scores:
            safe_addstr(stdscr, lb_top + 2, max(0, (w - 18) // 2), "Рекордов пока нет!")
        else:
            for idx, entry in enumerate(scores[:8]):  # Show top 8 in menu
                line = f"{idx+1:2d}. {entry['name']:<12} | {entry['score']:4d} pts | {entry['difficulty']}"
                safe_addstr(stdscr, lb_top + 2 + idx, max(0, (w - len(line)) // 2), line)

        stdscr.refresh()

        ch = stdscr.getch()
        if ch in (ord('q'), ord('Q')):
            return None, player_name
        elif ch in (ord('1'), ord('2'), ord('3'), ord('4')):
            diff_key = chr(ch)
            return DIFFICULTIES[diff_key], player_name
        elif ch in (ord('5'), ord('c'), ord('C')):
            new_name = prompt_string(stdscr, lb_top + 11, max(0, (w - 30) // 2), "Новое имя: ")
            if new_name:
                player_name = new_name


def spawn_item(snake, obstacles, current_food=None):
    """Spawns an item (food or obstacle) in an empty grid cell."""
    while True:
        pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
        if pos not in snake and pos not in obstacles and pos != current_food:
            return pos


def run_game(stdscr, difficulty_info, player_name):
    """Main game loop for Snake."""
    check_min_dimensions(stdscr, min_w=84, min_h=44)
    stdscr.clear()
    stdscr.nodelay(True)  # Non-blocking getch

    # Grid width is 40 cells * 2 chars/cell = 80 chars wide
    grid_cols = GRID_WIDTH * 2
    grid_rows = GRID_HEIGHT

    max_y, max_x = stdscr.getmaxyx()

    offset_y = max(1, (max_y - (grid_rows + 2)) // 2)
    offset_x = max(1, (max_x - (grid_cols + 2)) // 2)

    # Initial Snake state
    start_x = GRID_WIDTH // 2
    start_y = GRID_HEIGHT // 2
    snake = [(start_x, start_y), (start_x - 1, start_y), (start_x - 2, start_y)]
    direction = (1, 0)  # Moving right initially
    next_direction = direction

    score = 0
    obstacles = []
    food = spawn_item(snake, obstacles)

    base_speed = difficulty_info["speed"]
    is_dynamic = difficulty_info["dynamic"]
    obstacle_rate = difficulty_info["obstacle_rate"]
    diff_name = difficulty_info["name"]

    paused = False

    while True:
        # Key handling
        ch = stdscr.getch()
        if ch != -1:
            if ch in (ord('q'), ord('Q')):
                return "menu"
            elif ch in (ord('p'), ord('P'), ord(' ')):
                paused = not paused
            elif not paused:
                # Directions: UP, DOWN, LEFT, RIGHT
                if ch in (curses.KEY_UP, ord('w'), ord('W')) and direction != (0, 1):
                    next_direction = (0, -1)
                elif ch in (curses.KEY_DOWN, ord('s'), ord('S')) and direction != (0, -1):
                    next_direction = (0, 1)
                elif ch in (curses.KEY_LEFT, ord('a'), ord('A')) and direction != (1, 0):
                    next_direction = (-1, 0)
                elif ch in (curses.KEY_RIGHT, ord('d'), ord('D')) and direction != (-1, 0):
                    next_direction = (1, 0)

        # Draw Header info
        header = f" Игрок: {player_name} | Счет: {score} | Сложность: {diff_name} | P:Пауза Q:Выход "
        safe_addstr(stdscr, offset_y - 1, offset_x, header[:grid_cols + 2], curses.A_BOLD)

        # Draw Frame
        draw_box(stdscr, offset_y, offset_x, grid_rows + 2, grid_cols + 2, " С З М Е Й К А ")

        if paused:
            pause_str = " PAUSED (Нажмите P/Пробел для продолжения) "
            safe_addstr(stdscr, offset_y + grid_rows // 2, offset_x + max(1, (grid_cols - len(pause_str)) // 2), pause_str, curses.A_REVERSE | curses.A_BOLD)
            stdscr.refresh()
            time.sleep(0.1)
            continue

        direction = next_direction

        # Calculate new head position with pass-through (wrap around) walls
        new_head = (
            (snake[0][0] + direction[0]) % GRID_WIDTH,
            (snake[0][1] + direction[1]) % GRID_HEIGHT
        )

        # Check collision with self
        if new_head in snake:
            save_high_score(player_name, score, diff_name)
            return game_over_screen(stdscr, player_name, score, diff_name, "Столкновение со своим хвостом!")

        # Check collision with obstacle
        if new_head in obstacles:
            save_high_score(player_name, score, diff_name)
            return game_over_screen(stdscr, player_name, score, diff_name, "Столкновение с препятствием!")

        # Move Snake
        snake.insert(0, new_head)

        # Check if food eaten
        if new_head == food:
            score += 10
            food = spawn_item(snake, obstacles)

            # Chance to spawn a new obstacle when food is eaten
            if random.random() < obstacle_rate and len(obstacles) < 25:
                new_obs = spawn_item(snake, obstacles, current_food=food)
                next_next_head = ((new_head[0] + direction[0]) % GRID_WIDTH, (new_head[1] + direction[1]) % GRID_HEIGHT)
                if new_obs != next_next_head:
                    obstacles.append(new_obs)
        else:
            # Remove tail
            snake.pop()

        # Render Grid Contents
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                scr_y = offset_y + 1 + r
                scr_x = offset_x + 1 + (c * 2)
                pos = (c, r)

                if pos == snake[0]:
                    safe_addstr(stdscr, scr_y, scr_x, SNAKE_HEAD)
                elif pos in snake:
                    safe_addstr(stdscr, scr_y, scr_x, SNAKE_BODY)
                elif pos == food:
                    safe_addstr(stdscr, scr_y, scr_x, FOOD_ICON)
                elif pos in obstacles:
                    safe_addstr(stdscr, scr_y, scr_x, OBSTACLE_ICON)
                else:
                    safe_addstr(stdscr, scr_y, scr_x, EMPTY_ICON)

        stdscr.refresh()

        # Calculate current sleep speed
        current_speed = base_speed
        if is_dynamic:
            speed_reduction = (score // 30) * 0.01
            current_speed = max(0.04, base_speed - speed_reduction)

        time.sleep(current_speed)


def game_over_screen(stdscr, player_name, score, difficulty, reason):
    """Display Game Over screen with top scores and restart option."""
    stdscr.nodelay(False)
    check_min_dimensions(stdscr, min_w=84, min_h=28)
    stdscr.clear()

    h, w = stdscr.getmaxyx()

    title = "💥 G A M E   O V E R 💥"
    safe_addstr(stdscr, 1, max(0, (w - len(title)) // 2), title, curses.A_BOLD | curses.color_pair(2))

    reason_str = f"Причина: {reason}"
    safe_addstr(stdscr, 3, max(0, (w - len(reason_str)) // 2), reason_str)

    score_str = f"Игрок: {player_name}   |   Итоговый счет: {score} pts"
    safe_addstr(stdscr, 4, max(0, (w - len(score_str)) // 2), score_str, curses.A_BOLD | curses.color_pair(3))

    # Display Leaderboard
    scores = load_high_scores()
    lb_top = 6
    safe_addstr(stdscr, lb_top, max(0, (w - 25) // 2), "🏆 ТОП-10 РЕКОРДОВ 🏆", curses.A_BOLD | curses.color_pair(2))
    safe_addstr(stdscr, lb_top + 1, max(0, (w - 40) // 2), "─" * 40)

    for idx, entry in enumerate(scores[:8]):
        is_current = (entry["name"] == player_name and entry["score"] == score)
        attr = curses.A_BOLD | curses.color_pair(2) if is_current else curses.A_NORMAL
        line = f"{idx+1:2d}. {entry['name']:<12} | {entry['score']:4d} pts | {entry['difficulty']}"
        safe_addstr(stdscr, lb_top + 2 + idx, max(0, (w - len(line)) // 2), line, attr)

    prompt1 = "[ R / ENTER ] - Играть снова"
    prompt2 = "[ M ] - В главное меню"
    prompt3 = "[ Q ] - Выйти из игры"

    bottom_y = lb_top + 11
    safe_addstr(stdscr, bottom_y, max(0, (w - len(prompt1)) // 2), prompt1, curses.A_BOLD)
    safe_addstr(stdscr, bottom_y + 1, max(0, (w - len(prompt2)) // 2), prompt2)
    safe_addstr(stdscr, bottom_y + 2, max(0, (w - len(prompt3)) // 2), prompt3)

    stdscr.refresh()

    while True:
        ch = stdscr.getch()
        if ch in (ord('r'), ord('R'), 10, 13):  # R or Enter -> Restart same difficulty
            return "restart"
        elif ch in (ord('m'), ord('M')):
            return "menu"
        elif ch in (ord('q'), ord('Q')):
            return "quit"


def main(stdscr):
    # Initialize curses colors
    curses.curs_set(0)  # Hide cursor
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_GREEN, -1)

    check_min_dimensions(stdscr, min_w=84, min_h=20)
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    # Initial player name prompt
    title = "🐍 З М Е Й К А 🐍"
    safe_addstr(stdscr, 2, max(0, (w - len(title)) // 2), title, curses.A_BOLD | curses.color_pair(2))

    player_name = prompt_string(stdscr, 5, max(0, (w - 30) // 2), "Введите ваше имя: ")
    if not player_name:
        player_name = "Игрок 1"

    while True:
        diff_info, player_name = show_menu(stdscr, player_name)
        if not diff_info:
            break  # Quit selected

        action = "restart"
        while action == "restart":
            action = run_game(stdscr, diff_info, player_name)

        if action == "quit":
            break


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
