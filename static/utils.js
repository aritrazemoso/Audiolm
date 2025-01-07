/**
 * VoiceStreamAI Client - WebSocket-based real-time transcription
 *
 * Contributor:
 * - Alessandro Saccoia - alessandro.saccoia@gmail.com
 */

let websocket;
let context;
let processor;
let globalStream;
let isRecording = false;
let stopTime = Date()

const websocketAddress = document.querySelector('#websocketAddress');
const selectedLanguage = document.querySelector('#languageSelect');
const websocketStatus = document.querySelector('#webSocketStatus');
const connectButton = document.querySelector("#connectButton");
const startButton = document.querySelector('#startButton');
const stopButton = document.querySelector('#stopButton');
const transcriptionDiv = document.querySelector('#transcription');
const languageDiv = document.querySelector('#detected_language');
const processingTimeDiv = document.querySelector('#processing_time');
const panel = document.querySelector('#silence_at_end_of_chunk_options_panel');
const selectedStrategy = document.querySelector('#bufferingStrategySelect');
const chunk_length_seconds = document.querySelector('#chunk_length_seconds');
const chunk_offset_seconds = document.querySelector('#chunk_offset_seconds');

websocketAddress.addEventListener("input", resetWebsocketHandler);

websocketAddress.addEventListener("keydown", (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        connectWebsocketHandler();
    }
});

connectButton.addEventListener("click", connectWebsocketHandler);

function resetWebsocketHandler() {
    if (isRecording) {
        stopRecordingHandler();
    }
    if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
    }
    connectButton.disabled = false;
}

async function generateAudio(query_text) {
    try {
        // Add loading state

        const query = encodeURIComponent(query_text);
        const response = await fetch(`/stream-audio/?query=${query}`);

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const audioBlob = await response.blob();
        let endTime = Date.now();
        const audioURL = URL.createObjectURL(audioBlob);
        document.getElementById('audioPlayer').src = audioURL;
        document.getElementById("chatgpt_audio").style.display = "block";
        document.getElementById("queryText").innerHTML = `<strong>Query:</strong> ${query_text} Processing Time:${(endTime - stopTime) / 1000} seconds`;
        const audioPlayer = document.getElementById('audioPlayer');
        audioPlayer.load();
        audioPlayer.play();
    } catch (error) {
        console.error('Error generating audio:', error);
        alert('Failed to generate audio response. Please try again.');
    } finally {
        // Remove loading state
        const buttonContainer = document.querySelector('#generateAudio').parentElement;
        buttonContainer.classList.remove('loading');
    }
}
function connectWebsocketHandler() {
    if (!websocketAddress.value) {
        console.log("WebSocket address is required.");
        return;
    }

    websocket = new WebSocket(websocketAddress.value);
    websocket.onopen = () => {
        console.log("WebSocket connection established");
        websocketStatus.textContent = 'Connected';
        startButton.disabled = false;
        connectButton.disabled = true;
        resetTranscription();
    };
    websocket.onclose = event => {
        console.log("WebSocket connection closed", event);
        websocketStatus.textContent = 'Not Connected';
        startButton.disabled = true;
        stopButton.disabled = true;
        connectButton.disabled = false;
    };
    websocket.onmessage = event => {
        console.log("Message from server:", event.data);
        const transcript_data = JSON.parse(event.data);
        switch (transcript_data.type) {
            case 'chunk_transcription':
                updateTranscription(transcript_data);
                break;
            case 'final_transcription':
                console.log("Final transcription:", transcript_data.full_text);
                // generateAudio(transcript_data.full_text);
                break;
            default:
                break;

        }
    };
}

function resetTranscription() {
    while (transcriptionDiv.firstChild) {
        transcriptionDiv.removeChild(transcriptionDiv.firstChild);
    }
}

function updateTranscription(transcript_data) {
    if (Array.isArray(transcript_data.words) && transcript_data.words.length > 0) {
        // Append words with color based on their probability
        transcript_data.words.forEach(wordData => {
            const span = document.createElement('span');
            const probability = wordData.probability;
            span.textContent = wordData.word + ' ';

            // Set the color based on the probability
            if (probability > 0.9) {
                span.style.color = 'green';
            } else if (probability > 0.6) {
                span.style.color = 'orange';
            } else {
                span.style.color = 'red';
            }

            transcriptionDiv.appendChild(span);
        });

        // Add a new line at the end
        transcriptionDiv.appendChild(document.createElement('br'));
    } else {
        // Fallback to plain text
        const span = document.createElement('span');
        span.textContent = transcript_data.text;
        transcriptionDiv.appendChild(span);
        transcriptionDiv.appendChild(document.createElement('br'));
    }

    // Update the language information
    if (transcript_data.language && transcript_data.language_probability) {
        languageDiv.textContent = transcript_data.language + ' (' + transcript_data.language_probability.toFixed(2) + ')';
    } else {
        languageDiv.textContent = 'Not Supported';
    }

    // Update the processing time, if available
    if (transcript_data.processing_time) {
        processingTimeDiv.textContent = 'Processing time: ' + transcript_data.processing_time.toFixed(2) + ' seconds';
    }
}

