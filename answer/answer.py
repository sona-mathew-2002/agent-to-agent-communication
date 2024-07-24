from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
import json
import asyncio
import requests
import logging
import aiohttp

#Currently only offer is creating a channel and conversation happens through that channel. So I have commented the channel creation here

class WebRTCClient:
    def __init__(self, signaling_server_url, id):
        self.SIGNALING_SERVER_URL = signaling_server_url
        self.ID = id
        stun_server = RTCIceServer(urls='stun:stun.l.google.com:19302')
        turn_server = RTCIceServer(urls='turn:global.relay.metered.ca:80', 
                                   username="8d3d0de583bce36b8234bd42",
                                   credential="8p8XHm8NAlB45Uxs")
        self.config = RTCConfiguration(iceServers=[stun_server, turn_server])
        self.peer_connection = None
        self.channels = {}
        # self.channels_ready = {
        #     # 'chat': asyncio.Event(),
        #     # 'home': asyncio.Event()
        # }

    async def setup_signal(self):
        print("Starting setup")
        self.peer_connection = RTCPeerConnection(configuration=self.config)
        
        @self.peer_connection.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            print(f"ICE connection state is {self.peer_connection.iceConnectionState}")
            

        @self.peer_connection.on("icegatheringstatechange")
        async def on_icegatheringstatechange():
            print(f"ICE gathering state is {self.peer_connection.iceGatheringState}")

        # self.channels['chat'] = self.peer_connection.createDataChannel("chat")
        # self.channels['home'] = self.peer_connection.createDataChannel("home")

        for channel_name, channel in self.channels.items():
            @channel.on("open")
            def on_open(channel=channel, name=channel_name):
                print(f"Channel {name} opened")
                self.channels_ready[name].set()
                # channel.send(f"Hello from Offerer via {name} Datachannel")

            @channel.on("message")
            def on_message(message, name=channel_name):
                print(f"Received via RTC Datachannel {name}: {message}")

        @self.peer_connection.on("datachannel")
        async def on_datachannel(channel):
            print(f"Data channel '{channel.label}' created by remote party")
            self.channels[channel.label] = channel

            @channel.on("open")
            def on_open():
                print(f"Data channel '{channel.label}' is open")

            @channel.on("message")
            async def on_message(message):
                print(f"Received via {channel.label}: {message}")
                response = await self.send_message_to_rasa(message)
                print("Response from Rasa:", response)
                channel.send(response)
                print("response from rasa sent")
                

        # Get offer
        try:
            resp = requests.get(self.SIGNALING_SERVER_URL + "/get_offer")
            print(f"Offer request status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if data["type"] == "offer":
                    rd = RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                    await self.peer_connection.setRemoteDescription(rd)
                    await self.peer_connection.setLocalDescription(await self.peer_connection.createAnswer())

                    message = {
                        "id": self.ID,
                        "sdp": self.peer_connection.localDescription.sdp,
                        "type": self.peer_connection.localDescription.type
                    }
                    r = requests.post(self.SIGNALING_SERVER_URL + '/answer', data=message)
                    print(f"Answer sent, status: {r.status_code}")
            else:
                print(f"Failed to get offer. Status code: {resp.status_code}")
        except Exception as e:
            print(f"Error during signaling: {str(e)}")
            return

        # try:
        #     await asyncio.wait_for(asyncio.gather(self.channels_ready['chat'].wait()), timeout=30)
        #     print("All channels are ready for sending messages")
        # except asyncio.TimeoutError:
        #     print("Timeout waiting for channels to be ready")


    async def send_message_to_rasa(self, message):
        url = "http://localhost:5006/webhooks/rest/webhook"
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