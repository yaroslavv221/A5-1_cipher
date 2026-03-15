# server.py
import socket
import threading
import subprocess
import secrets
import telebot
import time
import crypto_logic
from typing import Optional

BOT_TOKEN: str = 'ВСТАВЬТЕ_ВАШ_ТОКЕН'
bot: telebot.TeleBot = telebot.TeleBot(BOT_TOKEN)

AUDIO_PORT: int = 9090
API_PORT: int = 9091
FRAME: int = 0x2F

CURRENT_KEY_HEX: str = secrets.token_hex(8).upper()

def get_local_ip() -> str:
    """Определяет локальный IP-адрес машины в сети."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1 (Локальная петля - нет сети)"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: telebot.types.Message) -> None:
    text = (
        "🔐 *Сервер безопасной связи A5/1*\n\n"
        "Доступные команды:\n"
        "/generate - Сгенерировать и применить новый ключ\n"
        "/current - Узнать текущий активный ключ"
    )
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['generate'])
def generate_new_key(message: telebot.types.Message) -> None:
    global CURRENT_KEY_HEX
    CURRENT_KEY_HEX = secrets.token_hex(8).upper()
    bot.reply_to(message, f"*Новый ключ установлен!*\n\n`{CURRENT_KEY_HEX}`", parse_mode='Markdown')
    print(f"[БОТ] Установлен новый ключ: {CURRENT_KEY_HEX}")

@bot.message_handler(commands=['current'])
def show_current_key(message: telebot.types.Message) -> None:
    bot.reply_to(message, f"Текущий ключ на сервере:\n`{CURRENT_KEY_HEX}`", parse_mode='Markdown')

def api_server_loop() -> None:
    """Сервер раздачи ключей (Порт 9091)"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', API_PORT))
        s.listen(5)
        print(f"[API] Сервер раздачи ключей слушает порт {API_PORT}...")
        
        while True:
            try:
                conn, addr = s.accept()
                with conn:
                    conn.sendall(CURRENT_KEY_HEX.encode('utf-8'))
            except Exception as e:
                print(f"[API] Ошибка: {e}")

def audio_server_loop() -> None:
    """Основной сервер приема и расшифровки звука (Порт 9090)"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', AUDIO_PORT))
        s.listen(1)
        print(f"[АУДИО] Сервер связи слушает порт {AUDIO_PORT} (TCP)...")

        while True:
            conn, addr = s.accept()
            print(f"\n[АУДИО] >>> Входящий звонок от {addr}")
            
            try:
                key_int: int = int(CURRENT_KEY_HEX, 16)
            except ValueError:
                print("[АУДИО] Ошибка формата ключа, использую нули.")
                key_int = 0
                
            crypto_logic.init_a51(key_int, FRAME)
            
            player_process: Optional[subprocess.Popen] = None

            try:
                player_process = subprocess.Popen(
                    ["aplay", "-t", "raw", "-f", "S16_LE", "-r", "8000", "-c", "1"],
                    stdin=subprocess.PIPE
                )

                with conn:
                    while True:
                        data: bytes = conn.recv(1024)
                        if not data:
                            break
                        
                        decrypted: bytes = crypto_logic.encrypt_chunk(data)
                        
                        if player_process.poll() is None:
                            player_process.stdin.write(decrypted)
                            player_process.stdin.flush()
                        else:
                            print("[АУДИО] Ошибка: процесс aplay неожиданно завершился.")
                            break
                            
            except Exception as e:
                print(f"[АУДИО] Ошибка во время сеанса: {e}")
            finally:
                print("[АУДИО] <<< Звонок завершен.")
                if player_process:
                    if player_process.stdin:
                        try:
                            player_process.stdin.close()
                        except Exception:
                            pass # Игнорируем ошибку, если поток уже закрыт
                    player_process.terminate()
                    player_process.wait()

if __name__ == "__main__":
    my_ip: str = get_local_ip()
    print("=" * 50)
    print(" ЗАПУСК ASTRA NATIVE SERVER")
    print(f" ВАШ IP АДРЕС ДЛЯ КЛИЕНТА: {my_ip}")
    print(f" НАЧАЛЬНЫЙ КЛЮЧ: {CURRENT_KEY_HEX}")
    print("=" * 50)
    
    api_thread: threading.Thread = threading.Thread(target=api_server_loop, daemon=True)
    api_thread.start()

    audio_thread: threading.Thread = threading.Thread(target=audio_server_loop, daemon=True)
    audio_thread.start()

    print("[БОТ] Попытка подключения к Telegram...")
    try:
        bot.polling(none_stop=True, interval=3, timeout=20)
    except Exception as e:
        print("\n[ВНИМАНИЕ] Чат-бот недоступен (нет интернета)")
        print("[СЕРВЕР] Переход в автономный режим. Локальная связь активна.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[СЕРВЕР] Остановка автономного режима...")
    except KeyboardInterrupt:
        print("\n[СЕРВЕР] Остановка сервера...")
