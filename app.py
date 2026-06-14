import os
import json
import time
import random
import html
import gradio as gr
import agents
import voice
import transcribe
import events
import world_state
from worlds import get_world, WORLDS, list_worlds

MOCK = os.environ.get("TINYWORLD_MOCK", "0") == "1"

MOOD_EMOJI = {
    "happy": "😊", "stressed": "😰", "bored": "😐", "excited": "🤩",
    "hungry": "🍕", "tired": "😴", "nostalgic": "🥹", "curious": "🧐",
    "proud": "😤", "embarrassed": "🫣",
}

VIBE_COLORS = {
    "energy": ("#ff6b6b", "#ffb15f"),
    "social": ("#38e8ff", "#9b6bff"),
}

CHAR_COLORS = {
    "Marta Voss": "#ff5fa2", "Jay Park": "#ff8a5f", "Nia Okafor": "#7CFFB2",
    "Luca Bell": "#38e8ff", "Priya Raman": "#9b6bff",
}
PALETTE = ["#ff5fa2", "#ff8a5f", "#7CFFB2", "#38e8ff", "#9b6bff"]


def esc(value):
    return html.escape(str(value), quote=True)


def char_color(world, name):
    for i, c in enumerate(world["cast"]):
        if c["name"] == name:
            return c.get("color") or CHAR_COLORS.get(name) or PALETTE[i % len(PALETTE)]
    return "#9b6bff"


# ---------------------------------------------------------------- canvas payloads
def build_world_payload(world_id):
    world = get_world(world_id)
    board = world["board"]
    cast = []
    for c in world["cast"]:
        home_key = c.get("home", "square")
        tile = board["hotspots_tile"].get(home_key, [6, 6])
        cast.append({
            "name": c["name"], "short": c["name"].split()[0],
            "emoji": c.get("emoji", "👤"),
            "color": char_color(world, c["name"]),
            "home": tile,
        })
    payload = {
        "cols": board["cols"], "rows": board["rows"],
        "roads": board["roads"], "plaza": board["plaza"],
        "plaza_center": board.get("plaza_center", [board["cols"] / 2, board["rows"] / 2]),
        "buildings": board["buildings"], "trees": board.get("trees", []),
        "props": board.get("props", []), "cast": cast,
        "hotspots": board.get("hotspots_tile", {}), "ambient": board.get("ambient", 12),
    }
    return json.dumps(payload)


def build_reactions_payload(world_id, reactions):
    world = get_world(world_id)
    board = world["board"]
    hs = board["hotspots_tile"]
    acts = board.get("activities", {})
    out = {"ts": time.time(), "reactions": []}
    for r in reactions:
        name = r["name"]
        key = r.get("moved_to") or world_state.get_position(world_id, name)
        act = acts.get(name, {})
        action = (r.get("action") or "").strip()
        short_action = (action[:24].rstrip() + "…") if len(action) > 25 else action
        label = short_action or act.get("label", "")
        vehicle = act.get("vehicle", "")
        if key and key in hs:
            tgt = hs[key]
        else:
            home = next((c.get("home") for c in world["cast"] if c["name"] == name), None)
            tgt = hs.get(home) or hs.get("square") or [0, 0]
        out["reactions"].append({
            "name": name, "short": name.split()[0],
            "mood": r["mood"], "moodEmoji": MOOD_EMOJI.get(r["mood"], "😐"),
            "text": r["text"], "target": tgt, "activity": label, "vehicle": vehicle,
            "running": False,
        })
    return json.dumps(out)


# ---------------------------------------------------------------- roster / ticker / log
def render_vibe_bar(label, value, colors):
    c1, c2 = colors
    pct = int(value * 100)
    return (
        f'<div class="vibe-row"><span class="vibe-label">{label}</span>'
        f'<div class="vibe-track"><div class="vibe-fill" style="width:{pct}%;'
        f'background:linear-gradient(90deg,{c1},{c2});color:{c1}"></div></div>'
        f'<span class="vibe-val">{pct}</span></div>'
    )


