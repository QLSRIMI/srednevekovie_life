import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Классы для предметов и валюты
class Item:
    def __init__(self, name: str, description: str, item_type: str):
        self.name = name
        self.description = description
        self.item_type = item_type

class Currency:
    def __init__(self, gold: int = 0, silver: int = 0, bronze: int = 0):
        self.bronze = bronze
        self.silver = silver
        self.gold = gold

    def normalize(self):
        self.silver += self.bronze // 10
        self.bronze = self.bronze % 10
        self.gold += self.silver // 100
        self.silver = self.silver % 100

    def add_bronze(self, amount: int):
        self.bronze += amount
        self.normalize()

    def total_value(self):
        return self.gold * 10000 + self.silver * 100 + self.bronze

    def __str__(self):
        return f"💰 Золото: {self.gold} | Серебро: {self.silver} | Бронза: {self.bronze}"

class Weapon(Item):
    def __init__(self, name: str, description: str, damage: int):
        super().__init__(name, description, "оружие")
        self.damage = damage

class Armor(Item):
    def __init__(self, name: str, description: str, defense: int):
        super().__init__(name, description, "броня")
        self.defense = defense

class Monster:
    def __init__(self, name: str, health: int, min_damage: int, max_damage: int):
        self.name = name
        self.health = health
        self.min_damage = min_damage
        self.max_damage = max_damage

    def attack_player(self):
        return random.randint(self.min_damage, self.max_damage)

class Backpack:
    def __init__(self, size: int):
        self.size = size
        self.slots = []

    def add_item(self, item: Item, quantity: int = 1):
        if len(self.slots) >= self.size:
            raise ValueError("Инвентарь полон")

        if item.item_type in ["оружие", "броня"]:
            self.slots.append({"item": item, "quantity": 1})
        else:
            added = False
            for slot in self.slots:
                if slot["item"].name == item.name and slot["quantity"] < 100:
                    slot["quantity"] += quantity
                    added = True
                    break
            if not added:
                self.slots.append({"item": item, "quantity": quantity})

    def get_category_items(self, category: str):
        return [slot for slot in self.slots if slot["item"].item_type == category]

class Player:
    def __init__(self, user_id: int, name: str):
        self.user_id = user_id
        self.name = name
        self.backpack = Backpack(size=12)
        self.currency = Currency()
        self.total_damage = 0
        self.monsters_killed = 0
        self.current_monster = None
        self.health = 100
        self.encountered_monsters = set()  # Множество для отслеживания встреченных монстров
        self.battle_log = []  # Лог боя для отображения статистики

        self.add_item(Weapon("Меч", "Острый меч", 10))

    def add_item(self, item: Item, quantity: int = 1):
        try:
            self.backpack.add_item(item, quantity)
            return True
        except ValueError:
            return False

    def take_damage(self, damage: int):
        self.health -= damage
        if self.health < 0:
            self.health = 0

    def is_alive(self):
        return self.health > 0

    def heal(self, amount: int):
        self.health += amount
        if self.health > 100:
            self.health = 100

    def add_to_battle_log(self, message: str):
        self.battle_log.append(message)

    def clear_battle_log(self):
        self.battle_log = []

class GameStates(StatesGroup):
    MAIN_MENU = State()
    INVENTORY = State()
    FIGHT = State()
    ADMIN_MENU = State()

players = {}
ADMIN_IDS = [5693659771, 1135853083]
monsters_list = [
    Monster("Гоблин", 50, 5, 10),
    Monster("Орк", 80, 10, 15),
    Monster("Дракон", 150, 20, 30),
    Monster("Мечта SLB", 490000, 9000, 30000)
]

TG_TOKEN = '7753644115:AAFm5eVYosykGc98IYKenkkwoUQT7HujWsk'
bot = Bot(token=TG_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Inline-клавиатуры
def main_menu_inline():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Вызвать монстра", callback_data="summon_monster"),
        InlineKeyboardButton(text="Топ игроков", callback_data="show_top_menu")
    )
    builder.row(
        InlineKeyboardButton(text="Админ-меню", callback_data="admin_menu"),
        InlineKeyboardButton(text="Инвентарь", callback_data="open_inv")
    )
    return builder.as_markup()

