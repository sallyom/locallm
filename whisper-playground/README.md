### Build Model Service

From this directory,

```bash
podman build -t whisper:image .
```

### Download Model

We need to download the model from HuggingFace. There are various Whisper models available which vary in size and can be found [here](https://huggingface.co/ggerganov/whisper.cpp). We will be using the `small` model which is about 466 MB.

- **small**
    - Download URL: [https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin](https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin)

```bash
cd ../models
wget --no-config --quiet --show-progress -O ggml-small.bin <Download URL>
cd ../
```

### Download audio files

Whisper.cpp requires as an input 16-bit WAV audio files. To convert your input audio files to 16-bit WAV format you can use `ffmpeg` like this:

```bash
ffmpeg -i <input.mp3> -ar 16000 -ac 1 -c:a pcm_s16le <output.wav>
```

Make sure to download your audio files in your `Local/path/to/locallm/models` folder.

### Deploy Model

Deploy the LLM and volume mount the model of choice.

```bash
podman run --rm -it \
        -v Local/path/to/locallm/models:/models:Z \
        -e AUDIO_FILE=/models/<audio-filename>
        whisper:image
```