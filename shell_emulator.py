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

    def run_start_script(self):
        try:
            # Получаем абсолютный путь к файлу start_script.sh
            script_path = os.path.abspath(self.start_script)
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"File not found: {script_path}")

            # Путь к bash.exe в Git Bash
            git_bash_path = r"C:\Program Files\Git\bin\bash.exe"

            result = subprocess.run([git_bash_path, script_path], capture_output=True, text=True, encoding='utf-8')
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, result.stdout)
            self.output_text.config(state='disabled')
            self.log_action(f"Executed start script: {script_path}")
        except Exception as e:
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, f"Error executing start script: {e}\n")
            self.output_text.config(state='disabled')
            self.log_action(f"Error executing start script: {e}")

        # Добавляем постоянное приглашение после выполнения стартового скрипта
        self.prompt()

    def initUI(self):
        self.root.title('Shell Emulator')
        self.root.geometry('800x600')

        # Создаем текстовое поле для вывода команд и результатов
        self.output_text = Text(self.root, state='disabled', wrap='none', bg='black', fg='white', insertbackground='white')
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

        # Добавляем постоянное приглашение
        self.prompt()

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

    def execute_command(self, event=None):
        # Получаем текст команды
        command = self.input_text.get("1.0", tk.END).strip()
        self.input_text.delete("1.0", tk.END)

        self.output_text.config(state='normal')
        self.output_text.insert(tk.END, f"{command}\n")
        self.output_text.see(tk.END)  # Автоматически прокручиваем вниз
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
            self.output_text.see(tk.END)  # Автоматически прокручиваем вниз
            self.output_text.config(state='disabled')

        # Добавляем постоянное приглашение после выполнения команды
        self.prompt()
        self.output_text.see(tk.END)  # Автоматически прокручиваем вниз после добавления приглашения

    def ls(self, args):
        path = self.cwd if not args else os.path.join(self.cwd, args[0])
        if path in self.vfs:
            if self.vfs[path] is None:  # Directory
                files = [f for f in self.vfs.keys() if f.startswith(path) and f != path]
                if "-R" in args:
                    self.ls_recursive(path, files)
                else:
                    self.output_text.config(state='normal')
                    self.output_text.insert(tk.END, "\n".join(files) + "\n")
                    self.output_text.config(state='disabled')
            else:
                self.output_text.config(state='normal')
                self.output_text.insert(tk.END, self.vfs[path] + "\n")
                self.output_text.config(state='disabled')
        else:
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, "Directory not found\n")
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
            self.cwd = "papka"
        else:
            new_path = os.path.join(self.cwd, args[0])
            if new_path == "..":
                # Переход в родительский каталог
                self.cwd = os.path.dirname(self.cwd)
                if self.cwd == "":
                    self.cwd = "papka"
            elif new_path in self.vfs and self.vfs[new_path] is None:
                self.cwd = new_path
            else:
                self.output_text.config(state='normal')
                self.output_text.insert(tk.END, "Directory not found\n")
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
        prompt_path = self.cwd if self.cwd != "papka" else "~"
        self.output_text.insert(tk.END, f"user@shell:{prompt_path}$ ")
        self.output_text.config(state='disabled')


if __name__ == '__main__':
    root = tk.Tk()
    shell = ShellEmulator(root)
    root.mainloop()