# Changes

- **Removed Hardcoded API Key:** The `OPENAI_API_KEY` is now fetched from an environment variable, which is a more secure practice.
- **Updated OpenAI API Usage:** The code now uses the `OpenAI` client and the `client.chat.completions.create` method, which is the modern way to interact with the OpenAI API.
- **Improved Import Handling:** The code now specifically catches `ImportError` if the `openai` library is not installed.
- **Instantiated Client:** The `OpenAI` client is instantiated only if the library is present and an API key is provided.