def inventory_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Оружие", callback_data="inv_оружие"),
        InlineKeyboardButton(text="Броня", callback_data="inv_броня")
    )
    builder.row(
        InlineKeyboardButton(text="Лут", callback_data="inv_лут"),
        InlineKeyboardButton(text="Материалы", callback_data="inv_материалы")
    )
    builder.row(
        InlineKeyboardButton(text="Назад", callback_data="back_main")
    )
    return builder.as_markup()

def get_player_info(player: Player):
    return (
        f"👤 {player.name}\n"
        f"🆔 ID: {player.user_id}\n"
        f"💥 Урон: {player.total_damage}\n"
        f"👾 Убито: {player.monsters_killed}\n"
        f"❤️ Здоровье: {player.health}\n"
        f"{player.currency}\n"
        f"🎒 Слотов: {len(player.backpack.slots)}/{player.backpack.size}"
    )

# Обработчики
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.from_user.full_name
    if user_id not in players:
        players[user_id] = Player(user_id, name)
    player = players[user_id]

    print(f"Player {player.name} inventory: {player.backpack.slots}")

    text = get_player_info(player) + "\n\nВыберите действие:"
    await message.answer(text, reply_markup=main_menu_inline())
    await state.set_state(GameStates.MAIN_MENU)

@dp.callback_query(lambda c: c.data == "open_inv")
async def show_inventory(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Выберите категорию инвентаря:",
        reply_markup=inventory_inline_keyboard()
    )
    await state.set_state(GameStates.INVENTORY)

@dp.callback_query(lambda c: c.data.startswith("inv_"))
async def show_category(callback: types.CallbackQuery):
    player = players[callback.from_user.id]
    category = callback.data.split("_")[1]

    if category == "currency":
        text = f"Валюта:\n{player.currency}"
    else:
        items = player.backpack.get_category_items(category)
        print(f"Items in {category}: {items}")
        text = f"🔹 {category.capitalize()}:\n" + "\n".join([f"{i+1}. {item['item'].name} ({item['quantity']})" for i, item in enumerate(items)]) if items else "Пусто"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="open_inv")]])
    )

@dp.callback_query(lambda c: c.data == "summon_monster", GameStates.MAIN_MENU)
async def summon_monster(callback: types.CallbackQuery, state: FSMContext):
    player = players[callback.from_user.id]
    if player.current_monster:
        await callback.answer("Вы уже сражаетесь с монстром!")
        return

    # Задержка перед появлением монстра
    await callback.answer("Ищем монстра...")
    await asyncio.sleep(random.randint(5, 30))

    monster = random.choice(monsters_list)
    player.current_monster = monster
    player.clear_battle_log()  # Очищаем лог боя перед новым боем

    # Проверяем, встречался ли игрок с этим монстром ранее
    is_first_encounter = monster.name not in player.encountered_monsters
    if is_first_encounter:
        player.encountered_monsters.add(monster.name)

    if is_first_encounter:
        text = f"🦖 Появился монстр: {monster.name}\n❓ Характеристики неизвестны"
    else:
        text = f"🦖 Появился монстр: {monster.name}\n❤️ Здоровье: {monster.health}\n⚔️ Урон: {monster.min_damage}-{monster.max_damage}"

    # Отправляем новое сообщение с поиском монстра
    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Принять бой", callback_data="accept_fight")],
            [InlineKeyboardButton(text="Сбежать", callback_data="escape")]
        ])
    )
    await state.set_state(GameStates.FIGHT)  # Устанавливаем состояние FIGHT

@dp.callback_query(lambda c: c.data == "accept_fight", GameStates.FIGHT)
async def accept_fight(callback: types.CallbackQuery, state: FSMContext):
    player = players[callback.from_user.id]
    monster = player.current_monster

    # Добавляем информацию о начале боя в лог
    player.add_to_battle_log(f"🦖 Начало боя с {monster.name}!")

    await callback.message.edit_text(
        f"🦖 Вы вступили в бой с {monster.name}!\n❤️ Здоровье монстра: {monster.health}\n⚔️ Урон: {monster.min_damage}-{monster.max_damage}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Атаковать", callback_data="attack_monster")],
            [InlineKeyboardButton(text="Сбежать", callback_data="escape")]
        ])
    )
    await state.set_state(GameStates.FIGHT)  # Убедимся, что состояние остается FIGHT

