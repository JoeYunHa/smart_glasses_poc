import { useCallback, useEffect, useRef, useState } from "react";

interface UseTTSReturn {
  speaking: boolean;
  supported: boolean;
  speak: (text: string, lang?: string) => void;
  stop: () => void;
}

/**
 * Browser Web Speech API TTS hook.
 * Prefers a Korean voice when lang="ko-KR". Falls back to any available voice.
 * Cancels any in-progress utterance before starting a new one.
 */
export function useTTS(): UseTTSReturn {
  const [speaking, setSpeaking] = useState(false);
  const [supported] = useState(() => typeof window !== "undefined" && "speechSynthesis" in window);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Resolve the best available voice for the given language.
  const resolveVoice = useCallback((lang: string): SpeechSynthesisVoice | null => {
    if (!supported) return null;
    const voices = window.speechSynthesis.getVoices();
    // Prefer exact lang match, then prefix match (e.g. "ko" covers "ko-KR")
    return (
      voices.find((v) => v.lang === lang) ??
      voices.find((v) => v.lang.startsWith(lang.split("-")[0])) ??
      null
    );
  }, [supported]);

  const speak = useCallback((text: string, lang = "ko-KR") => {
    if (!supported || !text.trim()) return;

    // Strip emoji and excessive whitespace for cleaner audio output
    const cleaned = text.replace(/[\p{Emoji_Presentation}\p{Extended_Pictographic}]/gu, "").trim();

    window.speechSynthesis.cancel();
    setSpeaking(false);

    const utterance = new SpeechSynthesisUtterance(cleaned);
    utterance.lang = lang;
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    const voice = resolveVoice(lang);
    if (voice) utterance.voice = voice;

    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }, [supported, resolveVoice]);

  const stop = useCallback(() => {
    if (!supported) return;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  // Cancel any in-progress speech when the component unmounts.
  useEffect(() => {
    return () => {
      if (supported) window.speechSynthesis.cancel();
    };
  }, [supported]);

  return { speaking, supported, speak, stop };
}