startButton.addEventListener("click", startRecordingHandler);

function startRecordingHandler() {
    if (isRecording) return;
    isRecording = true;

    context = new AudioContext();

    let onSuccess = async (stream) => {
        // Push user config to server
        let language = selectedLanguage.value !== 'multilingual' ? selectedLanguage.value : null;
        sendAudioConfig(language);

        globalStream = stream;
        const input = context.createMediaStreamSource(stream);
        const recordingNode = await setupRecordingWorkletNode();
        recordingNode.port.onmessage = (event) => {
            processAudio(event.data);
        };
        input.connect(recordingNode);
    };
    let onError = (error) => {
        console.error(error);
    };
    navigator.mediaDevices.getUserMedia({
        audio: {
            echoCancellation: true,
            autoGainControl: false,
            noiseSuppression: true,
            latency: 0
        }
    }).then(onSuccess, onError);

    // Disable start button and enable stop button
    startButton.disabled = true;
    stopButton.disabled = false;
}

async function setupRecordingWorkletNode() {
    await context.audioWorklet.addModule('static/realtime-audio-processor.js');

    return new AudioWorkletNode(
        context,
        'realtime-audio-processor'
    );
}

stopButton.addEventListener("click", () => {
    setTimeout(stopRecordingHandler, 300)
});

function stopRecordingHandler() {
    console.log('Stop button clicked');
    if (!isRecording) return;
    isRecording = false;

    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ isFinal: true }));
        stopTime = Date.now();
    }


    if (globalStream) {
        globalStream.getTracks().forEach(track => track.stop());
    }
    if (processor) {
        processor.disconnect();
        processor = null;
    }
    if (context) {
        context.close().then(() => context = null);
    }

    startButton.disabled = false;
    stopButton.disabled = true;
}

function sendAudioConfig(language) {
    let processingArgs = {};

    if (selectedStrategy.value === 'silence_at_end_of_chunk') {
        processingArgs = {
            chunk_length_seconds: parseFloat(chunk_length_seconds.value),
            chunk_offset_seconds: parseFloat(chunk_offset_seconds.value)
        };
    }

    const audioConfig = {
        type: 'config',
        data: {
            sampleRate: context.sampleRate,
            channels: 1,
            language: language,
            processing_strategy: selectedStrategy.value,
            processing_args: processingArgs
        }
    };

    websocket.send(JSON.stringify(audioConfig));
}

function processAudio(sampleData) {
    // ASR (Automatic Speech Recognition) and VAD (Voice Activity Detection)
    // models typically require mono audio with a sampling rate of 16 kHz,
    // represented as a signed int16 array type.
    //
    // Implementing changes to the sampling rate using JavaScript can reduce
    // computational costs on the server.
    const outputSampleRate = 16000;
    const decreaseResultBuffer = decreaseSampleRate(sampleData, context.sampleRate, outputSampleRate);
    const audioData = convertFloat32ToInt16(decreaseResultBuffer);

    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(audioData);
    }
}

function decreaseSampleRate(buffer, inputSampleRate, outputSampleRate) {
    if (inputSampleRate < outputSampleRate) {
        console.error("Sample rate too small.");
        return;
    } else if (inputSampleRate === outputSampleRate) {
        return;
    }

    let sampleRateRatio = inputSampleRate / outputSampleRate;
    let newLength = Math.ceil(buffer.length / sampleRateRatio);
    let result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
        let nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
        let accum = 0, count = 0;
        for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
            accum += buffer[i];
            count++;
        }
        result[offsetResult] = accum / count;
        offsetResult++;
        offsetBuffer = nextOffsetBuffer;
    }
    return result;
}

function convertFloat32ToInt16(buffer) {
    let l = buffer.length;
    const buf = new Int16Array(l);
    while (l--) {
        buf[l] = Math.min(1, buffer[l]) * 0x7FFF;
    }
    return buf.buffer;
}

// Initialize WebSocket on page load
//  window.onload = initWebSocket;

function toggleBufferingStrategyPanel() {
    if (selectedStrategy.value === 'silence_at_end_of_chunk') {
        panel.classList.remove('hidden');
    } else {
        panel.classList.add('hidden');
    }
}
