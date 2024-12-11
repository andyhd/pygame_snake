from __future__ import annotations

import random
from typing import Any
from typing import NamedTuple

import pygame
import pygame.locals as pg
from pygame import Vector2
from pygame.event import Event

from pygskin import imgui
from pygskin.imgui import label
from pygskin.assets import Assets
from pygskin.direction import Direction
from pygskin.game import run_game
from pygskin.lazy import LazyObject
from pygskin.spritesheet import Spritesheet

assets = Assets()

SPRITESHEET = Spritesheet(
    LazyObject(lambda: assets.snake),
    rows=4,
    columns=4,
    name_map={
        "APPLE": (2, 3),
        "HEAD UP": (0, 0),
        "HEAD DOWN": (1, 1),
        "HEAD LEFT": (0, 1),
        "HEAD RIGHT": (1, 0),
        "TAIL UP": (0, 2),
        "TAIL DOWN": (1, 3),
        "TAIL LEFT": (0, 3),
        "TAIL RIGHT": (1, 2),
        "UP LEFT": (3, 0),
        "UP RIGHT": (2, 0),
        "DOWN LEFT": (3, 1),
        "DOWN RIGHT": (2, 1),
        "LEFT UP": (2, 1),
        "LEFT DOWN": (2, 0),
        "RIGHT UP": (3, 1),
        "RIGHT DOWN": (3, 0),
        "UP UP": (2, 2),
        "DOWN DOWN": (2, 2),
        "LEFT LEFT": (3, 2),
        "RIGHT RIGHT": (3, 2),
    },
)

DIRECTION_KEYS = {
    pygame.K_UP: Direction.UP,
    pygame.K_DOWN: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT,
}

CELL_SIZE = 32

WIDTH, HEIGHT = 25, 18


class Segment(NamedTuple):
    pos: Vector2
    direction: Direction = Direction.RIGHT


class Snake:
    def __init__(self) -> None:
        self.next_direction = Direction.RIGHT
        self.segments: list[Segment] = []

    @property
    def head(self) -> Segment:
        return self.segments[0]

    def grow(self) -> None:
        if self.segments:
            d = self.next_direction
            self.segments[0] = Segment(self.head.pos, d)
            new_head = Segment(self.head.pos + d.vector, d)
        else:
            new_head = Segment(Vector2(-2, 0))
        self.segments.insert(0, new_head)

    def shrink(self) -> None:
        self.segments.pop()

    def respawn(self) -> None:
        self.next_direction = Direction.RIGHT
        self.segments.clear()
        for i in range(3):
            self.grow()

    @property
    def occupied(self) -> list[Vector2]:
        return [segment.pos for segment in self.segments]

    def turn(self, direction: Direction) -> None:
        if direction.axis != self.head.direction.axis:
            self.next_direction = direction

    def hit_self(self) -> bool:
        return any(segment.pos == self.head.pos for segment in self.segments[1:])

    def draw(self, surface: pygame.Surface) -> None:
        previous = "TAIL"
        for segment in reversed(self.segments[1:]):
            surface.blit(
                SPRITESHEET[f"{previous} {segment.direction.name}"],
                segment.pos * CELL_SIZE,
            )
            previous = segment.direction.name
        surface.blit(
            SPRITESHEET[f"HEAD {previous}"],
            self.head.pos * CELL_SIZE,
        )



UPDATE = pygame.event.custom_type()


def get_update_world_fn(state: dict):
    snake = Snake()
    food_pos = Vector2()
    all_cells = set((x, y) for y in range(HEIGHT) for x in range(WIDTH))

    def random_pos(occupied: list[Vector2]) -> Vector2:
        occupied_set = set((int(x), int(y)) for x, y in occupied)
        return random.choice(list(all_cells - occupied_set))

    def reset_game():
        snake.respawn()
        food_pos.update(Vector2(random_pos(occupied=snake.occupied)))
        state["paused"] = True
        state["game_over"] = False
        state["score"] = 0

    reset_game()

    def update_world(surface: pygame.Surface, events: list[Event]) -> None:
        for event in events:
            if event.type == pg.KEYDOWN:
                if state["game_over"]:
                    reset_game()
                    state["paused"] = False
                    pygame.time.set_timer(UPDATE, 140)
                    break

                if event.key == pg.K_p:
                    state["paused"] = not state["paused"]
                    if not state["paused"]:
                        pygame.time.set_timer(UPDATE, 140)
                    else:
                        pygame.time.set_timer(UPDATE, 0)

                if not state["paused"] and (direction := DIRECTION_KEYS.get(event.key)):
                    snake.turn(direction)

            if event.type == UPDATE:
                snake.grow()

                pos = snake.head.pos
                hit_self = snake.hit_self()
                out_of_bounds = not (0 <= pos.x < width and 0 <= pos.y < height)
                if hit_self or out_of_bounds:
                    assets.die_sound.play()
                    state["game_over"] = True
                    pygame.time.set_timer(UPDATE, 0)

                elif pos == food_pos:
                    state["score"] += 1
                    assets.eat_sound.play()
                    food_pos.update(random_pos(occupied=snake.occupied + [food_pos]))

                else:
                    snake.shrink()

        surface.blit(SPRITESHEET["APPLE"], food_pos * CELL_SIZE)
        snake.draw(surface)

    return update_world


def play_game(width: int, height: int):
    state: dict[str, Any] = {}
    update_world = get_update_world_fn(state)
    gui = imgui.IMGUI()

    def _play_game(surface: pygame.Surface, events: list[Event], _) -> None:
        surface.fill((0, 40, 0))

        update_world(surface, events)

        rect = surface.get_rect()
        with imgui.render(gui, surface) as render:
            if state["paused"]:
                render(label("PAUSED\n\nP - Pause / Unpause"), center=rect.center)
            elif state["game_over"]:
                render(label("GAME OVER"), center=rect.center)
            else:
                render(label(f"Score: {state['score']}"), bottomleft=rect.bottomleft)

    return _play_game


if __name__ == "__main__":
    width, height = 25, 18
    run_game(
        pygame.Window("Snake", (width * CELL_SIZE, height * CELL_SIZE)),
        play_game(width, height),
    )
