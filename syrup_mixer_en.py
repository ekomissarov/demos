import math
import sys
from dataclasses import dataclass

import pygame


WIDTH, HEIGHT = 1400, 900
FPS = 60

BG = (239, 235, 224)
PANEL = (250, 248, 241)
INK = (40, 43, 46)
MUTED = (104, 108, 112)
OUTLINE = (70, 73, 76)
METAL_LIGHT = (214, 218, 220)
PIPE = (105, 111, 114)
WATER = (74, 155, 214)
SYRUP = (221, 117, 49)
GREEN = (61, 150, 105)
WHITE = (255, 255, 255)
SHADOW = (205, 200, 190)


def clamp(value, low, high):
    return max(low, min(high, value))


def lerp_color(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_text(surface, font, text, pos, color=INK, anchor="topleft"):
    image = font.render(text, True, color)
    rect = image.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(image, rect)
    return rect


@dataclass
class Slider:
    rect: pygame.Rect
    value: float
    label: str
    dragging: bool = False

    def handle_rect(self):
        x = self.rect.left + int(self.value * self.rect.width)
        return pygame.Rect(x - 12, self.rect.centery - 18, 24, 36)

    def set_from_mouse(self, mouse_x):
        self.value = clamp((mouse_x - self.rect.left) / self.rect.width, 0.0, 1.0)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit_area = self.rect.inflate(34, 42)
            if hit_area.collidepoint(event.pos):
                self.dragging = True
                self.set_from_mouse(event.pos[0])
                return True

        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_from_mouse(event.pos[0])
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        return False

    def draw(self, surface, font_small, font_value):
        draw_text(
            surface,
            font_small,
            self.label,
            (self.rect.left, self.rect.top - 33),
            MUTED,
        )

        pygame.draw.rect(surface, (222, 219, 210), self.rect, border_radius=7)

        fill = self.rect.copy()
        fill.width = int(self.rect.width * self.value)
        if fill.width > 0:
            pygame.draw.rect(
                surface,
                lerp_color(WATER, SYRUP, self.value),
                fill,
                border_radius=7,
            )

        handle = self.handle_rect()
        pygame.draw.rect(surface, SHADOW, handle.move(2, 3), border_radius=8)
        pygame.draw.rect(surface, WHITE, handle, border_radius=8)
        pygame.draw.rect(surface, OUTLINE, handle, width=2, border_radius=8)

        draw_text(
            surface,
            font_value,
            f"{round(self.value * 100)}%",
            (self.rect.right + 18, self.rect.centery),
            INK,
            "midleft",
        )


@dataclass
class Valve:
    center: tuple[int, int]
    radius: int
    value: float
    label: str
    dragging: bool = False
    drag_start_x: int = 0
    drag_start_value: float = 0.0

    def hit_rect(self):
        x, y = self.center
        margin = 22
        return pygame.Rect(
            x - self.radius - margin,
            y - self.radius - margin,
            2 * (self.radius + margin),
            2 * (self.radius + margin),
        )

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hit_rect().collidepoint(event.pos):
                self.dragging = True
                self.drag_start_x = event.pos[0]
                self.drag_start_value = self.value
                return True

        if event.type == pygame.MOUSEMOTION and self.dragging:
            dx = event.pos[0] - self.drag_start_x
            self.value = clamp(self.drag_start_value + dx / 180.0, 0.0, 1.0)
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        return False

    def draw(self, surface, font_small, font_value):
        x, y = self.center

        draw_text(
            surface,
            font_value,
            self.label,
            (x, y - self.radius - 44),
            INK,
            "midtop",
        )

        pygame.draw.circle(surface, SHADOW, (x + 3, y + 4), self.radius + 4)
        pygame.draw.circle(surface, METAL_LIGHT, (x, y), self.radius + 4)
        pygame.draw.circle(surface, OUTLINE, (x, y), self.radius + 4, 2)

        start_angle = math.radians(135)
        end_angle = math.radians(405)

        for i in range(21):
            t = i / 20
            angle = start_angle + (end_angle - start_angle) * t
            inner = self.radius - 4
            outer = self.radius + (5 if i % 5 == 0 else 2)
            p1 = (x + math.cos(angle) * inner, y + math.sin(angle) * inner)
            p2 = (x + math.cos(angle) * outer, y + math.sin(angle) * outer)
            pygame.draw.line(surface, MUTED, p1, p2, 2)

        pointer_angle = start_angle + (end_angle - start_angle) * self.value
        pointer_end = (
            x + math.cos(pointer_angle) * (self.radius - 12),
            y + math.sin(pointer_angle) * (self.radius - 12),
        )
        pygame.draw.line(surface, INK, (x, y), pointer_end, 7)
        pygame.draw.circle(surface, INK, (x, y), 8)

        draw_text(
            surface,
            font_value,
            f"{round(self.value * 10, 1):.1f}",
            (x, y + self.radius + 18),
            INK,
            "midtop",
        )
        draw_text(
            surface,
            font_small,
            "Flow rate (units)",
            (x, y + self.radius + 51),
            MUTED,
            "midtop",
        )
        draw_text(
            surface,
            font_small,
            "Drag left or right",
            (x, y + self.radius + 76),
            MUTED,
            "midtop",
        )


def draw_tank(surface, rect, concentration, title, font_title, font_small):
    pygame.draw.rect(surface, SHADOW, rect.move(4, 5), border_radius=22)
    pygame.draw.rect(surface, PANEL, rect, border_radius=22)
    pygame.draw.rect(surface, OUTLINE, rect, width=3, border_radius=22)

    liquid_rect = pygame.Rect(
        rect.left + 14,
        rect.top + 58,
        rect.width - 28,
        rect.height - 72,
    )
    liquid_color = lerp_color(WATER, SYRUP, concentration)
    pygame.draw.rect(surface, liquid_color, liquid_rect, border_radius=13)

    for i in range(3):
        yy = liquid_rect.top + 24 + i * 38
        pygame.draw.arc(
            surface,
            lerp_color(liquid_color, WHITE, 0.25),
            pygame.Rect(liquid_rect.left + 18, yy, liquid_rect.width - 36, 18),
            math.pi,
            math.tau,
            2,
        )

    draw_text(
        surface,
        font_title,
        title,
        (rect.centerx, rect.top + 16),
        INK,
        "midtop",
    )
    draw_text(
        surface,
        font_small,
        f"Syrup: {round(concentration * 100)}%",
        (rect.centerx, rect.bottom - 30),
        WHITE if concentration > 0.42 else INK,
        "midbottom",
    )


def draw_pipe(surface, points, width=18):
    if len(points) < 2:
        return
    pygame.draw.lines(surface, OUTLINE, False, points, width + 6)
    pygame.draw.lines(surface, PIPE, False, points, width)


def draw_stream(surface, x, y1, y2, flow, concentration, phase):
    if flow <= 0.01:
        return

    stream_width = max(3, int(5 + flow * 18))
    color = lerp_color(WATER, SYRUP, concentration)

    pygame.draw.line(surface, color, (x, y1), (x, y2), stream_width)

    spacing = 38
    offset = int((phase * (40 + flow * 100)) % spacing)
    for y in range(y1 + offset, y2, spacing):
        pygame.draw.line(
            surface,
            lerp_color(color, WHITE, 0.35),
            (x - stream_width // 4, y),
            (x + stream_width // 4, min(y + 12, y2)),
            max(1, stream_width // 5),
        )


def draw_bucket(surface, rect, mixture, fill_level, font_title, font_value):
    top_width = rect.width
    bottom_width = int(rect.width * 0.72)
    cx = rect.centerx

    outer_points = [
        (cx - top_width // 2, rect.top),
        (cx + top_width // 2, rect.top),
        (cx + bottom_width // 2, rect.bottom),
        (cx - bottom_width // 2, rect.bottom),
    ]

    pygame.draw.polygon(
        surface,
        SHADOW,
        [(x + 4, y + 5) for x, y in outer_points],
    )
    pygame.draw.polygon(surface, METAL_LIGHT, outer_points)
    pygame.draw.lines(surface, OUTLINE, True, outer_points, 4)

    fill_level = clamp(fill_level, 0.12, 0.88)
    top_y = rect.bottom - int(rect.height * fill_level)

    half_width_at_top = int(
        bottom_width / 2
        + (top_width - bottom_width) / 2
        * ((rect.bottom - top_y) / rect.height)
    )

    liquid_points = [
        (cx - half_width_at_top + 8, top_y),
        (cx + half_width_at_top - 8, top_y),
        (cx + bottom_width // 2 - 8, rect.bottom - 8),
        (cx - bottom_width // 2 + 8, rect.bottom - 8),
    ]

    mix_color = lerp_color(WATER, SYRUP, mixture)
    pygame.draw.polygon(surface, mix_color, liquid_points)
    pygame.draw.line(
        surface,
        lerp_color(mix_color, WHITE, 0.3),
        liquid_points[0],
        liquid_points[1],
        4,
    )

    handle_rect = pygame.Rect(rect.left - 25, rect.top - 42, rect.width + 50, 94)
    pygame.draw.arc(surface, OUTLINE, handle_rect, math.pi, math.tau, 7)

    draw_text(
        surface,
        font_title,
        "Mixture in Bucket",
        (cx, rect.bottom + 18),
        INK,
        "midtop",
    )
    draw_text(
        surface,
        font_value,
        f"{mixture * 100:.1f}% syrup",
        (cx, rect.bottom + 50),
        INK,
        "midtop",
    )


def main():
    pygame.init()
    pygame.display.set_caption("Syrup Mixer")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("arial", 24, bold=True)
    font_large = pygame.font.SysFont("arial", 34, bold=True)
    font_value = pygame.font.SysFont("arial", 22, bold=True)
    font_small = pygame.font.SysFont("arial", 17)

    slider_left = Slider(
        pygame.Rect(90, 356, 260, 14),
        0.25,
        "Source concentration",
    )
    slider_right = Slider(
        pygame.Rect(1050, 356, 260, 14),
        0.80,
        "Source concentration",
    )

    valve_left = Valve((500, 360), 52, 0.65, "Valve 1")
    valve_right = Valve((900, 360), 52, 0.45, "Valve 2")

    running = True
    phase = 0.0

    while running:
        dt = clock.tick(FPS) / 1000.0
        phase += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            slider_left.handle_event(event)
            slider_right.handle_event(event)
            valve_left.handle_event(event)
            valve_right.handle_event(event)

        c1 = slider_left.value
        c2 = slider_right.value
        q1 = valve_left.value
        q2 = valve_right.value

        total_flow = q1 + q2
        mixture = (c1 * q1 + c2 * q2) / total_flow if total_flow > 1e-9 else 0.0
        fill_level = clamp(0.16 + total_flow * 0.30, 0.16, 0.82)

        screen.fill(BG)

        draw_text(
            screen,
            font_large,
            "Interactive Syrup Mixer",
            (WIDTH // 2, 34),
            INK,
            "midtop",
        )
        draw_text(
            screen,
            font_small,
            "Sliders set concentration; valves control relative flow rate.",
            (WIDTH // 2, 82),
            MUTED,
            "midtop",
        )

        tank_left = pygame.Rect(70, 135, 320, 180)
        tank_right = pygame.Rect(1010, 135, 320, 180)

        draw_tank(
            screen,
            tank_left,
            c1,
            "Source 1",
            font_title,
            font_small,
        )
        draw_tank(
            screen,
            tank_right,
            c2,
            "Source 2",
            font_title,
            font_small,
        )

        slider_left.draw(screen, font_small, font_value)
        slider_right.draw(screen, font_small, font_value)

        draw_pipe(screen, [(390, 220), (500, 220), (500, 294)])
        draw_pipe(screen, [(1010, 220), (900, 220), (900, 294)])

        draw_pipe(screen, [(500, 424), (500, 505), (610, 505), (610, 540)])
        draw_pipe(screen, [(900, 424), (900, 505), (790, 505), (790, 540)])

        valve_left.draw(screen, font_small, font_value)
        valve_right.draw(screen, font_small, font_value)

        for x in (610, 790):
            pygame.draw.rect(
                screen,
                OUTLINE,
                (x - 19, 528, 38, 28),
                border_radius=6,
            )
            pygame.draw.rect(
                screen,
                METAL_LIGHT,
                (x - 15, 532, 30, 20),
                border_radius=5,
            )

        bucket_rect = pygame.Rect(555, 635, 290, 125)

        draw_stream(screen, 610, 554, bucket_rect.top + 12, q1, c1, phase)
        draw_stream(screen, 790, 554, bucket_rect.top + 12, q2, c2, phase + 0.17)
        draw_bucket(
            screen,
            bucket_rect,
            mixture,
            fill_level,
            font_title,
            font_value,
        )

        formula_rect = pygame.Rect(55, 615, 405, 225)
        pygame.draw.rect(screen, PANEL, formula_rect, border_radius=18)
        pygame.draw.rect(
            screen,
            (216, 211, 201),
            formula_rect,
            width=2,
            border_radius=18,
        )

        draw_text(
            screen,
            font_title,
            "Concentration Calculation",
            (formula_rect.centerx, 634),
            INK,
            "midtop",
        )
        draw_text(
            screen,
            font_small,
            "C = (C1 * Q1 + C2 * Q2) / (Q1 + Q2)",
            (formula_rect.centerx, 681),
            INK,
            "midtop",
        )
        draw_text(
            screen,
            font_small,
            f"({c1:.2f} * {q1:.2f} + {c2:.2f} * {q2:.2f}) / {total_flow:.2f}",
            (formula_rect.centerx, 718),
            MUTED,
            "midtop",
        )
        draw_text(
            screen,
            font_value,
            f"= {mixture * 100:.1f}%",
            (formula_rect.centerx, 752),
            GREEN,
            "midtop",
        )
        draw_text(
            screen,
            font_small,
            "C1, C2 = source concentrations",
            (formula_rect.left + 28, 792),
            MUTED,
        )
        draw_text(
            screen,
            font_small,
            "Q1, Q2 = relative flow rates",
            (formula_rect.left + 28, 818),
            MUTED,
        )

        help_rect = pygame.Rect(940, 615, 405, 225)
        pygame.draw.rect(screen, PANEL, help_rect, border_radius=18)
        pygame.draw.rect(
            screen,
            (216, 211, 201),
            help_rect,
            width=2,
            border_radius=18,
        )

        draw_text(
            screen,
            font_title,
            "Controls",
            (help_rect.centerx, 634),
            INK,
            "midtop",
        )
        draw_text(
            screen,
            font_small,
            "- Slider: click and drag to set concentration",
            (help_rect.left + 30, 684),
            MUTED,
        )
        draw_text(
            screen,
            font_small,
            "- Valve: drag left or right to adjust flow",
            (help_rect.left + 30, 721),
            MUTED,
        )
        draw_text(
            screen,
            font_small,
            "- Flow range: 0.0 to 10.0 units",
            (help_rect.left + 30, 758),
            MUTED,
        )
        draw_text(
            screen,
            font_small,
            "- Esc: exit the application",
            (help_rect.left + 30, 795),
            MUTED,
        )

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
