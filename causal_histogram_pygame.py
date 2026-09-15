"""
Interactive pygame visualization: three sliders (Treatment Effect,
Confounder -> Treatment, Confounder -> Outcome) regenerate the dataset
with generate_data() on the fly and redraw the histogram of y for the
whole population / control / treatment groups (same idea as the
matplotlib plot from the notebook).

Run: python causal_histogram_pygame.py
Requires: numpy, pandas, pygame  (pip install numpy pandas pygame)
"""

import numpy as np
import pandas as pd
import pygame


# ---------------------------------------------------------------------------
# Data generation function (single confounder, no instruments, no covariates
# for this scenario)
# ---------------------------------------------------------------------------
def generate_data(
    effect=0,
    sample_size=1000,
    n_confounders=1,
    n_instruments=0,
    n_covariates=1,
    w_t_coefs=None,
    w_y_coefs=None,
    z_t_coefs=None,
    x_y_coefs=None,
    random_state=None,
):
    """
    Generates a dataset with a target, a treatment, confounders,
    instruments and covariates.

    Parameters
    ----------
    effect: float. True effect, i.e. the coefficient of the treatment's
        influence on the target
    sample_size: int. Number of generated observations
    n_confounders: int. Number of confounders to generate (W -> T, W -> Y)
    n_instruments: int. Number of instruments to generate (Z -> T)
    n_covariates: int. Number of covariates to generate (X -> Y)
    w_t_coefs: array-like[float]/None. Coefficients of confounders'
        influence on the treatment, length n_confounders
    w_y_coefs: array-like[float]/None. Coefficients of confounders'
        influence on the target, length n_confounders
    z_t_coefs: array-like[float]/None. Coefficients of instruments'
        influence on the treatment, length n_instruments
    x_y_coefs: array-like[float]/None. Coefficients of covariates'
        influence on the target, length n_covariates
    random_state: int/None. Seed for reproducible generation. If None,
        the result is random on every call
    ----------
    Returns:
    data: pd.DataFrame of shape (sample_size, 2 + n_confounders + n_instruments + n_covariates).
        Generated data. Target: y, treatment: T, confounders: W_i,
        instruments: Z_i, covariates: X_i
    """

    rng = np.random.default_rng(random_state)

    if n_confounders > 0:
        locs_w = rng.uniform(low=-1, high=1, size=n_confounders)
        if w_t_coefs is None:
            w_t_coefs = np.full(n_confounders, 0.01)
        elif len(w_t_coefs) != n_confounders:
            raise ValueError(
                f"len(w_t_coefs)={len(w_t_coefs)} does not match n_confounders={n_confounders}"
            )
        if w_y_coefs is None:
            w_y_coefs = np.full(n_confounders, 1.0)
        elif len(w_y_coefs) != n_confounders:
            raise ValueError(
                f"len(w_y_coefs)={len(w_y_coefs)} does not match n_confounders={n_confounders}"
            )
    if n_instruments > 0:
        locs_z = rng.uniform(low=-1, high=1, size=n_instruments)
        if z_t_coefs is None:
            z_t_coefs = np.full(n_instruments, 0.01)
        elif len(z_t_coefs) != n_instruments:
            raise ValueError(
                f"len(z_t_coefs)={len(z_t_coefs)} does not match n_instruments={n_instruments}"
            )
    if n_covariates > 0:
        locs_x = rng.uniform(low=-1, high=1, size=n_covariates)
        if x_y_coefs is None:
            x_y_coefs = np.full(n_covariates, 1.0)
        elif len(x_y_coefs) != n_covariates:
            raise ValueError(
                f"len(x_y_coefs)={len(x_y_coefs)} does not match n_covariates={n_covariates}"
            )

    target = ["y"]
    treatment = ["T"]
    confounders = [f"W_{i}" for i in range(n_confounders)]
    instruments = [f"Z_{i}" for i in range(n_instruments)]
    covariates = [f"X_{i}" for i in range(n_covariates)]

    columns = target + treatment + confounders + instruments + covariates
    data = pd.DataFrame(index=np.arange(sample_size), columns=columns, dtype=float)

    p_bias = 0
    loc_bias = 0
    for i in range(n_confounders):
        w = rng.normal(loc=locs_w[i], size=sample_size)
        data[f"W_{i}"] = w
        p_bias += w_t_coefs[i] * w
        loc_bias += w_y_coefs[i] * w
    for i in range(n_instruments):
        z = rng.normal(loc=locs_z[i], size=sample_size)
        data[f"Z_{i}"] = z
        p_bias += z_t_coefs[i] * z
    for i in range(n_covariates):
        x = rng.normal(loc=locs_x[i], size=sample_size)
        data[f"X_{i}"] = x
        loc_bias += x_y_coefs[i] * x

    p = np.minimum(1, np.maximum(0, 0.5 + p_bias))
    t = rng.binomial(n=1, p=p, size=sample_size)
    data["T"] = t

    loc = loc_bias + effect * t
    y = rng.normal(loc=loc, size=sample_size)
    data["y"] = y

    return data


