import random
from collections.abc import Callable
from itertools import pairwise
from typing import NamedTuple

import pygame.locals as pg
from pygame import Event, Surface, Vector2, Window

from pygskin import (
    Assets,
    Direction,
    Timer,
    imgui,
    run_game,
    spritesheet,
)

assets = Assets()
spritesheet_data = assets.spritesheet
sprites = spritesheet(assets[spritesheet_data.pop("image")], **assets.spritesheet)
CONTROLS = {
    pg.K_UP: Direction.UP,
    pg.K_DOWN: Direction.DOWN,
    pg.K_LEFT: Direction.LEFT,
    pg.K_RIGHT: Direction.RIGHT,
}
CELL_SIZE = 32
WIDTH, HEIGHT = 25, 18


class Segment(NamedTuple):
    pos: Vector2
    direction: Direction = Direction.RIGHT


def main() -> Callable:
    cells = set(zip(range(WIDTH), range(HEIGHT)))
    snake: list[Segment] = []
    food = Vector2(random.choice(list(cells)))
    state = dict(game_over=False, score=0, next_direction=Direction.RIGHT)
    gui = imgui.IMGUI()
    timer = Timer(140, paused=True)

    def main_loop(surface: Surface, events: list[Event], _) -> None:
        if not snake:
            snake[:] = [Segment(Vector2(-i, 0), Direction.RIGHT) for i in range(3)]

        timer.tick()
        if timer.finished:
            timer.elapsed = 0

            # grow snake forwards
            direction = state["next_direction"]
            head = Segment(snake[0].pos + direction.vector, direction)
            snake.insert(0, head)

            snake_hit_self = any(segment.pos == head.pos for segment in snake[1:])
            out_of_bounds = not (0 <= head.pos.x < WIDTH and 0 <= head.pos.y < HEIGHT)
            if snake_hit_self or out_of_bounds:
                state["game_over"] = True
                timer.paused = True
                assets.die_sound.play()

            elif head.pos == food:
                # hit food
                state["score"] += 1
                assets.eat_sound.play()
                food.update(random.choice(list(cells - {tuple(_.pos) for _ in snake})))

            else:
                snake.pop()

        surface.fill((0, 40, 0))

        surface.blit(sprites("food"), food * CELL_SIZE)

        # draw snake
        *body, tail = snake
        surface.fblits(
            (sprites(f"{p}{c}"), pos * CELL_SIZE)
            for (_, p), (pos, c) in pairwise([(None, "H"), *body, (tail.pos, "T")])
        )

        rect = surface.get_rect()
        with imgui.render(gui, surface) as render:
            if state["game_over"]:
                render(imgui.label("GAME OVER"), center=rect.center)
            elif timer.paused:
                render(imgui.label("PAUSED\n\nP - Pause / Unpause"), center=rect.center)
            else:
                render(
                    imgui.label(f"Score: {state['score']}"),
                    bottomleft=rect.move(10, -10).bottomleft,
                    align="left",
                )

        for event in (ev for ev in events if ev.type == pg.KEYDOWN):
            if not timer.paused and (direction := CONTROLS.get(event.key)):
                if direction.axis != snake[0].direction.axis:
                    state["next_direction"] = direction

            if state["game_over"]:
                state.update(game_over=False, score=0, next_direction=Direction.RIGHT)
                snake.clear()
                timer.paused = False

            if event.key == pg.K_p:
                timer.paused = not timer.paused

    return main_loop


if __name__ == "__main__":
    run_game(Window("Snake", (WIDTH * CELL_SIZE, HEIGHT * CELL_SIZE)), main())