def render_roster(world_id):
    world = get_world(world_id)
    world_state.init_cast(world)
    state = world_state.get_state(world_id)
    vibes = world_state.get_vibes(world_id)
    cards = []
    for c in world["cast"]:
        name = c["name"]
        mood = state["moods"].get(name, "curious")
        mood_e = MOOD_EMOJI.get(mood, "😐")
        v = vibes.get(name, {"energy": 0.5, "social": 0.5})
        cards.append(
            f'<div class="roster-card" style="border-left-color:{char_color(world, name)}">'
            f'<div class="roster-emoji">{c.get("emoji", "👤")}</div>'
            f'<div class="roster-name">{name.split()[0]}</div>'
            f'<div class="roster-mood">{mood_e} {mood}</div>'
            f'<div class="roster-meters">{render_vibe_bar("⚡", v["energy"], VIBE_COLORS["energy"])}'
            f'{render_vibe_bar("💬", v["social"], VIBE_COLORS["social"])}</div>'
            f'</div>'
        )
    return f'<div class="roster-rail">{"".join(cards)}</div>'


def render_ticker(world_id):
    state = world_state.get_state(world_id)
    chaos = state["chaos"]
    filled = min(int(chaos * 5), 5)
    bar = "▰" * filled + "▱" * (5 - filled)
    unlocked = " 🔓" if chaos >= 0.5 else ""
    return (
        f'<div class="progress-ticker">'
        f'<span class="ticker-day">DAY {state["day"]}</span><span class="ticker-sep">·</span>'
        f'<span class="ticker-events">⚡ {state["event_count"]}</span><span class="ticker-sep">·</span>'
        f'<span class="ticker-chaos">CHAOS {bar}{unlocked}</span></div>'
    )


def render_mode_badge(status=None):
    status = status or agents.get_runtime_status()
    mode = status.get("mode")
    model = status.get("model") or "unknown"
    latency = status.get("latency")
    error = status.get("error")
    if mode == "live":
        label = f"🟢 Live · {model.split('/')[-1]}"
        if latency is not None:
            label += f" · {latency:.1f}s"
        cls = "mode-live"
    elif mode == "waking":
        label = f"🟡 Waking · {model.split('/')[-1]}"
        cls = "mode-waking"
    elif mode == "error":
        msg = f" · {error}" if error else ""
        label = f"🔴 LLM error{msg}"
        cls = "mode-error"
    else:
        label = "🟡 Offline demo (mock)"
        cls = "mode-mock"
    return f'<div class="mode-badge {cls}">{esc(label)}</div>'


def render_town_log(world_id, reactions=None, followup=None):
    world = get_world(world_id)
    if not reactions:
        return ('<div class="town-log-inner"><div class="town-log-empty">'
                'The town log is empty.<br>Throw an event to start the story.</div></div>')
    lines = []
    for r in reactions:
        char = next((c for c in world["cast"] if c["name"] == r["name"]), None)
        emoji = char.get("emoji", "👤") if char else "👤"
        name = esc(r["name"])
        text = esc(r["text"])
        mood = esc(r["mood"])
        lines.append(
            f'<div class="log-entry"><div class="log-head">'
            f'<span class="log-emoji">{emoji}</span><span class="log-name">{name}</span>'
            f'<span class="log-mood">{MOOD_EMOJI.get(r["mood"], "😐")}</span></div>'
            f'<div class="log-text" data-mood="{mood}">"{text}"</div></div>'
        )
    if followup:
        lines.append(f'<div class="log-entry log-followup"><div class="log-text">🔗 <em>{esc(followup["text"])}</em></div></div>')
    gossip_from = [r for r in reactions if random.random() < 0.3]
    if gossip_from:
        source = random.choice(gossip_from)
        others = [c["name"] for c in world["cast"] if c["name"] != source["name"]]
        if others:
            target = random.choice(others)
            snippet = source["text"][:60] + ("…" if len(source["text"]) > 60 else "")
            lines.append(f'<div class="log-entry log-gossip"><div class="log-text">🗣️ '
                         f'<em>Word spreads: {esc(target.split()[0])} hears "{esc(snippet)}"</em></div></div>')
            world_state.add_gossip(world_id, target, snippet)
    return f'<div class="town-log-inner">{"".join(lines)}</div>'


