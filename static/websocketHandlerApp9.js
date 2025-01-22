class MediaSourceHandler {
    constructor(mimeCodec = 'audio/mpeg') {


        this.mimeCodec = mimeCodec;
        this.mediaSource = new MediaSource();
        this.sourceBuffer = null;
        this.audioQueue = [];
        this.isAppending = false;

        // Bind MediaSource to the audio element
        this.audioSrc = URL.createObjectURL(this.mediaSource);

        // Event listeners
        this.mediaSource.addEventListener('sourceopen', this.onSourceOpen.bind(this));
        this.mediaSource.addEventListener('error', this.onSourceError.bind(this));
    }

    onSourceOpen() {
        console.log('MediaSource is open');

        // Initialize SourceBuffer for MP3
        try {
            this.sourceBuffer = this.mediaSource.addSourceBuffer(this.mimeCodec);
            this.sourceBuffer.addEventListener('error', this.onSourceBufferError.bind(this));
        } catch (error) {
            console.error('Error creating SourceBuffer:', error);
        }
    }

    onSourceError(e) {
        console.error('MediaSource error:', e);
    }

    onSourceBufferError(e) {
        console.error('SourceBuffer error:', e);
    }

    appendChunk(chunk) {
        if (!this.sourceBuffer) {
            console.warn('SourceBuffer not initialized');
            return;
        }

        this.audioQueue.push(chunk);
        this.appendToSourceBuffer();
    }

    appendToSourceBuffer() {
        if (this.isAppending || !this.audioQueue.length) return;

        this.isAppending = true;
        const chunk = this.audioQueue.shift();

        try {
            this.sourceBuffer.appendBuffer(chunk);
        } catch (error) {
            console.error('Error appending chunk:', error);
            this.isAppending = false;
            return;
        }

        this.sourceBuffer.addEventListener(
            'updateend',
            () => {
                this.isAppending = false;
                this.appendToSourceBuffer(); // Process the next chunk
            },
            { once: true }
        );
    }

    endStream() {
        if (this.mediaSource.readyState === 'open') {
            this.mediaSource.endOfStream();
        }
        console.log('MediaSource stream ended');
    }
}

const USER_ID_KEY = "USER_ID_KEY"
const EventType = Object.freeze({
    ASK_QUESTION: "askQuestion",
    AUDIO_PACKET: "audioPacket",
    END_QUESTION: "endQuestion",
    START_ANSWER: "startAnswer",
    END_ANSWER: "endAnswer",
    TRANSCRIPTION: "final_transcription",
    ANSWER: "answer",
    RECEIVE_RESUME: "receiveResume"
});
let websocket = null

const getUserId = () => {
    const userId = localStorage.getItem(USER_ID_KEY);
    if (userId) {
        return userId;
    } else {
        const newUserId = crypto.randomUUID().toString();
        localStorage.setItem(USER_ID_KEY, newUserId);
        return newUserId;
    }
}

class ResumeHandler {
    constructor() {
        this.modal = document.getElementById('uploadModal');
        this.uploadBtn = document.getElementById('uploadBtn');
        this.closeBtn = document.querySelector('.close-modal');
        this.dropzone = document.getElementById('dropzone');
        this.fileInput = document.getElementById('fileInput');
        this.fileList = document.getElementById('fileList');
        this.userId = getUserId(); // Default user ID - you might want to generate this dynamically
        this.info = null



        this.setupEventListeners();
        this.checkIfResumeExistThenRender()
    }

    checkIfResumeExistThenRender() {
        const localStorageInfo = localStorage.getItem(`resume_${this.userId}`);
        if (localStorageInfo) {
            this.info = JSON.parse(localStorageInfo)
        }
        if (this.info) {
            const listItem = this.createFileListItem("Localstorage", 'Uploading...');
            this.fileList.appendChild(listItem);
            // this.displayExtractedInfo(this.info, listItem);
        }
    }

