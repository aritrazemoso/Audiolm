import asyncio
import json
import os
import time
import websocket
from fastapi import WebSocket


from .buffer_stategy_interface import BufferingStrategyInterface
from configs.vad.vad_interface import VADInterface


class SilenceAtEndOfChunk(BufferingStrategyInterface):
    """
    A buffering strategy that processes audio at the end of each chunk with
    silence detection.

    This class is responsible for handling audio chunks, detecting silence at
    the end of each chunk, and initiating the transcription process for the
    chunk.

    Attributes:
        client (Client): The client instance associated with this buffering
                         strategy.
        chunk_length_seconds (float): Length of each audio chunk in seconds.
        chunk_offset_seconds (float): Offset time in seconds to be considered
                                      for processing audio chunks.
    """

    def __init__(self, client, **kwargs):
        """
        Initialize the SilenceAtEndOfChunk buffering strategy.

        Args:
            client (Client): The client instance associated with this buffering
                             strategy.
            **kwargs: Additional keyword arguments, including
                      'chunk_length_seconds' and 'chunk_offset_seconds'.
        """
        self.client = client

        self.chunk_length_seconds = os.environ.get("BUFFERING_CHUNK_LENGTH_SECONDS")
        if not self.chunk_length_seconds:
            self.chunk_length_seconds = kwargs.get("chunk_length_seconds")
        self.chunk_length_seconds = float(self.chunk_length_seconds)

        self.chunk_offset_seconds = os.environ.get("BUFFERING_CHUNK_OFFSET_SECONDS")
        if not self.chunk_offset_seconds:
            self.chunk_offset_seconds = kwargs.get("chunk_offset_seconds")
        self.chunk_offset_seconds = float(self.chunk_offset_seconds)

        self.error_if_not_realtime = os.environ.get("ERROR_IF_NOT_REALTIME")
        if not self.error_if_not_realtime:
            self.error_if_not_realtime = kwargs.get("error_if_not_realtime", False)

        self.processing_flag = False

    async def process_audio(
        self,
        websocket: websocket,
        vad_pipeline: VADInterface,
        asr_pipeline,
        transcriptions_list: list,
    ):
        """
        Process audio chunks by checking their length and processing them.
        """
        chunk_length_in_bytes = (
            self.chunk_length_seconds
            * self.client.sampling_rate
            * self.client.samples_width
        )
        if len(self.client.buffer) > chunk_length_in_bytes:
            if self.processing_flag:
                exit(
                    "Error in realtime processing: tried processing a new "
                    "chunk while the previous one was still being processed"
                )

            self.client.scratch_buffer += self.client.buffer
            self.client.buffer.clear()
            self.processing_flag = True
            # Process directly instead of creating a new task
            await self.process_audio_chunk(
                websocket, vad_pipeline, asr_pipeline, transcriptions_list
            )

    async def process_audio_chunk(
        self,
        websocket: WebSocket,
        vad_pipeline,
        asr_pipeline,
        transcriptions_list: list,
    ):
        """
        Process a single chunk of audio data.
        """
        try:
            start = time.time()
            vad_results = await vad_pipeline.detect_activity(self.client)

            if len(vad_results) == 0:
                self.client.scratch_buffer.clear()
                self.client.buffer.clear()
                self.processing_flag = False
                return

            last_segment_should_end_before = (
                len(self.client.scratch_buffer)
                / (self.client.sampling_rate * self.client.samples_width)
            ) - self.chunk_offset_seconds

            if vad_results[-1]["end"] < last_segment_should_end_before:
                transcription = await asr_pipeline.transcribe(self.client)
                if transcription["text"] != "":
                    end = time.time()
                    transcription["processing_time"] = end - start
                    transcription["chunk_id"] = self.client.file_counter

                    # Store transcription
                    transcriptions_list.append(transcription)

                    # Send individual chunk transcription
                    json_transcription = json.dumps(transcription)
                    await websocket.send_text(json_transcription)

                self.client.scratch_buffer.clear()
                self.client.increment_file_counter()
        finally:
            self.processing_flag = False
