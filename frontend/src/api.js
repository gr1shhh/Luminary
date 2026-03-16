import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const planStory = (topic) =>
  axios.post(`${BASE_URL}/plan`, { topic });

export const generateStory = (topic, plan, steering) =>
  axios.post(`${BASE_URL}/story`, { topic, plan, steering });

export const critiqueScene = (scene_number, scene_text, tone) =>
  axios.post(`${BASE_URL}/critique`, { scene_number, scene_text, tone });

export const regenerateScene = (scene_number, original_text, instruction, tone) =>
  axios.post(`${BASE_URL}/regenerate`, { scene_number, original_text, instruction, tone });

export const streamAssets = async (scenes, art_style, onProgress, onScene, onDone) => {
  const response = await fetch(`${BASE_URL}/generate-assets/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenes, art_style }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE messages are delimited by double newline \n\n
    // Split on double newline to get complete messages
    const messages = buffer.split('\n\n');
    // Last element may be incomplete — keep in buffer
    buffer = messages.pop();

    for (const message of messages) {
      // Each message may have multiple lines starting with "data: "
      const dataLine = message.split('\n').find(l => l.startsWith('data: '));
      if (!dataLine) continue;
      try {
        const data = JSON.parse(dataLine.slice(6));
        if (data.type === 'progress') onProgress(data);
        if (data.type === 'scene') onScene(data);
        if (data.type === 'done') onDone();
      } catch (e) {
        console.error('SSE parse error:', e.message);
      }
    }
  }

  // Process any remaining complete message in buffer
  if (buffer.includes('data: ')) {
    const dataLine = buffer.split('\n').find(l => l.startsWith('data: '));
    if (dataLine) {
      try {
        const data = JSON.parse(dataLine.slice(6));
        if (data.type === 'done') onDone();
      } catch (e) {}
    }
  }
};

export const regenerateImage = (scene_number, scene_text, art_style) =>
  axios.post(`${BASE_URL}/regenerate-image`, { scene_number, scene_text, art_style });

export const regenerateSceneAssets = (scene_number, scene_text, art_style, tone, instruction) =>
  axios.post(`${BASE_URL}/regenerate-scene-assets`, { scene_number, scene_text, art_style, tone, instruction });