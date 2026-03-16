import { useState } from 'react';
import './index.css';
import Landing from './screens/Landing';
import SceneReview from './screens/SceneReview';
import StoryViewer from './screens/StoryViewer';
import { Analytics } from "@vercel/analytics/react";


export default function App() {
  const [screen, setScreen] = useState('landing');
  const [topic, setTopic] = useState('');
  const [plan, setPlan] = useState(null);
  const [scenes, setScenes] = useState([]);
  const [preGeneratedAssets, setPreGeneratedAssets] = useState({});

  const handleStart = (t) => {
    setTopic(t);
    setScreen('review');
  };

  const handleApprove = (p, s, assets = {}) => {
    setPlan(p);
    setScenes(s);
    setPreGeneratedAssets(assets);
    setScreen('viewer');
  };

  const handleRestart = () => {
    setTopic('');
    setPlan(null);
    setScenes([]);
    setPreGeneratedAssets({});
    setScreen('landing');
  };

  return (
    <>
    <Analytics />
    <div className="app">
      {screen === 'landing' && (
        <Landing onStart={handleStart} />
      )}
      {screen === 'review' && (
        <SceneReview
          topic={topic}
          onApprove={handleApprove}
          onRestart={handleRestart}
        />
      )}
      {screen === 'viewer' && (
        <StoryViewer
          topic={topic}
          plan={plan}
          scenes={scenes}
          preGeneratedAssets={preGeneratedAssets}
          onRestart={handleRestart}
        />
      )}
    </div>
    </>
  );
}