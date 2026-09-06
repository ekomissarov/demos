"""
Bayes' Theorem — Rare Disease Test, interactive pygame visualization.

Refactor notes (vs. original):
- Fixed a per-frame font re-creation (was rebuilding a pygame.font.SysFont
  every loop iteration instead of once at startup).
- Removed duplicate / unused palette entries (RED_SOFT, GREEN_SOFT were
  defined but never used; inline magic-number colors replaced with the
  named palette instead).
- Renamed slider variables to avoid the `false_positive` (Slider) vs.
  `false_positive_count` (int) naming collision.
- Grouped fonts and colors into small dataclasses/namespaces instead of
  loose globals.
- Split the giant frame-drawing block into one function per panel
  (header, sliders, tree, grid, footer) driven by a `Stats` dataclass,
  so each piece can be read/tested independently.
- Added type hints and docstrings throughout.
- Font lookup now tries a short list of common sans-serif fonts instead
  of hardcoding "arial", which doesn't exist on most non-Windows systems.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import pygame

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------

pygame.init()

WIDTH, HEIGHT = 1500, 1000
POPULATION = 10_000

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bayes' Theorem — Rare Disease Test")
clock = pygame.time.Clock()


def make_font(size: int, bold: bool = False) -> pygame.font.Font:
    """SysFont with a fallback chain, since 'arial' rarely exists on Linux/Mac."""
    return pygame.font.SysFont("arial,helvetica,dejavusans,sans", size, bold=bold)


@dataclass(frozen=True)
class Fonts:
    title: pygame.font.Font
    section: pygame.font.Font
    body: pygame.font.Font
    small: pygame.font.Font
    tiny: pygame.font.Font
    big: pygame.font.Font
    result: pygame.font.Font


FONTS = Fonts(
    title=make_font(36, bold=True),
    section=make_font(23, bold=True),
    body=make_font(20),
    small=make_font(17),
    tiny=make_font(15),
    big=make_font(30, bold=True),
    result=make_font(25, bold=True),
)


@dataclass(frozen=True)
class Palette:
    bg: tuple = (246, 248, 251)
    card: tuple = (255, 255, 255)
    text: tuple = (30, 34, 42)
    muted: tuple = (104, 112, 124)
    border: tuple = (216, 222, 230)
    track: tuple = (207, 213, 222)

    blue: tuple = (55, 111, 226)
    blue_soft: tuple = (236, 243, 255)

    red: tuple = (207, 76, 76)
    red_soft: tuple = (255, 244, 244)      # sick / negative branch card fill
    red_soft2: tuple = (255, 240, 240)     # true-positive node fill
    red_soft3: tuple = (252, 246, 246)     # false-negative node fill

    green: tuple = (43, 153, 92)
    green_soft: tuple = (240, 250, 245)    # healthy branch card fill
    green_soft2: tuple = (238, 249, 243)   # false-positive node fill
    green_soft3: tuple = (246, 251, 248)   # true-negative node fill

    # Brighter shades = positive test, pale shades = negative test (dot grid)
    red_pos: tuple = (205, 67, 67)
    red_neg: tuple = (242, 188, 188)
    green_pos: tuple = (40, 160, 92)
    green_neg: tuple = (192, 226, 207)

    gold: tuple = (214, 153, 52)
    gold_soft: tuple = (255, 248, 231)


C = Palette()


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def fmt_count(x: float) -> str:
    return f"{int(round(x)):,}"


def draw_card(rect: pygame.Rect, fill=C.card, border=C.border, radius=14, width=1) -> None:
    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    pygame.draw.rect(screen, border, rect, width, border_radius=radius)


def draw_node(rect: pygame.Rect, title: str, value: str, subtitle: str,
              border_color, fill_color) -> None:
    draw_card(rect, fill_color, border_color, radius=12, width=2)
    screen.blit(FONTS.small.render(title, True, C.muted), (rect.x + 16, rect.y + 10))
    screen.blit(FONTS.big.render(value, True, C.text), (rect.x + 16, rect.y + 32))
    if subtitle:
        screen.blit(FONTS.tiny.render(subtitle, True, C.muted), (rect.x + 16, rect.bottom - 22))


def draw_branch(start, end, color, label: str | None = None, label_pos=None) -> None:
    pygame.draw.line(screen, color, start, end, 3)
    if label and label_pos:
        surf = FONTS.small.render(label, True, color)
        bg = surf.get_rect(center=label_pos).inflate(10, 6)
        pygame.draw.rect(screen, C.bg, bg, border_radius=5)
        screen.blit(surf, surf.get_rect(center=label_pos))


def draw_legend_item(x: int, y: int, color, text: str) -> None:
    pygame.draw.rect(screen, color, (x, y + 3, 14, 14), border_radius=3)
    screen.blit(FONTS.tiny.render(text, True, C.text), (x + 22, y))


# --------------------------------------------------------------------------
# Slider
# --------------------------------------------------------------------------


class Slider:
    def __init__(self, x: int, y: int, w: int, value: float, title: str, math_label: str):
        self.x = x
        self.y = y
        self.w = w
        self.value = value
        self.title = title
        self.math_label = math_label
        self.dragging = False

    def handle(self, event: pygame.event.Event) -> None:
        hit = pygame.Rect(self.x - 12, self.y - 18, self.w + 24, 36)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if hit.collidepoint(event.pos):
                self.dragging = True
                self.set_from_mouse(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_from_mouse(event.pos[0])

    def set_from_mouse(self, mx: int) -> None:
        self.value = clamp((mx - self.x) / self.w, 0.0, 1.0)

    def draw(self) -> None:
        screen.blit(FONTS.body.render(self.title, True, C.text), (self.x, self.y - 54))
        screen.blit(
            FONTS.small.render(f"{self.math_label} = {pct(self.value)}", True, C.muted),
            (self.x, self.y - 30),
        )

        pygame.draw.line(screen, C.track, (self.x, self.y), (self.x + self.w, self.y), 6)

        end_x = int(self.x + self.value * self.w)
        pygame.draw.line(screen, C.blue, (self.x, self.y), (end_x, self.y), 6)
        pygame.draw.circle(screen, C.blue, (end_x, self.y), 10)


prevalence_slider = Slider(65, 175, 350, 0.01, "Disease prevalence", "P(A)")
sensitivity_slider = Slider(575, 175, 350, 0.95, "Test sensitivity / Recall", "P(B | A) = TP / (TP + FN)")
fpr_slider = Slider(1085, 175, 350, 0.05, "False-positive rate", "P(B | \u00acA)")
sliders = [prevalence_slider, sensitivity_slider, fpr_slider]


# --------------------------------------------------------------------------
# Stats
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Stats:
    prevalence: float          # P(A)
    sensitivity: float         # P(B | A)
    fpr: float                 # P(B | ~A)

    sick: float
    healthy: float

    true_positive: float
    false_negative: float
    false_positive: float
    true_negative: float

    posterior: float           # P(A | B), i.e. precision / PPV

    tp_n: int
    fn_n: int
    fp_n: int
    tn_n: int
    colors: list


def compute_stats(pA: float, pBA: float, pBnotA: float) -> Stats:
    sick = POPULATION * pA
    healthy = POPULATION - sick

    true_positive = sick * pBA
    false_negative = sick * (1 - pBA)
    false_positive = healthy * pBnotA
    true_negative = healthy * (1 - pBnotA)

    all_positive = true_positive + false_positive
    posterior = true_positive / all_positive if all_positive > 1e-12 else 0.0

    colors, tp_n, fn_n, fp_n, tn_n = build_population_colors(
        POPULATION, sick, true_positive, false_positive
    )

    return Stats(
        prevalence=pA, sensitivity=pBA, fpr=pBnotA,
        sick=sick, healthy=healthy,
        true_positive=true_positive, false_negative=false_negative,
        false_positive=false_positive, true_negative=true_negative,
        posterior=posterior,
        tp_n=tp_n, fn_n=fn_n, fp_n=fp_n, tn_n=tn_n, colors=colors,
    )


def build_population_colors(population: int, sick_count: float,
                             tp_count: float, fp_count: float):
    """
    Return exactly `population` colors.

    Ordering is intentionally grouped so the structure is easy to see:
    1) sick + positive
    2) sick + negative
    3) healthy + positive
    4) healthy + negative
    """
    sick_n = int(round(sick_count))
    tp_n = int(round(tp_count))
    fp_n = int(round(fp_count))

    tp_n = max(0, min(tp_n, sick_n))
    fn_n = sick_n - tp_n

    healthy_n = population - sick_n
    fp_n = max(0, min(fp_n, healthy_n))
    tn_n = healthy_n - fp_n

    colors = (
        [C.red_pos] * tp_n
        + [C.red_neg] * fn_n
        + [C.green_pos] * fp_n
        + [C.green_neg] * tn_n
    )

    # Safety against rounding edge cases
    if len(colors) < population:
        colors.extend([C.green_neg] * (population - len(colors)))
    elif len(colors) > population:
        colors = colors[:population]

    return colors, tp_n, fn_n, fp_n, tn_n


def draw_dot_grid(rect: pygame.Rect, colors: list) -> None:
    """Draw a 100 x 100 grid = exactly 10,000 people, one square per person."""
    cols = rows = 100
    gap = 1

    cell_w = max(1, (rect.width - (cols - 1) * gap) // cols)
    cell_h = max(1, (rect.height - (rows - 1) * gap) // rows)
    cell = max(1, min(cell_w, cell_h))

    grid_w = cols * cell + (cols - 1) * gap
    grid_h = rows * cell + (rows - 1) * gap

    start_x = rect.x + (rect.width - grid_w) // 2
    start_y = rect.y + (rect.height - grid_h) // 2

    for i, color in enumerate(colors):
        row, col = divmod(i, cols)
        x = start_x + col * (cell + gap)
        y = start_y + row * (cell + gap)
        pygame.draw.rect(screen, color, (x, y, cell, cell))


# --------------------------------------------------------------------------
# Panel drawing
# --------------------------------------------------------------------------


def draw_header() -> None:
    screen.blit(FONTS.title.render("Bayes' Theorem — Rare Disease Test", True, C.text), (46, 28))
    screen.blit(
        FONTS.body.render("Among positive tests, how many people actually have the disease?", True, C.muted),
        (46, 72),
    )


def draw_tree_panel(stats: Stats) -> None:
    tree_card = pygame.Rect(44, 225, 735, 635)
    draw_card(tree_card)
    screen.blit(FONTS.section.render("Population tree", True, C.text), (68, 249))

    root = pygame.Rect(74, 478, 170, 80)
    sick_rect = pygame.Rect(310, 345, 190, 88)
    healthy_rect = pygame.Rect(310, 610, 190, 88)

    tp_rect = pygame.Rect(555, 300, 190, 88)
    fn_rect = pygame.Rect(555, 430, 190, 88)
    fp_rect = pygame.Rect(555, 565, 190, 88)
    tn_rect = pygame.Rect(555, 695, 190, 88)

    pA, pBA, pBnotA = stats.prevalence, stats.sensitivity, stats.fpr

    draw_branch((244, 500), (310, 390), C.red, pct(pA), (275, 430))
    draw_branch((244, 535), (310, 650), C.green, pct(1 - pA), (277, 592))

    draw_branch((500, 372), (555, 344), C.red, pct(pBA), (527, 330))
    draw_branch((500, 410), (555, 474), C.red, pct(1 - pBA), (527, 470))

    draw_branch((500, 635), (555, 610), C.green, pct(pBnotA), (527, 596))
    draw_branch((500, 675), (555, 739), C.green, pct(1 - pBnotA), (527, 735))

    draw_node(root, "Population", "10,000", "", C.blue, C.blue_soft)
    draw_node(sick_rect, "Have disease", fmt_count(stats.sick), "A", C.red, C.red_soft)
    draw_node(healthy_rect, "Healthy", fmt_count(stats.healthy), "\u00acA", C.green, C.green_soft)

    draw_node(tp_rect, "Positive", fmt_count(stats.tp_n), "true positive", C.red, C.red_soft2)
    draw_node(fn_rect, "Negative", fmt_count(stats.fn_n), "false negative", C.red, C.red_soft3)
    draw_node(fp_rect, "Positive", fmt_count(stats.fp_n), "false positive", C.green, C.green_soft2)
    draw_node(tn_rect, "Negative", fmt_count(stats.tn_n), "true negative", C.green, C.green_soft3)


def draw_grid_panel(stats: Stats) -> None:
    grid_card = pygame.Rect(805, 225, 651, 635)
    draw_card(grid_card)

    gx, gy = grid_card.x + 28, grid_card.y + 24

    screen.blit(FONTS.section.render("10,000 people", True, C.text), (gx, gy))
    screen.blit(FONTS.small.render("Each dot represents one person.", True, C.muted), (gx, gy + 34))

    grid_rect = pygame.Rect(gx, gy + 72, grid_card.width - 56, 350)
    draw_card(grid_rect, (251, 252, 254), C.border, radius=10)
    draw_dot_grid(grid_rect.inflate(-14, -14), stats.colors)

    legend_y = grid_rect.bottom + 22
    draw_legend_item(gx, legend_y, C.red_pos, "Disease + positive")
    draw_legend_item(gx + 245, legend_y, C.red_neg, "Disease + negative")
    draw_legend_item(gx, legend_y + 28, C.green_pos, "Healthy + positive")
    draw_legend_item(gx + 245, legend_y + 28, C.green_neg, "Healthy + negative")

    summary_y = legend_y + 76
    screen.blit(
        FONTS.body.render(
            f"Positive tests: {fmt_count(stats.tp_n)} true + {fmt_count(stats.fp_n)} false "
            f"= {fmt_count(stats.tp_n + stats.fp_n)}",
            True, C.text,
        ),
        (gx, summary_y),
    )

    summary_y += 35
    result_box = pygame.Rect(gx, summary_y, grid_card.width - 56, 82)
    draw_card(result_box, C.gold_soft, C.gold, radius=12, width=2)

    screen.blit(
        FONTS.small.render("Precision / Positive Predictive Value", True, C.muted),
        (result_box.x + 18, result_box.y + 10),
    )
    result_text = (
        f"P(A | B) = {fmt_count(stats.tp_n)} / {fmt_count(stats.tp_n + stats.fp_n)} "
        f"= {pct(stats.posterior)}"
    )
    screen.blit(FONTS.result.render(result_text, True, C.text), (result_box.x + 18, result_box.y + 36))


def draw_footer(stats: Stats) -> None:
    footer = pygame.Rect(44, 885, 1412, 82)
    draw_card(footer)

    pA, pBA, pBnotA = stats.prevalence, stats.sensitivity, stats.fpr

    recall_line = f"Recall = P(B | A) = {pct(pBA)}"
    precision_line = (
        f"Precision = P(A | B) = "
        f"[{pBA:.3f} \u00d7 {pA:.3f}] / "
        f"([{pBA:.3f} \u00d7 {pA:.3f}] + [{pBnotA:.3f} \u00d7 {1 - pA:.3f}]) "
        f"= {pct(stats.posterior)}"
    )

    screen.blit(FONTS.body.render(recall_line, True, C.text), (68, 900))
    screen.blit(FONTS.small.render(precision_line, True, C.text), (68, 932))


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------


def main() -> None:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            for slider in sliders:
                slider.handle(event)

        stats = compute_stats(prevalence_slider.value, sensitivity_slider.value, fpr_slider.value)

        screen.fill(C.bg)
        draw_header()
        for slider in sliders:
            slider.draw()
        draw_tree_panel(stats)
        draw_grid_panel(stats)
        draw_footer(stats)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
