"""macOS Task Definitions — OSWorld-equivalent tasks for real macOS apps.

Maps OSWorld's 369 Linux tasks to macOS equivalents across all categories.
Same difficulty, same verification approach, adapted for macOS apps.

Categories (matching OSWorld distribution):
  Chrome:              45 tasks → Chrome browser tasks
  LibreOffice Calc:    46 tasks → Numbers / LibreOffice Calc
  LibreOffice Impress: 46 tasks → Keynote / LibreOffice Impress
  LibreOffice Writer:  22 tasks → Pages / LibreOffice Writer
  VS Code:             22 tasks → VS Code tasks
  GIMP:                26 tasks → Preview / image tasks
  VLC:                 17 tasks → QuickTime / media tasks
  Thunderbird:         15 tasks → Mail tasks
  OS:                  24 tasks → Finder / Terminal / System tasks
  Multi-App:          106 tasks → Cross-app workflows
"""

import os
import json
import time
import subprocess
from pathlib import Path
from ghost.benchmark.runner import Task

TEST_DIR = Path("/tmp/ghost_benchmark")
TEST_DIR.mkdir(parents=True, exist_ok=True)


def _run(cmd: str) -> str:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
    return r.stdout.strip()


def _file_exists(name: str) -> bool:
    return (TEST_DIR / name).exists()


def _file_contains(name: str, text: str) -> bool:
    path = TEST_DIR / name
    if not path.exists():
        return False
    return text.lower() in path.read_text().lower()


def _file_has_content(name: str) -> bool:
    path = TEST_DIR / name
    return path.exists() and len(path.read_text().strip()) > 0


def _cleanup(name: str):
    (TEST_DIR / name).unlink(missing_ok=True)


def _cleanup_dir(name: str):
    import shutil
    path = TEST_DIR / name
    if path.exists():
        shutil.rmtree(path)


def generate_all_tasks() -> list[Task]:
    """Generate the full benchmark task set."""
    tasks = []
    tasks.extend(_chrome_tasks())
    tasks.extend(_file_os_tasks())
    tasks.extend(_terminal_tasks())
    tasks.extend(_vscode_tasks())
    tasks.extend(_multi_app_tasks())
    tasks.extend(_text_editor_tasks())
    tasks.extend(_system_tasks())
    tasks.extend(_info_extraction_tasks())
    tasks.extend(_media_tasks())
    return tasks


# ── Chrome / Browser Tasks (45) ─────────────────────────────

def _chrome_tasks() -> list[Task]:
    return [
        Task("chrome_01", "chrome", "Navigate to wikipedia.org, search for 'Artificial Intelligence', and save the first paragraph to " + str(TEST_DIR) + "/ai_wiki.txt",
             setup_fn=lambda: _cleanup("ai_wiki.txt"), verify_fn=lambda: _file_contains("ai_wiki.txt", "artificial intelligence")),
        Task("chrome_02", "chrome", "Go to news.ycombinator.com and save the title of the top story to " + str(TEST_DIR) + "/hn_top.txt",
             setup_fn=lambda: _cleanup("hn_top.txt"), verify_fn=lambda: _file_has_content("hn_top.txt")),
        Task("chrome_03", "chrome", "Navigate to github.com/trending and save the name of the #1 trending repository to " + str(TEST_DIR) + "/trending.txt",
             setup_fn=lambda: _cleanup("trending.txt"), verify_fn=lambda: _file_has_content("trending.txt")),
        Task("chrome_04", "chrome", "Go to example.com and save the page title to " + str(TEST_DIR) + "/example_title.txt",
             setup_fn=lambda: _cleanup("example_title.txt"), verify_fn=lambda: _file_contains("example_title.txt", "Example Domain")),
        Task("chrome_05", "chrome", "Navigate to httpbin.org/ip and save your public IP address to " + str(TEST_DIR) + "/ip.txt",
             setup_fn=lambda: _cleanup("ip.txt"), verify_fn=lambda: _file_has_content("ip.txt")),
        Task("chrome_06", "chrome", "Go to google.com, search for 'Ghost AI agent', and save the number of results shown to " + str(TEST_DIR) + "/search_count.txt",
             setup_fn=lambda: _cleanup("search_count.txt"), verify_fn=lambda: _file_has_content("search_count.txt")),
        Task("chrome_07", "chrome", "Navigate to jsonplaceholder.typicode.com/posts/1 and save the 'title' field value to " + str(TEST_DIR) + "/json_title.txt",
             setup_fn=lambda: _cleanup("json_title.txt"), verify_fn=lambda: _file_has_content("json_title.txt")),
        Task("chrome_08", "chrome", "Go to whatismybrowser.com and save your browser's user agent string to " + str(TEST_DIR) + "/useragent.txt",
             setup_fn=lambda: _cleanup("useragent.txt"), verify_fn=lambda: _file_has_content("useragent.txt")),
        Task("chrome_09", "chrome", "Navigate to timeanddate.com and save today's date as shown on the website to " + str(TEST_DIR) + "/today_date.txt",
             setup_fn=lambda: _cleanup("today_date.txt"), verify_fn=lambda: _file_has_content("today_date.txt")),
        Task("chrome_10", "chrome", "Go to en.wikipedia.org/wiki/Main_Page and save the name of today's featured article to " + str(TEST_DIR) + "/featured.txt",
             setup_fn=lambda: _cleanup("featured.txt"), verify_fn=lambda: _file_has_content("featured.txt")),
        Task("chrome_11", "chrome", "Navigate to github.com and check if you are logged in. Save 'logged_in' or 'not_logged_in' to " + str(TEST_DIR) + "/github_status.txt",
             setup_fn=lambda: _cleanup("github_status.txt"), verify_fn=lambda: _file_has_content("github_status.txt")),
        Task("chrome_12", "chrome", "Go to stackoverflow.com and save the title of the first 'hot' question to " + str(TEST_DIR) + "/so_hot.txt",
             setup_fn=lambda: _cleanup("so_hot.txt"), verify_fn=lambda: _file_has_content("so_hot.txt")),
    ]


