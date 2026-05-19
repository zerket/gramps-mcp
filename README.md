# Gramps Web MCP Server

MCP сервер для взаимодействия с [Gramps Web](https://github.com/gramps-project/gramps-web) через Claude Code. Позволяет управлять семейным деревом — добавлять людей, семьи, события, источники и другие генеалогические данные — на естественном языке.

## Возможности

- **45 MCP инструментов** — полный CRUD для 10 типов сущностей
- **Smart merge update** — безопасное частичное обновление через GET → слияние → PUT с ETag
- **Convenience tools** — создание персоны с рождением, смертью, родителями и супругом в одном вызове
- **JWT auth** — автоматическое обновление токена за 30с до истечения, retry при 401
- **Гайд по русской генеалогии** — встроенные MCP prompts для работы с кириллическими данными

## Установка

```bash
git clone <repo-url> gramps-mcp
cd gramps-mcp
python3 -m venv .venv
.venv/bin/pip install mcp[cli] httpx pydantic pydantic-settings
```

## Настройка

Создай `.env` файл с параметрами твоего Gramps Web инстанса:

```env
GRAMPS_API_URL=http://192.168.1.100:5000
GRAMPS_USERNAME=admin
GRAMPS_PASSWORD=your-password
REQUEST_TIMEOUT=30
```

- `GRAMPS_API_URL` — адрес Gramps Web (без `/api` на конце)
- `GRAMPS_USERNAME` / `GRAMPS_PASSWORD` — учётные данные пользователя с правами Editor или выше

## Запуск

```bash
cd gramps-mcp
PYTHONPATH=src .venv/bin/python -m gramps_mcp.server
```

Сервер работает через STDIO — не слушает порт, общается через стандартный ввод/вывод по протоколу JSON-RPC.

## Подключение к Claude Code

Добавь в конфигурацию Claude Code (`~/.claude/settings.json` или `.claude/settings.json` в проекте):

```json
{
  "mcpServers": {
    "gramps-web": {
      "command": "/absolute/path/to/gramps-mcp/.venv/bin/python",
      "args": ["-m", "gramps_mcp.server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/gramps-mcp/src",
        "GRAMPS_API_URL": "http://192.168.1.100:5000",
        "GRAMPS_USERNAME": "admin",
        "GRAMPS_PASSWORD": "your-password"
      }
    }
  }
}
```

После перезапуска Claude Code инструменты Gramps Web появятся в списке доступных.

## Инструменты

### Поиск (4)
| Инструмент | Описание |
|-----------|----------|
| `search_entities` | Полнотекстовый поиск по всем типам сущностей |
| `search_entities_gql` | Структурированный поиск через Gramps Query Language |
| `get_entity_by_handle` | Получить сущность по Gramps handle (UUID) |
| `get_entity_by_gramps_id` | Получить сущность по пользовательскому ID (I0001) |

### Создание (10)
| Инструмент | Описание |
|-----------|----------|
| `create_person` | Создать персону (с опциональными рождением/смертью) |
| `create_family` | Создать семью (родители + дети) |
| `create_event` | Создать событие (рождение, брак, перепись, etc.) |
| `create_place` | Создать место (с координатами) |
| `create_source` | Создать источник (документ, архивная запись) |
| `create_citation` | Создать цитату (ссылка на конкретную страницу источника) |
| `create_media` | Создать медиа-объект |
| `create_note` | Создать заметку |
| `create_repository` | Создать репозиторий (архив, библиотека) |
| `create_tag` | Создать тег |

### Чтение (4)
| Инструмент | Описание |
|-----------|----------|
| `list_entities` | Список сущностей с пагинацией и GQL-фильтрами |
| `get_person_detail` | Детальная информация о персоне: таймлайн, семьи, события |
| `batch_get_entities` | Получить несколько сущностей по списку handle |
| `list_recent_changes` | Недавние изменения в базе |

### Обновление (10)
| Инструмент | Описание |
|-----------|----------|
| `update_person` | Обновить персону (smart merge) |
| `update_family` | Обновить семью |
| `update_event` | Обновить событие |
| `update_place` | Обновить место |
| `update_source` | Обновить источник |
| `update_citation` | Обновить цитату |
| `update_media` | Обновить медиа |
| `update_note` | Обновить заметку |
| `update_repository` | Обновить репозиторий |
| `update_tag` | Обновить тег |

### Удаление (2)
| Инструмент | Описание |
|-----------|----------|
| `delete_entity` | Удалить одну сущность |
| `batch_delete_entities` | Массовое удаление (до 50 за раз) |

### Быстрые операции (6)
| Инструмент | Описание |
|-----------|----------|
| `create_person_full` | **Главный инструмент ввода данных** — персона + рождение + смерть + родители + супруг + заметки в одном вызове |
| `add_child_to_family` | Добавить ребёнка в существующую семью |
| `add_spouse` | Создать брак между двумя персонами |
| `set_person_birth` | Установить/обновить дату и место рождения |
| `set_person_death` | Установить/обновить дату и место смерти |
| `link_parents` | Привязать ребёнка к родителям (создаст семью если нужно) |

### Анализ (6)
| Инструмент | Описание |
|-----------|----------|
| `get_tree_stats` | Статистика базы: количество записей каждого типа |
| `get_ancestors` | Предки персоны (до 10 поколений) |
| `get_descendants` | Потомки персоны (до 10 поколений) |
| `get_relationship` | Родственная связь между двумя персонами |
| `get_person_timeline` | Хронология событий персоны |
| `find_orphaned` | Поиск «осиротевших» записей без связей |

### Теги (3)
| Инструмент | Описание |
|-----------|----------|
| `list_tags` | Список всех тегов |
| `tag_entity` | Добавить тег к сущности |
| `untag_entity` | Убрать тег с сущности |

## Примеры использования

### Ввод новой персоны

```
Создай персону: Иван Петрович Кравченко, родился 15 мая 1925 в селе Великая
Белозёрка, умер 3 декабря 1998 в Москве. Отец — Пётр Семёнович Кравченко,
мать — Мария Ивановна (в девичестве Шевченко). Жена — Анна Фёдоровна,
поженились в 1950.
```

Claude вызовет `create_person_full` со всеми параметрами.

### Поиск и обновление

```
Найди всех Кравченко в дереве. Для каждого проверь, заполнена ли дата рождения.
Если нет — спроси у меня.
```

Claude сделает `search_entities` → для каждого `get_person_detail` → проверит `birth_ref_index`.

### Исследование родственных связей

```
Кем приходится Иван Петрович Кравченко Николаю Семёновичу Кравченко?
```

Claude вызовет `get_relationship` и покажет результат.

## Архитектура

```
src/gramps_mcp/
  server.py         # FastMCP instance, lifespan, main()
  config.py         # Pydantic Settings (.env → настройки)
  auth.py           # AuthManager (JWT кэш, авто-обновление, 401 retry)
  client.py         # GrampsWebAPIClient (httpx → Gramps Web REST API)
  models.py         # Pydantic модели для валидации входных данных
  tools/
    search.py       # Поиск и lookup
    create.py       # Создание всех 10 типов сущностей
    read.py         # Чтение, списки, batch get
    update.py       # Smart merge обновление
    delete.py       # Удаление (одиночное + batch)
    convenience.py  # Многошаговые операции
    analysis.py     # Анализ дерева
    tags.py         # Управление тегами
```

## Требования

- Python 3.11+
- Gramps Web API v3.x (проверено на v3.13.1)
- Права пользователя: Editor или выше для создания/изменения данных

## Лицензия

MIT
