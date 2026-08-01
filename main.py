import sys
import os
import disnake
from disnake.ext import commands
from dotenv import load_dotenv

# Принудительно кодируем вывод в UTF-8 для корректной работы эмодзи в консоли Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Загружаем переменные окружения из .env файла
load_dotenv()

# --- КОНФИГУРАЦИЯ ID ---
TOKEN = os.getenv("BOT_TOKEN")
CREATOR_CHANNEL_ID = int(os.getenv("CREATOR_CHANNEL_ID", "1533052343665430590"))  # Канал «Зайди, чтобы создать»

intents = disnake.Intents.default()
intents.guilds = True
intents.voice_states = True  # КРИТИЧЕСКИ ВАЖНО для отслеживания заходов в войс

bot = commands.Bot(command_prefix="v!", intents=intents)

# Список для хранения ID временно созданных ботом каналов
temp_channels = []


@bot.event
async def on_ready():
    print(f"БОТ АВТО-ГОЛОСОВЫХ [{bot.user}] успешно запущен и готов к работе!")


@bot.event
async def on_voice_state_update(member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
    guild = member.guild

    # === СЦЕНАРИЙ 1: ЧЕЛОВЕК ЗАШЕЛ В КАНАЛ-ГЕНЕРАТОР ===
    if after.channel and after.channel.id == CREATOR_CHANNEL_ID:
        category = after.channel.category

        # Собираем номера всех существующих каналов с именем "сцена-X"
        existing_numbers = set()
        for channel in guild.voice_channels:
            if channel.name.startswith("сцена-"):
                try:
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
            print("[Ошибка] У бота нет прав 'Manage Channels' (Управление каналами) или 'Move Members' (Перемещение участников).")
        except Exception as e:
            print(f"[Ошибка] Не удалось создать канал: {e}")

    # === СЦЕНАРИЙ 2: ЧЕЛОВЕК ВЫШЕЛ ИЗ КАНАЛА ===
    if before.channel and before.channel.id in temp_channels:
        # Если в этом канале больше никого не осталось
        if len(before.channel.members) == 0:
            try:
                await before.channel.delete()
                temp_channels.remove(before.channel.id)
                print(f"[Авто-Войс] Канал '{before.channel.name}' опустел и был успешно удален.")
            except disnake.NotFound:
                if before.channel.id in temp_channels:
                    temp_channels.remove(before.channel.id)
            except disnake.Forbidden:
                print(f"[Ошибка] Не удалось удалить канал '{before.channel.name}': нет прав.")


if __name__ == "__main__":
    if not TOKEN:
        print("ОШИБКА: Токен BOT_TOKEN не найден в .env файле!")
    else:
        bot.run(TOKEN)
