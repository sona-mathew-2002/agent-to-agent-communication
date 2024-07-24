from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
import json
import asyncio
import requests
import os
from dotenv import load_dotenv
import aiohttp

#Initially ice gathering occurs
#After completing ice gathering offer is sent
# Answer is received as a response to offer
# Data channel is opened


# Load environment variables from .env file
load_dotenv()


class WebRTCClient:
    def __init__(self, signaling_server_url, id):
        self.SIGNALING_SERVER_URL = signaling_server_url
        self.ID = id
        stun_server_url = os.getenv('STUN_SERVER_URL')
        turn_server_url = os.getenv('TURN_SERVER_URL')
        turn_username = os.getenv('TURN_USERNAME')
        turn_credential = os.getenv('TURN_CREDENTIAL')

        if not all([stun_server_url, turn_server_url, turn_username, turn_credential]):
            raise ValueError("Environment variables for STUN and TURN servers must be set")

        stun_server = RTCIceServer(urls=stun_server_url)
        turn_server = RTCIceServer(urls=turn_server_url, username=turn_username, credential=turn_credential)

        self.config = RTCConfiguration(iceServers=[stun_server, turn_server])
        self.peer_connection = None
        self.channels = {}
        self.channels_ready = {
            'chat': asyncio.Event(),
            # 'home': asyncio.Event()
        }

    async def setup_signal(self):
        print("Starting setup")
        self.peer_connection = RTCPeerConnection(configuration=self.config)
        
        @self.peer_connection.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            print(f"ICE connection state is {self.peer_connection.iceConnectionState}")

        @self.peer_connection.on("icegatheringstatechange")
        async def on_icegatheringstatechange():
            print(f"ICE gathering state is {self.peer_connection.iceGatheringState}")

        # Create both channels
        self.channels['chat'] = self.peer_connection.createDataChannel("chat")
        # self.channels['home'] = self.peer_connection.createDataChannel("home")

        for channel_name, channel in self.channels.items():
            @channel.on("open")
            async def on_open(channel=channel, name=channel_name):
                print(f"Channel {name} opened")
                self.channels_ready[name].set()
                if name == "chat":
                    initial_message = "Hi"
                    channel.send(initial_message)
                    print(f"Sent initial message: {initial_message}")

            @channel.on("message")
            async def on_message(message, name=channel_name):
                print(f"Received via RTC Datachannel {name}: {message}")
                response = await self.send_message_to_rasa(message)
                print("Response from Rasa:", response)
                channel.send(response)

        @self.peer_connection.on("datachannel")
        def on_datachannel(channel):
            print(f"Data channel '{channel.label}' created by remote party")
            self.channels[channel.label] = channel

            @channel.on("open")
            def on_open():
                print(f"Data channel '{channel.label}' is open")

            @channel.on("message")
            def on_message(message):
                print(f"Received via {channel.label}: {message}")


        # send offer
        try:
            offer = await self.peer_connection.createOffer()
            await self.peer_connection.setLocalDescription(offer)
            message = {"id": self.ID, "sdp": self.peer_connection.localDescription.sdp, "type": self.peer_connection.localDescription.type}
            r = requests.post(self.SIGNALING_SERVER_URL + '/offer', data=message)
            print(f"Offer sent, status: {r.status_code}")
        except Exception as e:
            print(f"Error during offer creation and sending: {str(e)}")
            return

        #POLL FOR ANSWER
        try:
            while True:
                resp = requests.get(self.SIGNALING_SERVER_URL + "/get_answer")
                if resp.status_code == 503:
                    print("Answer not ready, trying again")
                    await asyncio.sleep(1)
                elif resp.status_code == 200:
                    data = resp.json()
                    if data["type"] == "answer":
                        rd = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                        await self.peer_connection.setRemoteDescription(rd)
                        print("Remote description set")
                        break
                    else:
                        print("Wrong type")
                        break

                print(f"Answer polling status: {resp.status_code}")
        except Exception as e:
            print(f"Error during answer polling: {str(e)}")
            return

        # Wait for both channels to be ready
        try:
            await asyncio.wait_for(asyncio.gather(self.channels_ready['chat'].wait()), timeout=30)
            print("All channels are ready for sending messages")
        except asyncio.TimeoutError:
            print("Timeout waiting for channels to be ready")


    #function to send message to RASA
    async def send_message_to_rasa(self, message):
        url = "http://localhost:5005/webhooks/rest/webhook"
        payload = {
            "sender": "user",
            "message": message
        }
        headers = {
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                response_json = await response.json()
                if response_json and isinstance(response_json, list) and len(response_json) > 0:
                    return response_json[0].get('text', '')
                return ''

    #function to send message through channel
    async def send_message(self, channel_name, message):
        if channel_name not in self.channels:
            print(f"Invalid channel name: {channel_name}")
            return

        if not self.channels_ready[channel_name].is_set():
            print(f"Channel {channel_name} is not ready yet. Please wait.")
            return

        channel = self.channels[channel_name]
        if channel and channel.readyState == "open":
            print(f"Sending via RTC Datachannel {channel_name}: {message}")
            channel.send(message)
        else:
            print(f"Channel {channel_name} is not open. Cannot send message.")