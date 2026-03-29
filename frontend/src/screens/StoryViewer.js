import { useState, useEffect, useRef, useMemo } from "react";
import { streamAssets, regenerateImage } from "../api";
import "./StoryViewer.css";

function buildPhrases(scene_text, word_timings) {
	if (!word_timings || word_timings.length === 0) return [];
	const originalWords = scene_text.trim().split(/\s+/);
	const CHUNK_SIZE = 6;
	const phrases = [];
	for (let i = 0; i < word_timings.length; i += CHUNK_SIZE) {
		const chunk = word_timings.slice(i, i + CHUNK_SIZE);
		const displayWords = originalWords.slice(i, i + CHUNK_SIZE).join(" ");
		phrases.push({ text: displayWords, start: chunk[0].time });
	}
	return phrases;
}

export default function StoryViewer({ topic, plan, scenes, preGeneratedAssets = {}, characterDescriptions = "", onRestart }) {
	const [generatedScenes, setGeneratedScenes] = useState([]);
	const [status, setStatus] = useState("loading");
	const [progress, setProgress] = useState({ current: 0, total: 0 });
	const [current, setCurrent] = useState(0);
	const [loadingImage, setLoadingImage] = useState(false);
	const [regenUsed, setRegenUsed] = useState(false); // 1 regen per story total
	const [confirmRegen, setConfirmRegen] = useState(false);
	const audioRef = useRef(null);
	const [phraseIndex, setPhraseIndex] = useState(-1);

	const MOCK = process.env.REACT_APP_MOCK === "true";
	const BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

	useEffect(() => {
		generateAssets();
	}, []);

	const phrases = useMemo(() => {
		const scene = generatedScenes[current];
		if (!scene) return [];
		return buildPhrases(scene.scene_text, scene.word_timings);
	}, [current, generatedScenes]);

	// Autoplay + reset phrase when scene changes
	useEffect(() => {
		if (status !== "ready") return;
		setPhraseIndex(-1);
		setConfirmRegen(false);
		if (audioRef.current) {
			audioRef.current.pause();
			audioRef.current.currentTime = 0;
		}
		const timer = setTimeout(() => {
			audioRef.current?.play().catch(() => {});
		}, 100);
		return () => clearTimeout(timer);
	}, [current, status]);

	// Phrase sync
	useEffect(() => {
		const audio = audioRef.current;
		if (!audio || phrases.length === 0) return;
		const handleTimeUpdate = () => {
			const t = audio.currentTime;
			let idx = -1;
			for (let i = 0; i < phrases.length; i++) {
				if (t >= phrases[i].start) idx = i;
				else break;
			}
			setPhraseIndex(idx);
		};
		audio.addEventListener("timeupdate", handleTimeUpdate);
		return () => audio.removeEventListener("timeupdate", handleTimeUpdate);
	}, [current, phrases, status]);

	const generateAssets = async () => {
		if (MOCK) {
			try {
				const res = await fetch(`${BASE}/sample/story.json`);
				const data = await res.json();
				setGeneratedScenes(data.scenes);
				setStatus("ready");
			} catch (err) {
				console.error("Failed to load mock story.json:", err);
				const fallback = scenes.map((text, i) => ({
					scene_number: i + 1,
					scene_text: text,
					image_b64: null,
					audio_b64: null,
					mock_image_url: `${BASE}/sample/scene_${(i % 4) + 1}.png`,
					mock_audio_url: `${BASE}/sample/scene_${(i % 4) + 1}.mp3`,
					word_timings: [],
				}));
				setGeneratedScenes(fallback);
				setStatus("ready");
			}
			return;
		}

		const initial = scenes.map((text, i) => ({
			scene_number: i + 1,
			scene_text: text,
			image_b64: null,
			audio_b64: null,
			word_timings: [],
		}));

		const preGenMap = {};
		Object.values(preGeneratedAssets).forEach((a) => {
			preGenMap[a.scene_number] = a;
		});
		const merged = initial.map((s) => (preGenMap[s.scene_number] ? { ...s, ...preGenMap[s.scene_number] } : s));
		setGeneratedScenes(merged);

		const scene1 = merged.find((s) => s.scene_number === 1);
		if (scene1 && scene1.image_b64 && scene1.audio_b64) setStatus("ready");

		const missingScenes = merged.filter((s) => !s.image_b64);
		if (missingScenes.length === 0) {
			setStatus("ready");
			return;
		}

		try {
			await streamAssets(
				missingScenes.map((s) => s.scene_text),
				plan.art_style,
				characterDescriptions,
				(p) => setProgress({ current: p.scene, total: missingScenes.length }),
				(streamedScene) => {
					const originalNumber = missingScenes[streamedScene.scene_number - 1]?.scene_number;
					if (!originalNumber) return;
					setGeneratedScenes((prev) => {
						const updated = prev.map((s) =>
							s.scene_number === originalNumber
								? { ...s, image_b64: streamedScene.image_b64, audio_b64: streamedScene.audio_b64, word_timings: streamedScene.word_timings || [] }
								: s,
						);
						if (originalNumber === 1) setStatus("ready");
						return updated;
					});
				},
				() => console.log("Stream done"),
			);
		} catch (err) {
			console.error("Stream error:", err);
		}
	};

	const handlePrev = () => {
		audioRef.current?.pause();
		setCurrent((i) => i - 1);
	};
	const handleNext = () => {
		audioRef.current?.pause();
		setCurrent((i) => i + 1);
	};

	const handleRegenClick = () => {
		if (MOCK || regenUsed || loadingImage) return;
		setConfirmRegen(true);
		audioRef.current?.pause();
	};

	const handleRegenConfirm = async () => {
		setConfirmRegen(false);
		setLoadingImage(true);
		try {
			const res = await regenerateImage(scene.scene_number, scene.scene_text, plan.art_style, characterDescriptions);
			const updated = [...generatedScenes];
			updated[current] = { ...updated[current], image_b64: res.data.image_b64 };
			setGeneratedScenes(updated);
			setRegenUsed(true); // disable all regen buttons for this story
		} catch (err) {
			console.error(err);
		}
		setLoadingImage(false);
		// Restart audio and subtitles from beginning
		setPhraseIndex(-1);
		if (audioRef.current) {
			audioRef.current.currentTime = 0;
			audioRef.current.play().catch(() => {});
		}
	};

	// ── Loading screen ──
	if (status === "loading") {
		return (
			<div className="viewer-loading">
				<div className="viewer-loading-eyebrow">Creating your story</div>
				<div className="viewer-loading-topic">"{topic}"</div>
				<div className="viewer-loading-spinner" />
				<div className="viewer-loading-label">{progress.current > 0 ? `Generating scene ${progress.current} of ${progress.total}...` : "Starting..."}</div>
				{progress.total > 0 && (
					<div className="viewer-loading-bar">
						<div className="viewer-loading-fill" style={{ width: `${(progress.current / progress.total) * 100}%` }} />
					</div>
				)}
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
	const currentPhrase = phraseIndex >= 0 ? phrases[phraseIndex]?.text : null;

	return (
		<div className="viewer">
			<div className="viewer-scene" key={current}>
				<div className="viewer-image-wrap">
					{/* Image */}
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

					{/* Subtitle overlay */}
					{currentPhrase && (
						<div className="viewer-subtitle-overlay">
							<span className="viewer-subtitle-text">{currentPhrase}</span>
						</div>
					)}

					{/* Regen button + inline confirm */}
					{!MOCK &&
						<div className="viewer-regen-wrap">
							<button
								className={`viewer-regen-image-btn ${regenUsed ? "used" : ""}`}
								onClick={handleRegenClick}
								disabled={loadingImage || regenUsed}
								title={regenUsed ? "Already regenerated" : "New image"}
							>
								{loadingImage ? "..." : "↺"}
							</button>

							{/* Inline confirm — appears to the left of the button */}
							{confirmRegen && (
								<div className="viewer-regen-confirm">
									<div className="viewer-regen-confirm-text">
										Regenerate? <span>1 use per story.</span>
									</div>
									<div className="viewer-regen-confirm-actions">
										<button className="viewer-regen-confirm-cancel" onClick={() => setConfirmRegen(false)}>
											Cancel
										</button>
										<button className="viewer-regen-confirm-ok" onClick={handleRegenConfirm}>
											Yes
										</button>
									</div>
								</div>
							)}
						</div>
					}

					{/* Loading overlay */}
					{loadingImage && (
						<div className="viewer-regen-loading">
							<div className="viewer-image-loading-spinner" />
							<span>Generating new image...</span>
						</div>
					)}

					{/* Audio */}
					{(scene.audio_b64 || scene.mock_audio_url) && (
						<audio
							ref={audioRef}
							src={scene.mock_audio_url || `data:audio/mp3;base64,${scene.audio_b64}`}
							onEnded={() => {
								if (!isLast) setCurrent((i) => i + 1);
							}}
						/>
					)}
				</div>
			</div>

			{/* Navigation */}
			<div className="viewer-nav">
				<button className="viewer-nav-btn" onClick={handlePrev} disabled={isFirst}>
					← Prev
				</button>
				<div className="viewer-dots">
					{generatedScenes.map((_, i) => (
						<div key={i} className={`viewer-dot ${i === current ? "active" : ""}`} onClick={() => setCurrent(i)} />
					))}
				</div>
				{isLast ? (
					<button className="viewer-nav-btn viewer-restart-btn" onClick={onRestart}>
						✦ New story
					</button>
				) : (
					<button className="viewer-nav-btn" onClick={handleNext}>
						Next →
					</button>
				)}
			</div>
		</div>
	);
}
