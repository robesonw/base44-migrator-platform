"""
Generator for Base44 compatibility client adapter.
Generates a compatibility SDK that mimics Base44 client API.
"""
import json
from pathlib import Path
from typing import Dict, List, Any
from app.generators.client_adapter_gen.utils import entity_to_slug, detect_language


def generate_base44_client_adapter(
    target_dir: Path,
    storage_plan: Dict[str, Any],
    ui_contract: Dict[str, Any],
    base44_usage: Dict[str, Any],
    source_dir: Path,
) -> List[str]:
    """
    Generate Base44 compatibility client adapter in target directory.
    
    Returns list of generated file paths.
    """
    generated_files = []
    
    # Detect language (ts or js)
    lang = detect_language(source_dir, ui_contract)
    ext = lang
    
    # Get entities from storage plan
    entities = [e["name"] for e in storage_plan.get("entities", [])]
    
    # Create src/api directory (prefer frontend/src/api if frontend dir exists)
    frontend_dir = target_dir / "frontend"
    if frontend_dir.exists():
        api_dir = frontend_dir / "src" / "api"
    else:
        api_dir = target_dir / "src" / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate HTTP client
    http_file = api_dir / f"http.{ext}"
    http_file.write_text(_generate_http_client(ext), encoding="utf-8")
    generated_files.append(str(http_file.relative_to(target_dir)))
    
    # Generate entities module
    entities_file = api_dir / f"entities.{ext}"
    entities_file.write_text(_generate_entities_module(entities, ext), encoding="utf-8")
    generated_files.append(str(entities_file.relative_to(target_dir)))
    
    # Generate LLM module
    llm_file = api_dir / f"llm.{ext}"
    llm_file.write_text(_generate_llm_module(ext), encoding="utf-8")
    generated_files.append(str(llm_file.relative_to(target_dir)))
    
    # Generate storage stub
    storage_file = api_dir / f"storage.{ext}"
    storage_file.write_text(_generate_storage_stub(ext), encoding="utf-8")
    generated_files.append(str(storage_file.relative_to(target_dir)))
    
    # Generate functions stub
    functions_file = api_dir / f"functions.{ext}"
    functions_file.write_text(_generate_functions_stub(ext), encoding="utf-8")
    generated_files.append(str(functions_file.relative_to(target_dir)))
    
    # Generate integrations module (compatibility layer)
    integrations_file = api_dir / f"integrations.{ext}"
    integrations_file.write_text(_generate_integrations_module(ext), encoding="utf-8")
    generated_files.append(str(integrations_file.relative_to(target_dir)))
    
    # Generate auth stub
    auth_file = api_dir / f"auth.{ext}"
    auth_file.write_text(_generate_auth_stub(ext), encoding="utf-8")
    generated_files.append(str(auth_file.relative_to(target_dir)))
    
    # Generate main base44Client
    client_file = api_dir / f"base44Client.{ext}"
    client_file.write_text(_generate_base44_client(ext), encoding="utf-8")
    generated_files.append(str(client_file.relative_to(target_dir)))
    
    # Generate .env.example file (in frontend dir if it exists, otherwise target root)
    frontend_dir = target_dir / "frontend"
    if frontend_dir.exists():
        env_example_file = frontend_dir / ".env.example"
    else:
        env_example_file = target_dir / ".env.example"
    _generate_env_example(env_example_file)
    generated_files.append(str(env_example_file.relative_to(target_dir)))
    
    return generated_files


def _generate_http_client(ext: str) -> str:
    """Generate HTTP client wrapper."""
    if ext == "ts":
        return '''/**
 * HTTP client wrapper for API requests
 */
const API_BASE_URL = (typeof process !== 'undefined' && process.env?.VITE_API_BASE_URL) || 
                      (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || 
                      'http://localhost:8081';

export async function httpRequest(
  method: string,
  url: string,
  data?: any
): Promise<any> {
  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
    config.body = JSON.stringify(data);
  }

  const response = await fetch(`${API_BASE_URL}${url}`, config);

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `HTTP ${response.status}: ${errorText}`;
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorMessage;
    } catch (e) {
      // Use text error if JSON parsing fails
    }
    throw new Error(errorMessage);
  }

  // DELETE returns 204 No Content
  if (response.status === 204) {
    return null;
  }

  return await response.json();
}
'''
    else:
        return '''/**
 * HTTP client wrapper for API requests
 */
const API_BASE_URL = (typeof process !== 'undefined' && process.env?.VITE_API_BASE_URL) || 
                      (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || 
                      'http://localhost:8081';

export async function httpRequest(method, url, data = null) {
  const config = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
    config.body = JSON.stringify(data);
  }

  const response = await fetch(`${API_BASE_URL}${url}`, config);

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `HTTP ${response.status}: ${errorText}`;
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorMessage;
    } catch (e) {
      // Use text error if JSON parsing fails
    }
    throw new Error(errorMessage);
  }

  // DELETE returns 204 No Content
  if (response.status === 204) {
    return null;
  }

  return await response.json();
}
'''


