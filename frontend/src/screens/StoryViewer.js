import { useState, useEffect, useRef } from 'react';
import { streamAssets, regenerateImage, regenerateSceneAssets } from '../api';
import './StoryViewer.css';

export default function StoryViewer({ topic, plan, scenes, onRestart }) {
  const [generatedScenes, setGeneratedScenes] = useState([]);
  const [status, setStatus] = useState('loading'); // loading | ready
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [current, setCurrent] = useState(0);
  const [editOpen, setEditOpen] = useState(false);
  const [editInput, setEditInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingImage, setLoadingImage] = useState(false);

  const audioRef = useRef(null);
  const MOCK = process.env.REACT_APP_MOCK === 'true';

  useEffect(() => { generateAssets(); }, []);

  // Auto-play audio when scene changes
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    // Small delay to let component re-render with new audio src
    const timer = setTimeout(() => {
      if (audioRef.current && audioRef.current.src) {
        audioRef.current.play().catch(() => {});
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [current, status]);

  const generateAssets = async () => {
    if (MOCK) {
      setProgress({ current: 0, total: scenes.length });
      const mock = [];
      for (let i = 0; i < scenes.length; i++) {
        setProgress({ current: i + 1, total: scenes.length });
        await new Promise(r => setTimeout(r, 900));
        mock.push({ scene_number: i + 1, scene_text: scenes[i], image_b64: null, audio_b64: null });
      }
      setGeneratedScenes(mock);
      setStatus('ready');
      return;
    }

    try {
      await streamAssets(
        scenes,
        plan.art_style,
        (p) => setProgress({ current: p.scene, total: p.total }),
        (scene) => setGeneratedScenes(prev => [...prev, scene]),
        () => setStatus('ready'),
      );
    } catch (err) {
      console.error(err);
      setStatus('ready');
    }
  };

  const scene = generatedScenes[current];
  const isFirst = current === 0;
  const isLast = current === generatedScenes.length - 1;

  const handlePrev = () => {
    if (audioRef.current) audioRef.current.pause();
    setCurrent(i => i - 1);
    setEditOpen(false);
  };
  const handleNext = () => {
    if (audioRef.current) audioRef.current.pause();
    setCurrent(i => i + 1);
    setEditOpen(false);
  };

  const handleRegenerateImage = async () => {
    setLoadingImage(true);
    try {
      if (!MOCK) {
        const res = await regenerateImage(scene.scene_number, scene.scene_text, plan.art_style);
        const updated = [...generatedScenes];
        updated[current] = { ...updated[current], image_b64: res.data.image_b64 };
        setGeneratedScenes(updated);
      }
    } catch (err) { console.error(err); }
    setLoadingImage(false);
  };

  const handleRewrite = async () => {
    if (!editInput.trim() || loading) return;
    setLoading(true);
    try {
      if (MOCK) {
        await new Promise(r => setTimeout(r, 1200));
        const updated = [...generatedScenes];
        updated[current] = { ...updated[current], scene_text: `[Rewritten] ${scene.scene_text}` };
        setGeneratedScenes(updated);
      } else {
        const res = await regenerateSceneAssets(
          scene.scene_number, scene.scene_text,
          plan.art_style, plan.tone, editInput
        );
        const updated = [...generatedScenes];
        updated[current] = { ...updated[current], ...res.data };
        setGeneratedScenes(updated);
      }
    } catch (err) { console.error(err); }
    setEditInput('');
    setEditOpen(false);
    setLoading(false);
  };

  // ── Loading screen ──
  if (status === 'loading') {
    return (
      <div className="viewer-loading">
        <div className="viewer-loading-eyebrow">Creating your story</div>
        <div className="viewer-loading-topic">"{topic}"</div>
        <div className="viewer-loading-spinner" />
        <div className="viewer-loading-label">
          {progress.current > 0
            ? `Generating scene ${progress.current} of ${progress.total}...`
            : 'Starting...'}
        </div>
        {progress.total > 0 && (
          <div className="viewer-loading-bar">
            <div
              className="viewer-loading-fill"
              style={{ width: `${(progress.current / progress.total) * 100}%` }}
            />
          </div>
        )}
      </div>
    );
  }

  if (!scene) return null;

  return (
    <div className="viewer">

      {/* Header */}
      <div className="viewer-header">
        <div className="viewer-eyebrow">Your Story</div>
        <div className="viewer-topic">"{topic}"</div>
        <div className="viewer-counter">{current + 1} / {generatedScenes.length}</div>
      </div>

      {/* Scene */}
      <div className="viewer-scene" key={current}>

        {/* Image */}
        <div className="viewer-image-wrap">
          {scene.image_b64 ? (
            <img className="viewer-image" src={`data:image/png;base64,${scene.image_b64}`} alt={`Scene ${scene.scene_number}`} />
          ) : (
            <div className="viewer-image-placeholder"><span>Scene {scene.scene_number}</span></div>
          )}
          <button className="viewer-regen-image-btn" onClick={handleRegenerateImage} disabled={loadingImage} title="New image">
            {loadingImage ? '...' : '↺'}
          </button>
        </div>

        {/* Body */}
        <div className="viewer-body">
          <div className="viewer-scene-number">Scene {scene.scene_number}</div>
          <div className="viewer-scene-text">{scene.scene_text}</div>

          {scene.audio_b64 && (
            <audio className="viewer-audio" controls src={`data:audio/mp3;base64,${scene.audio_b64}`} />
          )}

          {editOpen && (
            <div className="viewer-edit-row">
              <input
                className="viewer-edit-input"
                type="text"
                placeholder="How would you like to change this scene?"
                value={editInput}
                onChange={e => setEditInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleRewrite()}
                disabled={loading}
                autoFocus
              />
              <button className="viewer-edit-submit" onClick={handleRewrite} disabled={!editInput.trim() || loading}>
                {loading ? '...' : '↑'}
              </button>
            </div>
          )}

          <button className="viewer-edit-btn" onClick={() => setEditOpen(o => !o)}>
            {editOpen ? '✕ Cancel' : '✏ Rewrite this scene'}
          </button>
        </div>
      </div>

      {/* Navigation */}
      <div className="viewer-nav">
        <button className="viewer-nav-btn" onClick={handlePrev} disabled={isFirst}>← Prev</button>
        <div className="viewer-dots">
          {generatedScenes.map((_, i) => (
            <div key={i} className={`viewer-dot ${i === current ? 'active' : ''}`} onClick={() => { setCurrent(i); setEditOpen(false); }} />
          ))}
        </div>
        <button className="viewer-nav-btn" onClick={handleNext} disabled={isLast}>Next →</button>
      </div>

      <div className="viewer-footer">
        <button className="viewer-restart" onClick={onRestart}>✦ Create another story</button>
      </div>

    </div>
  );
}