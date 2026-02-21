## Configuring AI

To configure the AI functionality of your application, you will need to set the following environment variables in the `.env` file:

- `AI_PROVIDER`: Choose between `openai`, `anthropic`, `google`, or `azure` depending on which AI provider you want to use.
- `AI_MODEL`: Specify the model name for the chosen provider, e.g., `gpt-4o` for OpenAI.
- `AI_API_KEY`: Provide the API key for the chosen provider to authenticate your requests.

This configuration will enable your application to invoke the chosen AI service to generate responses.