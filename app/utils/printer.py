import json
from termcolor import colored


class Printer:
    @staticmethod
    def print_json(json_string):
        try:
            json_object = json.loads(json_string)
            print(colored(json.dumps(json_object, indent=2), "green"))
        except json.JSONDecodeError:
            print(colored(json_string, "blue"))

    @staticmethod
    def print_colored(text, color):
        print(colored(str(text), color))
