import pygame, sys, time, math, random, asyncio
from typing import Self, Union


class Island:
    def __init__(
            self,
            pos: tuple[float, float],
            color: pygame.Color = pygame.color.THECOLORS["gray"],
            radius: float = 4
    ) -> None:
        self.pos = pos
        self.color = color
        self.radius = radius
        self.bridges: list["Bridge"] = []

    def blit(self, screen: pygame.Surface) -> None:
        pygame.draw.circle(
            screen,
            self.color,
            self.pos,
            self.radius
        )

    def contains(self, pos, r_other=0) -> None:
        x1, y1 = self.pos
        x2, y2 = pos
        dist_x = x2 - x1
        dist_y = y2 - y1
        r = self.radius + r_other
        return dist_x * dist_x + dist_y * dist_y < r * r

    def add_bridge(self, bridge: "Bridge"):
        self.bridges.append(bridge)

    def remove_bridge(self, bridge: "Bridge", remove_other: bool = True):
        if remove_other:
            bridge.get_other(self).remove_bridge(bridge, False)
        self.bridges.remove(bridge)

    def bridge_to(self, island: Self) -> None:
        Bridge(self, island)

    def get_center_dist(self, island: Self) -> float:
        x1, y1 = self.pos
        x2, y2 = island.pos
        x = x2 - x1
        y = y2 - y1
        return math.sqrt(x*x + y*y)

    def is_connected(self) -> bool:
        return len(self.bridges) != 0

    def get_connected(self):
        return [b.get_other(self) for b in self.bridges]


class Bridge:
    def __init__(
            self,
            island_1: Island,
            island_2: Island
    ):
        self.island_1 = island_1
        self.island_2 = island_2

    def add_self(self):
        self.island_1.add_bridge(self)
        self.island_2.add_bridge(self)

    def get_other(self, island: Island) -> Union[Self, Island]:
        if island == self.island_2:
            return self.island_1
        elif island == self.island_1:
            return self.island_2
        else:
            return None
        # return self.island_1 if island == self.island_2 else self.island_2

    def cost(self) -> float:
        x1, y1 = self.island_1.pos
        x2, y2 = self.island_2.pos
        x = x2 - x1
        y = y2 - y1
        # no need to sqrt, doesn't change anything
        return x*x + y*y

    def unpack(self) -> tuple[Self, Island, Island]:
        return self, self.island_1, self.island_2

    @staticmethod
    def check_cost(i1: Island, i2: Island) -> float:
        b = Bridge(i1, i2)
        c = b.cost()
        i1.remove_bridge(b)
        return c


SCREEN_DIM: tuple[int, int] = (1920, 1080)
ISLANDS: list[Island] = []

START_REPEAT = 0.5
DELTA_CHANGE_START = 0.7
DELTA_CHANGE_DELTA = 0.05

repeat: dict[int, tuple[int, float]] = {
    pygame.K_RSHIFT: (100, 0.01),
    pygame.K_LSHIFT: (10, 0.1),
    pygame.K_SPACE: (1, 0.3)
}


def update_islands(islands: list[Island]) -> None:
    clear_bridges(islands)
    cost_algo(islands)


def clear_bridges(islands: list[Island]):
    for isl in islands:
        isl.bridges.clear()


def cost_algo(islands: list[Island]):
    bridges = []
    # list all bridges
    for i1, isl1 in enumerate(islands):
        for i2, isl2 in enumerate(islands):
            if i1 >= i2: # technically not needed
                continue
            bridges.append(Bridge(isl1, isl2))

    # sort them all
    bridges = sorted(bridges, key=lambda b_: b_.cost())

    # the exact number that is needed
    for i in range(len(islands) - 1):
        b, isl1, isl2 = bridges.pop(0).unpack()

        # check if this bridge is redundant
        # slowest part atm
        def check_connection_recur(
                check: list[Island],
                goal: Island,
                checked: Union[list[Island], None] = None
        ):
            if not checked:
                checked = []
            for isl in check:
                if isl in checked:
                    continue
                if isl == goal:
                    return True
                checked.append(isl)
                if check_connection_recur(isl.get_connected(), goal, checked):
                    return True

            return False

        # while it is redundant keep popping
        while check_connection_recur([isl1], isl2):
            b, isl1, isl2 = bridges.pop(0).unpack()

        # materialize the bridge
        b.add_self()