@dp.callback_query(lambda c: c.data == "attack_monster", GameStates.FIGHT)
async def attack_monster(callback: types.CallbackQuery, state: FSMContext):
    player = players[callback.from_user.id]
    monster = player.current_monster
    weapon = next((slot["item"] for slot in player.backpack.slots if isinstance(slot["item"], Weapon)), None)
    if not weapon:
        await callback.answer("У вас нет оружия!")
        return

    damage = weapon.damage
    monster.health -= damage
    player.total_damage += damage

    # Добавляем информацию об атаке в лог
    player.add_to_battle_log(f"⚔️ Вы нанесли {damage} урона монстру {monster.name}!")

    if monster.health <= 0:
        player.monsters_killed += 1
        player.current_monster = None
        player.currency.add_bronze(random.randint(10, 50))

        # Добавляем информацию о победе в лог
        player.add_to_battle_log(f"🎉 Монстр {monster.name} побежден!")
        player.add_to_battle_log(f"💰 Вы получили {random.randint(10, 50)} бронзовых монет!")

        # Показываем итоговую статистику боя
        battle_summary = "\n".join(player.battle_log)
        await callback.message.edit_text(
            f"🎉 Монстр {monster.name} побежден!\n{battle_summary}",
            reply_markup=main_menu_inline()
        )
        await state.set_state(GameStates.MAIN_MENU)
    else:
        monster_damage = monster.attack_player()
        player.take_damage(monster_damage)

        # Добавляем информацию об атаке монстра в лог
        player.add_to_battle_log(f"🦖 Монстр {monster.name} нанес вам {monster_damage} урона!")

        if not player.is_alive():
            # Воскрешение с 50% здоровья
            player.heal(50)

            # Отнимаем 10% от всех денег
            total_currency = player.currency.total_value()
            lost_currency = int(total_currency * 0.1)
            player.currency = Currency()  # Сбрасываем валюту
            player.currency.add_bronze(total_currency - lost_currency)

            # Шанс 10% на потерю случайного предмета
            if random.random() < 0.1 and player.backpack.slots:
                lost_item = random.choice(player.backpack.slots)
                player.backpack.slots.remove(lost_item)
                lost_item_name = lost_item["item"].name
                lost_item_quantity = lost_item["quantity"]
                player.add_to_battle_log(f"🎒 Вы потеряли предмет: {lost_item_name} ({lost_item_quantity} шт.).")

            # Показываем итоговую статистику боя и смерть
            battle_summary = "\n".join(player.battle_log)
            await callback.message.edit_text(
                f"💀 Вы погибли в бою с {monster.name}!\n"
                f"🔄 Вы воскрешены с 50% здоровья.\n"
                f"💰 Вы потеряли 10% своих денег.\n"
                f"{battle_summary}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Воскреснуть", callback_data="resurrect")]
                ])
            )
            await state.set_state(GameStates.MAIN_MENU)
        else:
            await callback.message.edit_text(
                f"⚔️ Вы нанесли {damage} урона. ❤️ Здоровье монстра: {monster.health}\n"
                f"🦖 Монстр атакует и наносит {monster_damage} урона!\n"
                f"❤️ Ваше здоровье: {player.health}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Атаковать", callback_data="attack_monster")],
                    [InlineKeyboardButton(text="Сбежать", callback_data="escape")]
                ])
            )

@dp.callback_query(lambda c: c.data == "escape", GameStates.FIGHT)
async def escape_monster(callback: types.CallbackQuery, state: FSMContext):
    player = players[callback.from_user.id]
    if player.current_monster:
        # Штраф за попытку сбежать
        health_loss = int(player.health * random.randint(1, 15) / 100)
        player.take_damage(health_loss)
        player.current_monster = None

        # Добавляем информацию о побеге в лог
        player.add_to_battle_log(f"🏃‍♂️ Вы сбежали от монстра, потеряв {health_loss} здоровья!")

        # Показываем итоговую статистику боя
        battle_summary = "\n".join(player.battle_log)
        await callback.message.edit_text(
            f"{battle_summary}",
            reply_markup=main_menu_inline()
        )
    else:
        await callback.message.edit_text(
            get_player_info(player),
            reply_markup=main_menu_inline()
        )
    await state.set_state(GameStates.MAIN_MENU)  # Возвращаемся в главное меню

