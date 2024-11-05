import sys
import os
import tarfile
import csv
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import tkinter as tk
from tkinter import Text, Entry, Button, Scrollbar
import subprocess

class ShellEmulator:
    def __init__(self, root):
        self.root = root
        self.cwd = "papka"  # Корневая директория
        self.vfs = {}
        self.log_file = 'log.xml'
        self.load_config()
        self.load_vfs()
        self.log_action("Session started")
        self.initUI()
        self.set_file_permissions()
        self.run_start_script()

    def set_file_permissions(self):
        file_path = self.start_script
        if os.path.exists(file_path):
            permissions = 0o777
            os.chmod(file_path, permissions)
        else:
            print(f"File not found: {file_path}")

    def load_config(self):
        with open('config.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self.vfs_path = row['Path to VFS Archive']
                self.log_file = row['Path to Log File']
                self.start_script = row['Path to Start Script']

    def load_vfs(self):
        with tarfile.open(self.vfs_path, 'r') as tar:
            for member in tar.getmembers():
                if member.isfile():
                    file_content = tar.extractfile(member).read().decode('utf-8')
                    self.vfs[member.name] = file_content
                else:
                    self.vfs[member.name] = None

    def log_action(self, action):
        try:
            tree = ET.parse(self.log_file)
            root = tree.getroot()
        except FileNotFoundError:
            root = ET.Element("log")

        entry = ET.SubElement(root, "entry")
        entry.set("timestamp", datetime.now().isoformat())
        entry.text = action

        tree = ET.ElementTree(root)
        tree.write(self.log_file, encoding='utf-8', xml_declaration=True)

    def initUI(self):
        self.root.title('Shell Emulator')
        self.root.geometry('800x600')

        # Создаем текстовое поле для вывода команд и результатов
        self.output_text = Text(self.root, state='disabled', wrap='none', bg='black', fg='white',
                                insertbackground='white')
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # Добавляем полосу прокрутки для вывода
        self.output_scrollbar = Scrollbar(self.root, command=self.output_text.yview)
        self.output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.config(yscrollcommand=self.output_scrollbar.set)

        # Создаем текстовое поле для ввода команд
        self.input_text = Text(self.root, height=1, wrap='none', bg='black', fg='white', insertbackground='white')
        self.input_text.pack(fill=tk.X)

        # Привязываем событие нажатия клавиши Enter
        self.input_text.bind('<Return>', self.execute_command)

    def run_start_script(self):
        try:
            script_path = os.path.abspath(self.start_script)
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"File not found: {script_path}")

            with open(script_path, 'r', encoding='utf-8') as file:
                commands = file.read().strip().split('\n')

            for command in commands:
                self.output_text.config(state='normal')
                # Выводим корректное приглашение с "~" для корневой директории
                prompt_path = "~" if self.cwd == "papka" else self.cwd
                self.output_text.insert(tk.END, f"user@shell:{prompt_path}$ {command}\n")
                self.output_text.config(state='disabled')

                # Выполняем команду без добавления нового приглашения
                self.execute_command(None, command, from_start_script=True)

            self.log_action(f"Executed start script: {script_path}")

            # После выполнения всех команд добавляем одно приглашение для пользователя
            self.prompt()  # Теперь вызов prompt здесь

        except Exception as e:
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, f"Error executing start script: {e}\n")
            self.output_text.config(state='disabled')
            self.log_action(f"Error executing start script: {e}")

    def execute_command(self, event=None, command=None, from_start_script=False):
        if command is None:
            command = self.input_text.get("1.0", tk.END).strip()
            self.input_text.delete("1.0", tk.END)

        if not from_start_script:
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, f"{command}\n")
            self.output_text.config(state='disabled')

        self.log_action(command)
        parts = command.split()
        if not parts:
            return

        cmd = parts[0]
        args = parts[1:]

        if cmd == "ls":
            self.ls(args)
        elif cmd == "cd":
            self.cd(args)  # cd уже вызывает prompt внутри
            self.output_text.see(tk.END)  # Убедитесь, что прокрутка вниз вызывается здес
        elif cmd == "echo":
            self.echo(args)
        elif cmd == "mv":
            self.mv(args)
        elif cmd == "find":
            self.find(args)
        elif cmd == "exit":
            self.root.quit()
        else:
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, f"Command not found: {cmd}\n")
            self.output_text.config(state='disabled')

        # Добавляем prompt только для интерактивных команд
        if not from_start_script and cmd != "cd":
            self.prompt()  # Здесь prompt также вызывается
            self.output_text.see(tk.END)  # Здесь прокрутка тоже будет срабатывать

    def load_vfs(self):
        with tarfile.open(self.vfs_path, 'r') as tar:
            for member in tar.getmembers():
                if member.isfile():
                    file_content = tar.extractfile(member).read().decode('utf-8')
                    self.vfs[member.name] = {
                        'content': file_content,
                        'size': len(file_content),
                        'mtime': member.mtime
                    }
                else:
                    self.vfs[member.name] = {
                        'content': None,  # Папка
                        'size': 4096,  # Размер метаданных папки
                        'mtime': member.mtime
                    }
            # Отладочный вывод
            print("Loaded VFS structure:")
            for key, value in self.vfs.items():
                print(f"{key}: {value}")

    def ls(self, args):
        path = self.cwd
        if path in self.vfs:
            if self.vfs[path]['content'] is None:  # Это директория
                files = [f for f in self.vfs.keys() if f.startswith(path + '/') and f.count('/') == path.count('/') + 1]

                long_format = "-l" in args
                human_readable = "-h" in args

                output_lines = []

                for file in files:
                    full_path = file
                    file_info = self.vfs[full_path]

                    size = file_info['size']

                    # Преобразуем размер в человеко-читаемый формат, если задан флаг -h
                    size_display = self.human_readable_size(size) if human_readable else str(size)

                    if long_format:
                        type_flag = 'd' if file_info['content'] is None else '-'
                        permissions = "rw-rw-r--"  # Убедитесь, что у вас есть способ установить права доступа
                        owner = "user"
                        group = "user"
                        last_modified = time.strftime('%b %d %H:%M', time.localtime(file_info['mtime']))

                        output_lines.append(
                            f"{type_flag}{permissions} 1 {owner} {group} {size_display} {last_modified} {file.split('/')[-1]}")
                    else:
                        output_lines.append(file.split('/')[-1])

                self.output_text.config(state='normal')
                self.output_text.insert(tk.END, "\n".join(output_lines) + "\n")
                self.output_text.see(tk.END)
                self.output_text.config(state='disabled')
            else:
                # Этот блок будет выполняться, если текущий путь не является директорией
                self.output_text.config(state='normal')
                self.output_text.insert(tk.END, f"{path} is not a directory\n")
                self.output_text.config(state='disabled')
        else:
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, "Directory not found\n")
            self.output_text.see(tk.END)
            self.output_text.config(state='disabled')

    def human_readable_size(self, size):
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 ** 3:
            return f"{size / (1024 ** 2):.1f} MB"
        else:
            return f"{size / (1024 ** 3):.1f} GB"

    def get_size_recursive(self, path):
        total_size = 0
        for item in self.vfs.keys():
            if item.startswith(path + '/') and item != path:  # Убедитесь, что это не сам путь
                total_size += self.vfs[item]['size']
        return total_size

    def ls_recursive(self, path, files):
        self.output_text.config(state='normal')
        self.output_text.insert(tk.END, f"{path}:\n")
        self.output_text.insert(tk.END, "\n".join(files) + "\n\n")
        self.output_text.config(state='disabled')

        for file in files:
            if self.vfs[file] is None:  # Directory
                sub_files = [f for f in self.vfs.keys() if f.startswith(file) and f != file]
                self.ls_recursive(file, sub_files)

    def cd(self, args):
        # Перемещение на один каталог вверх
        if not args:
            self.cwd = "papka"  # Если нет аргументов, переходим в корневую директорию
        else:
            path = args[0]

            if path == "..":  # Переход на один уровень вверх
                if self.cwd != "papka":  # Если мы не находимся в корневом каталоге
                    self.cwd = "/".join(self.cwd.split("/")[:-1]) or "papka"
            elif path == "-":  # Возвращение в предыдущий каталог
                if hasattr(self, 'prev_cwd'):
                    self.cwd, self.prev_cwd = self.prev_cwd, self.cwd
                else:
                    self.output_text.config(state='normal')
                    self.output_text.insert(tk.END, "No previous directory\n")
                    self.output_text.config(state='disabled')
                    self.prompt()  # Обновление приглашения
                    return
            elif path == "/":  # Переход в корневую директорию
                self.cwd = "papka"  # Или используйте любую другую строку, обозначающую корневую директорию
            else:
                # Нормализация пути
                components = self.cwd.strip("/").split("/") + path.split("/")
                normalized_components = []

                for component in components:
                    if component == "" or component == ".":  # Пропускаем пустые и текущие директории
                        continue
                    elif component == "..":  # Подъем на уровень вверх
                        if normalized_components:
                            normalized_components.pop()  # Убираем последний элемент
                    else:
                        normalized_components.append(component)  # Добавляем текущую директорию

                # Сборка нормализованного пути
                full_vfs_path = "/".join(normalized_components).strip("/")

                # Проверяем, существует ли целевой путь в VFS и является ли он директорией
                if full_vfs_path in self.vfs and self.vfs[full_vfs_path]['content'] is None:
                    self.prev_cwd = self.cwd  # Сохраняем предыдущий каталог
                    self.cwd = full_vfs_path  # Обновляем текущую директорию
                else:
                    self.output_text.config(state='normal')
                    self.output_text.insert(tk.END, f"cd: no such file or directory: {path}\n")
                    self.output_text.config(state='disabled')
                    self.prompt()  # Обновление приглашения после ошибки
                    return

        self.prompt()  # Обновление приглашения после успешного выполнения команды

    def echo(self, args):
        self.output_text.config(state='normal')
        self.output_text.insert(tk.END, " ".join(args) + "\n")
        self.output_text.config(state='disabled')

    def mv(self, args):
        if len(args) == 2:
            src, dest = args
            if src in self.vfs:
                self.vfs[dest] = self.vfs.pop(src)
                self.output_text.config(state='normal')
                self.output_text.insert(tk.END, f"Moved {src} to {dest}\n")
                self.output_text.config(state='disabled')
            else:
                self.output_text.config(state='normal')
                self.output_text.insert(tk.END, "File not found\n")
                self.output_text.config(state='disabled')
        else:
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, "Usage: mv <source> <destination>\n")
            self.output_text.config(state='disabled')

    def find(self, args):
        if not args:
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, "Usage: find <filename>\n")
            self.output_text.config(state='disabled')
            return

        filename = args[0]
        found = [f for f in self.vfs.keys() if filename in f]
        self.output_text.config(state='normal')
        self.output_text.insert(tk.END, "\n".join(found) if found else "File not found\n")
        self.output_text.config(state='disabled')

    def prompt(self):
        self.output_text.config(state='normal')
        # Проверяем, если cwd равен "papka", то заменяем его на "~"
        prompt_path = "~" if self.cwd == "papka" else self.cwd.replace("papka/", "~/")
        self.output_text.insert(tk.END, f"user@shell:{prompt_path}$ ")
        self.output_text.config(state='disabled')

        # Автоматически прокручиваем вниз после добавления приглашения
        self.output_text.see(tk.END)


if __name__ == '__main__':
    root = tk.Tk()
    shell = ShellEmulator(root)
    root.mainloop()