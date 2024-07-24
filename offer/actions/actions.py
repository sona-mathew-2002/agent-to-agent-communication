# from typing import Any, Text, Dict, List
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher

# class ActionSuggestDay(Action):
#     def __init__(self):
#         self.calendar = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
#         self.current_index = 0

#     def name(self) -> Text:
#         return "action_suggest_day"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
#         if self.current_index >= len(self.calendar):
#             dispatcher.utter_message(text="I'm sorry, I don't have any more available days to suggest.")
#             return []

#         suggested_day = self.calendar[self.current_index]
#         self.current_index += 1

#         dispatcher.utter_message(text=f"How about {suggested_day}? Does that work for you?")
#         return [{"event": "slot", "name": "day", "value": suggested_day}]


# from typing import Any, Text, Dict, List
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher

# class ActionProvideAvailability(Action):
#     def __init__(self):
#         self.calendar = ["Monday", "Wednesday", "Friday"]

#     def name(self) -> Text:
#         return "action_provide_availability"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
#         availability_str = ", ".join(self.calendar)
#         dispatcher.utter_message(text=f"Here are my available days: {availability_str}")
        
#         return [{"event": "slot", "name": "agent1_availability", "value": self.calendar}]

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from datetime import datetime, timedelta

class ActionProvideAvailability(Action):
    def __init__(self):
        # Generate a list of available dates for the next 30 days
        self.calendar = [
            (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(30) if (datetime.now() + timedelta(days=i)).weekday() in [0, 2, 4]  # Mon, Wed, Fri
        ]

    def name(self) -> Text:
        return "action_provide_availability"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        availability_str = ", ".join(self.calendar)
        dispatcher.utter_message(text=f"Here are my available dates: {availability_str}")
        
        return [SlotSet("agent1_availability", self.calendar)]