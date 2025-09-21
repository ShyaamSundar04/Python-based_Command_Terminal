# Python-based_Command_Terminal


A lightweight Python-based command terminal backend (CLI) with:
- Basic file and directory operations (ls, cd, pwd, mkdir, rm, touch, cat, mv, cp)
- Error handling for invalid commands
- System monitoring (cpu, mem, processes) using psutil if present, otherwise fallback
- Persistent command history (~/.py_terminal_history)
- Tab auto-completion for known commands and filesystem paths using readline
- Command history navigation (via readline)
- Ability to run arbitrary system commands as fallback (e.g., git, python) via subprocess

▶️ Run: python py_terminal.py
