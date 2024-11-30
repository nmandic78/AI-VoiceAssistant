# main.py

import os, sys, time
import platform
import threading
import signal
from pynput import keyboard
from pynput.keyboard import Controller, Key
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QAction
import pyperclip

import shutil
from pathlib import Path
try:
    import GPUtil
except ImportError:
    GPUtil = None

# Import modules
import stt_module
import llm_module

# Communicator class to handle signals between threads
class Communicator(QObject):
    start_transcription = pyqtSignal()
    stop_transcription = pyqtSignal()

kb_controller = Controller()

# Initialize global variables
query = ''
base_system_prompt = ''
llm_memory = False



def gather_system_info():
    info = {}

    # OS info
    info["os"] = platform.system()
    info["os_version"] = platform.version()
    info["os_release"] = platform.release()
    if info["os"] == "Linux":
        try:
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME='):
                        info["os_distribution"] = line.strip().split('=')[1].strip('"')
                        break
        except FileNotFoundError:
            info["os_distribution"] = "Unknown"
    else:
        info["os_distribution"] = "Unknown"

    # Shell
    info["shell"] = os.environ.get("SHELL", "cmd" if info["os"] == "Windows" else "Unknown")

    # CPU info
    info["cpu"] = platform.processor()

    # GPU info
    if GPUtil:
        gpus = GPUtil.getGPUs()
        info["gpus"] = [gpu.name for gpu in gpus]
    else:
        info["gpus"] = "GPUtil not installed"

    # Python version
    info["python_version"] = platform.python_version()

    # Path separator
    info["path_separator"] = os.path.sep

    # Home directory
    info["home_directory"] = str(Path.home())

    # Package manager (Linux)
    if info["os"] == "Linux":
        if shutil.which("apt"):
            info["package_manager"] = "apt"
        elif shutil.which("yum"):
            info["package_manager"] = "yum"
        elif shutil.which("dnf"):
            info["package_manager"] = "dnf"
        else:
            info["package_manager"] = "Unknown"

    # Root/admin privileges
    info["is_admin"] = os.geteuid() == 0 if info["os"] != "Windows" else os.environ.get("USERNAME") == "Administrator"

    return info

def create_system_prompt():
    base_system_prompt = (
        "You are an expert AI system specializing in generating clean and concise code or shell commands. "
        "Provide only the requested output in the most efficient and direct manner. "
        "When given a task, respond exclusively with functional code or shell commands, avoiding any additional explanations, comments, or docstrings. "
        "If task is not writing code, assume you are in the shell. "
    )
    
    # Gather system info
    system_info = gather_system_info()
    
    # Add system information to the prompt
    system_info_prompt = (
        f"\n\nCurrent System Information:\n"
        f"- OS: {system_info['os']} {system_info.get('os_distribution', '')} {system_info['os_release']}\n"
        f"- Shell: {system_info['shell']}\n"
        f"- CPU: {system_info['cpu']}\n"
    )
    if system_info["gpus"] != "GPUtil not installed":
        system_info_prompt += f"- GPU: {', '.join(system_info['gpus'])}\n"
    system_info_prompt += (
        f"- Python Version: {system_info['python_version']}\n"
        f"- Path Separator: {system_info['path_separator']}\n"
        f"- Home Directory: {system_info['home_directory']}\n"
    )
    if system_info["os"] == "Linux":
        system_info_prompt += f"- Package Manager: {system_info['package_manager']}\n"
    system_info_prompt += f"- Admin Privileges: {system_info['is_admin']}\n"
    
    # Combine base prompt with system info
    full_prompt = base_system_prompt + system_info_prompt
    
    return full_prompt

def set_initial_conversation_history(system_prompt):
    llm_module.conversation_history = [
    {
        "role": "system",
        "content": system_prompt
    }
]

def on_activate_start(comm):
    print("Hotkey Cmd+Shift pressed.")
    comm.start_transcription.emit()

def on_activate_stop(comm):
    print("Hotkey Cmd+Ctrl pressed.")
    comm.stop_transcription.emit()

def hotkey_listener(comm):
    """
    Listens for global hotkeys and emits signals accordingly.
    """
    # Detect the OS
    os_name = platform.system()

    # Define hotkeys based on the OS
    if os_name == "Linux":
        hotkeys = {
            '<cmd>+<shift>': lambda: on_activate_start(comm),
            '<cmd>+<ctrl>': lambda: on_activate_stop(comm)
        }
    elif os_name == "Windows":
        hotkeys = {
            '<win>+<shift>': lambda: on_activate_start(comm),
            '<win>+<ctrl>': lambda: on_activate_stop(comm)
        }
    else:
        print(f"[ERROR] Unsupported OS: {os_name}")
        return

    try:
        with keyboard.GlobalHotKeys(hotkeys) as listener:
            listener.join()
    except Exception as e:
        print(f"[ERROR] Hotkey listener exception: {e}")

