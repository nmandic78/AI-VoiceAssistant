
# AI VoiceAssistant

AI VoiceAssistant is a Python-based voice assistant that combines speech-to-text (STT), text-to-speech (TTS), and either a locally hosted large language model (LLM) powered by [llama.cpp](https://github.com/ggerganov/llama.cpp) or the OpenAI API. It provides a simple way to interact with AI through voice commands, leveraging clipboard context and hotkeys for smooth operation. 
It is specialized for shell commands and coding. It gathers system info (OS, shell, GPU, python version, home dir, etc.) to provide correct commands for environment it runs.

## Features
- **Speech-to-Text (STT):** Converts spoken commands into text using a hotkey.
- **Flexible LLM Options:**
  - Local LLM via [llama.cpp](https://github.com/ggerganov/llama.cpp)
  - OpenAI API (requires API key; currently a To-Do to use environment variables for the API key)
- **Clipboard Integration:** Use the clipboard as additional context for commands.
- **Hotkey-based Control:** 
  - Start recording: `CMD` / `WinKey` / `Super` + `Shift`
  - Execute the transcribed command: `CMD` / `WinKey` / `Super` + `Control`
  - Cancel command execution: Speak the word `Cancel`.
- **Code Interaction:** Refactor or optimize code by including clipboard content in commands when the word "buffer" is spoken.
- **Memory:** Option to enable or dissable LLM memory via try icon menu. Useful when subsequent commands are needed with reference to command-response history.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/AI-VoiceAssistant.git
   cd AI-VoiceAssistant
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Option 1: Set up Llama.cpp:**
   - Follow the instructions on the [llama.cpp GitHub page](https://github.com/ggerganov/llama.cpp) to compile and set up the LLM server.
   - Download the required LLM model from HuggingFace in GGUF format and place it in any directory. I recommend some of Qwen2.5-Coder-Instruct models (https://huggingface.co/bartowski?search_models=Qwen2.5-Coder).
   - Start the Llama.cpp server:
     ```bash
     ./server --model /path/to/your/model
     ```
   - If possible use FlashAttention2 parameter (e.g. ./llama-server -m '/mnt/disk2/LLM_MODELS/models/Qwen2.5-Coder-14B-Instruct-Q8_0.gguf' -fa -ngl 99 ) for faster inference (see instructions in llama.cpp repo)

4. **Option 2: Use OpenAI API:**
   - Obtain an OpenAI API key from [OpenAI](https://openai.com).
   - Modify the code to input your API key when prompted. (ToDo: enable passing the API key via an environment variable.)

5. Run the Voice Assistant:
   ```bash
   python main.py
   ```

## Usage Instructions

### Hotkey Functions
- **Start Recording Speech:** Press `CMD` / `WinKey` / `Super` + `Shift`.
  - Speak your command. The assistant will transcribe it and display the text in real time.
  
- **Execute the Command:** Press `CMD` / `WinKey` / `Super` + `Control`.
  - If the word "Cancel" is detected, the command will not execute.
  - If the first word spoken is "buffer", clipboard content will be included in the prompt sent to the LLM.

### Example Commands
- **General Commands:**
  - "Extract the audio from a video file (input.mp4) and save it as an MP3 file."
  - "Cancel." (aborts execution)
  
- **Programming:**
  - Copy some code to the clipboard and say:
    - "Write a function to generate a report (in JSON format) summarizing disk usage statistics." 
    - "Buffer. Optimize this code."
    - "Buffer. Refactor the code to improve readability."

Transcription floating window:
![image](https://github.com/user-attachments/assets/b5caab28-6ec6-459a-9b47-861a653e69d7)

Enable/disable memory:

![Screenshot from 2024-11-30 16-30-47](https://github.com/user-attachments/assets/2754af6d-0626-49d3-ae48-a0778607186c)


## Demo

Short demonstration recorded in real time: https://youtu.be/UB_ZXU_a0xY

### Notes
- Ensure the Llama.cpp server is running before starting the Python script if using the local LLM.
- If using OpenAI API, ensure the API key is correctly set.

## To-Do
- Add an option to pass the OpenAI API key as an argument or environment variable for improved security and ease of use.

## Contributing
Contributions are welcome! Feel free to submit issues or pull requests to improve the project.

## License
This project is licensed under the MIT License. See the `LICENSE` file for more details.