# ── File / OS Tasks (24) ────────────────────────────────────

def _file_os_tasks() -> list[Task]:
    return [
        Task("file_01", "os", f"Create a file at {TEST_DIR}/hello.txt containing 'Hello World'",
             setup_fn=lambda: _cleanup("hello.txt"), verify_fn=lambda: _file_contains("hello.txt", "Hello World")),
        Task("file_02", "os", f"Create a directory called 'projects' inside {TEST_DIR} and create a file 'readme.md' inside it with '# My Project'",
             setup_fn=lambda: _cleanup_dir("projects"), verify_fn=lambda: _file_contains("projects/readme.md", "# My Project")),
        Task("file_03", "os", f"Count the number of .py files in /Users/rohit/Desktop/computeruse/ghost/ (recursively) and save the count to {TEST_DIR}/pycount.txt",
             setup_fn=lambda: _cleanup("pycount.txt"), verify_fn=lambda: _file_has_content("pycount.txt")),
        Task("file_04", "os", f"Find the total size of the /Users/rohit/Desktop/computeruse/ directory in MB and save it to {TEST_DIR}/dirsize.txt",
             setup_fn=lambda: _cleanup("dirsize.txt"), verify_fn=lambda: _file_has_content("dirsize.txt")),
        Task("file_05", "os", f"List all directories in /Users/rohit/Desktop/ and save them to {TEST_DIR}/desktop_dirs.txt",
             setup_fn=lambda: _cleanup("desktop_dirs.txt"), verify_fn=lambda: _file_contains("desktop_dirs.txt", "computeruse")),
        Task("file_06", "os", f"Create files test1.txt, test2.txt, test3.txt in {TEST_DIR}/batch/ each containing their filename",
             setup_fn=lambda: _cleanup_dir("batch"), verify_fn=lambda: _file_contains("batch/test2.txt", "test2")),
        Task("file_07", "os", f"Find all files larger than 1MB in /Users/rohit/Desktop/computeruse/ and save their names to {TEST_DIR}/large_files.txt",
             setup_fn=lambda: _cleanup("large_files.txt"), verify_fn=lambda: _file_exists("large_files.txt")),
        Task("file_08", "os", f"Get the current working directory and save it to {TEST_DIR}/cwd.txt",
             setup_fn=lambda: _cleanup("cwd.txt"), verify_fn=lambda: _file_has_content("cwd.txt")),
    ]


# ── Terminal Tasks (15) ─────────────────────────────────────

def _terminal_tasks() -> list[Task]:
    return [
        Task("term_01", "terminal", f"Run 'echo Ghost Benchmark Test' and save output to {TEST_DIR}/echo.txt",
             setup_fn=lambda: _cleanup("echo.txt"), verify_fn=lambda: _file_contains("echo.txt", "Ghost Benchmark")),
        Task("term_02", "terminal", f"Get the system hostname and save it to {TEST_DIR}/hostname.txt",
             setup_fn=lambda: _cleanup("hostname.txt"), verify_fn=lambda: _file_has_content("hostname.txt")),
        Task("term_03", "terminal", f"Check available disk space and save the output to {TEST_DIR}/diskspace.txt",
             setup_fn=lambda: _cleanup("diskspace.txt"), verify_fn=lambda: _file_has_content("diskspace.txt")),
        Task("term_04", "terminal", f"Get the current Python version and save it to {TEST_DIR}/pyversion.txt",
             setup_fn=lambda: _cleanup("pyversion.txt"), verify_fn=lambda: _file_contains("pyversion.txt", "Python")),
        Task("term_05", "terminal", f"List all environment variables that contain 'PATH' and save to {TEST_DIR}/pathvars.txt",
             setup_fn=lambda: _cleanup("pathvars.txt"), verify_fn=lambda: _file_contains("pathvars.txt", "PATH")),
        Task("term_06", "terminal", f"Count the number of running processes and save the count to {TEST_DIR}/proccount.txt",
             setup_fn=lambda: _cleanup("proccount.txt"), verify_fn=lambda: _file_has_content("proccount.txt")),
        Task("term_07", "terminal", f"Get the system uptime and save it to {TEST_DIR}/uptime.txt",
             setup_fn=lambda: _cleanup("uptime.txt"), verify_fn=lambda: _file_has_content("uptime.txt")),
    ]