    setupEventListeners() {
        // Modal controls
        this.uploadBtn.addEventListener('click', () => this.openModal());
        this.closeBtn.addEventListener('click', () => this.closeModal());
        window.addEventListener('click', (e) => {
            if (e.target === this.modal) this.closeModal();
        });

        // Drag and drop handlers
        this.dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropzone.classList.add('dragover');
        });

        this.dropzone.addEventListener('dragleave', () => {
            this.dropzone.classList.remove('dragover');
        });

        this.dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropzone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length) this.handleFiles(files);
        });

        this.dropzone.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', () => {
            if (this.fileInput.files.length) {
                this.handleFiles(this.fileInput.files);
            }
        });
    }

    openModal() {
        this.modal.style.display = 'flex';
    }

    closeModal() {
        this.modal.style.display = 'none';
    }

    handleFiles(files) {
        Array.from(files).forEach(file => {
            if (this.validateFile(file)) {
                this.uploadFile(file);
            } else {
                alert('Please upload a PDF file under 5MB');
            }
        });
    }

    validateFile(file) {
        const validTypes = ['application/pdf'];
        const maxSize = 5 * 1024 * 1024; // 5MB
        return validTypes.includes(file.type) && file.size <= maxSize;
    }

    async uploadFile(file) {
        try {
            // Show upload in progress
            const listItem = this.createFileListItem(file.name, 'Uploading...');
            this.fileList.appendChild(listItem);

            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`/upload?user_id=${this.userId}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const result = await response.json();

            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({
                    type: EventType.RECEIVE_RESUME,
                }))
            }

            // Update UI with extracted information
            // this.displayExtractedInfo(result.extracted_info, listItem);
            this.info = result.extracted_info
            localStorage.setItem(`resume_${this.userId}`, JSON.stringify(result.extracted_info));

            this.closeModal();
        } catch (error) {
            console.error('Upload failed:', error);
            alert('Upload failed. Please try again.');
        }
    }

    createFileListItem(filename, status) {
        const li = document.createElement('li');
        li.className = 'file-item';
        li.innerHTML = `
    <div class="file-header">
        <i class="fas fa-file-pdf"></i>
        <span class="file-name">${filename}</span>
        <span class="file-status">${status}</span>
    </div>
    <div class="extracted-info"></div>
`;
        return li;
    }

    displayExtractedInfo(info, listItem) {
        const extractedInfoDiv = listItem.querySelector('.extracted-info');

        // Create sections for different types of information
        const personalInfoSection = this.createPersonalInfoSection(info.personal_information);
        const skillsSection = this.createSkillsSection(info.skills);
        const workExperienceSection = this.createWorkExperienceSection(info.work_experience);
        const projectsSection = this.createProjectsSection(info.projects);

        // Combine all sections
        extractedInfoDiv.innerHTML = `
            ${personalInfoSection}
            ${skillsSection}
            ${workExperienceSection}
            ${projectsSection}
        `;
    }

    createPersonalInfoSection(personalInfo) {
        return `
            <div class="info-section">
                <h4>Personal Information</h4>
                <p>${JSON.stringify(personalInfo) || 'Not provided'}</p>
            </div>
        `;
    }

    createSkillsSection(skills) {
        const skillsList = Array.isArray(skills) && skills.length > 0
            ? skills.join(', ')
            : 'None found';

        return `
            <div class="info-section">
                <h4>Skills</h4>
                <p>${skillsList}</p>
            </div>
        `;
    }

    createWorkExperienceSection(experiences) {
        if (!Array.isArray(experiences) || experiences.length === 0) {
            return `
                <div class="info-section">
                    <h4>Work Experience</h4>
                    <p>No work experience found</p>
                </div>
            `;
        }

        const experienceItems = experiences.map(exp => `
            <div class="experience-item">
                <h5>${exp.company} - ${exp.role}</h5>
                <p class="duration">${exp.duration}</p>
                
                ${this.createListSection('Responsibilities', exp.responsibilities)}
                ${this.createListSection('Achievements', exp.achievements)}
                ${this.createListSection('Technologies', exp.technologies)}
            </div>
        `).join('');

        return `
            <div class="info-section">
                <h4>Work Experience</h4>
                ${experienceItems}
            </div>
        `;
    }

    createProjectsSection(projects) {
        if (!Array.isArray(projects) || projects.length === 0) {
            return `
                <div class="info-section">
                    <h4>Projects</h4>
                    <p>No projects found</p>
                </div>
            `;
        }

        const projectItems = projects.map(project => `
            <div class="project-item">
                <h5>${project.name}</h5>
                <p class="description">${project.description}</p>
                
                ${this.createListSection('Technologies', project.technologies)}
                ${this.createListSection('Contributions', project.contributions)}
                ${this.createListSection('Outcomes', project.outcomes)}
                ${this.createListSection('Methodologies', project.methodologies)}
            </div>
        `).join('');

        return `
            <div class="info-section">
                <h4>Projects</h4>
                ${projectItems}
            </div>
        `;
    }

    createListSection(title, items) {
        if (!Array.isArray(items) || items.length === 0) {
            return '';
        }

        const listItems = items.map(item => `<li>${item}</li>`).join('');

        return `
            <div class="list-section">
                <h6>${title}:</h6>
                <ul>${listItems}</ul>
            </div>
        `;
    }

    // Helper method to sanitize text to prevent XSS
    sanitizeText(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Method to clear the display
    clearDisplay(listItem) {
        const extractedInfoDiv = listItem.querySelector('.extracted-info');
        if (extractedInfoDiv) {
            extractedInfoDiv.innerHTML = '';
        }
    }


}





class AudioChat {
    constructor() {
        this.recordButton = document.getElementById('recordButton');
        this.timerDisplay = document.getElementById('timer');
        this.statusDisplay = document.getElementById('status');
        this.messagesContainer = document.getElementById('messages');
        this.resumeHandler = new ResumeHandler()

        //this is for showing transcriptions
        this.currentTranscriptionDiv = null
        this.currentAudioResponseDiv = null

        // this.audioClient = new AudioStreamClient();

        this.audioClientMap = new Map()
        this.mediaSourceMap = new Map()


        this.isRecording = false;
        this.mediaRecorder = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.timerInterval = null;
        this.websocket = null;
        this.startTime = null;
        this.apiUrl = '/askchatpt/';
        this.streamUrl = '/stream-audio/';

        // things related to recoding
        this.audioContext = null;
        this.processor = null;
        this.globalStream = null;

        // Initialize speech recognition
        if (!('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
            alert('Speech recognition is not supported in this browser.');
            // Provide fallback options
        } else {
            this.recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            // Proceed with initialization
        }


        this.setupEventListeners();
        this.initWebSocket()
    }

    getAudioClient(response_id) {
        if (!this.audioClientMap.has(response_id)) {
            const audioPlayer = document.createElement('audio');
            audioPlayer.id = `audio-play-button_${response_id}`;
            document.body.appendChild(audioPlayer);
            this.audioClientMap.set(response_id, new AudioStreamClient(audioPlayer));
        }
        return this.audioClientMap.get(response_id);
    }

    getMediaSourceByResponseId(response_id) {
        if (!this.mediaSourceMap.has(response_id)) {
            const mediaSource = new MediaSourceHandler();
            this.mediaSourceMap.set(response_id, mediaSource);
        }
        return this.mediaSourceMap.get(response_id);
    }

    createAudioResponseMessage(response_id) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message received audio-response';
        messageDiv.id = `response_${response_id}`;

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = 'AI';

        const messageContent = document.createElement('div');
        messageContent.className = `message-content`;
        messageContent.id = `message-content_${response_id}`

        // Container for text response
        const textResponse = document.createElement('div');
        textResponse.className = 'message-text';
        textResponse.id = `chatgpt_response_box_${response_id}`;
        messageContent.appendChild(textResponse);

        // Audio player container
        const audioPlayer = document.createElement("audio")
        audioPlayer.id = `audio-player_${response_id}`;
        audioPlayer.src = this.getMediaSourceByResponseId(response_id).audioSrc
        audioPlayer.controls = true
        audioPlayer.autoplay = true

        audioPlayer.onended = () => {
            audioPlayer.duration = 0
        }

        messageContent.appendChild(audioPlayer);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);

        return messageDiv;
    }
    updateAudioPlayerUI(response_id) {
        //if not played yet
        const audioPlayer = document.getElementById(`audio-player_${response_id}`);
        if (audioPlayer) {
            if (audioPlayer.duration == 0)
                audioPlayer.play()
        }

    }

    base64ToArrayBuffer(base64String) {
        // Remove any data URL prefix if present
        const base64Data = base64String.replace(/^data:.*?;base64,/, '');

        // Convert base64 to binary string
        const binaryString = atob(base64Data);

        // Create Uint8Array from binary string
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        return bytes.buffer;
    }

    initWebSocket() {
        let userId = localStorage.getItem(USER_ID_KEY)
        if (!userId) {
            userId = crypto.randomUUID().toString()
            localStorage.setItem(USER_ID_KEY, userId)
        }
        if (!this.websocket || this.websocket.readyState === WebSocket.CLOSED) {
            this.websocket = new WebSocket(`ws://localhost:8000/ws/audio/${userId}`);
            websocket = this.websocket
            this.websocket.onmessage = async (event) => {
                if (typeof event.data === 'string') {
                    const transcript_data = JSON.parse(event.data);
                    switch (transcript_data.type) {
                        case 'chunk_transcription':
                            if (!this.currentTranscriptionDiv) {
                                this.currentTranscriptionDiv = this.createTranscriptionMessage(transcript_data.text);
                                this.messagesContainer.appendChild(this.currentTranscriptionDiv);
                            } else {
                                const transcriptDiv = this.currentTranscriptionDiv.querySelector('.message-text');
                                if (transcriptDiv) {
                                    transcriptDiv.textContent += transcript_data.text;
                                }
                            }
                            console.log("Chunk transcription:", transcript_data);
                            break;
                        case 'final_transcription':
                            this.currentTranscriptionDiv = null
                            console.log("Final transcription:", transcript_data.full_text);
                            break;
                        case 'chatgpt_response':
                            this.ifCurrentResponseDivIsNotExistCreateOne(transcript_data.response_id)
                            console.log("ChatGPT response:", transcript_data);
                            const chatgptResponse = this.currentAudioResponseDiv.querySelector(`#chatgpt_response_box_${transcript_data.response_id}`)
                            chatgptResponse.innerText = chatgptResponse.innerText + transcript_data.content
                            break
                        case 'askQuestion':
                            console.log("Ask question:", transcript_data);
                            this.addResponseMessage(`${window.location.origin}/audio/${transcript_data.audio}`, transcript_data.text, transcript_data.response_id);
                            // this.play_audio_player_by_id(transcript_data.response_id)
                            break
                        case 'audio_chunk':
                            console.log("Audio chunk", transcript_data);
                            this.ifCurrentResponseDivIsNotExistCreateOne(transcript_data.response_id)
                            const arrayBuffer = this.base64ToArrayBuffer(transcript_data.content);
                            this.getMediaSourceByResponseId(transcript_data.response_id).appendChunk(arrayBuffer);
                            this.updateAudioPlayerUI(transcript_data.response_id)
                            break
                        case 'audio_end':
                            console.log("Audio end");
                            setTimeout(() => {
                                this.currentAudioResponseDiv = null
                                this.getMediaSourceByResponseId(transcript_data.response_id).endStream()
                            }, 1000);
                            break
                        case 'chat_history':
                            console.log("Chat history", transcript_data);
                            this.renderHistory(transcript_data.history)
                            break
                        case 'askForResume':
                            this.resumeHandler.openModal()
                            break
                        default:
                            console.log("Received unknown data:", event.data);
                    }
                } else if (event.data instanceof Blob) {
                    // if (!isFirstChunkReceived) {
                    //     isFirstChunkReceived = true;
                    //     endTime = Date.now();
                    //     const audio_generation_time = document.getElementById("audio_generation_time")
                    //     audio_generation_time.innerText = "Audio Generation Time Taken (" + (endTime - startTime) / 1000 + " seconds)"
                    // }
                    // const arrayBuffer = await event.data.arrayBuffer();
                    // console.log("Received non-string data:", event.data);
                    // this.ifCurrentResponseDivIsNotExistCreateOne()
                    // this.audioClient.appendAudioChunk(arrayBuffer);

                    // // Update audio player UI
                    // this.updateAudioPlayerUI();

                }


            };
            this.websocket.onclose = function () {
                console.log("WebSocket closed. Retrying in 2 seconds...");
                setTimeout(this.initWebSocket, 2000);
            };
        }
    }

    renderHistory(history) {
        for (const chat of history) {
            const audio_url = `${window.location.origin}/audio/${chat['audio']}`
            if (chat['role'] === 'assistant') {
                this.addResponseMessage(audio_url, chat['content'], chat['id'], "received")
            } else {
                this.addResponseMessage(audio_url, chat['content'], chat['id'], "sent")
            }
        }
    }

    async fetchAudioBlob(url) {
        const response = await fetch(url);
        return response.blob();
    }

    ifCurrentResponseDivIsNotExistCreateOne(response_id) {
        const responseBox = document.getElementById(`response_${response_id}`)
        if (!responseBox) {
            this.currentAudioResponseDiv = this.createAudioResponseMessage(response_id);
            this.messagesContainer.appendChild(this.currentAudioResponseDiv);
            // Trigger reflow before adding visible class
            this.currentAudioResponseDiv.offsetHeight;
            this.currentAudioResponseDiv.classList.add('visible');
        } else {
            this.currentAudioResponseDiv = responseBox
        }


    }

    webSocketSendMessageWithEvent(event, message) {
        this.websocket.send(JSON.stringify({
            type: event,
            message: message
        }))
    }

    setupEventListeners() {
        this.recordButton.addEventListener('click', () => {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                this.startRecording();
            }
        });
    }


    startTimer() {
        this.startTime = Date.now();
        this.timerInterval = setInterval(() => {
            const elapsed = Date.now() - this.startTime;
            const minutes = Math.floor(elapsed / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            this.timerDisplay.textContent =
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    stopTimer() {
        clearInterval(this.timerInterval);
        this.timerDisplay.textContent = '00:00';
    }

    updateStatus(message) {
        this.statusDisplay.textContent = message;
    }

    addLoadingMessage() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message received';

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = 'AI';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'loading-indicator';
        loadingIndicator.innerHTML = '<i class="fas fa-spinner"></i> Processing your message...';

        messageContent.appendChild(loadingIndicator);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);

        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

        return messageDiv;
    }

    addResponseMessage(audioBlob) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message received';

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = 'AI';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const audioPlayer = this.createCustomAudioPlayer(audioBlob);
        messageContent.appendChild(audioPlayer);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);

        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    addMessageToChat(audioBlob) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message sent';

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = 'Y';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const audioPlayer = this.createCustomAudioPlayer(audioBlob);
        messageContent.appendChild(audioPlayer);

        messageDiv.appendChild(messageContent);
        messageDiv.appendChild(avatar);

        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

        // Process the audio through the API
        this.processAudioData(audioBlob);
    }

    createTranscriptionMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message sent';

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = 'Y';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const transcriptDiv = document.createElement('div');
        transcriptDiv.className = 'message-text';
        transcriptDiv.textContent = text;

        messageContent.appendChild(transcriptDiv);
        messageDiv.appendChild(messageContent);
        messageDiv.appendChild(avatar);

        return messageDiv;
    }

    async processTranscription(transcription) {
        try {
            // Show loading message
            const loadingMessage = this.addLoadingMessage();

            // Get audio response from the stream endpoint
            const audioBlob = await this.streamAudioFromText(transcription);

            // Remove loading message and add response
            loadingMessage.remove();
            this.addResponseMessage(audioBlob, transcription);

        } catch (error) {
            console.error('Error processing transcription:', error);
            this.updateStatus('Error getting response');
        }
    }

    async setupRecordingWorkletNode() {
        await this.audioContext.audioWorklet.addModule('static/realtime-audio-processor.js');

        return new AudioWorkletNode(
            this.audioContext,
            'realtime-audio-processor'
        );
    }

    handleMediaRecoder(stream) {
        this.mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus',
            bitsPerSecond: 256000
        });


        this.mediaRecorder.ondataavailable = (event) => {
            this.audioChunks.push(event.data);
        };

        this.mediaRecorder.onstop = () => {
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(audioBlob);
            // const audioPlayer = document.getElementById('recordedAudioPlayer');
            // audioPlayer.src = audioUrl;
            // document.getElementById('recordedAudioContainer').style.display = 'block';
            // audioPlayer.load();
        };

        this.mediaRecorder.start();

        this.isRecording = true;
    }

    processAudio(sampleData) {
        // ASR (Automatic Speech Recognition) and VAD (Voice Activity Detection)
        // models typically require mono audio with a sampling rate of 16 kHz,
        // represented as a signed int16 array type.
        //
        // Implementing changes to the sampling rate using JavaScript can reduce
        // computational costs on the server.
        const outputSampleRate = 16000;
        const decreaseResultBuffer = this.decreaseSampleRate(sampleData, this.audioContext.sampleRate, outputSampleRate);
        const audioData = this.convertFloat32ToInt16(decreaseResultBuffer);

        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(audioData);
        }
    }

    decreaseSampleRate(buffer, inputSampleRate, outputSampleRate) {
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

    convertFloat32ToInt16(buffer) {
        let l = buffer.length;
        const buf = new Int16Array(l);
        while (l--) {
            buf[l] = Math.min(1, buffer[l]) * 0x7FFF;
        }
        return buf.buffer;
    }


    async startRecording() {
        try {

            if (this.isRecording) return;
            this.isRecording = true;

            this.audioContext = new AudioContext();

            let onSuccess = async (stream) => {
                // Push user config to server
                this.webSocketSendMessageWithEvent(EventType.START_ANSWER, "Starting Answer");

                this.globalStream = stream;
                const input = this.audioContext.createMediaStreamSource(stream);
                const recordingNode = await this.setupRecordingWorkletNode();
                this.handleMediaRecoder(stream);
                recordingNode.port.onmessage = (event) => {
                    this.processAudio(event.data);
                };
                input.connect(recordingNode);


                this.recordButton.innerHTML = '<i class="fas fa-stop"></i><span>Stop Recording</span>';
                this.recordButton.classList.add('recording');
                this.startTimer();
                this.updateStatus('Recording in progress...');

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





        } catch (error) {
            console.error('Error accessing microphone:', error);
            this.updateStatus('Error accessing microphone');
        }
    }

    async stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.recognition.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());

            this.audioContext.close().then(() => this.audioContext = null);


            if (this.globalStream) {
                this.globalStream.getTracks().forEach(track => track.stop());
            }

            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.webSocketSendMessageWithEvent(EventType.END_ANSWER, "Stopping Answer");
            }


            this.isRecording = false;
            this.recordButton.innerHTML = '<i class="fas fa-microphone"></i><span>Start Recording</span>';
            this.recordButton.classList.remove('recording');
            this.stopTimer();
            this.updateStatus('Processing...');
        }
    }

    async streamAudioFromText(text) {
        try {
            const response = await fetch(`${this.streamUrl}?query=${encodeURIComponent(text)}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.blob();
        } catch (error) {
            console.error('Error streaming audio:', error);
            throw error;
        }
    }

    play_audio_player_by_id(response_id) {
        const audioPlayer = document.getElementById(`audio-play-button_${response_id}`);
        if (audioPlayer) {
            audioPlayer.click();
        }
    }
    createCustomAudioPlayer(audioBlob, response_id = "id") {
        const playerContainer = document.createElement('div');
        playerContainer.className = 'custom-audio-player';

        const playButton = document.createElement('button');
        playButton.className = 'audio-play-button';
        playButton.id = `audio-play-button_${response_id}`
        playButton.innerHTML = '<i class="fas fa-play"></i>';

        const timeline = document.createElement('div');
        timeline.className = 'audio-timeline';
        const progress = document.createElement('div');
        progress.className = 'audio-progress';
        progress.style.width = '0%';
        timeline.appendChild(progress);

        const timeDisplay = document.createElement('div');
        timeDisplay.className = 'audio-time';
        timeDisplay.textContent = '00:00';

        const audio = document.createElement('audio');
        audio.autoplay = true;
        audio.id = `audio_player_${response_id}`;
        if (typeof audioBlob === 'string') {
            audio.src = audioBlob;
        } else {
            audio.src = URL.createObjectURL(audioBlob);
        }

        let isPlaying = false;

        // Play the audio automatically when the player is created
        // audio.play().then(() => {
        //     isPlaying = true;
        //     playButton.innerHTML = '<i class="fas fa-pause"></i>';
        // }).catch((error) => {
        //     console.error('Autoplay failed:', error);
        // });

        playButton.addEventListener('click', () => {
            if (isPlaying) {
                audio.pause();
                isPlaying = false;
                playButton.innerHTML = '<i class="fas fa-play"></i>';
            } else {
                audio.play();
                isPlaying = true;
                playButton.innerHTML = '<i class="fas fa-pause"></i>';
            }
            isPlaying = !isPlaying;
        });

        audio.addEventListener('timeupdate', () => {
            const currentTime = Math.floor(audio.currentTime);
            const minutes = Math.floor(currentTime / 60);
            const seconds = currentTime % 60;
            timeDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            progress.style.width = `${(audio.currentTime / audio.duration) * 100}%`;
        });

        audio.addEventListener('ended', () => {
            playButton.innerHTML = '<i class="fas fa-play"></i>';
            isPlaying = false;
        });

        timeline.addEventListener('click', (e) => {
            const rect = timeline.getBoundingClientRect();
            const pos = (e.clientX - rect.left) / rect.width;
            audio.currentTime = pos * audio.duration;
        });

        playerContainer.appendChild(playButton);
        playerContainer.appendChild(timeline);
        playerContainer.appendChild(timeDisplay);

        return playerContainer;
    }


    addResponseMessage(audioBlob, transcription, response_id = "id", messageType = "received") {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${messageType}`;

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = 'AI';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const transcriptDiv = document.createElement('div');
        transcriptDiv.className = 'message-text';
        transcriptDiv.textContent = transcription;
        messageContent.appendChild(transcriptDiv);

        const audioPlayer = document.createElement('audio');
        audioPlayer.id = `audio_player_${response_id}`;
        if (typeof audioBlob === 'string') {
            audioPlayer.src = audioBlob;
        } else {
            audioPlayer.src = URL.createObjectURL(audioBlob);
        }
        audioPlayer.controls = true;
        messageContent.appendChild(audioPlayer);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);

        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

}



// Initialize both classes
const audioChat = new AudioChat();
