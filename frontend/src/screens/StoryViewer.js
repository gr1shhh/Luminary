import { useState, useEffect, useRef } from 'react';
import { streamAssets, regenerateImage, regenerateSceneAssets } from '../api';
import './StoryViewer.css';

export default function StoryViewer({ topic, plan, scenes, onRestart }) {
  const [generatedScenes, setGeneratedScenes] = useState([]);
  const [status, setStatus] = useState('loading');
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [current, setCurrent] = useState(0);
  const [editOpen, setEditOpen] = useState(false);
  const [editInput, setEditInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingImage, setLoadingImage] = useState(false);
  const audioRef = useRef(null);

  const MOCK = process.env.REACT_APP_MOCK === 'true';

  useEffect(() => { generateAssets(); }, []);

  // Autoplay when scene changes
  useEffect(() => {
    if (status !== 'ready') return;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    const timer = setTimeout(() => {
      audioRef.current?.play().catch(() => {});
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
        scenes, plan.art_style,
        (p) => setProgress({ current: p.scene, total: p.total }),
        (scene) => {
          console.log('Scene received:', scene.scene_number);
          setGeneratedScenes(prev => {
            // Show viewer as soon as first scene arrives
            if (prev.length === 0) setStatus('ready');
            return [...prev, scene];
          });
        },
        () => { console.log('Stream done'); },
      );
      setStatus('ready');
    } catch (err) {
      console.error('Stream error:', err);
      setStatus('ready');
    }
  };

  const handlePrev = () => { audioRef.current?.pause(); setCurrent(i => i - 1); setEditOpen(false); };
  const handleNext = () => { audioRef.current?.pause(); setCurrent(i => i + 1); setEditOpen(false); };

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
        const res = await regenerateSceneAssets(scene.scene_number, scene.scene_text, plan.art_style, plan.tone, editInput);
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
          {progress.current > 0 ? `Generating scene ${progress.current} of ${progress.total}...` : 'Starting...'}
        </div>
        {progress.total > 0 && (
          <div className="viewer-loading-bar">
            <div className="viewer-loading-fill" style={{ width: `${(progress.current / progress.total) * 100}%` }} />
          </div>
        )}
        {/* Scene text preview */}
        {progress.current > 0 && scenes[progress.current - 1] && (
          <div className="viewer-loading-preview">
            <div className="viewer-loading-preview-label">Scene {progress.current}</div>
            <div className="viewer-loading-preview-text">{scenes[progress.current - 1]}</div>
          </div>
        )}
      </div>
    );
  }

  const scene = generatedScenes[current];
  if (!scene) return null;

  const isFirst = current === 0;
  const isLast = current === generatedScenes.length - 1;

  return (
    <div className="viewer">

      {/* Full bleed image */}
      <div className="viewer-image-wrap" key={current}>
        {scene.image_b64 ? (
          <img className="viewer-image" src={`data:image/png;base64,${scene.image_b64}`} alt={`Scene ${scene.scene_number}`} />
        ) : (
          <div className="viewer-image-placeholder"><span>Scene {scene.scene_number}</span></div>
        )}
      </div>

      {/* Gradient overlay */}
      <div className="viewer-overlay" />

      {/* Hidden autoplay audio */}
      {scene.audio_b64 && (
        <audio ref={audioRef} src={`data:audio/mp3;base64,${scene.audio_b64}`} />
      )}

      {/* Top bar */}
      <div className="viewer-topbar">
        <button className="viewer-restart" onClick={onRestart}>✦ New story</button>
        <div className="viewer-counter">{current + 1} / {generatedScenes.length}</div>
      </div>

      {/* Regenerate image button */}
      <button className="viewer-regen-image-btn" onClick={handleRegenerateImage} disabled={loadingImage} title="New image">
        {loadingImage ? '...' : '↺'}
      </button>

      {/* Bottom content */}
      <div className="viewer-bottom">
        <div className="viewer-scene-number-row">
          <div className="viewer-scene-number">Scene {scene.scene_number}</div>
          {generatedScenes.length < scenes.length && (
            <div className="viewer-generating-badge">
              ⟳ Generating scene {generatedScenes.length + 1} of {scenes.length}...
            </div>
          )}
        </div>
        <div className="viewer-scene-text">{scene.scene_text}</div>

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

        <div className="viewer-nav">
          <button className="viewer-nav-btn" onClick={handlePrev} disabled={isFirst}>← Prev</button>
          <div className="viewer-dots">
            {generatedScenes.map((_, i) => (
              <div key={i} className={`viewer-dot ${i === current ? 'active' : ''}`}
                onClick={() => { setCurrent(i); setEditOpen(false); }} />
            ))}
          </div>
          <button className="viewer-nav-btn" onClick={handleNext} disabled={isLast}>Next →</button>
          <button className="viewer-edit-btn" onClick={() => setEditOpen(o => !o)}>
            {editOpen ? '✕ Cancel' : '✏ Edit'}
          </button>
        </div>
      </div>

    </div>
  );
}