@dp.callback_query(lambda c: c.data == "resurrect")
async def resurrect(callback: types.CallbackQuery, state: FSMContext):
    player = players[callback.from_user.id]
    player.heal(50)  # Воскрешаем с 50% здоровья
    await callback.message.edit_text(
        f"🔄 Вы воскрешены с 50% здоровья.",
        reply_markup=main_menu_inline()
    )
    await state.set_state(GameStates.MAIN_MENU)

@dp.callback_query(lambda c: c.data == "back_main")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    player = players[callback.from_user.id]
    await callback.message.edit_text(
        get_player_info(player) + "\n\nВыберите действие:",
        reply_markup=main_menu_inline()
    )
    await state.set_state(GameStates.MAIN_MENU)

@dp.callback_query(lambda c: c.data == "show_top_menu")
async def show_top_menu(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Топ по урону", callback_data="top_damage"),
        InlineKeyboardButton(text="Топ по убийствам", callback_data="top_kills")
    )
    builder.row(
        InlineKeyboardButton(text="Топ по валюте", callback_data="top_currency"),
        InlineKeyboardButton(text="Назад", callback_data="back_main")
    )
    await callback.message.edit_text(
        "Выберите топ:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith("top_"))
async def show_top(callback: types.CallbackQuery):
    global players
    top_type = callback.data.split("_")[1]
    top_text = "🚫 Неизвестный тип топа"

    if top_type == "damage":
        top_players = sorted(players.values(), key=lambda p: p.total_damage, reverse=True)
        top_text = "🏆 Топ по урону:\n" + "\n".join([f"{i + 1}. {p.name}: {p.total_damage} урона" for i, p in enumerate(top_players[:10])])
    elif top_type == "kills":
        top_players = sorted(players.values(), key=lambda p: p.monsters_killed, reverse=True)
        top_text = "🏆 Топ по убийствам:\n" + "\n".join([f"{i + 1}. {p.name}: {p.monsters_killed} убийств" for i, p in enumerate(top_players[:10])])
    elif top_type == "currency":
        top_players = sorted(players.values(), key=lambda p: p.currency.total_value(), reverse=True)
        top_text = "🏆 Топ по валюте:\n" + "\n".join([f"{i + 1}. {p.name}: {p.currency}" for i, p in enumerate(top_players[:10])])

    await callback.message.edit_text(
        top_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="show_top_menu")]])
    )

@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет доступа к админ-меню!")
        return
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Добавить оружие", callback_data="add_weapon"),
        InlineKeyboardButton(text="Добавить броню", callback_data="add_armor")
    )
    builder.row(
        InlineKeyboardButton(text="Добавить валюту", callback_data="add_currency"),
        InlineKeyboardButton(text="Добавить материалы", callback_data="add_materials")
    )
    builder.row(
        InlineKeyboardButton(text="Назад", callback_data="back_main")
    )
    await callback.message.edit_text(
        "Админ-меню:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(GameStates.ADMIN_MENU)

@dp.callback_query(lambda c: c.data == "add_weapon", GameStates.ADMIN_MENU)
async def add_weapon(callback: types.CallbackQuery):
    player = players[callback.from_user.id]
    weapon = Weapon("Меч", "Острый меч", 10)
    if player.add_item(weapon):
        await callback.answer("Добавлено оружие: Меч")
    else:
        await callback.answer("Инвентарь полон!")

@dp.callback_query(lambda c: c.data == "add_armor", GameStates.ADMIN_MENU)
async def add_armor(callback: types.CallbackQuery):
    player = players[callback.from_user.id]
    armor = Armor("Щит", "Прочный щит", 5)
    if player.add_item(armor):
        await callback.answer("Добавлена броня: Щит")
    else:
        await callback.answer("Инвентарь полон!")

@dp.callback_query(lambda c: c.data == "add_currency", GameStates.ADMIN_MENU)
async def add_currency(callback: types.CallbackQuery):
    player = players[callback.from_user.id]
    player.currency.add_bronze(100)
    await callback.answer("Добавлено 100 бронзовых монет!")

@dp.callback_query(lambda c: c.data == "add_materials", GameStates.ADMIN_MENU)
async def add_materials(callback: types.CallbackQuery):
    player = players[callback.from_user.id]
    materials = Item("Дерево", "Прочная древесина", "материалы")
    if player.add_item(materials, quantity=50):
        await callback.answer("Добавлено 50 единиц материалов: Дерево")
    else:
        await callback.answer("Инвентарь полон!")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())