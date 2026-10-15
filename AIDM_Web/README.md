# AIDM Web

English | [Russian](README.ru.md)

Browser version of [AI Dungeon Master](../README.md). The same worlds, story cards, memory bank and summarization, played in a browser. A phone on the same Wi-Fi, or on the same Tailscale network, can open the page.

The desktop program is described in the main README. This page is only about the web build.

## Release

1. In `AIDM_Web`, run `build_web.ps1`.
2. The script writes `App_web/` with `AIDM.exe` and a `worlds/` folder next to it.
3. Zip `App_web` and unpack that archive into any folder.
4. Run `AIDM.exe`.
5. Choose where the game should open: this computer, home Wi-Fi, or Tailscale.
6. Leave the console window open. Closing it stops the server.
7. Start the local model. By default the game expects [LM Studio](http://localhost:1234).

Campaigns created in the program are saved in `worlds` next to `AIDM.exe`. That folder travels with the zip. The build does not copy existing campaigns or API keys: `worlds/settings.json` in the archive is an empty template.

## From source

```text
cd AIDM_Web
pip install -r requirements.txt
python run_web.py
```

A source launch keeps worlds in `AIDM_Web/worlds`. Only the packaged exe keeps them beside the program.

## Network

The first window asks how to open the game. The choice is remembered.

| Choice | Who can open the page |
|--------|------------------------|
| This computer only | This PC, at `http://127.0.0.1:8765` |
| Home Wi-Fi | Devices on the same Wi-Fi. The window shows the address. |
| Tailscale | Devices on the same Tailscale network. Tailscale has to be running before you press Start. Shared Wi-Fi is not required. |

The server uses port **8765**. If a phone does not open the page, allow inbound TCP 8765 in Windows Firewall. The computer has to stay on.

## Playing

The page opens in the browser after you press Start.

- **Menu** opens worlds, world files, cards, memory, settings, the last prompt and the scene prompt.
- **Take a turn** shows the text field and Send. **What's next?** asks for a direction and continues the scene.
- **Undo**, **Reroll** and **Edit** work on the latest lines.
- The bar under the log shows how full the context is since the last summary.
- Worlds can be exported and imported as a zip of that world's files. Program settings are not included.

Story cards, the memory bank, summarization and the settings fields work as in the [desktop program](../README.md).
