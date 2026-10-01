PLAYER_PREFIX = "Игрок:"
DM_PREFIX = "Мастер:"
INTRO_PREFIX = "Вступление:"

TRANSLATIONS = {
    "ru": {
        "lang.ru": "Русский",
        "lang.en": "English",
        "window_title": "🐉 AI Dungeon Master",
        "app_title": "🐉 AI DUNGEON MASTER 🐉",
        "no_worlds": "Нет миров",
        "ready": "● Готов",
        "summary_until": "До суммаризации: -",
        "memory_until": "До памяти: -",
        "btn.world_files": "📁 Файлы мира",
        "btn.cards": "📇 Карточки",
        "btn.worlds": "🔄 Миры",
        "btn.ai_settings": "⚙️ Настройки ИИ",
        "btn.quit": "❌ Выйти",
        "btn.next": "❓ Дальше?",
        "btn.reroll": "🔁 Реролл",
        "btn.edit_last": "✏️ Редактировать",
        "btn.prompt": "📋 Промпт",
        "btn.scene_prompt": "🎨 Промпт сцены",
        "btn.summary": "📝 Суммаризация",
        "btn.memory": "🧠 Память",
        "btn.undo": "⏪ Отменить ход",
        "btn.send": "▶ Отправить",
        "btn.create": "Создать",
        "btn.create_ok": "✅ Создать",
        "btn.cancel": "❌ Отмена",
        "btn.cancel_plain": "Отмена",
        "btn.close": "Закрыть",
        "btn.close_x": "❌ Закрыть",
        "btn.save": "💾 Сохранить",
        "btn.save_ok": "✅ Сохранить",
        "btn.save_as": "💾 Сохранить как...",
        "btn.delete": "Удалить",
        "btn.delete_icon": "🗑 Удалить",
        "btn.load": "Загрузить",
        "btn.add": "➕ Добавить",
        "btn.copy": "📋 Копировать",
        "btn.index_now": "🔄 Индексировать сейчас",
        "toggle.summary_on": "📝 Сумм.: ВКЛ",
        "toggle.summary_off": "📝 Сумм.: ВЫКЛ",
        "toggle.memory_on": "🧠 Память: ВКЛ",
        "toggle.memory_off": "🧠 Память: ВЫКЛ",
        "summary.off": "Сумм.: выкл",
        "summary.until": "До сумм.: {n}",
        "memory.off": "Память: {n} | выкл",
        "memory.until": "Память: {n} | до инд.: {remaining}",
        "context.usage": "Контекст: {used} / {total}",
        "btn.stop": "⏹ Стоп",
        "status.generating": "● Генерация...",
        "status.scene_prompt": "● Промпт сцены...",
        "status.summary_memory": "● Суммаризация и память...",
        "status.summary": "● Суммаризация...",
        "status.memory": "● Индексация памяти...",
        "menu.select_all": "Выделить всё",
        "menu.copy": "Копировать",
        "menu.paste": "Вставить",
        "menu.cut": "Вырезать",
        "dialog.manage_worlds": "🔄 Управление мирами",
        "dialog.your_worlds": "Ваши миры:",
        "dialog.delete_world": "Удалить мир",
        "dialog.delete_world_q": "Удалить мир '{name}' безвозвратно?",
        "dialog.create_world": "🔄 Создать новый мир",
        "dialog.world_name": "Название мира (папка):",
        "dialog.default_world_name": "Новый мир",
        "dialog.bad_name": "Ошибка",
        "dialog.bad_name_msg": "Некорректное или занятое имя",
        "dialog.world_files": "📁 Файлы мира",
        "dialog.choose_file": "Выберите файл:",
        "dialog.unsaved": "● Есть несохранённые изменения",
        "dialog.attention": "Внимание",
        "dialog.file_unsaved": "В файле «{label}» есть изменения. Сохранить?",
        "dialog.close_unsaved": "Есть несохранённые изменения. Сохранить перед закрытием?",
        "dialog.cards_title": "📇 Карточки историй",
        "dialog.cards_need_world": "Сначала выберите или создайте мир.",
        "dialog.next_title": "❓ Дальше?",
        "dialog.next_hint": "Опишите, что должно произойти в следующем ходу.\nИИ реализует это в повествовании.",
        "dialog.empty_input": "Пустой ввод",
        "dialog.empty_next": "Опишите, что должно произойти дальше.",
        "dialog.ai_settings": "⚙️ Настройки ИИ",
        "dialog.api_config": "Конфигурация API",
        "dialog.manual_preset": "— Вручную —",
        "dialog.save_preset": "Сохранить конфигурацию",
        "dialog.preset_name": "Название конфигурации:",
        "dialog.delete_preset_info": "Удаление",
        "dialog.delete_preset_pick": "Выберите сохранённую конфигурацию для удаления.",
        "dialog.delete_preset": "Удалить конфигурацию",
        "dialog.delete_preset_q": "Удалить конфигурацию «{name}»?",
        "dialog.api_url": "URL API (Chat Completions):",
        "dialog.api_key": "API-ключ (необязательно):",
        "dialog.show_key": "Показать ключ",
        "dialog.model": "Модель (необязательно):",
        "dialog.gen_params": "Параметры генерации",
        "dialog.stream": "Показывать ответ по мере генерации",
        "dialog.auto_summary": "Автосуммаризация",
        "dialog.memory_bank": "Банк памяти",
        "dialog.temperature": "Температура (0.0 - 2.0):",
        "dialog.max_tokens": "Макс. токенов в ответе:",
        "dialog.context_size": "Размер контекста:",
        "dialog.summary_every": "Суммаризация (каждые N ходов):",
        "dialog.memory_every": "Банк памяти (индексация каждые N ходов):",
        "dialog.memory_top_k": "Макс. воспоминаний в промпте:",
        "dialog.image_style": "Формат промпта для изображений:",
        "image_style.sd": "Stable Diffusion (теги, веса)",
        "image_style.midjourney": "Midjourney (--параметры)",
        "image_style.flux": "Flux (естественный текст)",
        "image_style.generic": "Универсальный (текст)",
        "dialog.language": "Язык интерфейса:",
        "dialog.quit": "Выход",
        "dialog.quit_q": "Действительно выйти из игры?",
        "dialog.edit_dm": "✏️ Редактировать ответ",
        "dialog.edit_dm_label": "Редактирование ответа:",
        "dialog.edit_player": "✏️ Редактировать ход",
        "dialog.edit_player_label": "Редактирование вашего действия:",
        "dialog.edit_prev": "◀ Пред.",
        "dialog.edit_next": "След. ▶",
        "dialog.prompt_title": "📋 Последний промпт",
        "dialog.no_prompt": "Нет данных о запросе.",
        "dialog.prompt_time": "=== ВРЕМЯ ЗАПРОСА ===\n{time}\n\n=== ПРИМЕРНОЕ КОЛ-ВО ТОКЕНОВ ===\n{tokens}\n\n",
        "dialog.prompt_body": "=== SYSTEM ===\n{system}\n\n=== USER ===\n{user}\n",
        "dialog.memory_title": "🧠 Банк памяти",
        "dialog.no_world": "Мир не выбран.",
        "dialog.memory_empty": "Банк памяти пуст. Записи появятся после нескольких ходов.",
        "dialog.memory_stats": "Записей: {n} | Проиндексировано ходов: {turns}",
        "dialog.memory_entry": "=== {id} | ходы {start}-{end} ===\nКлючи: {keys}\nNPC: {npcs} | Локация: {location}\n{summary}\n",
        "dialog.no_worlds_title": "Нет миров",
        "dialog.no_worlds_q": "У вас нет ни одного мира. Создать новый?",
        "cards.list": "Карточки:",
        "cards.search": "Поиск карточек...",
        "cards.title": "Название:",
        "cards.desc": "Описание:",
        "cards.triggers": "Триггеры (через запятую — ключевые слова для подтягивания карточки):",
        "cards.triggers_ph": "арион, таверна, меч",
        "cards.empty_triggers": "Пустые триггеры = карточка всегда активна в промпте",
        "cards.untitled": "Без названия",
        "cards.new": "Новая карточка",
        "cards.delete": "Удалить",
        "cards.delete_q": "Удалить выбранную карточку?",
        "cards.save_with_world": "Сохранятся вместе с миром",
        "cards.generate_desc": "✨ Сгенерировать описание",
        "cards.generating": "Генерация описания...",
        "cards.generate_desc_title": "Генерация описания карточки",
        "cards.enter_title_first": "Сначала введите название карточки",
        "scene.prompt_label": "Промпт",
        "scene.negative_label": "Антипромпт",
        "scene.copy_prompt": "📋 Копировать промпт",
        "scene.copy_negative": "📋 Копировать антипромпт",
        "scene.copied_prompt": "🎨 Промпт сцены скопирован.",
        "scene.copied_negative": "🎨 Антипромпт скопирован.",
        "scene.generating": "Создание промпта...",
        "scene.stop": "⏹ Стоп",
        "scene.needs_world": "Сначала загрузите мир.",
        "scene.needs_history": "Нужна хотя бы одна реплика мастера в истории.",
        "dialog.corrupt_title": "Повреждённые данные",
        "dialog.corrupt_history": "Мир «{name}» не загружен: файл {file} повреждён и не читается даже из резервной копии.\n\nИстория не изменена — её можно починить вручную.\nПодробности: {detail}\n\nРезервная копия лежит рядом: {file}.bak",
        "on": "ВКЛ",
        "off": "ВЫКЛ",
        "summary_enabled_word": "включена",
        "summary_disabled_word": "выключена",
        "memory_enabled_word": "включён",
        "memory_disabled_word": "выключён",
        "msg.cards_saved": "✅ Карточки историй сохранены",
        "msg.file_saved": "✅ Файл {name} сохранён",
        "msg.preset_saved": "💾 Конфигурация API «{name}» сохранена.",
        "msg.settings_saved": "⚙️ Настройки сохранены. API: {api}{model}{preset}. Стриминг: {stream}. Суммаризация: {summary}. Память: {memory}.",
        "msg.model_part": ", модель: {model}",
        "msg.preset_part": ", конфиг: {name}",
        "msg.dm_edited": "📝 Ответ Мастера изменен.",
        "msg.player_edited": "📝 Ваш ход изменен.",
        "msg.force_summary": "📝 Принудительное обновление краткого содержания...",
        "msg.prompt_copied": "📋 Промпт скопирован.",
        "msg.force_memory": "🧠 Принудительная индексация памяти...",
        "msg.summary_toggled": "📝 Автосуммаризация {state}.",
        "msg.memory_toggled": "🧠 Банк памяти {state}.",
        "msg.welcome": "Добро пожаловать! Создайте новый мир через кнопку «🔄 Миры».",
        "msg.world_loaded": "✅ Мир '{name}' загружен.",
        "msg.undone": "⏪ Последнее сообщение удалено.",
        "msg.no_memory_turns": "🧠 Нет новых ходов для индексации.",
        "msg.memory_entry": "🧠 Память [{id}]: {summary}... (ключи: {keys})",
        "msg.memory_offline": "❌ Банк памяти: сервер ИИ недоступен.",
        "msg.memory_error": "⚠️ Ошибка индексации памяти: {msg}",
        "msg.empty_model": "⚠️ Модель вернула пустой ответ.",
        "msg.tokens": "📊 Токены: Контекст: {p} | Ответ: {c} | Всего: {t}/{ctx}",
        "msg.reviewing": "📝 ИИ пересматривает хронологию...",
        "msg.no_server": "❌ Ошибка: Локальный сервер ИИ не запущен!",
        "msg.error": "❌ Ошибка: {msg}",
        "msg.summary_ok": "✨ Краткое содержание мира успешно синхронизировано!",
        "msg.summary_fail": "⚠️ Не удалось автоматически обновить саммари: {msg}",
        "msg.history_restored": "♻️ История восстановлена из резервной копии (файл был повреждён).",
        "msg.stop_requested": "⏹ Останавливаю генерацию...",
        "msg.scene_prompt_done": "🎨 Промпт сцены готов.",
        "msg.scene_prompt_fail": "⚠️ Не удалось создать промпт сцены: {msg}",
        "msg.action_stopped": "⏹ Генерация остановлена. Ответ сохранён частично — его можно отредактировать или удалить.",
        "msg.summary_stopped": "⏹ Суммаризация остановлена.",
        "msg.memory_stopped": "⏹ Индексация памяти остановлена.",
        "msg.language_changed": "🌐 Язык интерфейса: {lang_name}",
        "world_file.introduction.txt": "Вступление",
        "world_file.ai_instructions.txt": "Инструкции ИИ",
        "world_file.plot_basics.txt": "Основы сюжета",
        "world_file.author_notes.txt": "Авторские пометки",
        "world_file.summary.txt": "Краткое содержание",
        "world_file.story_cards": "Карточки историй",
        "hist.player": "Игрок:",
        "hist.dm": "Мастер:",
        "hist.intro": "Вступление:",
        "prompt.continue": "(Продолжай повествование.)",
        "prompt.direction": "Автор задаёт направление следующего хода:\n{hint}\n\nРеализуй это в повествовании органично, сохраняя стиль, контекст и правила мира. Не упоминай, что это «задание от автора» — просто развивай сюжет.",
        "prompt.no_reasoning": "ВАЖНО: Отвечай сразу, без размышлений, анализа или внутренних монологов. Не используй теги <think>, <thinking>, <reasoning> или подобные. Начинай ответ сразу с повествования.",
        "prompt.summary_header": "=== Сжатая хроника прошлых событий (summary.txt) ===\n{text}\n",
        "prompt.history_header": "ИСТОРИЯ ТЕКУЩЕЙ ИГРОВОЙ СЕССИИ:",
        "prompt.memory_header": "=== РЕЛЕВАНТНЫЕ ВОСПОМИНАНИЯ (банк памяти) ===\n",
        "prompt.cards_header": "=== РЕЛЕВАНТНЫЕ КАРТОЧКИ ИСТОРИИ ===\n",
        "prompt.card_triggers": " (триггеры: {triggers})",
        "prompt.card_always": " (всегда активна)",
        "prompt.cards_missing": "Информация отсутствует.",
        "prompt.none": "Отсутствует.",
        "prompt.memory_index": """Проанализируй фрагмент текстовой RPG-сессии.
Сделай:
1. summary — 2-4 предложения, только ключевые события и факты (имена, предметы, решения)
2. keys — до 3 ключевых СЛОВ (не словосочетаний) для поиска, только самые важные! (имена NPC, локации, предметы, события)
3. location — текущая локация или null
4. npcs — список упомянутых NPC

ФРАГМЕНТ:
{fragment}

Ответь ТОЛЬКО валидным JSON:
{{"summary": "...", "keys": ["...", "..."], "location": "...", "npcs": ["..."]}}""",
        "prompt.summary": """Перед тобой история текстовой ролевой игры и её старое содержание.
Твоя задача: составить обновленное, чистое и емкое КРАТКОЕ СОДЕРЖАНИЕ (summary).
ПРАВИЛА:
1. Сформируй краткую историю в хронологическом порядке.
2. Игнорируй мелкую рутину.
3. Пиши лаконично, тезисно.
4. Учти СТАРОЕ краткое содержание.

СТАРОЕ КРАТКОЕ СОДЕРЖАНИЕ:
{old_summary}

АКТУАЛЬНАЯ ИСТОРИЯ ИГРЫ:
{history}

Выдай только текст нового краткого содержания простым текстом без лишних *, вступлений и Markdown.""",
        "prompt.card_desc_gen": """Ты помогаешь пользователю создать описание для карточки истории в текстовой RPG.

Контекст мира:
{world_context}

Название карточки: {card_title}

Базовая информация (plot_basics):
{plot_basics}

Авторские пометки:
{author_notes}

Фрагмент истории для контекста:
{history_fragment}

Создай подробное описание карточки (~5 предложений) в контексте этого мира. Опиши персонажа, локацию или объект, его характеристики, роль в мире. Не используй Markdown, пиши обычным текстом.
Описание:""",
        "prompt.scene_image": """Ты составляешь промпт для генерации изображения текущей сцены текстовой RPG.

Основы сюжета:
{plot_basics}

Недавние события (последние ходы):
{history_fragment}

Релевантные карточки истории:
{cards_block}

{style_rules}

Ограничения по содержанию снимаются: NSFW, насилие, кровь и эротические элементы разрешены и должны описываться прямо и без цензуры, если они соответствуют сцене.

Верни СТРОГО один JSON-объект без пояснений и без Markdown, с двумя полями:
{{"prompt": "<текст промпта>", "negative_prompt": "<анти-промпт: что НЕ должно быть на изображении>"}}""",
        "prompt.scene_style.sd": """Создай один подробный визуальный промпт для текущей сцены в формате Stable Diffusion / SDXL.

ФОРМАТ: теги через запятую, как в тегах бустимилков (Danbooru). Порядок тегов: главный объект, детали внешности, одежда и снаряжение, действие и поза, окружение, время суток и освещение, стиль и качество. Вес тега указывай скобками: (красные волосы:1.2). Не используй точки, связные предложения и слова вроде «изображение», «фото», «рисунок».

Теги качества добавь в конец промпта: masterpiece, best quality, highly detailed, sharp focus.

Анти-промпт пиши теми же тегами через запятую и не включай в него NSFW и насилие: lowres, worst quality, low quality, jpeg artifacts, blurry, bad anatomy, bad hands, extra fingers, extra limbs, fused fingers, malformed limbs, deformed, disfigured, extra digits, fewer digits, cropped, out of frame, text, signature, watermark, logo.""",
        "prompt.scene_style.midjourney": """Создай один подробный визуальный промпт для текущей сцены в формате Midjourney.

ФОРМАТ: связное естественное описание на английском языке, одним абзацем. Описывай только то, что видно: персонажей (внешность, одежду, позы), окружение, время суток, освещение, настроение, ракурс и композицию. Не используй теги через запятую, веса в скобках и технические термины вроде «8k».

В конце добавь параметры Midjourney: --ar 16:9 --style raw --v 7

Анти-промпт опиши словами, а не тегами: перечисли, чего не должно быть на изображении (например: extra fingers, text, watermark, distorted anatomy). Не включай в него NSFW и насилие.""",
        "prompt.scene_style.flux": """Создай один подробный визуальный промпт для текущей сцены в формате Flux / естественный текст.

ФОРМАТ: связное описание на английском языке, 2-4 предложения, в порядке: кто и что в кадре, внешность и одежда персонажей, действие, окружение, освещение, стиль и настроение. Не используй теги через запятую, веса в скобках и служебные слова вроде «negative prompt», «quality».

Теги качества в конце не нужны — Flux их игнорирует.

Анти-промпт — отдельное связное предложение, описывающее, чего не должно быть на изображении (например: «artifacts, extra fingers, text, watermark, distorted anatomy»). Не включай в него NSFW и насилие.""",
        "prompt.scene_style.generic": """Создай один подробный визуальный промпт для текущей сцены.

ФОРМАТ: связное описание на английском языке, 2-4 предложения. Описывай только то, что видно: персонажей (внешность, одежду, позы), окружение, время суток, освещение, стиль, настроение, ракурс и композицию. Не используй теги через запятую и веса в скобках.

Анти-промпт — отдельное связное предложение, описывающее, чего не должно быть на изображении. Не включай в него NSFW и насилие.""",
    },
    "en": {
        "lang.ru": "Русский",
        "lang.en": "English",
        "window_title": "🐉 AI Dungeon Master",
        "app_title": "🐉 AI DUNGEON MASTER 🐉",
        "no_worlds": "No worlds",
        "ready": "● Ready",
        "summary_until": "Until summary: -",
        "memory_until": "Until memory: -",
        "btn.world_files": "📁 World files",
        "btn.cards": "📇 Cards",
        "btn.worlds": "🔄 Worlds",
        "btn.ai_settings": "⚙️ AI settings",
        "btn.quit": "❌ Quit",
        "btn.next": "❓ What next?",
        "btn.reroll": "🔁 Reroll",
        "btn.edit_last": "✏️ Edit last",
        "btn.prompt": "📋 Prompt",
        "btn.scene_prompt": "🎨 Scene Prompt",
        "btn.summary": "📝 Summarize",
        "btn.memory": "🧠 Memory",
        "btn.undo": "⏪ Undo turn",
        "btn.send": "▶ Send",
        "btn.create": "Create",
        "btn.create_ok": "✅ Create",
        "btn.cancel": "❌ Cancel",
        "btn.cancel_plain": "Cancel",
        "btn.close": "Close",
        "btn.close_x": "❌ Close",
        "btn.save": "💾 Save",
        "btn.save_ok": "✅ Save",
        "btn.save_as": "💾 Save as...",
        "btn.delete": "Delete",
        "btn.delete_icon": "🗑 Delete",
        "btn.load": "Load",
        "btn.add": "➕ Add",
        "btn.copy": "📋 Copy",
        "btn.index_now": "🔄 Index now",
        "toggle.summary_on": "📝 Summ.: ON",
        "toggle.summary_off": "📝 Summ.: OFF",
        "toggle.memory_on": "🧠 Memory: ON",
        "toggle.memory_off": "🧠 Memory: OFF",
        "summary.off": "Summ.: off",
        "summary.until": "Until summ.: {n}",
        "memory.off": "Memory: {n} | off",
        "memory.until": "Memory: {n} | until idx.: {remaining}",
        "context.usage": "Context: {used} / {total}",
        "btn.stop": "⏹ Stop",
        "status.generating": "● Generating...",
        "status.scene_prompt": "● Scene prompt...",
        "status.summary_memory": "● Summary and memory...",
        "status.summary": "● Summarizing...",
        "status.memory": "● Indexing memory...",
        "menu.select_all": "Select all",
        "menu.copy": "Copy",
        "menu.paste": "Paste",
        "menu.cut": "Cut",
        "dialog.manage_worlds": "🔄 Manage worlds",
        "dialog.your_worlds": "Your worlds:",
        "dialog.delete_world": "Delete world",
        "dialog.delete_world_q": "Delete world '{name}' permanently?",
        "dialog.create_world": "🔄 Create a new world",
        "dialog.world_name": "World name (folder):",
        "dialog.default_world_name": "New World",
        "dialog.bad_name": "Error",
        "dialog.bad_name_msg": "Invalid or already used name",
        "dialog.world_files": "📁 World files",
        "dialog.choose_file": "Choose a file:",
        "dialog.unsaved": "● Unsaved changes",
        "dialog.attention": "Warning",
        "dialog.file_unsaved": "File “{label}” has unsaved changes. Save?",
        "dialog.close_unsaved": "There are unsaved changes. Save before closing?",
        "dialog.cards_title": "📇 Story cards",
        "dialog.cards_need_world": "Select or create a world first.",
        "dialog.next_title": "❓ What next?",
        "dialog.next_hint": "Describe what should happen on the next turn.\nThe AI will write it into the story.",
        "dialog.empty_input": "Empty input",
        "dialog.empty_next": "Describe what should happen next.",
        "dialog.ai_settings": "⚙️ AI settings",
        "dialog.api_config": "API configuration",
        "dialog.manual_preset": "— Manual —",
        "dialog.save_preset": "Save configuration",
        "dialog.preset_name": "Configuration name:",
        "dialog.delete_preset_info": "Delete",
        "dialog.delete_preset_pick": "Select a saved configuration to delete.",
        "dialog.delete_preset": "Delete configuration",
        "dialog.delete_preset_q": "Delete configuration “{name}”?",
        "dialog.api_url": "API URL (Chat Completions):",
        "dialog.api_key": "API key (optional):",
        "dialog.show_key": "Show key",
        "dialog.model": "Model (optional):",
        "dialog.gen_params": "Generation settings",
        "dialog.stream": "Show the reply as it is generated",
        "dialog.auto_summary": "Auto-summary",
        "dialog.memory_bank": "Memory bank",
        "dialog.temperature": "Temperature (0.0 - 2.0):",
        "dialog.max_tokens": "Max response tokens:",
        "dialog.context_size": "Context size:",
        "dialog.summary_every": "Summarize every N turns:",
        "dialog.memory_every": "Memory bank (index every N turns):",
        "dialog.memory_top_k": "Max memories in the prompt:",
        "dialog.image_style": "Image prompt format:",
        "image_style.sd": "Stable Diffusion (tags, weights)",
        "image_style.midjourney": "Midjourney (--parameters)",
        "image_style.flux": "Flux (natural text)",
        "image_style.generic": "Generic (text)",
        "dialog.language": "Interface language:",
        "dialog.quit": "Quit",
        "dialog.quit_q": "Really quit the game?",
        "dialog.edit_dm": "✏️ Edit reply",
        "dialog.edit_dm_label": "Edit the DM reply:",
        "dialog.edit_player": "✏️ Edit your turn",
        "dialog.edit_player_label": "Edit your action:",
        "dialog.edit_prev": "◀ Prev",
        "dialog.edit_next": "Next ▶",
        "dialog.prompt_title": "📋 Last prompt",
        "dialog.no_prompt": "No prompt data yet.",
        "dialog.prompt_time": "=== REQUEST TIME ===\n{time}\n\n=== APPROXIMATE TOKEN COUNT ===\n{tokens}\n\n",
        "dialog.prompt_body": "=== SYSTEM ===\n{system}\n\n=== USER ===\n{user}\n",
        "dialog.memory_title": "🧠 Memory bank",
        "dialog.no_world": "No world selected.",
        "dialog.memory_empty": "Memory bank is empty. Entries appear after a few turns.",
        "dialog.memory_stats": "Entries: {n} | Indexed turns: {turns}",
        "dialog.memory_entry": "=== {id} | turns {start}-{end} ===\nKeys: {keys}\nNPCs: {npcs} | Location: {location}\n{summary}\n",
        "dialog.no_worlds_title": "No worlds",
        "dialog.no_worlds_q": "You have no worlds yet. Create one?",
        "cards.list": "Cards:",
        "cards.search": "Search cards...",
        "cards.title": "Title:",
        "cards.desc": "Description:",
        "cards.triggers": "Triggers (comma-separated keywords that pull this card into the prompt):",
        "cards.triggers_ph": "arion, tavern, sword",
        "cards.empty_triggers": "Empty triggers = the card is always included in the prompt",
        "cards.untitled": "Untitled",
        "cards.new": "New card",
        "cards.delete": "Delete",
        "cards.delete_q": "Delete the selected card?",
        "cards.save_with_world": "Saved together with the world",
        "cards.generate_desc": "✨ Generate Description",
        "cards.generating": "Generating description...",
        "cards.generate_desc_title": "Generate Card Description",
        "cards.enter_title_first": "Please enter a card title first",
        "scene.prompt_label": "Prompt",
        "scene.negative_label": "Negative prompt",
        "scene.copy_prompt": "📋 Copy prompt",
        "scene.copy_negative": "📋 Copy negative prompt",
        "scene.copied_prompt": "🎨 Scene prompt copied.",
        "scene.copied_negative": "🎨 Negative prompt copied.",
        "scene.generating": "Generating prompt...",
        "scene.stop": "⏹ Stop",
        "scene.needs_world": "Please load a world first.",
        "scene.needs_history": "The history needs at least one Game Master reply.",
        "dialog.corrupt_title": "Corrupted data",
        "dialog.corrupt_history": "World \"{name}\" was not loaded: file {file} is corrupted and cannot be read, including from the backup.\n\nHistory was left untouched — you can repair it manually.\nDetails: {detail}\n\nThe backup is next to it: {file}.bak",
        "on": "ON",
        "off": "OFF",
        "summary_enabled_word": "enabled",
        "summary_disabled_word": "disabled",
        "memory_enabled_word": "enabled",
        "memory_disabled_word": "disabled",
        "msg.cards_saved": "✅ Story cards saved",
        "msg.file_saved": "✅ File {name} saved",
        "msg.preset_saved": "💾 API configuration “{name}” saved.",
        "msg.settings_saved": "⚙️ Settings saved. API: {api}{model}{preset}. Streaming: {stream}. Summary: {summary}. Memory: {memory}.",
        "msg.model_part": ", model: {model}",
        "msg.preset_part": ", preset: {name}",
        "msg.dm_edited": "📝 DM reply updated.",
        "msg.player_edited": "📝 Your turn updated.",
        "msg.force_summary": "📝 Forcing a summary update...",
        "msg.prompt_copied": "📋 Prompt copied.",
        "msg.force_memory": "🧠 Forcing memory indexing...",
        "msg.summary_toggled": "📝 Auto-summary {state}.",
        "msg.memory_toggled": "🧠 Memory bank {state}.",
        "msg.welcome": "Welcome! Create a new world with the “🔄 Worlds” button.",
        "msg.world_loaded": "✅ World '{name}' loaded.",
        "msg.undone": "⏪ Last message removed.",
        "msg.no_memory_turns": "🧠 No new turns to index.",
        "msg.memory_entry": "🧠 Memory [{id}]: {summary}... (keys: {keys})",
        "msg.memory_offline": "❌ Memory bank: AI server is unavailable.",
        "msg.memory_error": "⚠️ Memory indexing error: {msg}",
        "msg.empty_model": "⚠️ The model returned an empty reply.",
        "msg.tokens": "📊 Tokens: Context: {p} | Reply: {c} | Total: {t}/{ctx}",
        "msg.reviewing": "📝 The AI is reviewing the chronicle...",
        "msg.no_server": "❌ Error: local AI server is not running!",
        "msg.error": "❌ Error: {msg}",
        "msg.summary_ok": "✨ World summary updated!",
        "msg.summary_fail": "⚠️ Could not auto-update the summary: {msg}",
        "msg.history_restored": "♻️ History restored from backup (the file was corrupted).",
        "msg.stop_requested": "⏹ Stopping generation...",
        "msg.scene_prompt_done": "🎨 Scene prompt is ready.",
        "msg.scene_prompt_fail": "⚠️ Could not create the scene prompt: {msg}",
        "msg.action_stopped": "⏹ Generation stopped. The partial reply was kept — you can edit or undo it.",
        "msg.summary_stopped": "⏹ Summarization stopped.",
        "msg.memory_stopped": "⏹ Memory indexing stopped.",
        "msg.language_changed": "🌐 Interface language: {lang_name}",
        "world_file.introduction.txt": "Introduction",
        "world_file.ai_instructions.txt": "AI instructions",
        "world_file.plot_basics.txt": "Plot basics",
        "world_file.author_notes.txt": "Author notes",
        "world_file.summary.txt": "Summary",
        "world_file.story_cards": "Story cards",
        "hist.player": "Player:",
        "hist.dm": "DM:",
        "hist.intro": "Introduction:",
        "prompt.continue": "(Continue the narrative.)",
        "prompt.direction": "The author sets the direction for the next turn:\n{hint}\n\nRealize this organically in the narration, keeping the style, context, and world rules. Do not mention that this is an author instruction — just advance the story.",
        "prompt.no_reasoning": "IMPORTANT: Respond immediately without reasoning, analysis, or internal monologue. Do not use , <thinking>, <reasoning>, or similar tags. Start your response directly with the narrative.",
        "prompt.summary_header": "=== Compressed chronicle of past events (summary.txt) ===\n{text}\n",
        "prompt.history_header": "CURRENT SESSION HISTORY:",
        "prompt.memory_header": "=== RELEVANT MEMORIES (memory bank) ===\n",
        "prompt.cards_header": "=== RELEVANT STORY CARDS ===\n",
        "prompt.card_triggers": " (triggers: {triggers})",
        "prompt.card_always": " (always active)",
        "prompt.cards_missing": "No information.",
        "prompt.none": "None.",
        "prompt.memory_index": """Analyze this fragment of a text RPG session.
Produce:
1. summary — 2-3 sentences, only key events and facts (names, items, decisions)
2. keys — up to 3 search keywords, only the most important ones (NPC names, locations, items, events)
3. location — current location or null
4. npcs — list of mentioned NPCs

FRAGMENT:
{fragment}

Reply with VALID JSON only:
{{"summary": "...", "keys": ["...", "..."], "location": "...", "npcs": ["..."]}}""",
        "prompt.summary": """You are given a text RPG history and its previous summary.
Your task: write an updated, clean, compact SUMMARY.
RULES:
1. Form a short history in chronological order.
2. Ignore minor routine.
3. Write concisely, in brief points.
4. Take the OLD summary into account.

OLD SUMMARY:
{old_summary}

CURRENT GAME HISTORY:
{history}

Output only the new summary as plain text with no extra *, introductions, or Markdown.""",
        "prompt.card_desc_gen": """You are helping a user create a description for a story card in a text RPG.

World context:
{world_context}

Card title: {card_title}

Basic information (plot_basics):
{plot_basics}

Author notes:
{author_notes}

Story fragment for context:
{history_fragment}

Create a detailed card description (~5 sentences) in the context of this world. Describe the character, location, or object, its characteristics, and role in the world. Do not use Markdown, write in plain text.
Description:""",
        "prompt.scene_image": """You are composing a prompt for image generation of the current scene in a text RPG.

Plot basics:
{plot_basics}

Recent events (last turns):
{history_fragment}

Relevant story cards:
{cards_block}

{style_rules}

Content restrictions are lifted: NSFW, violence, blood and erotic elements are allowed and should be described directly and without censorship if they fit the scene.

Return STRICTLY a single JSON object, no explanations and no Markdown, with two fields:
{{"prompt": "<prompt text>", "negative_prompt": "<negative prompt: what should NOT be in the image>"}}""",
        "prompt.scene_style.sd": """Create one detailed visual prompt for the current scene in the Stable Diffusion / SDXL format.

FORMAT: comma-separated tags in the style of booru (Danbooru) tags. Tag order: main subject, appearance details, clothing and gear, action and pose, environment, time of day and lighting, style and quality. Express tag weight with parentheses: (red hair:1.2). Do not use full sentences or words like "image", "photo", "painting".

Append quality tags at the end of the prompt: masterpiece, best quality, highly detailed, sharp focus.

Write the negative prompt as the same kind of comma-separated tags, and do NOT put NSFW or violence in it: lowres, worst quality, low quality, jpeg artifacts, blurry, bad anatomy, bad hands, extra fingers, extra limbs, fused fingers, malformed limbs, deformed, disfigured, extra digits, fewer digits, cropped, out of frame, text, signature, watermark, logo.""",
        "prompt.scene_style.midjourney": """Create one detailed visual prompt for the current scene in the Midjourney format.

FORMAT: a single flowing paragraph of natural English. Describe only what is visible: characters (appearance, clothing, poses), environment, time of day, lighting, mood, camera angle and composition. Do not use comma-separated tags, parenthesised weights, or technical terms like "8k".

End with Midjourney parameters: --ar 16:9 --style raw --v 7

Write the negative prompt as words, not tags: list what should not appear (for example: extra fingers, text, watermark, distorted anatomy). Do NOT put NSFW or violence in it.""",
        "prompt.scene_style.flux": """Create one detailed visual prompt for the current scene for Flux / natural text models.

FORMAT: 2-4 sentences of natural English, ordered as: who and what is in frame, character appearance and clothing, action, environment, lighting, style and mood. Do not use comma-separated tags, parenthesised weights, or service words like "negative prompt" or "quality".

Do NOT append quality tags — Flux ignores them.

The negative prompt is one separate sentence describing what should not be in the image (for example: "artifacts, extra fingers, text, watermark, distorted anatomy"). Do NOT put NSFW or violence in it.""",
        "prompt.scene_style.generic": """Create one detailed visual prompt for the current scene.

FORMAT: 2-4 sentences of natural English. Describe only what is visible: characters (appearance, clothing, poses), environment, time of day, lighting, style, mood, camera angle and composition. Do not use comma-separated tags or parenthesised weights.

The negative prompt is one separate sentence describing what should not be in the image. Do NOT put NSFW or violence in it.""",
    },
}