def render_explainer(world_id, reactions=None, focus=None):
    world = get_world(world_id)
    if not reactions:
        return ('<div class="explain-inner"><div class="explain-empty">'
                'Pick a <b>scenario</b> or throw an event, then this panel explains '
                '<b>why each person reacted the way they did</b> — great for teaching how '
                'different people respond to the same situation.</div></div>')
    parts = []
    if focus:
        parts.append(f'<div class="explain-focus">🎓 <b>Think about:</b> {esc(focus)}</div>')
    else:
        parts.append('<div class="explain-focus">🎓 <b>Why did they react this way?</b></div>')
    for r in reactions:
        c = next((x for x in world["cast"] if x["name"] == r["name"]), None)
        if not c:
            continue
        trait = (c.get("traits") or ["distinct"])[0]
        hint = c.get("catchphrase_hint", "responds in their own way")
        col = char_color(world, r["name"])
        understanding = esc((r.get("understanding") or "").strip())
        action = esc((r.get("action") or "").strip())
        first_name = esc(r["name"].split()[0])
        mood = esc(r["mood"])
        trait_text = esc(trait)
        if understanding or action:
            reason = (
                f'reads it as: <em>{understanding}</em> ' if understanding else ''
            ) + (
                f'so they <b>{action}</b>.' if action else ''
            )
            parts.append(
                f'<div class="explain-row"><b style="color:{col}">{first_name}</b> '
                f'(feeling <em>{mood}</em>, naturally <em>{trait_text}</em>) {reason}</div>'
            )
        else:
            parts.append(
                f'<div class="explain-row"><b style="color:{col}">{first_name}</b> '
                f'feels <em>{mood}</em> and is naturally <em>{trait_text}</em>, '
                f'so they {esc(hint)}.</div>'
            )
    return f'<div class="explain-inner">{"".join(parts)}</div>'


def scenario_choices(world_id):
    world = get_world(world_id)
    return [(s["title"], s["id"]) for s in world.get("scenarios", [])]


def render_stage_shell():
    return '<div class="stage" id="tw-stage"><canvas id="tw-canvas"></canvas><div class="stage-vignette"></div></div>'


# ---------------------------------------------------------------- assets
def _read(path):
    full = os.path.join(os.path.dirname(__file__), path)
    if os.path.exists(full):
        with open(full) as f:
            return f.read()
    return ""


css_content = _read("assets/style.css")
js_content = _read("assets/game.js")

DEFAULT_WORLD = os.environ.get("TW_DEFAULT_WORLD", "maple_street")
world_list = list_worlds()
world_names = {w["id"]: w["name"] for w in world_list}


