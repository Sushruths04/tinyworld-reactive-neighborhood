import os
import random
import gradio as gr
import agents
import voice
import transcribe
import events
import characters as chars
from unpredictability import get_mood, reroll_mood, maybe_form_reflection

MOCK = os.environ.get("TINYWORLD_MOCK", "0") == "1"

MOOD_ENERGY = {
    "happy": 80, "excited": 90, "proud": 75, "curious": 70,
    "stressed": 40, "bored": 30, "tired": 20, "hungry": 45,
    "nostalgic": 55, "embarrassed": 50,
}
MOOD_SOCIAL = {
    "happy": 85, "excited": 80, "curious": 75, "proud": 60,
    "nostalgic": 65, "stressed": 35, "bored": 25, "tired": 30,
    "hungry": 40, "embarrassed": 45,
}

_vibes = {c["name"]: {"energy": 60, "social": 60} for c in chars.CHARACTERS}
_event_count = 0
_chaos_level = 0

EMOJI = {
    "Marta Voss": "🧓",
    "Jay Park": "🚴",
    "Nia Okafor": "🚑",
    "Luca Bell": "🧒",
    "Priya Raman": "👩‍💼",
}

HOME = {
    "Marta Voss": (1, 1),
    "Jay Park": (3, 9),
    "Nia Okafor": (5, 2),
    "Luca Bell": (2, 6),
    "Priya Raman": (6, 7),
}

TILES = [
    ["sky","sky","sky","sky","sky","sky","sky","sky","sky","sky","sky","sky"],
    ["grass","house","grass","road","grass","grass","tree","grass","grass","road","grass","grass"],
    ["grass","grass","grass","road","grass","park","park","grass","grass","road","grass","tree"],
    ["road","road","road","road","road","road","road","road","road","road","road","road"],
    ["grass","tree","grass","road","grass","grass","house","grass","grass","road","grass","grass"],
    ["grass","house","grass","road","grass","grass","grass","grass","grass","road","grass","tree"],
    ["road","road","road","road","road","road","road","road","road","road","road","road"],
    ["grass","grass","grass","grass","grass","grass","grass","tree","grass","grass","grass","grass"],
]

TILE_COLORS = {
    "sky": "#87ceeb",
    "grass": "#5a8a3c",
    "road": "#6f7790",
    "house": "#c45b5b",
    "park": "#7CFFB2",
    "tree": "#2f7d46",
}

TILE_ICONS = {
    "sky": "",
    "grass": "",
    "road": "",
    "house": "🏠",
    "park": "🌿",
    "tree": "🌲",
}

MOOD_EMOJI = {
    "happy": "😊",
    "stressed": "😰",
    "bored": "😐",
    "excited": "🤩",
    "hungry": "🍕",
    "tired": "😴",
    "nostalgic": "🥹",
    "curious": "🧐",
    "proud": "😤",
    "embarrassed": "🫣",
}

VIBE_COLORS = {
    "energy": ("#ff6b6b", "#ff9999"),
    "social": ("#38e8ff", "#9b6bff"),
}


def render_vibe_bar(label, value, colors):
    c1, c2 = colors
    return (
        f'<div class="vibe-row">'
        f'<span class="vibe-label">{label}</span>'
        f'<div class="vibe-track">'
        f'<div class="vibe-fill" style="width:{value}%;background:linear-gradient(90deg,{c1},{c2})"></div>'
        f'</div>'
        f'<span class="vibe-val">{value}</span>'
        f'</div>'
    )


