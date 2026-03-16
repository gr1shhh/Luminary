import { useState, useEffect, useRef } from 'react';
import { streamAssets, regenerateImage, regenerateSceneAssets } from '../api';
import './StoryViewer.css';

export default function StoryViewer({ topic, plan, scenes, preGeneratedAssets = {}, onRestart }) {
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
    // Step 1: Immediately seed ALL scenes with text — viewer is usable right away
    const BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const initial = scenes.map((text, i) => ({
      scene_number: i + 1,
      scene_text: text,
      image_b64: null,
      audio_b64: null,
      ...(MOCK && {
        mock_image_url: `${BASE}/sample/scene_${(i % 4) + 1}.png`,
        mock_audio_url: `${BASE}/sample/scene_${(i % 4) + 1}.mp3`,
      }),
    }));

    // Merge any pre-generated assets on top
    const preGenMap = {};
    Object.values(preGeneratedAssets).forEach(a => { preGenMap[a.scene_number] = a; });
    const merged = initial.map(s => preGenMap[s.scene_number] ? { ...s, ...preGenMap[s.scene_number] } : s);

    setGeneratedScenes(merged);
    setStatus('ready');

    if (MOCK) return;

    // Step 2: Stream missing image/audio for scenes not yet generated
    const missingScenes = merged.filter(s => !s.image_b64);
    if (missingScenes.length === 0) return;

    console.log(`Streaming ${missingScenes.length} missing scenes:`, missingScenes.map(s => s.scene_number));

    try {
      await streamAssets(
        missingScenes.map(s => s.scene_text),
        plan.art_style,
        (p) => setProgress({ current: p.scene, total: missingScenes.length }),
        (streamedScene) => {
          // Map back to original scene number
          const originalNumber = missingScenes[streamedScene.scene_number - 1]?.scene_number;
          if (!originalNumber) return;
          console.log('Assets received for scene:', originalNumber);
          setGeneratedScenes(prev =>
            prev.map(s => s.scene_number === originalNumber
              ? { ...s, image_b64: streamedScene.image_b64, audio_b64: streamedScene.audio_b64 }
              : s
            )
          );
        },
        () => console.log('Stream done'),
      );
    } catch (err) {
      console.error('Stream error:', err);
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
  const nextScene = generatedScenes[current + 1];
  const isNextReady = nextScene && (nextScene.mock || (nextScene.image_b64 && nextScene.audio_b64));
  const prevScene = generatedScenes[current - 1];
  const isPrevReady = prevScene && (prevScene.mock || (prevScene.image_b64 && prevScene.audio_b64));

  return (
    <div className="viewer">

      {/* Scene card */}
      <div className="viewer-scene" key={current}>

        {/* Image */}
        <div className="viewer-image-wrap">
          {scene.mock_image_url ? (
            <img className="viewer-image" src={scene.mock_image_url} alt={`Scene ${scene.scene_number}`} />
          ) : scene.image_b64 ? (
            <img className="viewer-image" src={`data:image/png;base64,${scene.image_b64}`} alt={`Scene ${scene.scene_number}`} />
          ) : (
            <div className="viewer-image-placeholder">
              <div className="viewer-image-loading-spinner" />
              <span>Generating image...</span>
            </div>
          )}
          <button className="viewer-regen-image-btn" onClick={handleRegenerateImage} disabled={loadingImage} title="Generate new image">
            {loadingImage ? '...' : '↺'}
          </button>
        </div>

        {/* Body */}
        <div className="viewer-body">
          <div className="viewer-scene-text">{scene.scene_text}</div>

          {/* Hidden autoplay audio */}
          {(scene.audio_b64 || scene.mock_audio_url) && (
            <audio ref={audioRef} src={scene.mock_audio_url || `data:audio/mp3;base64,${scene.audio_b64}`} />
          )}


        </div>
      </div>

      {/* Navigation */}
      <div className="viewer-nav">
        <button className="viewer-nav-btn" onClick={handlePrev} disabled={isFirst}>← Prev</button>
        <div className="viewer-dots">
          {generatedScenes.map((_, i) => (
            <div key={i}
              className={`viewer-dot ${i === current ? 'active' : ''}`}
              onClick={() => { setCurrent(i); setEditOpen(false); }} />
          ))}
        </div>
        {isLast
          ? <button className="viewer-nav-btn viewer-restart-btn" onClick={onRestart}>✦ New story</button>
          : <button className="viewer-nav-btn" onClick={handleNext}>Next →</button>
        }
      </div>

    </div>
  );
}