# ---------------------------------------------------------------------------
# Slider widget
# ---------------------------------------------------------------------------
class Slider:
    def __init__(self, x, y, width, min_val, max_val, start_val, label):
        self.x = x
        self.y = y
        self.width = width
        self.min_val = min_val
        self.max_val = max_val
        self.value = start_val
        self.label = label
        self.height = 6
        self.handle_radius = 9
        self.dragging = False

    def _value_to_x(self, value):
        ratio = (value - self.min_val) / (self.max_val - self.min_val)
        return int(self.x + ratio * self.width)

    def _x_to_value(self, x):
        ratio = (x - self.x) / self.width
        ratio = min(1.0, max(0.0, ratio))
        return self.min_val + ratio * (self.max_val - self.min_val)

    def handle_pos(self):
        return self._value_to_x(self.value), self.y

    def handle_event(self, event):
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hx, hy = self.handle_pos()
            if (event.pos[0] - hx) ** 2 + (event.pos[1] - hy) ** 2 <= (self.handle_radius + 4) ** 2:
                self.dragging = True
            elif self.x <= event.pos[0] <= self.x + self.width and abs(event.pos[1] - self.y) <= 10:
                # click on the track — jump straight to that value
                self.value = self._x_to_value(event.pos[0])
                changed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.value = self._x_to_value(event.pos[0])
            changed = True
        return changed

    def draw(self, surface, font):
        # track
        pygame.draw.line(
            surface, (180, 180, 190), (self.x, self.y), (self.x + self.width, self.y), self.height
        )
        # filled part
        hx, hy = self.handle_pos()
        pygame.draw.line(surface, (90, 130, 220), (self.x, self.y), (hx, hy), self.height)
        # handle
        pygame.draw.circle(surface, (40, 60, 120), (hx, hy), self.handle_radius)
        pygame.draw.circle(surface, (255, 255, 255), (hx, hy), self.handle_radius - 3)
        # label
        label_surf = font.render(f"{self.label}: {self.value:.2f}", True, (20, 20, 20))
        surface.blit(label_surf, (self.x, self.y - 30))