def listen():
    """
    Slot to handle starting transcription.
    Runs in the main thread (PyQt event loop), so starts recording in a separate thread.
    """
    try:
        print("Starting transcription...")
        flags = Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus
        stt_module.window.setWindowFlags(stt_module.window.windowFlags() | flags)
        stt_module.window.show()  # Show the PyQt floating window

        # Start recording in a separate thread
        stt_module.start_record_and_transcription()
    except Exception as e:
        print(f"[ERROR] Exception in listen: {e}")

def stop_listen():
    """
    Slot to handle stopping transcription.
    """
    global query
    try:
        print("Stopping transcription...")
        stt_module.stop_record_and_transcription()
        stt_module.window.hide()  # Hide the PyQt floating window
        query = stt_module.final_transcription_text
        print("Final Transcription:", query)
        # Start LLM processing in a separate thread
        threading.Thread(target=llm_answer, daemon=True).start()
    except Exception as e:
        print(f"[ERROR] Exception in stop_listen: {e}")

def add_buffer(input_string):
    """
    If the input string starts with the word 'buffer', remove 'buffer' from the beginning,
    prepend the clipboard content, and return the resulting string.
    Otherwise, return the input string unchanged.
    """
    print('Input string: ', input_string)
    input_string = input_string.lstrip()
    # Check if the string starts with 'buffer' (case-insensitive) considering punctuation
    if input_string.lower().startswith('buffer'):
        print('Using clipboard content.')
        # Get clipboard content
        clipboard_content = pyperclip.paste()

        # Remove 'buffer' (ignoring punctuation or extra spaces after it)
        input_string = input_string[6:].lstrip()

        # Concatenate clipboard content with the modified input string
        return clipboard_content + '\n\n' + input_string
    else:
        print('Clipboard not used.')

    # If the string does not start with 'buffer', return it as is
    return input_string


def llm_answer():
    """
    Processes the transcription using the LLM module.
    """
    global query
    if not llm_memory: 
        set_initial_conversation_history(base_system_prompt)

    try:
        if "cancel" in query.lower():
            print('Query canceled.')
        elif len(query)>=10:
            query = add_buffer(query)
            print("Processing LLM response for query:", query)
            answer = llm_module.get_response(query)
            print('Answer:', answer)

            # Copy the answer to the clipboard
            pyperclip.copy(answer)
            time.sleep(0.1)  # Wait for clipboard to update

            # paste (Ctrl + V)
            kb_controller.press(Key.shift)
            kb_controller.press(Key.ctrl)
            kb_controller.press('v')
            kb_controller.release('v')
            kb_controller.release(Key.ctrl)
            kb_controller.release(Key.shift)
        else:
            print('Query is too short (under 10 characters)')
    except Exception as e:
        print(f"[ERROR] Exception in llm_answer: {e}")

def signal_handler(sig, frame):
    """
    Handle external signals like SIGINT for graceful shutdown.
    """
    print("\nGracefully shutting down...")
    stt_module.stop_record_and_transcription()
    QApplication.quit()

def quit_app():
    """
    Handle the Quit action from the system tray.
    """
    print("\nQuitting application via system tray...")
    stt_module.stop_record_and_transcription()
    QApplication.quit()

def memory_toggled(checked):
    global llm_memory
    status = "enabled" if checked else "disabled"
    llm_memory = True if checked else False
    print(f"LLM memory is now {status}")

def main():
    global base_system_prompt
    # Initialize the PyQt application
    app = QApplication(sys.argv)

    # Initialize the floating window (PyQt)
    stt_module.init_window()  # Ensure this creates a valid QWidget and assigns to stt_module.window

    # Initialize the communicator
    communicator = Communicator()

    # Connect signals to slots
    communicator.start_transcription.connect(listen)
    communicator.stop_transcription.connect(stop_listen)

    # Start the hotkey listener in a separate daemon thread
    hotkey_thread = threading.Thread(target=hotkey_listener, args=(communicator,), daemon=True)
    hotkey_thread.start()

    # Setup System Tray Icon
    tray_icon = QSystemTrayIcon(QIcon("AI1b.ico"), parent=app)
    tray_menu = QMenu()

    # LLM memory checkbox
    checkbox_action = QAction("Enable Memory")
    checkbox_action.setCheckable(True)
    checkbox_action.toggled.connect(memory_toggled)
    tray_menu.addAction(checkbox_action)

    quit_action = QAction("Quit")
    #quit_action.triggered.connect(signal_handler)
    quit_action.triggered.connect(quit_app)

    tray_menu.addAction(quit_action)
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()

    base_system_prompt = create_system_prompt()
    set_initial_conversation_history(base_system_prompt)

    print("Hotkey listeners started.")
    print("Press Cmd + SHIFT to start transcription (global).")
    print("Press Cmd + CTRL to stop transcription (global).")
    print("Use the system tray icon to quit the application.")

    # Install the custom signal handler for SIGINT
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Start the PyQt event loop
        sys.exit(app.exec())
    except KeyboardInterrupt:
        # This block might still be reached, but the signal handler should manage the shutdown
        print("\nExiting program.")
    finally:
        # Cleanup if necessary
        stt_module.stop_record_and_transcription()

if __name__ == "__main__":
    main()
