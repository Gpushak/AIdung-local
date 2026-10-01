# 🐉 AI Dungeon Master

🇬🇧 English | [🇷🇺 Русский](README.ru.md)

(A hacked-together version of AI Dungeon designed to run with a local model)

A local Game Master for text-based role-playing games. The application works with any LLM through an OpenAI-compatible API (by default — [LM Studio](http://localhost:1234)).

If you play in Russian, I recommend using Gemma 4 models. They are excellent at writing in Russian and offer a good size-to-quality ratio. I mainly use the 31B or 26B A4B models.

## Features

- **Text RPG sessions** — describe your actions, and the AI responds as the Game Master
- **Worlds** — each world is stored in a separate folder with its settings, history, and memory
- **Story Cards** — notes with triggers; relevant cards are automatically included in the prompt
- **Memory Bank** — the AI indexes previous turns and retrieves relevant memories using keywords
- **Automatic Summarization** — periodically compresses the chronicle into `summary.txt`
- **Streaming Responses** — the Game Master's response appears as it is generated
- **Interrupting Generation** — stop the response, summary, or memory indexing at any time
- **Scene Image Prompts** — build an image prompt and negative prompt from the latest turns and story cards
- **Context Management** — token counting and history trimming to fit the model's context window

## Launch

1. Download the release and extract it into a separate folder.
2. Run the `.exe`.
3. Start your local model and local server.

## Window Placement

The main window opens centered on screen, and every dialog opens centered over it. If a window would
not fit (for example a 900×1200 window on a 1080p screen), it is shrunk to the available work area
instead of hanging off the top edge. A margin is reserved at the bottom for the Windows taskbar, so
windows never end up underneath it.

## Quick Start

1. On the first launch, create a world using the **➕** button or **🔄 Worlds → Create**.
2. Fill in the tabs: AI instructions, plot basics, author notes, and story cards (optional).
3. Fill in the introduction tab with a description of the situation where you want the story to begin.
4. Enter an action in the input field (or leave it empty) and press **▶ Send** (or Enter).
5. If necessary, open **⚙️ AI Settings** and adjust the temperature, context size, and intervals.

## Interface

### Top Bar

| Element | Purpose |
|---------|---------|
| World Selection | Switch between saved worlds |
| **📝 Summary: ON/OFF** | Enable/disable automatic summarization |
| **🧠 Memory: ON/OFF** | Enable/disable the memory bank |
| **📁 World Files** | Edit the world's text files |
| **📇 Cards** | Story card editor |
| **🔄 Worlds** | Create, load, and delete worlds |
| **⚙️ AI Settings** | Generation and feature settings |

### Action Bar

| Button | Purpose |
|--------|---------|
| **🔁 Reroll** | Regenerate the last Game Master response |
| **🧠 Memory** | View the memory bank, manually index memories |
| **📋 Prompt** | View the last prompt sent to the model |
| **✏️ Edit** | Manually edit the Game Master's response |
| **📝 Summarize** | Force an update of the summary |
| **🧠 Memory** | View the memory bank, manually index memories |
| **🎨 Scene Prompt** | Build an image prompt for the current scene |
| **⏪ Undo Turn** | Delete the last message |
| **❓ What's Next?** | Describe the events you want to happen next |

## Stopping Generation

While the AI is working, the **▶ Send** button turns into a red **⏹ Stop** button (or press **Esc**).
It interrupts whatever is running at the moment:

- **Reply generation** — the text received so far is kept and saved to the story, so you can edit it or use **⏪ Undo Turn**. Background summary and memory indexing are not started.
- **Summarization / memory indexing** — the operation is cancelled, `summary.txt` and `memory_bank.json` are left unchanged, and the task will be retried after the next few turns.
- **Scene Prompt** — the generation is cancelled and no dialog opens.

The window with the generated prompt is **not modal**: you can copy it, switch to your image generator
(Automatic1111, ComfyUI, Midjourney) and come back to the game without closing anything.

A thin bar under the chat log always shows how much of the context window the last prompt used. It turns
yellow near 70% and red past 90%, so you know when to run a summarization or start a new campaign.

## Scene Image Prompts

**🎨 Scene Prompt** builds a ready-to-use image prompt for the current scene. The context passed to the model contains:

- `plot_basics.txt` together with the AI instructions and author notes
- the **last 5 completed turns** — each Game Master reply together with the player's turn before it
- **relevant story cards** matched by keywords found in those turns, plus every card that has no triggers (always-active cards)

The model returns a single JSON object with a `prompt` and a `negative_prompt` field. Both are shown in a
window with separate copy buttons. Content restrictions are lifted: NSFW, violence and erotic elements are
allowed when they fit the scene.

If the model does not return valid JSON, the raw response is shown as the prompt.

### Prompt Formats

Different image models expect different markup, so the format is selected in **⚙️ AI Settings → Image prompt format**:

| Format | What the prompt looks like |
|--------|---------------------------|
| **Stable Diffusion** (default) | comma-separated booru-style tags, weights as `(tag:1.2)`, quality tags appended |
| **Midjourney** | one English paragraph plus `--ar 16:9 --style raw --v 7` |
| **Flux** | 2–4 English sentences, no weights and no quality tags |
| **Generic** | 2–4 English sentences, no weights |

The setting is stored in `worlds/settings.json` as `image_prompt_style` (`sd`, `midjourney`, `flux`, `generic`).
The chosen format is shown above the prompt in the result window.

## World Structure

Each world is a folder inside the `worlds/` directory:

```text
worlds/
├── settings.json              # Global application settings
└── World Name/
    ├── ai_instructions.txt    # System instructions for the Game Master
    ├── plot_basics.txt        # Setting and initial plot
    ├── author_notes.txt       # Style, tone, and author's preferences
    ├── summary.txt            # Compressed chronicle (updated automatically)
    ├── story_cards.json       # Story cards
    ├── memory_bank.json       # Memory bank
    └── history.json           # Current session history
```

### Safe saving

Every file is written atomically: the data goes to a temporary file, is flushed to disk, the previous
version is copied to `<file>.bak`, and only then the temporary file is renamed into place. A crash or a
full disk during saving therefore cannot leave a truncated file.

If a file turns out to be unreadable at startup, the app tries `<file>.bak` first. When even the backup
is broken, **the world is not loaded and an error is shown** — a corrupted `history.json` never silently
becomes an empty campaign. Bank of memory and story cards degrade to defaults instead, because they can
be regenerated.

## Story Cards

Story Cards replace the old `characters.txt` file. Each card contains:

- **Title** — a heading (character, location, faction, etc.)
- **Description** — detailed information for the AI
- **Triggers** — comma-separated keywords

On each turn, cards whose triggers match the player's input and recent history are included in the prompt. **Empty triggers** mean that the card is always active.

Example `story_cards.json`:

```json
{
  "cards": [
    {
      "id": "card_001",
      "title": "Arion",
      "description": "Arion is an adventurer and warrior. He wears leather armor...",
      "triggers": ["arion", "hero", "warrior"]
    },
    {
      "id": "card_002",
      "title": "The Drunken Dragon Tavern",
      "description": "A noisy establishment on the outskirts of the city...",
      "triggers": ["tavern", "dragon", "bartender"]
    }
  ]
}
```

## Memory Bank

Every N turns (5 by default), the AI analyzes a new fragment of the session and saves an entry containing:

- a brief description of events;
- keywords;
- the location and mentioned NPCs.

During subsequent turns, relevant memories are added to the prompt. This helps preserve details during long campaigns.

## Summarization

Every N turns (10 by default), the AI updates `summary.txt` — a compressed chronicle of the entire story. The file takes the previous summary into account, so important facts are preserved even when recent history is trimmed due to the context limit.

Automatic summarization and the memory bank can be disabled using the buttons in the top bar or in the settings. The manual **📝 Summarize** and **🧠 Memory** buttons work independently of the automatic features.

## AI Settings

Global parameters are stored in `worlds/settings.json`. You can change them either by editing the file or through the application:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `temperature` | `0.7` | Response creativity |
| `max_tokens` | `300` | Maximum number of tokens in a response |
| `context_size` | `16384` | Model context window size |
| `summary_interval` | `10` | Automatically summarize every N turns |
| `memory_interval` | `5` | Index memories every N turns |
| `memory_top_k` | `5` | Number of memories/cards to include in the prompt |
| `image_prompt_style` | `sd` | Image prompt format: `sd`, `midjourney`, `flux`, `generic` |
| `stream_mode` | `true` | Show the reply as it is generated |
| `summary_enabled` | `true` | Enable/disable automatic summarization |
| `memory_enabled` | `true` | Enable/disable the memory bank |

## Tips

- For long campaigns, keep summarization and the memory bank enabled.
- Put locations, characters, and other elements you want to exist in the world into Story Cards.
- Use **📋 Prompt** to see exactly what the model receives on each turn.

## License / Usage

This project is intended for personal use.
