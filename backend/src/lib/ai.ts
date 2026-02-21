import { Configuration, OpenAIApi } from 'openai';
import { Anthropic } from 'anthropic';
import { config } from 'dotenv';

config();

const aiProvider = process.env.AI_PROVIDER;
const aiModel = process.env.AI_MODEL;
const aiApiKey = process.env.AI_API_KEY;

let aiClient;

if (aiProvider === 'openai') {
  const configuration = new Configuration({ apiKey: aiApiKey });
  aiClient = new OpenAIApi(configuration);
} else if (aiProvider === 'anthropic') {
  aiClient = new Anthropic({ apiKey: aiApiKey });
} else {
  throw new Error(`Unsupported AI provider: ${aiProvider}`);
}

export async function invokeLLM({ prompt, responseJsonSchema, systemPrompt }) {
  let result;
  try {
    if (aiProvider === 'openai') {
      const response = await aiClient.createChatCompletion({
        model: aiModel,
        messages: [{ role: 'user', content: prompt }],
        ...systemPrompt ? { messages: [{ role: 'system', content: systemPrompt }] } : {},
      });
      result = response.data.choices[0].message.content;
    } else if (aiProvider === 'anthropic') {
      const response = await aiClient.completions.create({
        model: aiModel,
        prompt,
        ...systemPrompt ? { systemPrompt } : {},
      });
      result = response.completion;
    }

    if (responseJsonSchema) {
      // Assuming you'll add JSON schema parsing here
      return JSON.parse(result);
    }
    return result;
  } catch (error) {
    throw new Error(`Error invoking LLM: ${error.message}`);
  }
}