class AudioStreamClient {
    constructor(audioElementId) {
        this.audioElement = document.getElementById(audioElementId);
        if (!this.audioElement) {
            throw new Error(`Audio element with id "${audioElementId}" not found`);
        }

        this.chunks = [];
        this.currentBlobUrl = null;
        this.isFirstChunk = true;
        this.isPlaying = false;
    }

    appendAudioChunk(chunk) {
        if (!chunk || chunk.byteLength === 0) {
            console.warn('Received empty chunk');
            return;
        }

        // Add the new chunk
        this.chunks.push(chunk);

        // Create a new blob from all chunks
        const blob = new Blob(this.chunks, { type: 'audio/mp3' });

        // Create a new URL for the blob
        const blobUrl = URL.createObjectURL(blob);

        // Clean up the previous blob URL
        if (this.currentBlobUrl) {
            URL.revokeObjectURL(this.currentBlobUrl);
        }

        // Store the current blob URL
        this.currentBlobUrl = blobUrl;

        // Update audio element
        const currentTime = this.audioElement.currentTime;
        this.audioElement.src = blobUrl;

        // If this is the first chunk, start playing immediately
        if (this.isFirstChunk) {
            this.isFirstChunk = false;
            this.play();
        } else if (this.isPlaying) {
            // If already playing, maintain playback
            this.audioElement.currentTime = currentTime;
            this.play();
        }
    }

    async play() {
        if (this.currentBlobUrl) {
            try {
                await this.audioElement.play();
                this.isPlaying = true;
            } catch (error) {
                console.error('Error playing audio:', error);
                this.isPlaying = false;
            }
        }
    }

    pause() {
        this.audioElement.pause();
        this.isPlaying = false;
    }

    reset() {
        this.chunks = [];
        this.isFirstChunk = true;
        this.isPlaying = false;
        if (this.currentBlobUrl) {
            URL.revokeObjectURL(this.currentBlobUrl);
            this.currentBlobUrl = null;
        }
        this.audioElement.src = '';
    }

    destroy() {
        this.reset();
        this.audioElement = null;
    }
}