def _generate_entities_module(entities: List[str], ext: str) -> str:
    """Generate entities proxy module."""
    if ext == "ts":
        return '''/**
 * Entities proxy for Base44 compatibility
 */
import { httpRequest } from './http';

function entityNameToSlug(entityName: string): string {
  return entityName
    .replace(/([A-Z])/g, '-$1')
    .toLowerCase()
    .replace(/^-/, '');
}

function createEntityClient(entityName: string) {
  const slug = entityNameToSlug(entityName);

  return {
    async list(options: { limit?: number; offset?: number; q?: string } = {}) {
      const params = new URLSearchParams();
      if (options.limit !== undefined) params.append('limit', options.limit.toString());
      if (options.offset !== undefined) params.append('offset', options.offset.toString());
      if (options.q !== undefined) params.append('q', options.q);
      
      const queryString = params.toString() ? `?${params.toString()}` : '';
      const response = await httpRequest('GET', `/api/${slug}${queryString}`);
      return response.items || [];
    },

    async get(id: string) {
      return await httpRequest('GET', `/api/${slug}/${id}`);
    },

    async create(data: any) {
      return await httpRequest('POST', `/api/${slug}`, data);
    },

    async update(id: string, data: any) {
      return await httpRequest('PUT', `/api/${slug}/${id}`, data);
    },

    async patch(id: string, data: any) {
      return await httpRequest('PATCH', `/api/${slug}/${id}`, data);
    },

    async delete(id: string) {
      return await httpRequest('DELETE', `/api/${slug}/${id}`);
    },

    async filter(filters: any) {
      // Client-side filtering after fetching all
      const all = await this.list({});
      return all.filter((item: any) => {
        return Object.entries(filters).every(([key, value]) => item[key] === value);
      });
    },
  };
}

// Create entities proxy
export const entities = new Proxy({}, {
  get(target: any, entityName: string) {
    if (!target[entityName]) {
      target[entityName] = createEntityClient(entityName);
    }
    return target[entityName];
  },
});
'''
    else:
        return '''/**
 * Entities proxy for Base44 compatibility
 */
import { httpRequest } from './http';

function entityNameToSlug(entityName) {
  return entityName
    .replace(/([A-Z])/g, '-$1')
    .toLowerCase()
    .replace(/^-/, '');
}

function createEntityClient(entityName) {
  const slug = entityNameToSlug(entityName);

  return {
    async list(options = {}) {
      const params = new URLSearchParams();
      if (options.limit !== undefined) params.append('limit', options.limit.toString());
      if (options.offset !== undefined) params.append('offset', options.offset.toString());
      if (options.q !== undefined) params.append('q', options.q);
      
      const queryString = params.toString() ? `?${params.toString()}` : '';
      const response = await httpRequest('GET', `/api/${slug}${queryString}`);
      return response.items || [];
    },

    async get(id) {
      return await httpRequest('GET', `/api/${slug}/${id}`);
    },

    async create(data) {
      return await httpRequest('POST', `/api/${slug}`, data);
    },

    async update(id, data) {
      return await httpRequest('PUT', `/api/${slug}/${id}`, data);
    },

    async patch(id, data) {
      return await httpRequest('PATCH', `/api/${slug}/${id}`, data);
    },

    async delete(id) {
      return await httpRequest('DELETE', `/api/${slug}/${id}`);
    },

    async filter(filters) {
      // Client-side filtering after fetching all
      const all = await this.list({});
      return all.filter((item) => {
        return Object.entries(filters).every(([key, value]) => item[key] === value);
      });
    },
  };
}

// Create entities proxy
export const entities = new Proxy({}, {
  get(target, entityName) {
    if (!target[entityName]) {
      target[entityName] = createEntityClient(entityName);
    }
    return target[entityName];
  },
});
'''


