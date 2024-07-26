from __future__ import annotations

import random
from dataclasses import dataclass

import pygame
import pygame.locals as pg

from pygskin.assets import Assets
from pygskin.direction import Direction
from pygskin.game import GameLoop
from pygskin.lazy import LazyObject
from pygskin.pubsub import message
from pygskin.spritesheet import Spritesheet
from pygskin.text import Text
from pygskin.window import Window

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


def translate_to_screen(pos: pygame.Vector2) -> pygame.Vector2:
    return pygame.Vector2(pos) * 32


class Food:
    def __init__(self) -> None:
        self.pos = pygame.Vector2()

    @property
    def image(self) -> pygame.Surface:
        return SPRITESHEET["APPLE"]

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.image, translate_to_screen(self.pos))


@dataclass
class Segment:
    pos: pygame.Vector2
    direction: Direction

    def project(self) -> Segment:
        return Segment(self.pos + self.direction.vector, self.direction)


class Snake:
    def __init__(self, pos: pygame.Vector2 | None = None) -> None:
        self.die = message()
        self.eat = message()
        self.reset(pos)

    def reset(self, pos: pygame.Vector2 | None = None) -> None:
        pos = pos or pygame.Vector2()
        self.next_direction = direction = Direction.RIGHT
        self.segments = [
            Segment(pos - direction.vector * i, direction) for i in range(3)
        ]

    @property
    def head(self) -> Segment:
        return self.segments[0]

    @property
    def occupied(self) -> set[tuple[float, float]]:
        return set((segment.pos.x, segment.pos.y) for segment in self.segments)

    def grow(self) -> None:
        self.head.direction = self.next_direction
        self.segments.insert(0, self.head.project())

    def shrink(self) -> None:
        self.segments.pop()

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
                translate_to_screen(segment.pos),
            )
            previous = segment.direction.name
        surface.blit(
            SPRITESHEET[f"HEAD {previous}"],
            translate_to_screen(self.head.pos),
        )


class World:
    def __init__(self) -> None:
        self.size = 25, 18
        self.rect = pygame.Rect((0, 0), self.size)
        width, height = map(range, self.size)
        self._cells = {(float(x), float(y)) for y in height for x in width}

    def __contains__(self, pos: pygame.Vector2) -> bool:
        return self.rect.collidepoint(pos)

    def random_pos(self, occupied: set[tuple[float, float]]) -> pygame.Vector2:
        return pygame.Vector2(random.choice(list(self._cells - occupied)))


class Score:
    def __init__(self) -> None:
        self.value = 0
        self.rect = self.image.get_rect()

    @property
    def image(self) -> pygame.Surface:
        return Text(
            f"Score: {self.value}",
            background=(0, 0, 0, 127),
            padding=[20],
        ).image

    def set(self, value: int) -> None:
        self.value = value
        if hasattr(self, "_image"):
            del self._image

    def increment(self) -> None:
        self.set(self.value + 1)


UPDATE = pygame.event.custom_type()


class Game(GameLoop):
    def setup(self) -> None:
        self.world = world = World()

        Window.size = translate_to_screen(pygame.Vector2(world.size))
        Window.title = "Snake"
        _ = Window.surface

        self.food = Food()
        self.snake = snake = Snake()

        self.paused = True
        self.game_over = True

        self.score = score = Score()
        score.rect.bottom = Window.rect.bottom

        snake.eat.subscribe(score.increment)
        snake.eat.subscribe(assets.eat_sound.play)
        snake.die.subscribe(assets.die_sound.play)
        snake.die.subscribe(lambda: setattr(self, "game_over", True))

        self.reset()

        self.pause_label = Text(
            ("PAUSED\n\nP - Pause / Unpause"),
            background=(0, 0, 255, 128),
            padding=[20],
        )
        self.pause_label.rect.center = Window.rect.center

        self.game_over_label = Text(
            "GAME OVER",
            background=(0, 0, 255, 128),
            padding=[20],
        )
        self.game_over_label.rect.center = Window.rect.center

        pygame.time.set_timer(UPDATE, 140)

    def reset(self) -> None:
        self.score.set(0)
        self.snake.reset()
        self.food.pos = self.world.random_pos(occupied=self.snake.occupied)
        self.paused = True
        self.game_over = False

    def update(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pg.KEYDOWN:
                if self.game_over:
                    return self.reset()

                if event.key == pg.K_p:
                    self.paused = not self.paused

                if not self.paused and (direction := DIRECTION_KEYS.get(event.key)):
                    self.snake.turn(direction)

            if event.type == pg.QUIT:
                self.running = False
                break

            if event.type == UPDATE:
                self.move_snake()

    def move_snake(self) -> None:
        if self.paused or self.game_over:
            return

        snake, world, food = self.snake, self.world, self.food

        snake.grow()

        if snake.hit_self() or snake.head.pos not in world:
            snake.die()

        elif snake.head.pos == food.pos:
            snake.eat()
            food.pos = world.random_pos(occupied=snake.occupied | {tuple(food.pos)})

        else:
            snake.shrink()

    def draw(self) -> None:
        screen = Window.surface
        screen.fill((0, 40, 0))
        self.food.draw(screen)
        self.snake.draw(screen)
        screen.blit(self.score.image, self.score.rect)

        if self.game_over:
            screen.blit(self.game_over_label.image, self.game_over_label.rect)

        elif self.paused:
            screen.blit(self.pause_label.image, self.pause_label.rect)

        pygame.display.flip()


if __name__ == "__main__":
    Game().start()