TEMPLATES = {
    "ru": {
        "introduction.txt": (
            "Вы — искатель приключений в мире фэнтези. История начинается здесь: "
            "опишите стартовую сцену, обстановку и с чего начинается приключение."
        ),
        "ai_instructions.txt": """Ты - ИИ мастер, который предоставляет любой контент для ролевых игр.
Инструкции, которые ты (Мастер) обязан соблюдать при написании:
- '!!' Двигай сюжет, не зацикливайся на одной сцене.
- '!' Отдавайте предпочтение действиям и диалогам, а не описаниям.
- '!' Не описывайте окружающую обстановку, освещение, погоду, звуки или жестикуляцию персонажей, если это напрямую не влияет на текущее действие.
- '!' Избегайте повторяющегося эмоционального повествования.
- '!' Пишите скорее как сценарий фильма, чем как роман.
- Будьте конкретны, описательны и изобретательны.
- Избегайте повторений и обобщений.
- Старайтесь развивать историю, даже если пользователь бездействует.
- Обычно говорите от второго лица (например, "О смотрит на вас"). Но используйте слова от третьего лица, если вам кажется, что история развивается именно так.
- Если ввод заканчивается на середине предложения, продолжайте с того места, где он был прерван.
- Подробно опишите внешность и характерные черты персонажей.

Разрешено принимать решения и писать за пользователя!
""",
        "plot_basics.txt": "Мир фэнтези.\nВы искатель приключений.\nУ вас есть меч и щит.\nВы носите легкую кожаную броню.",
        "author_notes.txt": "Стиль написания: Приключение, комедия, фэнтези.",
        "summary.txt": "",
    },
    "en": {
        "introduction.txt": (
            "You are an adventurer in a fantasy world. The story starts here: "
            "describe the opening scene, the setting, and how the adventure begins."
        ),
        "ai_instructions.txt": """You are an AI game master who provides any content for tabletop role-playing games.
Instructions you (the DM) must follow when writing:
- '!!' Drive the plot forward; do not loop on a single scene.
- '!' Prefer actions and dialogue over description.
- '!' Do not describe surroundings, lighting, weather, sounds, or character gestures unless they directly affect the current action.
- '!' Avoid repetitive emotional narration.
- '!' Write more like a film script than a novel.
- Be specific, descriptive, and inventive.
- Avoid repetition and generalizations.
- Keep the story moving even if the user does nothing.
- Usually write in the second person (e.g. "She looks at you"). Use third person when the story calls for it.
- If input ends mid-sentence, continue from where it was interrupted.
- Describe characters' appearance and distinctive traits in detail.

You may make decisions and write for the user!
""",
        "plot_basics.txt": "A fantasy world.\nYou are an adventurer.\nYou have a sword and a shield.\nYou wear light leather armor.",
        "author_notes.txt": "Writing style: Adventure, comedy, fantasy.",
        "summary.txt": "",
    },
}

