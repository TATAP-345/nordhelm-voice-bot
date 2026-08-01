import sys
import os
import disnake
from disnake.ext import commands
from dotenv import load_dotenv

# Настройка UTF-8 вывода для Windows консоли
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

# --- КОНФИГУРАЦИЯ ID ---
CREATOR_CHANNEL_ID = 1533052343665430590  # Канал «Зайди, чтобы создать»
# Бот будет автоматически создавать каналы в той же категории, где находится этот канал

intents = disnake.Intents.default()
intents.guilds = True
intents.voice_states = True  # КРИТИЧЕСКИ ВАЖНО для отслеживания заходов в войс

bot = commands.Bot(command_prefix="v!", intents=intents)

# Список для хранения ID временно созданных ботом каналов
temp_channels = []


@bot.event
async def on_ready():
    # Находим уже созданные ранее временные каналы при перезапуске бота
    for guild in bot.guilds:
        for channel in guild.voice_channels:
            if channel.name.startswith("сцена-") and channel.id not in temp_channels:
                temp_channels.append(channel.id)

    print(f"БОТ АВТО-ГОЛОСОВЫХ [{bot.user}] успешно запущен и готов к работе!")


@bot.event
async def on_voice_state_update(member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
    guild = member.guild

    # === СЦЕНАРИЙ 1: ЧЕЛОВЕК ЗАШЕЛ В КАНАЛ-ГЕНЕРАТОР ===
    if after.channel and after.channel.id == CREATOR_CHANNEL_ID:
        # Находим категорию, в которой сидит канал-генератор
        category = after.channel.category

        # Собираем номера всех существующих каналов с именем "сцена-X"
        existing_numbers = set()
        for channel in guild.voice_channels:
            if channel.name.startswith("сцена-"):
                try:
                    # Извлекаем цифру после дефиса
                    num = int(channel.name.split("-")[1])
                    existing_numbers.add(num)
                except (IndexError, ValueError):
                    continue

        # Ищем самый первый свободный номер (начиная с 1)
        target_number = 1
        while target_number in existing_numbers:
            target_number += 1

        new_channel_name = f"сцена-{target_number}"

        try:
            # Создаем новый голосовой канал в той же категории
            new_channel = await guild.create_voice_channel(
                name=new_channel_name,
                category=category
            )

            # Запоминаем ID созданного канала, чтобы потом его удалить
            temp_channels.append(new_channel.id)

            # Перемещаем пользователя в только что созданную комнату
            await member.move_to(new_channel)
            print(f"[Авто-Войс] Создан канал '{new_channel_name}' для {member.name}")

        except disnake.Forbidden:
            print(
                "[Ошибка] У бота нет прав 'Manage Channels' (Управление каналами) или 'Move Members' (Перемещение участников).")
        except Exception as e:
            print(f"[Ошибка] Не удалось создать канал: {e}")

    # === СЦЕНАРИЙ 2: ЧЕЛОВЕК ВЫШЕЛ ИЗ КАНАЛА ===
    # Проверяем канал, из которого пользователь только что ушёл (before)
    if before.channel and before.channel.id in temp_channels:
        # Если в этом канале больше никого не осталось (длина списка участников равна 0)
        if len(before.channel.members) == 0:
            try:
                # Удаляем пустую комнату
                await before.channel.delete()
                # Удаляем её ID из нашего списка отслеживания
                temp_channels.remove(before.channel.id)
                print(f"[Авто-Войс] Канал '{before.channel.name}' опустел и был успешно удален.")
            except disnake.NotFound:
                # На случай, если канал уже был удален вручную
                if before.channel.id in temp_channels:
                    temp_channels.remove(before.channel.id)
            except disnake.Forbidden:
                print(f"[Ошибка] Не удалось удалить канал '{before.channel.name}': нет прав.")

bot.run(os.getenv('BOT_TOKEN'))
