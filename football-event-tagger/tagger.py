"""
tagger.py -- click-to-log football event tagger (with shot outcomes)

How you'll use it:
  - Watch the match in a separate window.
  - Pause. On the left controls set Team, Action, Outcome and the Time,
    and type the Player number.
  - If the action is a SHOT, also set the "Shot outcome" box
    (Goal / On target / Off target / Blocked). It's ignored for non-shots.
  - Click the pitch where the event happened.
      * PASS: click START, then click END (two clicks).
      * everything else: one click.
  - Every event is written to events.csv immediately. "Undo" removes the last.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons, TextBox, Button
from mplsoccer import Pitch

# ---- 1. SETTINGS you can edit -------------------------------------------

TEAM_HOME = "Kattakurgan"
TEAM_AWAY = "Jayxun"
CSV_PATH  = "events.csv"

ACTIONS = ["Pass", "Shot", "Tackle", "Interception",
           "Clearance", "Block", "Dribble", "Aerial", "Foul", "Touch"]

# Shot-only outcomes. "Blocked" is kept separate from "On target" on purpose:
# a blocked shot is NOT an on-target shot in standard stat definitions.
SHOT_OUTCOMES = ["Goal", "On target", "Off target", "Blocked"]

# NOTE the new "shot_outcome" column at the end.
COLUMNS = ["time", "team", "player", "action",
           "x", "y", "end_x", "end_y", "outcome", "shot_outcome"]

# ---- 2. load existing events so you can stop and resume later -----------
if os.path.exists(CSV_PATH):
    events = pd.read_csv(CSV_PATH).to_dict("records")
else:
    events = []

def save():
    pd.DataFrame(events, columns=COLUMNS).to_csv(CSV_PATH, index=False)

# ---- 3. build the window -------------------------------------------------
pitch = Pitch(pitch_type="statsbomb", line_color="black", pitch_color="#f7f7f7")

fig = plt.figure(figsize=(15, 8.5))
# The pitch gets its own rectangle on the RIGHT: [left, bottom, width, height]
# as fractions of the window. Left edge at 0.32 leaves the left strip free.
pitch_ax = fig.add_axes([0.32, 0.05, 0.66, 0.90])
pitch.draw(ax=pitch_ax)

# Controls stack down the LEFT strip. Each is [left, bottom, width, height].
# They're spaced so each box's title sits in the gap above it, not on top of
# the box above. If anything looks cramped on your screen, nudge these numbers:
# raising 'bottom' moves a box up; raising 'height' makes it taller.
ax_undo    = fig.add_axes([0.02, 0.925, 0.10, 0.045])
ax_team    = fig.add_axes([0.02, 0.80,  0.22, 0.09]); ax_team.set_title("Team")
ax_action  = fig.add_axes([0.02, 0.45,  0.22, 0.30]); ax_action.set_title("Action")
ax_outcome = fig.add_axes([0.02, 0.34,  0.22, 0.07]); ax_outcome.set_title("Outcome")
ax_shot    = fig.add_axes([0.02, 0.18,  0.22, 0.12]); ax_shot.set_title("Shot outcome")
ax_player  = fig.add_axes([0.08, 0.11,  0.16, 0.04])
ax_time    = fig.add_axes([0.08, 0.05,  0.16, 0.04])

radio_team    = RadioButtons(ax_team,    [TEAM_HOME, TEAM_AWAY])
radio_action  = RadioButtons(ax_action,  ACTIONS)
radio_outcome = RadioButtons(ax_outcome, ["Successful", "Unsuccessful"])
radio_shot    = RadioButtons(ax_shot,    SHOT_OUTCOMES)     # <-- new
box_player    = TextBox(ax_player, "Player ", initial="")
box_time      = TextBox(ax_time,   "Time ",   initial="0:00")
btn_undo      = Button(ax_undo, "Undo")

# ---- 4. state used while tagging ----------------------------------------
pending_start = {"x": None, "y": None}   # remembers a pass's first click
drawn = []                               # the dots/arrows on screen, for undo

def colour():
    return "tab:blue" if radio_team.value_selected == TEAM_HOME else "tab:red"

def redraw_status():
    if events:
        last = events[-1]
        pitch_ax.set_title(f"{len(events)} events   |   "
                           f"last: {last['action']} by {last['team']}")
    else:
        pitch_ax.set_title("0 events logged")
    fig.canvas.draw_idle()

# ---- 5. what happens when you click the pitch ---------------------------
def on_click(event):
    if event.inaxes is not pitch_ax:     # ignore clicks on the controls
        return
    x, y = event.xdata, event.ydata
    action = radio_action.value_selected

    # For shots, capture the shot outcome; for anything else leave it blank.
    shot_outcome = radio_shot.value_selected if action == "Shot" else ""

    if action == "Pass" and pending_start["x"] is None:
        # first click of a pass = the start location
        pending_start["x"], pending_start["y"] = x, y
        dot = pitch_ax.scatter(x, y, c=colour(), s=25)
        drawn.append([dot])
        fig.canvas.draw_idle()
        return

    if action == "Pass":
        # second click = the end location; now we have a full pass
        sx, sy = pending_start["x"], pending_start["y"]
        row = dict(time=box_time.text, team=radio_team.value_selected,
                   player=box_player.text, action="Pass",
                   x=sx, y=sy, end_x=x, end_y=y,
                   outcome=radio_outcome.value_selected, shot_outcome="")
        arrow = pitch_ax.annotate("", xy=(x, y), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="->", color=colour()))
        drawn[-1].append(arrow)
        pending_start["x"] = None
    else:
        # any non-pass event = a single point
        row = dict(time=box_time.text, team=radio_team.value_selected,
                   player=box_player.text, action=action,
                   x=x, y=y, end_x="", end_y="",
                   outcome=radio_outcome.value_selected,
                   shot_outcome=shot_outcome)
        dot = pitch_ax.scatter(x, y, c=colour(), s=45,
                               edgecolors="black", zorder=3)
        drawn.append([dot])

    events.append(row)
    save()
    redraw_status()

def on_undo(_):
    if pending_start["x"] is not None:   # cancel a half-finished pass first
        for artist in drawn.pop():
            artist.remove()
        pending_start["x"] = None
        redraw_status()
        return
    if not events:
        return
    events.pop()
    if drawn:                            # remove its dot/arrow from screen
        for artist in drawn.pop():
            artist.remove()
    save()
    redraw_status()

fig.canvas.mpl_connect("button_press_event", on_click)
btn_undo.on_clicked(on_undo)

redraw_status()
plt.show()