def _generate_llm_module(ext: str) -> str:
    """Generate LLM provider module with OpenRouter support."""
    if ext == "ts":
        return '''/**
 * LLM provider abstraction with OpenRouter support
 */
const LLM_PROVIDER = (typeof process !== 'undefined' && process.env?.VITE_LLM_PROVIDER) || 
                      (typeof import.meta !== 'undefined' && import.meta.env?.VITE_LLM_PROVIDER) || 
                      'openrouter';

const OPENROUTER_API_KEY = (typeof process !== 'undefined' && process.env?.VITE_OPENROUTER_API_KEY) || 
                            (typeof import.meta !== 'undefined' && import.meta.env?.VITE_OPENROUTER_API_KEY) || 
                            '';

const OPENROUTER_MODEL = (typeof process !== 'undefined' && process.env?.VITE_OPENROUTER_MODEL) || 
                         (typeof import.meta !== 'undefined' && import.meta.env?.VITE_OPENROUTER_MODEL) || 
                         'meta-llama/llama-3.3-70b-instruct';

export async function invoke(prompt: string, options: any = {}): Promise<{
  text: string;
  raw: any;
  model: string;
  provider: string;
}> {
  const provider = (options.provider || LLM_PROVIDER).toLowerCase();

  if (provider === 'openrouter') {
    if (!OPENROUTER_API_KEY) {
      throw new Error('VITE_OPENROUTER_API_KEY environment variable is required for OpenRouter provider');
    }

    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': typeof window !== 'undefined' ? window.location.origin : '',
        'X-Title': 'Base44 Compatibility Client',
      },
      body: JSON.stringify({
        model: options.model || OPENROUTER_MODEL,
        messages: [
          {
            role: 'user',
            content: prompt,
          },
        ],
        ...options,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OpenRouter API error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    const text = data.choices?.[0]?.message?.content || '';

    // If response_json_schema was requested, try to parse JSON from text
    if (options.response_json_schema && text) {
      try {
        const jsonMatch = text.match(/\\{[\\s\\S]*\\}/);
        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          return {
            text: JSON.stringify(parsed),
            raw: data,
            model: data.model || OPENROUTER_MODEL,
            provider: 'openrouter',
            ...parsed, // Spread parsed JSON properties for direct access
          };
        }
      } catch (e) {
        // If parsing fails, return text as-is
      }
    }

    return {
      text,
      raw: data,
      model: data.model || OPENROUTER_MODEL,
      provider: 'openrouter',
    };
  } else if (provider === 'openai') {
    throw new Error('OpenAI provider not yet implemented. Please use OpenRouter or set VITE_LLM_PROVIDER=openrouter');
  } else if (provider === 'anthropic') {
    throw new Error('Anthropic provider not yet implemented. Please use OpenRouter or set VITE_LLM_PROVIDER=openrouter');
  } else {
    throw new Error(`Unknown LLM provider: ${provider}. Supported providers: openrouter, openai, anthropic`);
  }
}

export const llm = {
  invoke,
};
'''
    else:
        return '''/**
 * LLM provider abstraction with OpenRouter support
 */
const LLM_PROVIDER = (typeof process !== 'undefined' && process.env?.VITE_LLM_PROVIDER) || 
                      (typeof import.meta !== 'undefined' && import.meta.env?.VITE_LLM_PROVIDER) || 
                      'openrouter';

const OPENROUTER_API_KEY = (typeof process !== 'undefined' && process.env?.VITE_OPENROUTER_API_KEY) || 
                            (typeof import.meta !== 'undefined' && import.meta.env?.VITE_OPENROUTER_API_KEY) || 
                            '';

const OPENROUTER_MODEL = (typeof process !== 'undefined' && process.env?.VITE_OPENROUTER_MODEL) || 
                         (typeof import.meta !== 'undefined' && import.meta.env?.VITE_OPENROUTER_MODEL) || 
                         'meta-llama/llama-3.3-70b-instruct';

export async function invoke(prompt, options = {}) {
  const provider = (options.provider || LLM_PROVIDER).toLowerCase();

  if (provider === 'openrouter') {
    if (!OPENROUTER_API_KEY) {
      throw new Error('VITE_OPENROUTER_API_KEY environment variable is required for OpenRouter provider');
    }

    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': typeof window !== 'undefined' ? window.location.origin : '',
        'X-Title': 'Base44 Compatibility Client',
      },
      body: JSON.stringify({
        model: options.model || OPENROUTER_MODEL,
        messages: [
          {
            role: 'user',
            content: prompt,
          },
        ],
        ...options,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OpenRouter API error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    const text = data.choices?.[0]?.message?.content || '';

    // If response_json_schema was requested, try to parse JSON from text
    if (options.response_json_schema && text) {
      try {
        const jsonMatch = text.match(/\\{[\\s\\S]*\\}/);
        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          return {
            text: JSON.stringify(parsed),
            raw: data,
            model: data.model || OPENROUTER_MODEL,
            provider: 'openrouter',
            ...parsed, // Spread parsed JSON properties for direct access
          };
        }
      } catch (e) {
        // If parsing fails, return text as-is
      }
    }

    return {
      text,
      raw: data,
      model: data.model || OPENROUTER_MODEL,
      provider: 'openrouter',
    };
  } else if (provider === 'openai') {
    throw new Error('OpenAI provider not yet implemented. Please use OpenRouter or set VITE_LLM_PROVIDER=openrouter');
  } else if (provider === 'anthropic') {
    throw new Error('Anthropic provider not yet implemented. Please use OpenRouter or set VITE_LLM_PROVIDER=openrouter');
  } else {
    throw new Error(`Unknown LLM provider: ${provider}. Supported providers: openrouter, openai, anthropic`);
  }
}

export const llm = {
  invoke,
};
'''