def render_roster():
    cards = []
    for c in chars.CHARACTERS:
        name = c["name"]
        mood = get_mood(name)
        mood_e = MOOD_EMOJI.get(mood, "😐")
        char_e = EMOJI.get(name, "👤")
        v = _vibes[name]
        energy_bar = render_vibe_bar("⚡", v["energy"], VIBE_COLORS["energy"])
        social_bar = render_vibe_bar("💬", v["social"], VIBE_COLORS["social"])
        cards.append(
            f'<div class="roster-card">'
            f'<div class="roster-emoji">{char_e}</div>'
            f'<div class="roster-name">{name.split()[0]}</div>'
            f'<div class="roster-mood">{mood_e} {mood}</div>'
            f'{energy_bar}{social_bar}'
            f'</div>'
        )
    return f'<div class="roster-rail">{"".join(cards)}</div>'


def render_chaos_meter():
    global _event_count, _chaos_level
    filled = min(_chaos_level, 5)
    empty = 5 - filled
    bar = "█" * filled + "▯" * empty
    unlocked = " 🔓 CHAOS UNLOCKED!" if _chaos_level >= 5 else ""
    return (
        f'<div class="progress-ticker">'
        f'<span class="ticker-day">Day {(_event_count // 5) + 1}</span>'
        f'<span class="ticker-sep">·</span>'
        f'<span class="ticker-events">{_event_count} events</span>'
        f'<span class="ticker-sep">·</span>'
        f'<span class="ticker-chaos">Chaos {bar}</span>'
        f'{unlocked}'
        f'</div>'
    )


def render_recap(last_reactions, event_text):
    if not last_reactions:
        return '<div class="recap-card"><div class="recap-title">📸 TODAY IN TINYWORLD</div><div class="recap-empty">Throw an event to create a recap!</div></div>'
    top3 = sorted(last_reactions, key=lambda r: r["drama"], reverse=True)[:3]
    lines = []
    for r in top3:
        emoji = EMOJI.get(r["name"], "👤")
        mood_e = MOOD_EMOJI.get(r["mood"], "😐")
        lines.append(
            f'<div class="recap-row">'
            f'<span class="recap-emoji">{emoji}</span>'
            f'<span class="recap-name">{r["name"]}</span>'
            f'<span class="recap-mood">{mood_e}</span>'
            f'<div class="recap-text">"{r["text"][:100]}"</div>'
            f'</div>'
        )
    event_short = event_text[:60] + ("..." if len(event_text) > 60 else "")
    return (
        f'<div class="recap-card">'
        f'<div class="recap-title">📸 TODAY IN TINYWORLD</div>'
        f'<div class="recap-event">Event: "{event_short}"</div>'
        f'{"".join(lines)}'
        f'<div class="recap-footer">TinyWorld · Build Small Hackathon 2026</div>'
        f'</div>'
    )


def render_map(reactions=None):
    reactions_by_name = {}
    if reactions:
        for r in reactions:
            reactions_by_name[r["name"]] = r

    tiles_html = ""
    for row_idx, row in enumerate(TILES):
        for col_idx, tile in enumerate(row):
            color = TILE_COLORS.get(tile, "#5a8a3c")
            icon = TILE_ICONS.get(tile, "")

            char_name = None
            for name, (r, c) in HOME.items():
                if r == row_idx and c == col_idx:
                    char_name = name
                    break

            content = ""
            if char_name:
                mood = get_mood(char_name)
                mood_emoji = MOOD_EMOJI.get(mood, "😐")
                char_emoji = EMOJI.get(char_name, "👤")
                content = f'<div class="char-mood" title="{mood}">{mood_emoji}</div><div class="char-emoji">{char_emoji}</div>'

                if char_name in reactions_by_name:
                    rx = reactions_by_name[char_name]
                    bubble_text = rx["text"][:120] + ("..." if len(rx["text"]) > 120 else "")
                    content += f'<div class="speech-bubble">{bubble_text}</div>'
            elif icon:
                content = f'<div class="tile-icon">{icon}</div>'

            tiles_html += f'<div class="tile" style="background-color:{color}">{content}</div>'

    idle_class = "visible" if not reactions else ""
    return f'<div class="tw-map">{tiles_html}</div><div class="idle-overlay {idle_class}"><div class="idle-text">The neighborhood is quiet...<br>throw an event to see what happens!</div></div>'


