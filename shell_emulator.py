import sys
import os
import tarfile
import csv
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

                self.execute_command(None, command, from_start_script=True)

            self.log_action(f"Executed start script: {script_path}")

            # После выполнения всех команд добавляем одно приглашение для пользователя
            self.prompt()
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
            self.cd(args)
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

        # Приглашение добавляется только, если команда не из стартового скрипта
        if not from_start_script:
            self.prompt()

    def ls(self, args):
        path = self.cwd
        if path in self.vfs:
            if self.vfs[path] is None:  # Directory
                files = [f.replace(path + '/', '') for f in self.vfs.keys() if
                         f.startswith(path + '/') and f.count('/') == 1]
                if "-R" in args:
                    self.ls_recursive(path, files)
                else:
                    if "-a" in args:
                        # Выводим все файлы, включая скрытые
                        files = [f.replace(path + '/', '') for f in self.vfs.keys() if f.startswith(path + '/')]
                    if "-l" in args:
                        # Выводим подробную информацию о файлах
                        files_info = []
                        for file in files:
                            full_path = path + '/' + file
                            file_info = f"{full_path} - Size: {len(self.vfs[full_path])} bytes" if self.vfs[
                                full_path] else f"{full_path} - Directory"
                            files_info.append(file_info)
                        files = files_info
                    if "-F" in args:
                        # Добавляем символы, характеризующие тип
                        files = [f + '/' if self.vfs[path + '/' + f] is None else f for f in files]

                    self.output_text.config(state='normal')
                    self.output_text.insert(tk.END, "\n".join(files) + "\n")
                    self.output_text.see(tk.END)  # Автоматически прокручиваем вниз
                    self.output_text.config(state='disabled')
            else:
                self.output_text.config(state='normal')
                self.output_text.insert(tk.END, self.vfs[path] + "\n")
                self.output_text.see(tk.END)  # Автоматически прокручиваем вниз
                self.output_text.config(state='disabled')
        else:
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, "Directory not found\n")
            self.output_text.see(tk.END)  # Автоматически прокручиваем вниз
            self.output_text.config(state='disabled')

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
        if not args:
            # Если нет аргументов, переходим в корневую директорию
            self.cwd = "papka"
        else:
            path = args[0]  # Получаем путь из аргумента

            # Если путь абсолютный
            if path.startswith("/"):
                new_dir = ["papka"]  # Абсолютный путь, начинаем с "papka"
                path = path[1:]  # Убираем слэш в начале
            else:
                # Относительный путь от текущей директории
                new_dir = self.cwd.strip("/").split("/") if self.cwd != "papka" else []

            # Разбиваем путь на части
            parts = path.split("/")

            for part in parts:
                if part == "..":
                    # Переход на уровень выше
                    if len(new_dir) > 0:  # Не выходим за пределы корня
                        new_dir.pop()
                elif part == "." or part == "":  # Игнорируем текущий каталог (".") и пустые сегменты
                    continue
                else:
                    new_dir.append(part)  # Добавляем папку в новый путь

            # Собираем полный путь
            full_path = "/" + "/".join(new_dir).strip("/")

            # Проверяем, что конечный путь существует в виртуальной файловой системе
            if full_path in self.vfs and self.vfs[full_path] is None:  # Это каталог
                self.cwd = full_path  # Обновляем текущую директорию
            else:
                # Если путь не существует, выводим ошибку
                self.output_text.config(state='normal')
                self.output_text.insert(tk.END, f"cd: no such file or directory: {path}\n")
                self.output_text.see(tk.END)  # Автоматически прокручиваем вниз
                self.output_text.config(state='disabled')

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
        prompt_path = "~" if self.cwd == "papka" else self.cwd
        self.output_text.insert(tk.END, f"user@shell:{prompt_path}$ ")
        self.output_text.config(state='disabled')


if __name__ == '__main__':
    root = tk.Tk()
    shell = ShellEmulator(root)
    root.mainloop()