def _generate_integrations_module(ext: str) -> str:
    """Generate integrations.Core compatibility layer."""
    if ext == "ts":
        return '''/**
 * Integrations.Core compatibility layer for Base44
 * Routes InvokeLLM to the LLM module, stubs other methods
 */
import { invoke as llmInvoke } from './llm';
import { storage } from './storage';

export const Core = {
  /**
   * Invoke LLM - routes to llm.invoke()
   * Supports response_json_schema for structured JSON responses
   */
  async InvokeLLM(params: {
    prompt: string;
    file_urls?: string[];
    response_json_schema?: any;
    model?: string;
    [key: string]: any;
  }): Promise<any> {
    const { prompt, file_urls, response_json_schema, model, ...restOptions } = params;
    
    // Build messages array - if file_urls exist, we'd need to handle them
    // For now, OpenRouter API doesn't support file_urls directly in this format
    // This would need vision model support
    const options: any = {
      model,
      response_json_schema,
      ...restOptions,
    };

    const result = await llmInvoke(prompt, options);
    
    // If response_json_schema was provided and we got parsed JSON, return it directly
    if (response_json_schema && typeof result === 'object') {
      // Remove text/raw/model/provider props and return the rest (parsed JSON)
      const { text, raw, model: resultModel, provider, ...parsedData } = result;
      return Object.keys(parsedData).length > 0 ? parsedData : result;
    }
    
    return result;
  },

  /**
   * Upload file - stubbed for now
   */
  async UploadFile(params: { file: File | Blob }): Promise<{ file_url: string }> {
    throw new Error('UploadFile not yet implemented in compatibility client. Storage API needs backend implementation.');
  },

  /**
   * Extract data from uploaded file - stubbed
   */
  async ExtractDataFromUploadedFile(params: { file_url: string; [key: string]: any }): Promise<any> {
    throw new Error('ExtractDataFromUploadedFile not yet implemented in compatibility client.');
  },

  /**
   * Generate image - stubbed
   */
  async GenerateImage(params: { prompt: string; [key: string]: any }): Promise<{ image_url: string }> {
    throw new Error('GenerateImage not yet implemented in compatibility client.');
  },
};

export const integrations = {
  Core,
};
'''
    else:
        return '''/**
 * Integrations.Core compatibility layer for Base44
 * Routes InvokeLLM to the LLM module, stubs other methods
 */
import { invoke as llmInvoke } from './llm';
import { storage } from './storage';

export const Core = {
  /**
   * Invoke LLM - routes to llm.invoke()
   * Supports response_json_schema for structured JSON responses
   */
  async InvokeLLM(params) {
    const { prompt, file_urls, response_json_schema, model, ...restOptions } = params;
    
    // Build messages array - if file_urls exist, we'd need to handle them
    // For now, OpenRouter API doesn't support file_urls directly in this format
    // This would need vision model support
    const options = {
      model,
      response_json_schema,
      ...restOptions,
    };

    const result = await llmInvoke(prompt, options);
    
    // If response_json_schema was provided and we got parsed JSON, return it directly
    if (response_json_schema && typeof result === 'object') {
      // Remove text/raw/model/provider props and return the rest (parsed JSON)
      const { text, raw, model: resultModel, provider, ...parsedData } = result;
      return Object.keys(parsedData).length > 0 ? parsedData : result;
    }
    
    return result;
  },

  /**
   * Upload file - stubbed for now
   */
  async UploadFile(params) {
    throw new Error('UploadFile not yet implemented in compatibility client. Storage API needs backend implementation.');
  },

  /**
   * Extract data from uploaded file - stubbed
   */
  async ExtractDataFromUploadedFile(params) {
    throw new Error('ExtractDataFromUploadedFile not yet implemented in compatibility client.');
  },

  /**
   * Generate image - stubbed
   */
  async GenerateImage(params) {
    throw new Error('GenerateImage not yet implemented in compatibility client.');
  },
};

export const integrations = {
  Core,
};
'''


