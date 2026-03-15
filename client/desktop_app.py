import threading
import socket
import pyaudio
import crypto_logic

from kivymd.app import MDApp
from kivymd.uix.screen import Screen
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRectangleFlatIconButton, MDFillRoundFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.clock import Clock
from kivy.core.window import Window
from typing import Optional, Any

Window.size = (400, 650)

AUDIO_PORT: int = 9090
API_PORT: int = 9091


class SecurePhonePC(MDApp):
    """Главный класс графического интерфейса приложения на базе KivyMD"""

    def build(self) -> Screen:
        """Построение визуального дерева интерфейса"""
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"

        screen: Screen = Screen()
        layout: MDBoxLayout = MDBoxLayout(orientation='vertical', padding=20, spacing=20)

        layout.add_widget(MDLabel(text="SECURE VOICE\nWINDOWS CLIENT",halign="center",theme_text_color="Custom",text_color=(0, 1, 0.8, 1),font_style="H4"))


        net_card: MDCard = MDCard(orientation='vertical', padding=15, spacing=10, size_hint=(1, None), height=150)
        net_card.add_widget(MDLabel(text="Настройки соединения", font_style="Subtitle1"))
        self.ip_field: MDTextField = MDTextField(hint_text="IP Адрес сервера", text="192.168.0.12")
        net_card.add_widget(self.ip_field)
        layout.add_widget(net_card)


        crypto_card: MDCard = MDCard(orientation='vertical', padding=15, spacing=10, size_hint=(1, None), height=200)
        crypto_card.add_widget(MDLabel(text="Шифрование A5/1", font_style="Subtitle1"))
        self.key_field: MDTextField = MDTextField(hint_text="Секретный ключ", text="")
        crypto_card.add_widget(self.key_field)

        fetch_btn: MDRectangleFlatIconButton = MDRectangleFlatIconButton(text="Синхронизировать ключ",icon="sync",pos_hint={"center_x": 0.5},on_release=self.fetch_key_from_server)
        crypto_card.add_widget(fetch_btn)
        layout.add_widget(crypto_card)

        self.status_label: MDLabel = MDLabel(text="Готов к работе", halign="center", theme_text_color="Secondary")
        layout.add_widget(self.status_label)

        self.call_btn: MDFillRoundFlatButton = MDFillRoundFlatButton(text="ПОЗВОНИТЬ",font_size=20,size_hint=(1, None),height=60,on_release=self.toggle_call)
        layout.add_widget(self.call_btn)
        layout.add_widget(MDLabel(size_hint_y=None, height=10))

        screen.add_widget(layout)

        self.is_calling: bool = False
        self.thread: Optional[threading.Thread] = None

        Clock.schedule_once(self.fetch_key_from_server, 1)

        return screen

    def fetch_key_from_server(self, instance: Any = None) -> None:
        """Инициация фонового процесса запроса ключа у сервера"""
        target_ip: str = self.ip_field.text
        self.status_label.text = "Запрос ключа..."
        threading.Thread(target=self._network_fetch_key, args=(target_ip,), daemon=True).start()

    def _network_fetch_key(self, target_ip: str) -> None:
        """Установление соединения по порту 9091 для получения HEX-строки ключа"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect((target_ip, API_PORT))
                key_hex: str = s.recv(1024).decode('utf-8').strip()

                if key_hex:
                    Clock.schedule_once(lambda dt: self._update_key_ui(key_hex, "Ключ успешно синхронизован"))
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', "Ошибка: Сервер недоступен"))

    def _update_key_ui(self, new_key: str, status_msg: str) -> None:
        """Вспомогательная функция для обновления полей интерфейса"""
        self.key_field.text = new_key
        self.status_label.text = status_msg
        self.status_label.theme_text_color = "Primary"

    def toggle_call(self, instance: Any) -> None:
        """Обработчик нажатия главной кнопки. Переключает состояния звонка."""
        if not self.is_calling:
            self.start_call()
        else:
            self.stop_call()

    def start_call(self) -> None:
        """Визуальная и логическая подготовка к началу трансляции звука"""
        self.is_calling = True
        self.call_btn.text = "ЗАВЕРШИТЬ СВЯЗЬ"
        self.call_btn.md_bg_color = (1, 0, 0, 1)
        self.status_label.text = "Подключение к аудио-порту..."

        self.thread = threading.Thread(target=self.run_audio_client, daemon=True)
        self.thread.start()

    def stop_call(self) -> None:
        """Остановка вызова и возврат интерфейса в исходное состояние"""
        self.is_calling = False
        self.call_btn.text = "ПОЗВОНИТЬ"
        self.call_btn.md_bg_color = self.theme_cls.primary_color
        self.status_label.text = "Связь завершена"

    def run_audio_client(self) -> None:
        """
        Главный рабочий процесс клиента.
        Захватывает звук с микрофона, шифрует алгоритмом A5/1 и отправляет по TCP
        """
        target_ip: str = self.ip_field.text

        try:
            key_int: int = int(self.key_field.text, 16)
        except ValueError:
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', "Ошибка: Неверный формат ключа!"))
            Clock.schedule_once(lambda dt: self.stop_call())
            return

        frame: int = 0x2F # 22

        crypto_logic.init_a51(key_int, frame)

        # 2. Инициализация подсистемы звука
        p: pyaudio.PyAudio = pyaudio.PyAudio()
        stream: Optional[pyaudio.Stream] = None

        try:
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=8000, input=True, frames_per_buffer=1024)

            # 3. Установка сетевого соединения для передачи звука
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((target_ip, AUDIO_PORT))

                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', "В ЭФИРЕ (Шифрование активно)"))

                # 4. Основной цикл захвата и шифрования
                while self.is_calling:
                    # Читаем 1024 байта с микрофона
                    data: bytes = stream.read(1024, exception_on_overflow=False)

                    encrypted: bytes = crypto_logic.encrypt_chunk(data)

                    # Отправляем зашифрованный кусок на сервер
                    s.sendall(encrypted)

        except Exception as e:
            error_msg: str = str(e)
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', f"Ошибка: {error_msg}"))
        finally:
            # 5. Блок корректного освобождения ресурсов при прерывании связи
            if stream is not None:
                stream.stop_stream()
                stream.close()
            p.terminate()

            if self.is_calling:
                Clock.schedule_once(lambda dt: self.stop_call())


SecurePhonePC().run()