# ---------------------------------------------------------------- UI
with gr.Blocks(title="TinyWorld — AI Neighborhood Game") as demo:
    current_world_id = gr.State(DEFAULT_WORLD)
    last_reactions_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=7):
            gr.HTML('<div class="tw-topbar"><div class="tw-logo">TINYWORLD</div>'
                    '<div class="tw-tagline">the town that remembers</div></div>')
        with gr.Column(scale=2, min_width=160):
            world_picker = gr.Dropdown(
                choices=[(world_names.get(w["id"], w["id"]), w["id"]) for w in world_list],
                value=DEFAULT_WORLD, label="World")
        with gr.Column(scale=3, min_width=210):
            ticker_html = gr.HTML(render_ticker(DEFAULT_WORLD))
        with gr.Column(scale=2, min_width=210):
            mode_badge_html = gr.HTML(render_mode_badge())

    # the canvas stage (rendered once, never re-rendered → game loop persists)
    gr.HTML(render_stage_shell())

    # hidden data channels for the canvas
    world_box = gr.Textbox(value=build_world_payload(DEFAULT_WORLD), elem_id="tw-world",
                           elem_classes="tw-data", label="", interactive=True)
    reactions_box = gr.Textbox(value="", elem_id="tw-reactions", elem_classes="tw-data",
                               label="", interactive=True)

    with gr.Row(elem_id="tw-console"):
        with gr.Column(scale=8):
            event_input = gr.Textbox(
                placeholder="Type an event to throw at the neighborhood…  (e.g. a UFO lands in the park)",
                label="", show_label=False, lines=1)
        with gr.Column(scale=2, min_width=150):
            trigger_btn = gr.Button("⚡ THROW", variant="primary", elem_id="throw-btn")

    with gr.Row(elem_id="tw-actions"):
        with gr.Column(scale=6, min_width=260):
            scenario_dd = gr.Dropdown(choices=scenario_choices(DEFAULT_WORLD), value=None,
                                      label="🎓 Teaching scenario — a real situation to explore")
        with gr.Column(scale=2, min_width=140):
            run_scenario_btn = gr.Button("🎓 Run Scenario")
        with gr.Column(scale=2, min_width=140):
            random_btn = gr.Button("🎲 Random Chaos")

    with gr.Row(equal_height=False):
        with gr.Column(scale=3, min_width=220):
            gr.HTML('<div class="panel-title">🧑‍🤝‍🧑 Townsfolk</div>')
            roster_html = gr.HTML(render_roster(DEFAULT_WORLD))
        with gr.Column(scale=4, min_width=240):
            gr.HTML('<div class="panel-title">📜 Town Log</div>')
            town_log_html = gr.HTML(render_town_log(DEFAULT_WORLD))
        with gr.Column(scale=4, min_width=240):
            gr.HTML('<div class="panel-title">🎓 Learn — Why did they react?</div>')
            explainer_html = gr.HTML(render_explainer(DEFAULT_WORLD))

    gr.HTML('<div class="panel-title" style="margin-top:6px">🔊 Voice</div>')
    with gr.Row(elem_id="tw-audio", equal_height=False):
        with gr.Column(scale=4, min_width=240):
            mic_input = gr.Audio(sources=["microphone"], type="filepath", label="🎙️ 1 · Record your event")
            transcribe_btn = gr.Button("📝 2 · Transcribe to text")
            mic_status = gr.HTML('<div class="audio-cap">Record → press <b>Transcribe</b>: your words fill the '
                                 'event box, then press <b>⚡ THROW</b>. <i>Mic only works on '
                                 'http://localhost:7860 (blocked on 0.0.0.0).</i></div>')
        with gr.Column(scale=4, min_width=240):
            voice_output = gr.Audio(label="🔊 Auto-voice (plays after each event)", autoplay=True)
            gr.HTML('<div class="audio-cap">The <b>most dramatic</b> reaction is read aloud automatically.</div>')
        with gr.Column(scale=4, min_width=240):
            hear_name = gr.Dropdown(choices=[], label="🎧 Replay a character's voice")
            hear_btn = gr.Button("▶ Play their last line")
            gr.HTML('<div class="audio-cap">Pick any character and hear their <b>last line</b> again.</div>')

    gr.HTML('<div class="tw-footer">Built for <strong>Build Small Hackathon 2026</strong> · '
            'Hugging Face × Gradio · Thousand Token Wood<br>'
            'Models: <strong>Nemotron-Mini-4B</strong> (NVIDIA) + <strong>VoxCPM2</strong> (OpenBMB) · '
            '<strong>Whisper on Modal</strong> speech-to-text, Cohere fallback · <strong>Modal</strong><br>'
            '<span class="footer-muted">Switch maps with the <b>World</b> picker, top-right · '
            'open at <b>http://localhost:7860</b> for microphone access.</span></div>')

    # ---------------------------------------------------------- handlers
    def _run_event(world_id, event_text, focus=None):
        world = get_world(world_id)
        world_state.init_cast(world)
        result = agents.react(world_id, event_text)
        reactions = result["reactions"]
        runtime = result.get("runtime") or agents.get_runtime_status()
        followup = agents.generate_followup(reactions, event_text)
        top = max(reactions, key=lambda r: r["drama"])
        audio = None
        try:
            cd = next(c for c in world["cast"] if c["name"] == top["name"])
            audio = voice.generate_voice(top["text"], cd["voice_description"])
        except Exception as e:
            print(f"[app] voice failed: {e}")
        names = [r["name"] for r in reactions]
        return (render_town_log(world_id, reactions, followup), render_roster(world_id),
                render_ticker(world_id), audio,
                gr.Dropdown(choices=names, value=names[0] if names else None),
                reactions, build_reactions_payload(world_id, reactions),
                render_explainer(world_id, reactions, focus), render_mode_badge(runtime))

    def do_trigger(event_text, world_id):
        if not event_text or not event_text.strip():
            return (render_town_log(world_id), render_roster(world_id), render_ticker(world_id),
                    None, gr.Dropdown(choices=[], value=None), [], "", render_explainer(world_id),
                    render_mode_badge())
        return _run_event(world_id, event_text.strip())

    def run_scenario(scenario_id, world_id):
        world = get_world(world_id)
        scen = next((s for s in world.get("scenarios", []) if s["id"] == scenario_id), None)
        if not scen:
            return (gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
        return (scen["event"],) + _run_event(world_id, scen["event"], scen.get("focus"))

    def random_chaos(world_id):
        world = get_world(world_id)
        if world and world.get("events"):
            return random.choice(world["events"])
        return events.random_event()

    def switch_world(world_id):
        world = get_world(world_id)
        if world:
            world_state.reset_world(world_id)
            world_state.init_cast(world)
        return (build_world_payload(world_id), "", render_town_log(world_id),
                render_roster(world_id), render_ticker(world_id),
                gr.Dropdown(choices=scenario_choices(world_id), value=None),
                render_explainer(world_id), world_id, render_mode_badge())

    def transcribe_audio(audio_path):
        if not audio_path:
            return ("", '<div class="audio-cap">⚠ No recording found — press the mic ● record button first. '
                    '<i>The mic only works on http://localhost:7860.</i></div>')
        text = transcribe.transcribe(audio_path)
        if not text:
            return ("", '<div class="audio-cap">⚠ Could not transcribe. Try again, or just type the event.</div>')
        return (text, f'<div class="audio-cap">✅ Heard: "<b>{esc(text)}</b>" — now press <b>⚡ THROW</b>.</div>')

    def hear_reaction(name, world_id, reactions):
        if not reactions or not name:
            return None
        rx = next((r for r in reactions if r["name"] == name), None)
        if not rx:
            return None
        world = get_world(world_id)
        try:
            cd = next(c for c in world["cast"] if c["name"] == name)
            return voice.generate_voice(rx["text"], cd["voice_description"])
        except Exception as e:
            print(f"[app] hear failed: {e}")
            return None

    trig_out = [town_log_html, roster_html, ticker_html, voice_output,
                hear_name, last_reactions_state, reactions_box, explainer_html, mode_badge_html]
    trigger_btn.click(do_trigger, [event_input, current_world_id], trig_out)
    event_input.submit(do_trigger, [event_input, current_world_id], trig_out)
    run_scenario_btn.click(run_scenario, [scenario_dd, current_world_id], [event_input] + trig_out)
    random_btn.click(random_chaos, [current_world_id], [event_input])
    transcribe_btn.click(transcribe_audio, [mic_input], [event_input, mic_status])
    hear_btn.click(hear_reaction, [hear_name, current_world_id, last_reactions_state], [voice_output])
    world_picker.change(switch_world, [world_picker],
                        [world_box, reactions_box, town_log_html, roster_html, ticker_html,
                         scenario_dd, explainer_html, current_world_id, mode_badge_html])


if __name__ == "__main__":
    port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    print("\n  TinyWorld is starting…")
    print(f"  ▶ Open  http://localhost:{port}   (use localhost, not 0.0.0.0, so the mic works)\n")
    demo.launch(server_name="0.0.0.0", server_port=port, css=css_content, js=js_content or None)