async def main() -> None:
    pygame.init()
    pygame.font.init()
    font = pygame.font.SysFont(None, 20)
    screen: pygame.Surface = pygame.display.set_mode(SCREEN_DIM)

    waiting_to_repeat = False
    waiting_to_repeat_timestamp = 0
    repeating = False
    last_repeating_timestamp = 0

    toggle_crazy = False
    last_crazy_timestamp = 0
    crazy_delta_in = -1
    crazy_delta = math.exp(crazy_delta_in)
    text_hidden = False

    count_text_raw_s = ""
    crazy_delta_text_raw_s = ""
    count_text = None
    crazy_delta_text = None

    waiting_to_repeat_delta = False
    repeat_delta_ts = 0
    wait_for_repeat_delta_ts = 0
    repeating_delta = False

    controls_text_raw = '''Click or press space to add an island
Click or press delete to remove an island
Press left shift to add/remove 10 islands
Press right shift to add/remove 100 islands
Press backtick to toggle repeated adding/removing
    '''
    controls_texts = []
    for text_raw in controls_text_raw.split("\n"):
        print(text_raw)
        controls_texts.append(font.render(
            text_raw,
            False,
            pygame.color.THECOLORS["white"]
        ))

    while True:
        t = time.time()
        keys = pygame.key.get_pressed()

        if waiting_to_repeat_delta and t - wait_for_repeat_delta_ts > DELTA_CHANGE_START:
            repeating_delta = True

        if repeating_delta and t - repeat_delta_ts > DELTA_CHANGE_DELTA:
            repeat_delta_ts = t
            if keys[pygame.K_LEFT]:
                crazy_delta_in -= 0.1
                crazy_delta = math.exp(crazy_delta_in)

            if keys[pygame.K_RIGHT]:
                crazy_delta_in += 0.1
                crazy_delta = math.exp(crazy_delta_in)

        if not keys[pygame.K_LEFT] and not keys[pygame.K_RIGHT]:
            repeating_delta = False
            waiting_to_repeat_delta = False

        # handle repeat timing
        if waiting_to_repeat and t - waiting_to_repeat_timestamp > START_REPEAT:
            repeating = True

        repeat_delta = repeat[pygame.K_SPACE][1]
        for key in repeat.keys():
            if keys[key]:
                repeat_delta = repeat[key][1]
                break

        if repeating and t - last_repeating_timestamp > repeat_delta:
            if keys[pygame.K_q]:
                remove_random(False)

            add_random()
            last_repeating_timestamp = t

        if toggle_crazy and t - last_crazy_timestamp > crazy_delta:
            remove_random(False)
            add_random()
            last_crazy_timestamp = t

        # handle event object
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    ISLANDS.clear()
                    update_islands(ISLANDS)

                elif event.key == pygame.K_SPACE:
                    waiting_to_repeat = True
                    waiting_to_repeat_timestamp = t

                    for key in repeat.keys():
                        if keys[key]:
                            [add_random(False) for i in range(repeat[key][0])]
                            break
                    else:
                        add_random()
                    update_islands(ISLANDS)

                elif event.key == pygame.K_BACKSPACE:
                    for key in repeat.keys():
                        if keys[key]:
                            [remove_random(False) for i in range(repeat[key][0])]
                            break
                    else:
                        remove_random()
                    update_islands(ISLANDS)

                elif event.key == pygame.K_BACKQUOTE:
                    toggle_crazy = not toggle_crazy

                elif event.key == pygame.K_h:
                    text_hidden = not text_hidden

                elif event.key == pygame.K_LEFT:
                    waiting_to_repeat_delta = True
                    wait_for_repeat_delta_ts = t
                    crazy_delta_in -= 0.1
                    crazy_delta = math.exp(crazy_delta_in)

                elif event.key == pygame.K_RIGHT:
                    waiting_to_repeat_delta = True
                    wait_for_repeat_delta_ts = t
                    crazy_delta_in += 0.1
                    crazy_delta = math.exp(crazy_delta_in)

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    waiting_to_repeat = False
                    repeating = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_click(event)

            elif event.type == pygame.QUIT:
                exit_program()

        # ----- RENDER -----

        screen.fill(pygame.color.THECOLORS["black"])

        for island in ISLANDS:
            for bridge in island.bridges:
                i2: Island = bridge.get_other(island)
                pygame.draw.line(
                    screen,
                    pygame.color.THECOLORS["red"],
                    island.pos, i2.pos, 3
                )

        for island in ISLANDS:
            island.blit(screen)

        count_text_raw = f"Island Count : {len(ISLANDS)} - (h to toggle hide)"
        crazy_delta_text_raw = f"Delay: {crazy_delta:3f} - (left/right arrows to change speed)"

        if count_text_raw_s != count_text_raw:
            count_text = font.render(
                count_text_raw,
                False,
                (255, 255, 255)
            )
            count_text_raw_s = count_text_raw

        if crazy_delta_text_raw_s != crazy_delta_text_raw:
            crazy_delta_text = font.render(
                crazy_delta_text_raw,
                False,
                (255, 255, 255)
            )
            crazy_delta_text_raw_s = crazy_delta_text_raw

        if not text_hidden:
            screen.blit(count_text, (0, 0))
            for i, controls_text in enumerate(controls_texts):
                screen.blit(
                    controls_text,
                    (
                        SCREEN_DIM[0] - controls_text.get_bounding_rect().width - 10,
                        i * 15
                    )
                )
            if toggle_crazy:
                screen.blit(crazy_delta_text, (0, 30))


        pygame.display.flip()
        await asyncio.sleep(0)


def add_random(update=True):
    pos = (
        random.randint(0, SCREEN_DIM[0]),
        random.randint(0, SCREEN_DIM[1])
    )
    for isl in ISLANDS:
        if isl.contains(pos, int(isl.radius)):
            add_random()
            return

    ISLANDS.append(Island(pos))
    if update:
        update_islands(ISLANDS)


def remove_random(update=True):
    if len(ISLANDS) == 0: return
    del ISLANDS[random.randint(0, len(ISLANDS) - 1)]

    if update:
        update_islands(ISLANDS)


def mouse_click(event: pygame.event.Event) -> None:
    for isl in ISLANDS:
        if isl.contains(event.pos):
            ISLANDS.remove(isl)
            update_islands(ISLANDS)
            return
        elif isl.contains(event.pos, isl.radius):
            return # if we add an overlapping island
            # instead of removing the island we didn't
            # click just do nothing
    ISLANDS.append(Island(event.pos))
    update_islands(ISLANDS)
    return


def exit_program() -> None:
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    asyncio.run(main())
