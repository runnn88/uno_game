from __future__ import annotations

import pygame

from domain.entities.card import Card
from config.enums import CardColor, CardRank
from presentation.game_feedback import CardMotion, Toast
from presentation.theme import ACCENT, CARD_H, CARD_W, PANEL, SHADOW, TEXT


def draw_card_motions(app) -> None:
    if app.screen is None or app.card_renderer is None:
        return
    for motion in app.card_motions:
        t = min(1.0, motion.age / max(0.001, motion.duration))
        eased = 1 - (1 - t) ** 3
        bob = int(18 * (1 - abs(0.5 - t) * 2))
        x = int(motion.start[0] + (motion.end[0] - motion.start[0]) * eased)
        y = int(motion.start[1] + (motion.end[1] - motion.start[1]) * eased) - bob
        alpha = max(0, min(255, int(255 * (1 - max(0, t - 0.82) / 0.18))))
        layer = pygame.Surface((CARD_W + 16, CARD_H + 16), pygame.SRCALPHA)
        shadow = pygame.Surface((CARD_W + 10, CARD_H + 10), pygame.SRCALPHA)
        pygame.draw.rect(shadow, SHADOW, pygame.Rect(6, 7, CARD_W, CARD_H), border_radius=10)
        layer.blit(shadow, (0, 0))
        card_surface = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
        if motion.face_down or motion.card is None:
            _draw_motion_card_back(app, card_surface)
        else:
            app.card_renderer.draw_card(card_surface, _card_from_dict(motion.card), pygame.Rect(0, 0, CARD_W, CARD_H))
        card_surface.set_alpha(alpha)
        layer.blit(card_surface, (0, 0))
        app.screen.blit(layer, (x, y))


def draw_toasts(app) -> None:
    if app.screen is None or not app.toasts:
        return
    x = 930
    y = 168
    for toast in app.toasts[-3:]:
        progress_in = min(1.0, toast.age / 0.18)
        progress_out = min(1.0, max(0.0, (toast.duration - toast.age) / 0.28))
        alpha = int(235 * min(progress_in, progress_out))
        slide = int((1 - progress_in) * 34)
        rect = pygame.Rect(x + slide, y, 300, 92)
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PANEL, alpha), panel.get_rect(), border_radius=8)
        pygame.draw.rect(panel, (*toast.tone, alpha), pygame.Rect(0, 0, 7, rect.height), border_radius=8)
        pygame.draw.rect(panel, (*toast.tone, alpha), panel.get_rect(), 2, border_radius=8)
        app.screen.blit(panel, rect.topleft)
        app._draw_text(toast.title, rect.x + 18, rect.y + 12, toast.tone, size="small")
        _draw_toast_body(app, toast.body, rect.x + 18, rect.y + 40, 258, TEXT)
        y += 104


def _draw_motion_card_back(app, surface: pygame.Surface) -> None:
    pygame.draw.rect(surface, (255, 251, 242), surface.get_rect(), border_radius=10)
    inner = surface.get_rect().inflate(-8, -8)
    pygame.draw.rect(surface, (188, 213, 232), inner, border_radius=8)
    pygame.draw.ellipse(surface, ACCENT, inner.inflate(-12, -42))
    font, _small, _big = app._fonts()
    text = font.render("UNO", True, TEXT)
    surface.blit(text, text.get_rect(center=surface.get_rect().center))


def _draw_toast_body(app, text: str, x: int, y: int, width: int, color: tuple[int, int, int]) -> None:
    _font, small, _big = app._fonts()
    words = text.split()
    line = ""
    line_y = y
    for word in words:
        candidate = f"{line}{word} "
        if small.size(candidate)[0] <= width:
            line = candidate
            continue
        app._draw_text(line.rstrip(), x, line_y, color, size="small")
        line_y += 20
        line = f"{word} "
        if line_y > y + 38:
            break
    if line and line_y <= y + 38:
        app._draw_text(line.rstrip(), x, line_y, color, size="small")


def _card_from_dict(data: dict[str, str]) -> Card:
    return Card(data["id"], CardColor(data["color"]), CardRank(data["rank"]))
