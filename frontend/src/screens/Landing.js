import { useState } from 'react';
import './Landing.css';

const SUGGESTIONS = [
  'A NASA engineer watching the moon landing',
  'A soldier writing his last letter home before battle',
  'A lighthouse keeper on the night a ship disappears',
];

export default function Landing({ onStart }) {
  const [topic, setTopic] = useState('');

  const handleSubmit = () => {
    if (topic.trim()) onStart(topic.trim());
  };

  const handleKey = (e) => {
    if (e.key === 'Enter') handleSubmit();
  };

  return (
    <div className="landing">
      <div className="landing-hero">
        <div className="landing-eyebrow">AI Story Engine</div>
        <h1 className="landing-title">
          Lumi<span>nary</span>
        </h1>
        <p className="landing-sub">Turn any idea into a cinematic story</p>
      </div>

      <div className="landing-input-row">
        <input
          className="landing-input"
          type="text"
          placeholder="Describe a moment, a person, a world..."
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={handleKey}
          autoFocus
        />
        <button
          className="landing-submit"
          onClick={handleSubmit}
          disabled={!topic.trim()}
        >
          ↑
        </button>
      </div>

      <div className="landing-suggestions-label">or try one of these</div>

      <div className="landing-chips">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            className="landing-chip"
            onClick={() => onStart(s)}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}