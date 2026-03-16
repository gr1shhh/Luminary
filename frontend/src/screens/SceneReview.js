import { useState, useEffect } from 'react';
import { planStory, generateStory, critiqueScene, regenerateScene, generateSingleSceneAssets } from '../api';
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
  const preGeneratedAssets = useState({}); // scene_number -> asset data
  const [assets, setAssets] = preGeneratedAssets;

  const [pendingAssets, setPendingAssets] = useState({});
  const [completedCount, setCompletedCount] = useState(0);
  const [totalScenes, setTotalScenes] = useState(0);
  const MOCK = process.env.REACT_APP_MOCK === 'true';

  useEffect(() => { runPlanning(); }, []);

  // ── Step 1: Plan only ──
  const runPlanning = async () => {
    try {
      if (MOCK) {
        setStatus('planning'); setStatusText('Planning your story...');
        await new Promise(r => setTimeout(r, 1000));
        const mockPlan = { scene_count: 4, tone: 'melancholic and tense', art_style: 'Cartoon Illustration' };
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
          `Sergeant Thomas Hale sat in the dim trench, rifle across his knees, an unwritten letter in his hands. Dawn was two hours away. The assault would begin at first light. He pressed the pen to the paper and found he could not remember how to begin.`,
          `He wrote about the smell of his mother's kitchen. About his younger brother's laugh. About the dog that waited by the gate every evening. The words came slowly at first, then all at once, like a dam giving way in his chest.`,
          `The shelling started before he could finish. Men scrambled around him, but Thomas stayed seated, folding the letter with careful hands, pressing it into the breast pocket over his heart. Whatever happened next, she would know.`,
          `At the edge of the trench, just before the whistle, he looked up at the pale sky. The same sky she was under, somewhere far away. He thought: if this is the last thing I see, it is enough. Then the whistle blew, and he climbed.`,
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

  const generateWithRetry = async (sceneNumber, sceneText, artStyle) => {
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        const res = await generateSingleSceneAssets(sceneNumber, sceneText, artStyle);
        if (res.data.image_b64 && res.data.audio_b64) return res.data;
        console.log(`Scene ${sceneNumber} image missing, retrying (${attempt}/2)...`);
        await new Promise(r => setTimeout(r, 65000));
      } catch (err) {
        console.log(`Scene ${sceneNumber} attempt ${attempt} failed:`, err.message);
        if (attempt < 2) await new Promise(r => setTimeout(r, 65000));
        else throw err;
      }
    }
    throw new Error(`Scene ${sceneNumber} failed after 2 retries`);
  };

  const handleApprove = () => {
    setEditOpen(false);
    setEditInput('');

    const sceneNumber = currentScene + 1;
    const sceneText = scenes[currentScene];
    const isLast = currentScene === scenes.length - 1;

    if (!MOCK) {
      generateWithRetry(sceneNumber, sceneText, artStyle)
        .then(data => {
          setPendingAssets(prev => {
            const updated = { ...prev, [data.scene_number]: data };
            setCompletedCount(c => {
              const newCount = c + 1;
              if (newCount === scenes.length) {
                onApprove({ ...plan, art_style: artStyle }, scenes, updated);
              }
              return newCount;
            });
            return updated;
          });
        })
        .catch(err => {
          console.error('Scene generation failed after retries:', err);
          setStatus('error');
          setStatusText('Generation failed. Please try again in a few minutes.');
        });
    }

    if (!isLast) {
      setCurrentScene(i => i + 1);
    } else {
      if (MOCK) {
        onApprove({ ...plan, art_style: artStyle }, scenes, {});
      } else {
        setTotalScenes(scenes.length);
        setStatus('finalizing');
      }
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

  if (status === 'finalizing') {
    return (
      <div className="review-wrap">
        <div className="review-loading">
          <div className="review-spinner" />
          <div className="review-status-text">Finalizing your story...</div>
          <div className="review-loading-sub">{completedCount} of {totalScenes} scenes ready</div>
          <div className="viewer-loading-bar" style={{ width: 240, marginTop: 12 }}>
            <div className="viewer-loading-fill" style={{ width: `${totalScenes > 0 ? (completedCount / totalScenes) * 100 : 0}%` }} />
          </div>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="review-wrap">
        <div className="review-loading">
          <div className="review-status-text" style={{ color: '#c0392b' }}>{statusText}</div>
          <button className="steering-btn" style={{ marginTop: 16 }} onClick={() => window.location.reload()}>
            ↺ Start over
          </button>
        </div>
      </div>
    );
  }

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