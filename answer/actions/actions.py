

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from datetime import datetime, timedelta

class ActionFindCommonAvailability(Action):
    def __init__(self):
        # Generate a list of available dates for the next 30 days for the answer bot
        self.answer_calendar = [
            (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(30) if (datetime.now() + timedelta(days=i)).weekday() in [1, 2, 3]  # Tue, Wed, Thu
        ]
        
        # Restaurant's available dates (example - you should replace this with actual data)
        self.restaurant_calendar = [
            (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(30) if (datetime.now() + timedelta(days=i)).weekday() in [0, 2, 4, 5]  # Mon, Wed, Fri, Sat
        ]

    def name(self) -> Text:
        return "action_find_common_availability"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get the last message from the offer bot
        last_message = tracker.latest_message.get('text', '')
        
        # Extract the availability from the message
        offer_availability = self.extract_availability(last_message)
        
        # Find common dates among offer bot, answer bot, and restaurant
        common_dates = list(set(self.answer_calendar) & set(offer_availability) & set(self.restaurant_calendar))
        common_dates.sort()  # Sort the dates

        if common_dates:
            first_available = common_dates[0]
            dispatcher.utter_message(text=f"The first common available date for all parties is {first_available}. Shall we schedule for that date?")
            return [SlotSet("scheduled_date", first_available)]
        else:
            dispatcher.utter_message(text="I'm sorry, we don't have any common available dates among all parties.")
            return []

    def extract_availability(self, message: Text) -> List[Text]:
        # Extract the dates from the message
        # Assuming the message is in the format: "Here are my available dates: 2023-07-21, 2023-07-23, 2023-07-25"
        try:
            dates_str = message.split(":")[1].strip()
            return [date.strip() for date in dates_str.split(',')]
        except:
            # If there's any error in parsing, return an empty list
            return []