def render_initial_map():
    return render_map(None)


def trigger_event(event_text):
    if not event_text or not event_text.strip():
        return render_map(None), "", None, gr.update()

    reactions = agents.react(event_text.strip())

    top = max(reactions, key=lambda r: r["drama"])
    audio = None
    try:
        char_data = next(c for c in chars.CHARACTERS if c["name"] == top["name"])
        audio = voice.generate_voice(top["text"], char_data["voice_description"])
    except Exception as e:
        print(f"[app] voice generation failed: {e}")

    feed_lines = []
    for r in reactions:
        emoji = EMOJI.get(r["name"], "👤")
        mood_e = MOOD_EMOJI.get(r["mood"], "😐")
        feed_lines.append(f'{emoji} **{r["name"]}** ({mood_e} {r["mood"]}): "{r["text"]}"')
    feed_text = "\n\n".join(feed_lines)

    names = [r["name"] for r in reactions]

    return (
        render_map(reactions),
        feed_text,
        audio,
        gr.update(choices=names, value=names[0] if names else None),
    )


def random_chaos():
    return events.random_event()


def transcribe_audio(audio_path):
    if not audio_path:
        return ""
    return transcribe.transcribe(audio_path)


def hear_reaction(name, event_text_state, last_reactions_state):
    if not last_reactions_state or not name:
        return None

    rx = next((r for r in last_reactions_state if r["name"] == name), None)
    if not rx:
        return None

    try:
        char_data = next(c for c in chars.CHARACTERS if c["name"] == name)
        return voice.generate_voice(rx["text"], char_data["voice_description"])
    except Exception as e:
        print(f"[app] hear_reaction failed: {e}")
        return None


css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
css_content = ""
if os.path.exists(css_path):
    with open(css_path) as f:
        css_content = f.read()

js_path = os.path.join(os.path.dirname(__file__), "assets", "map.js")
js_content = ""
if os.path.exists(js_path):
    with open(js_path) as f:
        js_content = f.read()

