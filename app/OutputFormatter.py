from Color import Color
import os


class OutputFormatter:
    def __init__(self):
        pass

    @staticmethod
    def error(text):
        return f"{Color.RED}{text}{Color.END}"

    @staticmethod
    def success(text):
        return f"{Color.GREEN}{text}{Color.END}"

    @staticmethod
    def url_link(text):
        return f"{Color.MAGENTA}{text}{Color.END}"

    @staticmethod
    def description(text):
        return f"{Color.BLUE}{text}{Color.END}"

    @staticmethod
    def ai_response(text):
        return f"{Color.MAGENTA}{text}{Color.END}"

    @staticmethod
    def get_colored_filename(line, filename):
        """Return the filename with appropriate color based on its properties."""
        if line.startswith("d"):
            return f"{Color.BLUE}{line}{Color.END}"
        elif filename.startswith("."):
            return f"{Color.CYAN}{line}{Color.END}"
        else:
            return f"{Color.WHITE}{line}{Color.END}"

    def get_custom_prompt():
        username = os.getenv("USER") or os.getenv("USERNAME")
        pwd = os.getcwd()
        return f"{Color.CYAN}[{Color.GREEN}{username}{Color.END}@python-cli {Color.MAGENTA}{pwd}{Color.CYAN}]{Color.END}$ "
