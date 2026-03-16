import { useState, useEffect } from 'react';
import { streamAssets } from '../api';
import './Generating.css';

const MOCK_IMAGE = 'https://placehold.co/800x450/1a1a1a/888888?text=Scene+Image';

export default function Generating({ topic, plan, scenes, onDone, onRestart }) {
  const [generatedScenes, setGeneratedScenes] = useState([]);
  const [currentlyGenerating, setCurrentlyGenerating] = useState(1);
  const [done, setDone] = useState(false);

  const MOCK = process.env.REACT_APP_MOCK === 'true';

  useEffect(() => { runGeneration(); }, []);

  const runGeneration = async () => {
    if (MOCK) {
      for (let i = 0; i < scenes.length; i++) {
        setCurrentlyGenerating(i + 1);
        await new Promise(r => setTimeout(r, 1200));
        setGeneratedScenes(prev => [...prev, {
          scene_number: i + 1,
          scene_text: scenes[i],
          image_b64: null,
          audio_b64: null,
        }]);
      }
      setDone(true);
      return;
    }

    try {
      await streamAssets(
        scenes,
        plan.art_style,
        (progress) => setCurrentlyGenerating(progress.scene),
        (scene) => setGeneratedScenes(prev => [...prev, scene]),
        () => setDone(true),
      );
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="generating">

      {/* Header */}
      <div className="generating-header">
        <div className="generating-eyebrow">Creating your story</div>
        <div className="generating-topic">"{topic}"</div>
      </div>

      {/* Progress bar */}
      {!done && (
        <div className="generating-progress-wrap">
          <div className="generating-progress-bar">
            <div
              className="generating-progress-fill"
              style={{ width: `${((currentlyGenerating - 1) / scenes.length) * 100}%` }}
            />
          </div>
          <div className="generating-progress-label">
            Generating scene {currentlyGenerating} of {scenes.length}...
          </div>
        </div>
      )}

      {/* Scene cards streaming in */}
      <div className="generating-scenes">
        {generatedScenes.map((scene) => (
          <div key={scene.scene_number} className="generating-card">

            {/* Image */}
            <div className="generating-image-wrap">
              {scene.image_b64 ? (
                <img
                  className="generating-image"
                  src={`data:image/png;base64,${scene.image_b64}`}
                  alt={`Scene ${scene.scene_number}`}
                />
              ) : (
                <div className="generating-image-placeholder">
                  <span>Scene {scene.scene_number}</span>
                </div>
              )}
            </div>

            {/* Text */}
            <div className="generating-card-body">
              <div className="generating-card-number">Scene {scene.scene_number}</div>
              <div className="generating-card-text">{scene.scene_text}</div>

              {/* Audio */}
              {scene.audio_b64 && (
                <audio
                  className="generating-audio"
                  controls
                  src={`data:audio/mp3;base64,${scene.audio_b64}`}
                />
              )}
            </div>

          </div>
        ))}
      </div>

      {/* Done — proceed button */}
      {done && (
        <div className="generating-done">
          <button className="generating-done-btn" onClick={() => onDone(generatedScenes)}>
            ✦ &nbsp; View Your Story
          </button>
          <button className="generating-restart" onClick={onRestart}>Start over</button>
        </div>
      )}

    </div>
  );
}