def _generate_storage_stub(ext: str) -> str:
    """Generate storage stub."""
    if ext == "ts":
        return '''/**
 * Storage API stub (not yet implemented)
 */
export const storage = {
  upload: async (file: any, options?: any) => {
    throw new Error('Storage API not yet implemented in compatibility client');
  },
  download: async (path: string) => {
    throw new Error('Storage API not yet implemented in compatibility client');
  },
  list: async (prefix?: string) => {
    throw new Error('Storage API not yet implemented in compatibility client');
  },
};
'''
    else:
        return '''/**
 * Storage API stub (not yet implemented)
 */
export const storage = {
  upload: async (file, options) => {
    throw new Error('Storage API not yet implemented in compatibility client');
  },
  download: async (path) => {
    throw new Error('Storage API not yet implemented in compatibility client');
  },
  list: async (prefix) => {
    throw new Error('Storage API not yet implemented in compatibility client');
  },
};
'''


def _generate_functions_stub(ext: str) -> str:
    """Generate functions stub."""
    if ext == "ts":
        return '''/**
 * Functions API stub (not yet implemented)
 */
export const functions = {
  invoke: async (name: string, data?: any) => {
    throw new Error('Functions API not yet implemented in compatibility client');
  },
};
'''
    else:
        return '''/**
 * Functions API stub (not yet implemented)
 */
export const functions = {
  invoke: async (name, data) => {
    throw new Error('Functions API not yet implemented in compatibility client');
  },
};
'''


def _generate_auth_stub(ext: str) -> str:
    """Generate auth stub."""
    if ext == "ts":
        return '''/**
 * Auth API stub (backend doesn't have auth endpoints)
 */
export const auth = {
  me: async () => {
    return null;
  },
  logout: () => {
    // No-op
  },
  redirectToLogin: () => {
    // No-op
  },
};
'''
    else:
        return '''/**
 * Auth API stub (backend doesn't have auth endpoints)
 */
export const auth = {
  me: async () => {
    return null;
  },
  logout: () => {
    // No-op
  },
  redirectToLogin: () => {
    // No-op
  },
};
'''


def _generate_base44_client(ext: str) -> str:
    """Generate main base44Client export."""
    if ext == "ts":
        return '''/**
 * Base44 compatibility client
 */
import { entities } from './entities';
import { llm } from './llm';
import { storage } from './storage';
import { functions } from './functions';
import { integrations } from './integrations';
import { auth } from './auth';

const base44 = {
  entities,
  llm,
  storage,
  functions,
  integrations,
  auth,
};

export { base44 };
export default base44;
'''
    else:
        return '''/**
 * Base44 compatibility client
 */
import { entities } from './entities';
import { llm } from './llm';
import { storage } from './storage';
import { functions } from './functions';
import { integrations } from './integrations';
import { auth } from './auth';

const base44 = {
  entities,
  llm,
  storage,
  functions,
  integrations,
  auth,
};

export { base44 };
export default base44;
'''


def _generate_env_example(env_file: Path) -> None:
    """Generate .env.example file with LLM configuration."""
    content = """# API Base URL
VITE_API_BASE_URL=http://localhost:8081

# LLM Provider Configuration - OpenRouter
# Note: For Vite to expose env vars to client-side code, they must be prefixed with VITE_
VITE_OPENROUTER_API_KEY=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
VITE_OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct
VITE_LLM_PROVIDER=openrouter
"""
    env_file.write_text(content, encoding="utf-8")