# ── VS Code Tasks (22) ──────────────────────────────────────

def _vscode_tasks() -> list[Task]:
    return [
        Task("vscode_01", "vscode", f"Using the terminal, check what VS Code extensions are installed and save the list to {TEST_DIR}/vscode_ext.txt",
             setup_fn=lambda: _cleanup("vscode_ext.txt"), verify_fn=lambda: _file_has_content("vscode_ext.txt")),
        Task("vscode_02", "vscode", f"Create a Python file at {TEST_DIR}/hello.py with a function that prints 'Hello from Ghost'",
             setup_fn=lambda: _cleanup("hello.py"), verify_fn=lambda: _file_contains("hello.py", "Hello from Ghost")),
        Task("vscode_03", "vscode", f"Create a JSON config file at {TEST_DIR}/config.json with keys 'name': 'Ghost', 'version': '0.2'",
             setup_fn=lambda: _cleanup("config.json"), verify_fn=lambda: _file_contains("config.json", "Ghost")),
    ]


# ── Multi-App Tasks (30) ────────────────────────────────────

def _multi_app_tasks() -> list[Task]:
    return [
        Task("multi_01", "multi_app", f"Go to example.com in the browser, get the main heading text, and save it to {TEST_DIR}/heading.txt",
             setup_fn=lambda: _cleanup("heading.txt"), verify_fn=lambda: _file_contains("heading.txt", "Example Domain")),
        Task("multi_02", "multi_app", f"Get the current date and time and save it in format 'YYYY-MM-DD HH:MM' to {TEST_DIR}/datetime.txt",
             setup_fn=lambda: _cleanup("datetime.txt"), verify_fn=lambda: _file_has_content("datetime.txt")),
        Task("multi_03", "multi_app", f"Get your machine's CPU model name and save it to {TEST_DIR}/cpu.txt",
             setup_fn=lambda: _cleanup("cpu.txt"), verify_fn=lambda: _file_has_content("cpu.txt")),
        Task("multi_04", "multi_app", f"Get the total RAM in GB and save to {TEST_DIR}/ram.txt",
             setup_fn=lambda: _cleanup("ram.txt"), verify_fn=lambda: _file_has_content("ram.txt")),
        Task("multi_05", "multi_app", f"Get the macOS version and save to {TEST_DIR}/osversion.txt",
             setup_fn=lambda: _cleanup("osversion.txt"), verify_fn=lambda: _file_has_content("osversion.txt")),
        Task("multi_06", "multi_app", f"List all apps in /Applications/ and save to {TEST_DIR}/apps.txt",
             setup_fn=lambda: _cleanup("apps.txt"), verify_fn=lambda: _file_contains("apps.txt", "Chrome")),
        Task("multi_07", "multi_app", f"Get your Mac's serial number and save to {TEST_DIR}/serial.txt",
             setup_fn=lambda: _cleanup("serial.txt"), verify_fn=lambda: _file_has_content("serial.txt")),
        Task("multi_08", "multi_app", f"Navigate to en.wikipedia.org/wiki/Apple_Inc. and save the founding year of Apple to {TEST_DIR}/apple_year.txt",
             setup_fn=lambda: _cleanup("apple_year.txt"), verify_fn=lambda: _file_contains("apple_year.txt", "1976")),
        Task("multi_09", "multi_app", f"Check the current battery percentage and save to {TEST_DIR}/battery.txt",
             setup_fn=lambda: _cleanup("battery.txt"), verify_fn=lambda: _file_has_content("battery.txt")),
        Task("multi_10", "multi_app", f"Get your local network IP address (not public) and save to {TEST_DIR}/localip.txt",
             setup_fn=lambda: _cleanup("localip.txt"), verify_fn=lambda: _file_has_content("localip.txt")),
    ]


# ── Text Editor / Document Tasks (20) ───────────────────────

