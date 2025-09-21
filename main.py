#!/usr/bin/env python3
import os
import sys
import shlex
import subprocess
import shutil
import stat
import glob
import platform
from pathlib import Path
from datetime import datetime

#dependencies
try:
    import psutil
    HAS_PSUTIL = True
except Exception:
    HAS_PSUTIL = False

#readline
READLINE_AVAILABLE = True
try:
    import readline
    import rlcompleter
except Exception:
    try:
        import pyreadline as readline
        import rlcompleter
    except Exception:
        READLINE_AVAILABLE = False

#for configuration
HISTORY_FILE = Path.home() / ".py_terminal_history"
PROMPT = lambda cwd: f"py_terminal:{cwd}$ "

#Built-in commands
BUILTINS = [
    "ls", "cd", "pwd", "mkdir", "rm", "rmdir", "cat", "touch", "mv", "cp", "help",
    "exit", "quit", "clear", "sysinfo", "ps", "top", "history"
]

#Utility functions
def path_complete(text):
    """Return filesystem completions that match text."""
    expanded = os.path.expanduser(text)
    matches = glob.glob(expanded + "*")
    results = []
    for m in matches:
        # make ~ representation
        m_path = Path(m).as_posix()
        if str(m).startswith(str(Path.home())):
            m_sh = "~" + m_path[len(str(Path.home())):]
        else:
            m_sh = m_path
        #trailing slash for directories
        if os.path.isdir(m):
            m_sh += "/"
        results.append(m_sh)
    return results

def list_dir(path="."):
    try:
        entries = os.listdir(path)
    except Exception as e:
        raise
    out = []
    for name in sorted(entries):
        try:
            p = Path(path) / name
            if p.is_dir():
                out.append(name + "/")
            elif p.is_symlink():
                out.append(name + "@")
            else:
                out.append(name)
        except Exception:
            out.append(name)
    return out

def human_bytes(n):
    for unit in ['B','KB','MB','GB','TB','PB']:
        if abs(n) < 1024.0:
            return "%3.1f%s" % (n, unit)
        n /= 1024.0
    return "%.1f%s" % (n, 'EB')

#command implementations
def cmd_ls(args):
    path = args[0] if args else "."
    try:
        items = list_dir(path)
    except Exception as e:
        return f"ls: cannot access '{path}': {e}"
    return "\n".join(items)

def cmd_cd(args):
    if not args:
        target = str(Path.home())
    else:
        target = args[0]
    try:
        os.chdir(os.path.expanduser(target))
    except Exception as e:
        return f"cd: {e}"
    return ""

def cmd_pwd(args):
    return os.getcwd()

def cmd_mkdir(args):
    if not args:
        return "mkdir: missing operand"
    outputs = []
    for d in args:
        try:
            Path(os.path.expanduser(d)).mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            outputs.append(f"mkdir: cannot create directory '{d}': File exists")
        except Exception as e:
            outputs.append(f"mkdir: {d}: {e}")
    return "\n".join(outputs)

def cmd_rm(args):
    if not args:
        return "rm: missing operand"
    outputs = []
    for target in args:
        path = Path(os.path.expanduser(target))
        try:
            if path.is_dir() and not path.is_symlink():
                try:
                    path.rmdir()
                except OSError:
                    outputs.append(f"rm: cannot remove '{target}': Directory not empty")
            else:
                path.unlink()
        except FileNotFoundError:
            outputs.append(f"rm: cannot remove '{target}': No such file or directory")
        except Exception as e:
            outputs.append(f"rm: {target}: {e}")
    return "\n".join(outputs)

def cmd_rmdir(args):
    if not args:
        return "rmdir: missing operand"
    outs = []
    for d in args:
        try:
            Path(os.path.expanduser(d)).rmdir()
        except Exception as e:
            outs.append(f"rmdir: {d}: {e}")
    return "\n".join(outs)

def cmd_cat(args):
    if not args:
        return "cat: missing operand"
    out_lines = []
    for fname in args:
        try:
            with open(os.path.expanduser(fname), "r", encoding="utf-8", errors="replace") as f:
                out_lines.append(f.read())
        except Exception as e:
            out_lines.append(f"cat: {fname}: {e}")
    return "\n".join(out_lines)

def cmd_touch(args):
    if not args:
        return "touch: missing operand"
    outs = []
    for t in args:
        p = Path(os.path.expanduser(t))
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.now().timestamp()
            if p.exists():
                os.utime(p, (now, now))
            else:
                p.write_text("", encoding="utf-8")
        except Exception as e:
            outs.append(f"touch: {t}: {e}")
    return "\n".join(outs)

def cmd_mv(args):
    if len(args) < 2:
        return "mv: missing operand"
    *sources, dest = args
    dest = Path(os.path.expanduser(dest))
    outs = []
    try:
        if len(sources) > 1:
            dest.mkdir(parents=True, exist_ok=True)
            for s in sources:
                try:
                    shutil.move(s, str(dest))
                except Exception as e:
                    outs.append(f"mv: {s}: {e}")
        else:
            try:
                shutil.move(sources[0], str(dest))
            except Exception as e:
                outs.append(f"mv: {sources[0]}: {e}")
    except Exception as e:
        outs.append(str(e))
    return "\n".join(outs)