# ---------------------------------------------------------------------------
# Histogram drawing (analogue of the matplotlib plot from the notebook)
# ---------------------------------------------------------------------------
def draw_histogram(surface, rect, y_all, y_control, y_treatment, font, bins=20):
    px, py, pw, ph = rect
    pygame.draw.rect(surface, (250, 250, 252), rect)
    pygame.draw.rect(surface, (120, 120, 130), rect, 1)

    y_min, y_max = float(np.min(y_all)), float(np.max(y_all))
    if y_min == y_max:
        y_min, y_max = y_min - 1, y_max + 1
    edges = np.linspace(y_min, y_max, bins + 1)

    counts_all, _ = np.histogram(y_all, bins=edges)
    counts_control, _ = np.histogram(y_control, bins=edges)
    counts_treatment, _ = np.histogram(y_treatment, bins=edges)

    max_count = max(counts_all.max(), 1)
    plot_h = ph - 30  # room for the x-axis tick labels at the bottom

    def bar_rect(count, i):
        bar_h = int((count / max_count) * (plot_h - 10))
        bar_x = px + int(i * pw / bins)
        bar_w = max(1, int(pw / bins) - 1)
        bar_y = py + plot_h - bar_h
        return pygame.Rect(bar_x, bar_y, bar_w, bar_h)

    def draw_series(counts, color, alpha):
        overlay = pygame.Surface((pw, ph), pygame.SRCALPHA)
        for i, c in enumerate(counts):
            if c == 0:
                continue
            r = bar_rect(c, i)
            local_rect = pygame.Rect(r.x - px, r.y - py, r.width, r.height)
            pygame.draw.rect(overlay, (*color, alpha), local_rect)
        surface.blit(overlay, (px, py))

    # same order as in matplotlib: whole population, then control, then treatment
    draw_series(counts_all, (100, 100, 100), 90)
    draw_series(counts_control, (44, 160, 44), 110)   # C2 - green
    draw_series(counts_treatment, (214, 39, 40), 110)  # C3 - red

    # x-axis: a handful of labelled ticks
    n_ticks = 6
    for i in range(n_ticks + 1):
        val = y_min + i * (y_max - y_min) / n_ticks
        tick_x = px + int(i * pw / n_ticks)
        pygame.draw.line(surface, (150, 150, 150), (tick_x, py + plot_h), (tick_x, py + plot_h + 4))
        label = font.render(f"{val:.1f}", True, (60, 60, 60))
        surface.blit(label, (tick_x - label.get_width() // 2, py + plot_h + 6))

    # group means - vertical lines
    def mean_line(mean_val, color):
        if np.isnan(mean_val):
            return
        line_x = px + int((mean_val - y_min) / (y_max - y_min) * pw)
        line_x = min(px + pw, max(px, line_x))
        pygame.draw.line(surface, color, (line_x, py), (line_x, py + plot_h), 2)

    control_mean = float(np.mean(y_control)) if len(y_control) else float("nan")
    treatment_mean = float(np.mean(y_treatment)) if len(y_treatment) else float("nan")
    mean_line(control_mean, (44, 160, 44))
    mean_line(treatment_mean, (214, 39, 40))

    return control_mean, treatment_mean


def draw_legend(surface, x, y, font, control_mean, treatment_mean):
    entries = [
        ((100, 100, 100), "Whole population"),
        ((44, 160, 44), f"Control (mean: {control_mean:.3f})"),
        ((214, 39, 40), f"Treatment (mean: {treatment_mean:.3f})"),
    ]
    for i, (color, text) in enumerate(entries):
        ly = y + i * 22
        pygame.draw.rect(surface, color, pygame.Rect(x, ly, 16, 16))
        label = font.render(text, True, (20, 20, 20))
        surface.blit(label, (x + 24, ly - 2))


# ---------------------------------------------------------------------------
# Main application loop
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    width, height = 960, 720
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Causal Data Generator")

    font = pygame.font.SysFont("arial", 16)
    title_font = pygame.font.SysFont("arial", 20, bold=True)

    sample_size = 10000
    random_state = None

    # sliders are spaced out (260px wide, 40px gaps) so their labels never
    # collide with the neighbouring slider or with the title above them
    sliders = [
        Slider(x=40, y=120, width=260, min_val=-3.0, max_val=3.0, start_val=0.0,
               label="Treatment Effect"),
        Slider(x=340, y=120, width=260, min_val=-1.0, max_val=1.0, start_val=0.3,
               label="Confounder -> Treatment"),
        Slider(x=640, y=120, width=260, min_val=-3.0, max_val=3.0, start_val=0.0,
               label="Confounder -> Outcome"),
    ]

    def compute():
        data = generate_data(
            effect=sliders[0].value,
            sample_size=sample_size,
            n_confounders=1,
            n_instruments=0,
            n_covariates=0,
            w_t_coefs=[sliders[1].value],
            w_y_coefs=[sliders[2].value],
            z_t_coefs=None,
            x_y_coefs=None,
            random_state=random_state,
        )
        y_all = data["y"].to_numpy()
        y_control = data.query("T == 0")["y"].to_numpy()
        y_treatment = data.query("T == 1")["y"].to_numpy()
        return y_all, y_control, y_treatment

    y_all, y_control, y_treatment = compute()

    hist_rect = (40, 170, 880, 370)
    clock = pygame.time.Clock()
    running = True

    while running:
        changed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            for slider in sliders:
                if slider.handle_event(event):
                    changed = True

        if changed:
            y_all, y_control, y_treatment = compute()

        screen.fill((255, 255, 255))

        title = title_font.render(
            "Distribution of y: Population / Control / Treatment", True, (20, 20, 20)
        )
        screen.blit(title, (40, 20))

        for slider in sliders:
            slider.draw(screen, font)

        control_mean, treatment_mean = draw_histogram(
            screen, hist_rect, y_all, y_control, y_treatment, font
        )
        draw_legend(screen, 40, hist_rect[1] + hist_rect[3] + 20, font, control_mean, treatment_mean)

        hint = font.render(
            "Drag the sliders to regenerate the dataset and update the histogram in real time",
            True,
            (100, 100, 100),
        )
        screen.blit(hint, (40, height - 30))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
