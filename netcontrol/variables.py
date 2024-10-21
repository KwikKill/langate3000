import json

class Variables:
    def __init__(self):
        with open("/variables.json", "r") as file:
            self.data: dict = json.load(file)
    
    def ip_range(self) -> str:
        return self.data["ip_range"]