def cmd_cp(args):
    if len(args) < 2:
        return "cp: missing operand"
    *sources, dest = args
    dest = Path(os.path.expanduser(dest))
    outs = []
    try:
        if len(sources) > 1:
            dest.mkdir(parents=True, exist_ok=True)
            for s in sources:
                try:
                    s_path = Path(os.path.expanduser(s))
                    shutil.copy2(str(s_path), str(dest / s_path.name))
                except Exception as e:
                    outs.append(f"cp: {s}: {e}")
        else:
            s_path = Path(os.path.expanduser(sources[0]))
            if dest.is_dir():
                target = dest / s_path.name
            else:
                target = dest
            try:
                if s_path.is_dir():
                    shutil.copytree(str(s_path), str(target))
                else:
                    shutil.copy2(str(s_path), str(target))
            except Exception as e:
                outs.append(f"cp: {s_path}: {e}")
    except Exception as e:
        outs.append(str(e))
    return "\n".join(outs)

def cmd_clear(args):
    #Clear
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")
    return ""

def cmd_help(args):
    help_text = """
Built-in commands:
  ls [path]        - list directory contents
  cd [dir]         - change directory
  pwd              - print current working directory
  mkdir NAME...    - create directories
  rm NAME...       - remove files (won't remove non-empty dirs)
  rmdir NAME...    - remove empty directories
  cat FILE...      - print file contents
  touch FILE...    - create or update timestamp
  mv SRC... DEST   - move files or directories
  cp SRC... DEST   - copy files or directories
  clear            - clear the screen
  sysinfo          - show system information & resource usage
  ps               - list processes
  top              - show top CPU-consuming processes (limited)
  history          - show command history
  help             - show this help
  exit/quit        - quit the terminal

You may also run any system command (e.g., git, python) — output will be shown if available.
"""
    return help_text.strip()

#Monitoring and process listing
def cmd_sysinfo(args):
    sys_lines = []
    sys_lines.append(f"Platform: {platform.platform()}")
    sys_lines.append(f"Python: {sys.version.splitlines()[0]}")
    sys_lines.append(f"CWD: {os.getcwd()}")
    #Disk usage
    try:
        usage = shutil.disk_usage(os.getcwd())
        sys_lines.append(f"Disk: total={human_bytes(usage.total)} used={human_bytes(usage.used)} free={human_bytes(usage.free)}")
    except Exception:
        pass
    if HAS_PSUTIL:
        cpu_pct = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        sys_lines.append(f"CPU: {cpu_pct}%")
        sys_lines.append(f"Memory: {mem.percent}% ({human_bytes(mem.used)} / {human_bytes(mem.total)})")
    else:
        #Fallback:try os.getloadavg on Unix
        try:
            if hasattr(os, "getloadavg"):
                load1, load5, load15 = os.getloadavg()
                sys_lines.append(f"Load Average (1m/5m/15m): {load1:.2f} {load5:.2f} {load15:.2f}")
            else:
                sys_lines.append("CPU/Memory: install 'psutil' for more detailed stats")
        except Exception:
            pass
    return "\n".join(sys_lines)

def cmd_ps(args):
    lines = []
    if HAS_PSUTIL:
        lines.append(f"{'PID':>6} {'USER':>10} {'CPU%':>5} {'MEM%':>5} CMD")
        for p in psutil.process_iter(['pid', 'username', 'cpu_percent', 'memory_percent', 'name', 'cmdline']):
            try:
                pid = p.info['pid']
                user = (p.info['username'] or "")[:10]
                cpu = p.info['cpu_percent'] or 0.0
                mem = p.info['memory_percent'] or 0.0
                cmdline = " ".join(p.info.get('cmdline') or [p.info.get('name') or ""])
                lines.append(f"{pid:6d} {user:10} {cpu:5.1f} {mem:5.1f} {cmdline}")
            except Exception:
                continue
    else:
        #fallback to tasklist
        try:
            if platform.system() == "Windows":
                out = subprocess.check_output(["tasklist"], universal_newlines=True, stderr=subprocess.DEVNULL)
                return out
            else:
                out = subprocess.check_output(["ps", "aux"], universal_newlines=True, stderr=subprocess.DEVNULL)
                return out
        except Exception as e:
            return f"ps: error: {e}\n(install psutil for better process info)"
    return "\n".join(lines)