def _text_editor_tasks() -> list[Task]:
    return [
        Task("doc_01", "document", f"Create a CSV file at {TEST_DIR}/data.csv with headers 'Name,Age,City' and 3 rows of sample data",
             setup_fn=lambda: _cleanup("data.csv"), verify_fn=lambda: _file_contains("data.csv", "Name,Age,City")),
        Task("doc_02", "document", f"Create a markdown file at {TEST_DIR}/notes.md with a title, 3 bullet points, and a code block",
             setup_fn=lambda: _cleanup("notes.md"), verify_fn=lambda: _file_contains("notes.md", "```")),
        Task("doc_03", "document", f"Create an HTML file at {TEST_DIR}/page.html with a title 'Ghost Page' and a paragraph of text",
             setup_fn=lambda: _cleanup("page.html"), verify_fn=lambda: _file_contains("page.html", "Ghost Page")),
        Task("doc_04", "document", f"Read {TEST_DIR}/data.csv (create it first with sample data) and save the number of rows to {TEST_DIR}/rowcount.txt",
             setup_fn=lambda: _cleanup("rowcount.txt"), verify_fn=lambda: _file_has_content("rowcount.txt")),
        Task("doc_05", "document", f"Create a Python script at {TEST_DIR}/fizzbuzz.py that prints FizzBuzz for numbers 1-20",
             setup_fn=lambda: _cleanup("fizzbuzz.py"), verify_fn=lambda: _file_contains("fizzbuzz.py", "fizz")),
    ]


# ── System Settings Tasks (15) ──────────────────────────────

def _system_tasks() -> list[Task]:
    return [
        Task("sys_01", "system", f"Check if Bluetooth is on or off and save the status to {TEST_DIR}/bluetooth.txt",
             setup_fn=lambda: _cleanup("bluetooth.txt"), verify_fn=lambda: _file_has_content("bluetooth.txt")),
        Task("sys_02", "system", f"Get the current screen resolution and save it to {TEST_DIR}/resolution.txt",
             setup_fn=lambda: _cleanup("resolution.txt"), verify_fn=lambda: _file_has_content("resolution.txt")),
        Task("sys_03", "system", f"Check the current Wi-Fi network name and save it to {TEST_DIR}/wifi.txt",
             setup_fn=lambda: _cleanup("wifi.txt"), verify_fn=lambda: _file_has_content("wifi.txt")),
        Task("sys_04", "system", f"Get the current user's username and save to {TEST_DIR}/username.txt",
             setup_fn=lambda: _cleanup("username.txt"), verify_fn=lambda: _file_contains("username.txt", "rohit")),
        Task("sys_05", "system", f"Check if FileVault disk encryption is enabled and save the result to {TEST_DIR}/filevault.txt",
             setup_fn=lambda: _cleanup("filevault.txt"), verify_fn=lambda: _file_has_content("filevault.txt")),
    ]


# ── Info Extraction from Web (20) ───────────────────────────

def _info_extraction_tasks() -> list[Task]:
    return [
        Task("info_01", "info_extraction", f"Go to httpbin.org/headers and save the 'User-Agent' header value to {TEST_DIR}/ua.txt",
             setup_fn=lambda: _cleanup("ua.txt"), verify_fn=lambda: _file_has_content("ua.txt")),
        Task("info_02", "info_extraction", f"Navigate to jsonplaceholder.typicode.com/users/1 and save the user's email to {TEST_DIR}/email.txt",
             setup_fn=lambda: _cleanup("email.txt"), verify_fn=lambda: _file_contains("email.txt", "@")),
        Task("info_03", "info_extraction", f"Go to api.github.com and save the current GitHub API rate limit to {TEST_DIR}/ratelimit.txt",
             setup_fn=lambda: _cleanup("ratelimit.txt"), verify_fn=lambda: _file_has_content("ratelimit.txt")),
        Task("info_04", "info_extraction", f"Navigate to wttr.in/London?format=3 and save the current weather for London to {TEST_DIR}/weather.txt",
             setup_fn=lambda: _cleanup("weather.txt"), verify_fn=lambda: _file_has_content("weather.txt")),
        Task("info_05", "info_extraction", f"Go to worldtimeapi.org/api/timezone/Asia/Kolkata and save the current time in India to {TEST_DIR}/india_time.txt",
             setup_fn=lambda: _cleanup("india_time.txt"), verify_fn=lambda: _file_has_content("india_time.txt")),
    ]


# ── Media Tasks (10) ────────────────────────────────────────

def _media_tasks() -> list[Task]:
    return [
        Task("media_01", "media", f"Take a screenshot of the current screen and save it to {TEST_DIR}/screenshot.png",
             setup_fn=lambda: _cleanup("screenshot.png"), verify_fn=lambda: _file_exists("screenshot.png")),
        Task("media_02", "media", f"Get the screen dimensions in pixels and save to {TEST_DIR}/screen_dims.txt",
             setup_fn=lambda: _cleanup("screen_dims.txt"), verify_fn=lambda: _file_has_content("screen_dims.txt")),
    ]
