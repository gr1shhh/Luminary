import { useState, useEffect } from 'react';
import { planStory, generateStory, critiqueScene, regenerateScene } from '../api';
import './SceneReview.css';

const CRITIQUE_THRESHOLD = 7;
const MAX_CRITIQUE_RETRIES = 2;
const ART_STYLES = [
  'Cinematic Photorealistic',
  'Cartoon Illustration',
  'Watercolor Painting',
  'Comic Book',
  'Dark Fantasy Digital Art',
];

export default function SceneReview({ topic, onApprove, onRestart }) {
  const [status, setStatus] = useState('planning'); // planning | steering | generating | ready
  const [statusText, setStatusText] = useState('Planning your story...');
  const [plan, setPlan] = useState(null);
  const [artStyle, setArtStyle] = useState('');
  const [steering, setSteering] = useState('');
  const [scenes, setScenes] = useState([]);
  const [currentScene, setCurrentScene] = useState(0);
  const [editOpen, setEditOpen] = useState(false);
  const [editInput, setEditInput] = useState('');
  const [rewriting, setRewriting] = useState(false);

  const MOCK = process.env.REACT_APP_MOCK === 'true';

  useEffect(() => { runPlanning(); }, []);

  // ── Step 1: Plan only ──
  const runPlanning = async () => {
    try {
      if (MOCK) {
        setStatus('planning'); setStatusText('Planning your story...');
        await new Promise(r => setTimeout(r, 1000));
        const mockPlan = { scene_count: 3, tone: 'melancholic and tense', art_style: 'cinematic photorealistic' };
        setPlan(mockPlan);
        setArtStyle(mockPlan.art_style);
        setStatus('steering');
        return;
      }

      setStatus('planning'); setStatusText('Planning your story...');
      const planRes = await planStory(topic);
      const p = planRes.data;
      setPlan(p);
      setArtStyle(p.art_style);
      setStatus('steering');
    } catch (err) {
      setStatusText('Something went wrong. Please restart.');
      console.error(err);
    }
  };

  // ── Step 2: Generate + critique after user confirms steering ──
  const runGeneration = async () => {
    try {
      if (MOCK) {
        setStatus('generating'); setStatusText('Writing your scenes...');
        await new Promise(r => setTimeout(r, 800));
        setStatusText('Refining and critiquing...');
        await new Promise(r => setTimeout(r, 600));
        setScenes([
          `The control room hummed with nervous energy. Engineer Frank Matthews pressed his palms flat against the cold metal console, watching the numbers climb. Outside, the whole world held its breath.`,
          `Static crackled over the radio. Then Armstrong's voice — calm, impossible calm — cut through: "The Eagle has landed." Frank's knees buckled. Around him, grown men wept openly.`,
          `Hours later, alone on the roof of the building, Frank looked up at the moon. It looked the same as it always had. But everything was different now. Everything would always be different.`,
        ]);
        setStatus('ready');
        return;
      }

      setStatus('generating'); setStatusText('Writing your scenes...');
      const storyRes = await generateStory(topic, plan, steering || null);
      let sc = storyRes.data.scenes;

      setStatusText('Refining and critiquing...');
      for (let i = 0; i < sc.length; i++) {
        let retries = 0;
        while (retries < MAX_CRITIQUE_RETRIES) {
          const critiqueRes = await critiqueScene(i + 1, sc[i], plan.tone);
          const { score, rewritten } = critiqueRes.data;
          if (score < CRITIQUE_THRESHOLD && rewritten) { sc[i] = rewritten; retries++; }
          else break;
        }
      }
      setScenes(sc);
      setStatus('ready');
    } catch (err) {
      setStatusText('Something went wrong. Please restart.');
      console.error(err);
    }
  };

  const handleApprove = () => {
    setEditOpen(false);
    setEditInput('');
    if (currentScene < scenes.length - 1) {
      setCurrentScene(i => i + 1);
    } else {
      onApprove({ ...plan, art_style: artStyle }, scenes);
    }
  };

  const handleEdit = () => {
    setEditOpen(true);
    setTimeout(() => document.getElementById('edit-input')?.focus(), 50);
  };

  const handleRewrite = async () => {
    if (!editInput.trim() || rewriting) return;
    setRewriting(true);
    try {
      if (MOCK) {
        await new Promise(r => setTimeout(r, 1000));
        const updated = [...scenes];
        updated[currentScene] = `[Rewritten] ${scenes[currentScene]}`;
        setScenes(updated);
      } else {
        const res = await regenerateScene(currentScene + 1, scenes[currentScene], editInput, plan.tone);
        const updated = [...scenes];
        updated[currentScene] = res.data.scene_text;
        setScenes(updated);
      }
    } catch (err) { console.error(err); }
    setEditInput('');
    setEditOpen(false);
    setRewriting(false);
  };

  const isLast = scenes.length > 0 && currentScene === scenes.length - 1;

  return (
    <div className="review">

      {/* Header */}
      <div className="review-header">
        <div className="review-eyebrow">Your Story</div>
        <div className="review-topic">"{topic}"</div>
        {plan && status !== 'planning' && (
          <div className="review-meta">
            <span>{plan.scene_count} scenes</span>
            <span className="review-meta-dot">·</span>
            <span>{plan.tone}</span>
            <span className="review-meta-dot">·</span>
            <span className="review-meta-style">{artStyle}</span>
          </div>
        )}
      </div>

      {/* Loading */}
      {(status === 'planning' || status === 'generating') && (
        <div className="review-loading">
          <div className="review-spinner" />
          <div className="review-status-text">{statusText}</div>
        </div>
      )}

      {/* ── Steering screen ── */}
      {status === 'steering' && plan && (
        <div className="steering-wrap">

          {/* Art style selector */}
          <div className="steering-section">
            <div className="steering-label">Art Style</div>
            <div className="steering-styles">
              {ART_STYLES.map(style => (
                <button
                  key={style}
                  className={`steering-style-btn ${artStyle.toLowerCase() === style.toLowerCase() ? 'active' : ''}`}
                  onClick={() => setArtStyle(style.toLowerCase())}
                >
                  {style}
                </button>
              ))}
            </div>
          </div>

          {/* Steering input */}
          <div className="steering-section">
            <div className="steering-label">Any direction before we write? <span className="steering-optional">(optional)</span></div>
            <input
              className="steering-input"
              type="text"
              placeholder="e.g. make it more emotional, add a twist ending..."
              value={steering}
              onChange={e => setSteering(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && runGeneration()}
            />
          </div>

          {/* Generate button */}
          <button className="steering-generate-btn" onClick={runGeneration}>
            ✦ &nbsp; Write My Story
          </button>

          <button className="review-restart" onClick={onRestart}>Restart</button>
        </div>
      )}

      {/* ── Scene review ── */}
      {status === 'ready' && scenes.length > 0 && (
        <div className="review-scene-wrap">

          {/* Progress dots */}
          <div className="review-dots">
            {scenes.map((_, i) => (
              <div key={i} className={`review-dot ${i === currentScene ? 'active' : ''} ${i < currentScene ? 'done' : ''}`} />
            ))}
          </div>

          {/* Scene card */}
          <div className="review-card">
            <div className="review-card-number">Scene {currentScene + 1} of {scenes.length}</div>
            <div className="review-card-text">{scenes[currentScene]}</div>

            {editOpen && (
              <div className="review-edit-row">
                <input
                  id="edit-input"
                  className="review-edit-input"
                  type="text"
                  placeholder="What would you like to change?"
                  value={editInput}
                  onChange={e => setEditInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleRewrite()}
                  disabled={rewriting}
                />
                <button
                  className="review-edit-submit"
                  onClick={handleRewrite}
                  disabled={!editInput.trim() || rewriting}
                >
                  {rewriting ? '...' : '↑'}
                </button>
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="review-actions">
            <button className="review-btn-edit" onClick={editOpen ? () => setEditOpen(false) : handleEdit}>
              {editOpen ? '✕ Cancel' : '✏ Edit'}
            </button>
            <button className="review-btn-approve" onClick={handleApprove}>
              {isLast ? '✦ Generate Story' : '✓ Approve'}
            </button>
          </div>

          <button className="review-restart" onClick={onRestart}>Restart</button>
        </div>
      )}
    </div>
  );
}