def cmd_top(args):
    #Simple top-like display
    procs = []
    if HAS_PSUTIL:
        for p in psutil.process_iter(['pid', 'cpu_percent', 'memory_percent', 'name', 'cmdline']):
            try:
                info = p.info
                procs.append(info)
            except Exception:
                pass
        procs_sorted = sorted(procs, key=lambda i: (i.get('cpu_percent') or 0.0), reverse=True)[:10]
        lines = [f"{'PID':>6} {'CPU%':>5} {'MEM%':>5} CMD"]
        for i in procs_sorted:
            pid = i.get('pid')
            cpu = i.get('cpu_percent') or 0.0
            mem = i.get('memory_percent') or 0.0
            cmd = " ".join(i.get('cmdline') or [i.get('name') or ""])
            lines.append(f"{pid:6d} {cpu:5.1f} {mem:5.1f} {cmd}")
        return "\n".join(lines)
    else:
        return "top: install 'psutil' for top-like output (fallback not implemented)."

def cmd_history(args):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = [l.rstrip("\n") for l in f.readlines()]
        numbered = [f"{i+1}: {l}" for i, l in enumerate(lines)]
        return "\n".join(numbered)
    except FileNotFoundError:
        return "(no history)"
    except Exception as e:
        return f"history: {e}"

#Command dispatcher
DISPATCH = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "pwd": cmd_pwd,
    "mkdir": cmd_mkdir,
    "rm": cmd_rm,
    "rmdir": cmd_rmdir,
    "cat": cmd_cat,
    "touch": cmd_touch,
    "mv": cmd_mv,
    "cp": cmd_cp,
    "clear": cmd_clear,
    "help": cmd_help,
    "sysinfo": cmd_sysinfo,
    "ps": cmd_ps,
    "top": cmd_top,
    "history": cmd_history,
}

#Completion function
def completer(text, state):
    """
    Provide completions for built-in commands and filesystem paths.
    Called repeatedly with increasing state 0,1,... until returns None.
    """
    buffer = readline.get_line_buffer() if READLINE_AVAILABLE else ""
    begidx = readline.get_begidx() if READLINE_AVAILABLE else 0
    # decide completion candidates
    candidates = []
    if begidx == 0:
        #complete command names
        candidates = [c for c in BUILTINS if c.startswith(text)]
        #include system commands
        path_dirs = os.getenv("PATH", "").split(os.pathsep)
        seen = set(candidates)
        for d in path_dirs:
            if not d:
                continue
            try:
                for f in os.listdir(d):
                    if f.startswith(text) and f not in seen:
                        candidates.append(f)
                        seen.add(f)
            except Exception:
                continue
    else:
        #completing arguments
        candidates = path_complete(text)
    try:
        return candidates[state]
    except IndexError:
        return None

def run_external_command(cmd_tokens):
    """Run arbitrary system command and return output or error text."""
    try:
        out = subprocess.check_output(cmd_tokens, stderr=subprocess.STDOUT, universal_newlines=True)
        return out
    except subprocess.CalledProcessError as e:
        return e.output or f"Command exited with {e.returncode}"
    except FileNotFoundError:
        return f"{cmd_tokens[0]}: command not found"
    except Exception as e:
        return f"Error running command: {e}"

def save_history_on_exit():
    if READLINE_AVAILABLE:
        try:
            readline.write_history_file(str(HISTORY_FILE))
        except Exception:
            pass

def load_history():
    if READLINE_AVAILABLE:
        try:
            if HISTORY_FILE.exists():
                readline.read_history_file(str(HISTORY_FILE))
        except Exception:
            #if file doesn't exist, create directory implicitly
            pass
        #set completer function
        readline.set_completer(completer)
        readline.parse_and_bind("tab: complete")
    else:
        # No readline
        pass

def append_history_line(line):
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def main_loop():
    load_history()
    cwd = os.getcwd()
    try:
        while True:
            try:
                prompt = PROMPT(os.getcwd())
                if READLINE_AVAILABLE:
                    line = input(prompt)
                else:
                    # fallback input
                    line = input(prompt)
            except (KeyboardInterrupt, EOFError):
                print()  # newline
                break
            if not line.strip():
                continue
            append_history_line(line)
            parts = shlex.split(line)
            if not parts:
                continue
            cmd = parts[0]
            args = parts[1:]
            # builtins
            if cmd in ("exit", "quit"):
                break
            elif cmd in DISPATCH:
                try:
                    res = DISPATCH[cmd](args)
                except Exception as e:
                    res = f"{cmd}: error: {e}"
                if res:
                    print(res)
                continue
            elif cmd == "?" or cmd == "help":
                print(cmd_help(args))
                continue
            else:
                #As fallback, try to run as system command
                res = run_external_command(parts)
                if res:
                    print(res)
                continue
    finally:
        save_history_on_exit()

if __name__ == "__main__":
    print("Python Terminal (py_terminal) — type 'help' for commands, 'exit' to quit")
    if not READLINE_AVAILABLE:
        print("Note: readline not available on this platform. Tab-completion and persistent history may be limited.")
    else:
        print(f"History file: {HISTORY_FILE}")
    if not HAS_PSUTIL:
        print("Note: 'psutil' not found — process & system info will be limited. (pip install psutil recommended)")
    try:
        main_loop()
    except Exception as e:
        print("Fatal error:", e)
    finally:
        save_history_on_exit()
        print("Command history has been saved. Goodbye! 😍")
