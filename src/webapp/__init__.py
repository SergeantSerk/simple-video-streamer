import os
import json
import asyncio
import platform

from aiohttp import web
from aiortc import RTCPeerConnection, RTCRtpSender, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay

class WebApp:
    def __init__(self, play_from, video_codec: str, audio_codec: str, play_without_decoding: bool = True):
        self.relay: MediaRelay | None = None
        self.webcam: MediaPlayer | None = None
        self.pcs: set[RTCPeerConnection] = set()
        self.play_from = play_from
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.play_without_decoding = play_without_decoding

    async def on_shutdown(self, app):
        # close peer connections
        coros = [pc.close() for pc in self.pcs]
        await asyncio.gather(*coros)
        self.pcs.clear()

        if self.webcam is not None:
            if self.webcam.video is not None:
                self.webcam.video.stop()
            if self.webcam.audio is not None:
                self.webcam.audio.stop()

    async def index(self, request):
        content = open(os.path.join(os.path.dirname(__file__), "..", "index.html"), "r").read()
        return web.Response(content_type="text/html", text=content)


    async def javascript(self, request):
        content = open(os.path.join(os.path.dirname(__file__), "..", "client.js"), "r").read()
        return web.Response(content_type="application/javascript", text=content)


    async def offer(self, request):
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        pc = RTCPeerConnection()
        self.pcs.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print("Connection state is %s" % pc.connectionState)
            if pc.connectionState == "failed":
                await pc.close()
                self.pcs.discard(pc)

        # open media source
        audio, video = self.create_local_tracks(
            self.play_from, decode=not self.play_without_decoding
        )

        if audio:
            audio_sender = pc.addTrack(audio)
            if self.audio_codec:
                self.force_codec(pc, audio_sender, self.audio_codec)
            elif self.play_without_decoding:
                raise Exception("You must specify the audio codec using --audio-codec")

        if video:
            video_sender = pc.addTrack(video)
            if self.video_codec:
                self.force_codec(pc, video_sender, self.video_codec)
            elif self.play_without_decoding:
                raise Exception("You must specify the video codec using --video-codec")

        await pc.setRemoteDescription(offer)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
            ),
        )
    
    def create_local_tracks(self, play_from, decode):
        if play_from:
            player = MediaPlayer(play_from, decode=decode)
            return player.audio, player.video
        else:
            options = {"framerate": "60", "video_size": "1920x1080"}
            if self.relay is None:
                if platform.system() == "Darwin":
                    self.webcam = MediaPlayer(
                        "default:none", format="avfoundation", options=options
                    )
                elif platform.system() == "Windows":
                    self.webcam = MediaPlayer(
                        "video=Integrated Camera", format="dshow", options=options
                    )
                else:
                    self.webcam = MediaPlayer("/dev/video0", format="v4l2", options=options)
                self.relay = MediaRelay()
            return None, self.relay.subscribe(self.webcam.video)
        
    def force_codec(self, pc, sender, forced_codec: str):
        kind = forced_codec.split("/")[0]
        codecs = RTCRtpSender.getCapabilities(kind).codecs
        transceiver = next(t for t in pc.getTransceivers() if t.sender == sender)
        transceiver.setCodecPreferences(
            [codec for codec in codecs if codec.mimeType == forced_codec]
        )