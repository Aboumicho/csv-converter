"""
core.py
=======
Shared UI helpers used by both tool views.
"""

import tkinter as tk

from ui.colors import ACCENT, ACCENT_OK, CARD, CARD_ACTIVE, MUTED, TEXT


def make_card(
    parent: tk.Widget,
    column: int,
    title: str,
    subtitle: str,
    glyph: str,
    glyph_color: str,
    command,
    enabled: bool = True,
) -> dict:
    """
    Build a clickable square card widget placed in *parent*'s grid.

    Returns a ``refs`` dict with keys ``card``, ``glyph``, ``title``,
    ``subtitle``, ``command``, ``enabled``.
    """
    card = tk.Frame(
        parent, bg=CARD, width=240, height=240,
        highlightthickness=2, highlightbackground=CARD,
    )
    card.grid(row=0, column=column, padx=18, pady=18)
    card.grid_propagate(False)

    glyph_lbl = tk.Label(
        card, text=glyph, bg=CARD, fg=glyph_color,
        font=("Segoe UI Semibold", 34),
    )
    glyph_lbl.place(relx=0.5, rely=0.34, anchor="center")

    title_lbl = tk.Label(
        card, text=title, bg=CARD, fg=TEXT,
        font=("Segoe UI Semibold", 14),
    )
    title_lbl.place(relx=0.5, rely=0.62, anchor="center")

    sub_lbl = tk.Label(
        card, text=subtitle, bg=CARD, fg=MUTED,
        font=("Segoe UI", 9), wraplength=200, justify="center",
    )
    sub_lbl.place(relx=0.5, rely=0.78, anchor="center")

    refs = {
        "card": card,
        "glyph": glyph_lbl,
        "title": title_lbl,
        "subtitle": sub_lbl,
        "command": command,
        "enabled": enabled,
    }

    def on_click(_e=None):
        if refs["enabled"]:
            command()

    def on_enter(_e=None):
        if refs["enabled"]:
            card.configure(bg=CARD_ACTIVE, highlightbackground=ACCENT)
            for w in (glyph_lbl, title_lbl, sub_lbl):
                w.configure(bg=CARD_ACTIVE)

    def on_leave(_e=None):
        card.configure(bg=CARD, highlightbackground=CARD)
        for w in (glyph_lbl, title_lbl, sub_lbl):
            w.configure(bg=CARD)

    for w in (card, glyph_lbl, title_lbl, sub_lbl):
        w.bind("<Button-1>", on_click)
        w.bind("<Enter>", on_enter)
        w.bind("<Leave>", on_leave)

    return refs


def set_card_enabled(refs: dict, enabled: bool) -> None:
    """Toggle a card's enabled state and update its glyph colour."""
    refs["enabled"] = enabled
    refs["glyph"].configure(fg=ACCENT_OK if enabled else MUTED)