STORY_CARD_DEMOS = {
    "ru": {
        "cards": [
            {
                "id": "card_001",
                "title": "Арион",
                "description": "Арион - мужчина, 21 год.\nОн воин, орудует длинным мечом и щитом.\nИмеет красные волосы среднего размера, одет в кожанную броню",
                "triggers": ["арион", "воин"],
            }
        ]
    },
    "en": {
        "cards": [
            {
                "id": "card_001",
                "title": "Arion",
                "description": "Arion is a man, 21 years old.\nHe is a warrior, wields a long sword and a shield.\nHe has medium‑length red hair and is dressed in leather armor.",
                "triggers": ["arion", "warrior",],
            }
        ]
    },
}


def normalize_lang(value):
    value = str(value or "ru").lower()
    return "en" if value.startswith("en") else "ru"


def t(lang, key, **kwargs):
    lang = normalize_lang(lang)
    table = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    text = table.get(key) or TRANSLATIONS["ru"].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def default_templates(lang):
    lang = normalize_lang(lang)
    return dict(TEMPLATES.get(lang, TEMPLATES["ru"]))


def default_story_cards(lang=None):
    lang = normalize_lang(lang if lang is not None else "ru")
    demo = STORY_CARD_DEMOS.get(lang, STORY_CARD_DEMOS["ru"])
    return {"cards": [dict(card, triggers=list(card.get("triggers", []))) for card in demo["cards"]]}


def is_player_msg(msg):
    return isinstance(msg, str) and msg.startswith(PLAYER_PREFIX)


def is_dm_msg(msg):
    return isinstance(msg, str) and msg.startswith(DM_PREFIX)


def is_intro_msg(msg):
    return isinstance(msg, str) and msg.startswith(INTRO_PREFIX)


def player_text(msg):
    return msg[len(PLAYER_PREFIX) :].strip() if is_player_msg(msg) else msg


def dm_text(msg):
    return msg[len(DM_PREFIX) :].strip() if is_dm_msg(msg) else msg


def intro_text(msg):
    return msg[len(INTRO_PREFIX) :].strip() if is_intro_msg(msg) else msg


def localize_history_line(lang, msg):
    if is_player_msg(msg):
        return f"{t(lang, 'hist.player')} {player_text(msg)}"
    if is_dm_msg(msg):
        return f"{t(lang, 'hist.dm')} {dm_text(msg)}"
    if is_intro_msg(msg):
        return f"{t(lang, 'hist.intro')} {intro_text(msg)}"
    return msg


def localize_history(lang, messages):
    return [localize_history_line(lang, msg) for msg in messages]