with gr.Blocks(
    title="TinyWorld — AI Neighborhood Game",
) as demo:
    last_reactions_state = gr.State([])
    event_text_state = gr.State("")

    gr.HTML("""
    <div class="tw-header">
        <div class="tw-logo">🏘️ TINYWORLD</div>
        <div class="tw-tagline">Throw an event. Watch the neighborhood react.</div>
        <div class="tw-credits">Models: MiniCPM5-1B (×5 characters) · VoxCPM2 (voices) · Cohere Transcribe · Powered by Modal</div>
    </div>
    """)

    roster_html = gr.HTML(render_roster())
    chaos_meter_html = gr.HTML(render_chaos_meter())

    with gr.Row(equal_height=False):
        with gr.Column(scale=65):
            gr.HTML('<div class="glass-panel map-panel"><div class="panel-title">🏘️ THE NEIGHBORHOOD</div>')
            map_html = gr.HTML(render_initial_map())
            gr.HTML("</div>")

        with gr.Column(scale=35):
            gr.HTML('<div class="glass-panel feed-panel"><div class="panel-title">📜 NEIGHBORHOOD FEED</div>')
            feed_output = gr.Markdown(
                value="*The neighborhood is quiet... throw an event to see what happens!*",
                elem_id="feed",
            )
            gr.HTML("</div>")

    gr.HTML('<div class="glass-panel event-panel">')
    with gr.Row():
        event_input = gr.Textbox(
            placeholder="Throw an event at the neighborhood…",
            label="",
            scale=5,
            show_label=False,
        )
        mic_input = gr.Audio(
            sources=["microphone"],
            type="filepath",
            label="🎤",
            scale=2,
        )
    with gr.Row():
        trigger_btn = gr.Button("⚡ Trigger", variant="primary", scale=3)
        random_btn = gr.Button("🎲 Random Chaos", scale=2)
        transcribe_btn = gr.Button("🎙️ Transcribe Mic", scale=2)
    gr.HTML("</div>")

    gr.HTML('<div class="glass-panel voice-panel">')
    with gr.Row():
        voice_output = gr.Audio(label="🔊 Auto-play (most dramatic)", autoplay=True)
    with gr.Row():
        hear_name = gr.Dropdown(choices=[], label="Choose character", scale=3)
        hear_btn = gr.Button("🔊 Hear this one", scale=2)
    gr.HTML("</div>")

    recap_html = gr.HTML(render_recap([], ""))

    gr.HTML("""
    <div class="tw-footer">
        Built for <strong>Build Small Hackathon 2026</strong> · Hugging Face × Gradio · Thousand Token Wood track<br>
        Sponsor models: <strong>OpenBMB</strong> (MiniCPM5-1B, VoxCPM2) · <strong>Cohere</strong> (Transcribe) · <strong>Modal</strong> (serverless inference)
    </div>
    """)

    def do_trigger(event_text):
        global _event_count, _chaos_level
        if not event_text or not event_text.strip():
            return render_map(None), "", None, gr.Dropdown(choices=[], value=None), event_text, [], render_roster(), render_chaos_meter(), render_recap([], "")

        _event_count += 1
        _chaos_level = min(_chaos_level + 1, 7)

        reactions = agents.react(event_text.strip())

        # Smallville-lite: form reflections every ~5 events
        for c in chars.CHARACTERS:
            maybe_form_reflection(c["name"])

        # Vibe drift: nudge each character's vibes based on their mood
        for r in reactions:
            name = r["name"]
            mood = r["mood"]
            base_e = MOOD_ENERGY.get(mood, 50)
            base_s = MOOD_SOCIAL.get(mood, 50)
            _vibes[name]["energy"] = max(0, min(100, _vibes[name]["energy"] * 0.6 + base_e * 0.4 + random.randint(-5, 5)))
            _vibes[name]["social"] = max(0, min(100, _vibes[name]["social"] * 0.6 + base_s * 0.4 + random.randint(-5, 5)))

        # Consequence chain
        followup = agents.generate_followup(reactions, event_text.strip())

        top = max(reactions, key=lambda r: r["drama"])
        audio = None
        try:
            char_data = next(c for c in chars.CHARACTERS if c["name"] == top["name"])
            audio = voice.generate_voice(top["text"], char_data["voice_description"])
        except Exception as e:
            print(f"[app] voice generation failed: {e}")

        feed_lines = []
        for r in reactions:
            emoji = EMOJI.get(r["name"], "👤")
            mood_e = MOOD_EMOJI.get(r["mood"], "😐")
            feed_lines.append(f'{emoji} **{r["name"]}** ({mood_e} {r["mood"]}): "{r["text"]}"')
        if followup:
            feed_lines.append(f'\n*🔗 {followup["text"]}*')
        feed_text = "\n\n".join(feed_lines)

        names = [r["name"] for r in reactions]

        return (
            render_map(reactions),
            feed_text,
            audio,
            gr.Dropdown(choices=names, value=names[0] if names else None),
            event_text,
            reactions,
            render_roster(),
            render_chaos_meter(),
            render_recap(reactions, event_text.strip()),
        )

    trigger_btn.click(
        fn=do_trigger,
        inputs=[event_input],
        outputs=[map_html, feed_output, voice_output, hear_name, event_text_state, last_reactions_state, roster_html, chaos_meter_html, recap_html],
    )

    random_btn.click(fn=random_chaos, outputs=[event_input])

    transcribe_btn.click(
        fn=transcribe_audio,
        inputs=[mic_input],
        outputs=[event_input],
    )

    hear_btn.click(
        fn=hear_reaction,
        inputs=[hear_name, event_text_state, last_reactions_state],
        outputs=[voice_output],
    )

    demo.load(fn=render_initial_map, outputs=[map_html])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, css=css_content, js=js_content if js_content else None)
