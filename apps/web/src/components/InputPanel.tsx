import { ImageIcon, MapPin, Mic, MonitorSmartphone, Video } from "lucide-react";
import { useRef, useState } from "react";
import type { AgentMode, ContextRequest, DeviceInfo, GpsContext } from "@/types/agent";

const DEFAULT_DEVICES: DeviceInfo[] = [
  {
    device_id: "light-001",
    name: "거실 스마트 조명",
    type: "smart_light",
    supported_actions: ["turn_on", "turn_off", "set_brightness"],
    risk_level: "low",
    requires_confirmation: false,
    state: { power: "on" },
  },
  {
    device_id: "speaker-001",
    name: "블루투스 스피커",
    type: "speaker",
    supported_actions: ["play", "pause", "set_volume"],
    risk_level: "low",
    requires_confirmation: false,
    state: { power: "off" },
  },
];

const QUICK_SCENARIOS = [
  { label: "안전 경보", request: "지금 건너도 괜찮아?", gps: { latitude: 37.5665, longitude: 126.978, location_type: "crosswalk", place_name: "광화문 교차로" } },
  { label: "기기 제어", request: "거실 조명 꺼줘", gps: null },
  { label: "장면 설명", request: "여기 뭐가 있어?", gps: null },
  { label: "기억 검색", request: "아까 본 카페 다시 가려면?", gps: { latitude: 37.57, longitude: 126.982, location_type: "street", place_name: "삼청동" } },
];

interface Props {
  onSubmit: (ctx: ContextRequest, image?: File, video?: File) => void;
  loading: boolean;
}

export default function InputPanel({ onSubmit, loading }: Props) {
  const [request, setRequest] = useState("");
  const [mode, setMode] = useState<AgentMode>("optimized");
  const [gps, setGps] = useState<GpsContext | null>(null);
  const [useDevices, setUseDevices] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const imageRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLInputElement>(null);

  function applyScenario(s: (typeof QUICK_SCENARIOS)[0]) {
    setRequest(s.request);
    setGps(s.gps ?? null);
    if (s.label === "기기 제어") setUseDevices(true);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!request.trim()) return;
    const ctx: ContextRequest = {
      user_request: request,
      gps,
      nearby_devices: useDevices ? DEFAULT_DEVICES : [],
      mode,
    };
    onSubmit(ctx, imageFile ?? undefined, videoFile ?? undefined);
  }

  return (
    <form onSubmit={handleSubmit} className="bg-gray-900 rounded-xl p-5 space-y-4 border border-gray-700">
      <div className="flex items-center gap-2 mb-1">
        <Mic className="w-4 h-4 text-purple-400" />
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">입력 패널</h2>
      </div>

      {/* Quick scenarios */}
      <div className="flex flex-wrap gap-2">
        {QUICK_SCENARIOS.map((s) => (
          <button
            key={s.label}
            type="button"
            onClick={() => applyScenario(s)}
            className="text-xs px-3 py-1.5 rounded-full bg-gray-800 hover:bg-purple-900 text-gray-300 hover:text-purple-200 border border-gray-700 hover:border-purple-600 transition-colors"
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* User request */}
      <div>
        <label className="block text-xs text-gray-400 mb-1">사용자 요청</label>
        <input
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          placeholder="예: 지금 건너도 괜찮아? / 조명 꺼줘"
          className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-purple-500"
        />
      </div>

      {/* Mode toggle */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-400">모드:</span>
        {(["optimized", "baseline"] as AgentMode[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              mode === m
                ? "bg-purple-700 border-purple-500 text-white"
                : "bg-gray-800 border-gray-600 text-gray-400 hover:border-gray-500"
            }`}
          >
            {m === "optimized" ? "Optimized" : "Baseline"}
          </button>
        ))}
      </div>

      {/* GPS */}
      <div className="flex items-center gap-2">
        <MapPin className="w-4 h-4 text-gray-500" />
        <button
          type="button"
          onClick={() =>
            setGps(gps ? null : { latitude: 37.5665, longitude: 126.978, location_type: "crosswalk", place_name: "광화문" })
          }
          className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
            gps ? "bg-emerald-900 border-emerald-600 text-emerald-300" : "bg-gray-800 border-gray-600 text-gray-400"
          }`}
        >
          {gps ? `GPS: ${gps.place_name}` : "GPS 없음"}
        </button>
      </div>

      {/* Devices */}
      <div className="flex items-center gap-2">
        <MonitorSmartphone className="w-4 h-4 text-gray-500" />
        <button
          type="button"
          onClick={() => setUseDevices(!useDevices)}
          className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
            useDevices ? "bg-blue-900 border-blue-600 text-blue-300" : "bg-gray-800 border-gray-600 text-gray-400"
          }`}
        >
          {useDevices ? `주변 기기 ${DEFAULT_DEVICES.length}개 활성` : "주변 기기 없음"}
        </button>
      </div>

      {/* File uploads */}
      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => imageRef.current?.click()}
          className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors ${
            imageFile ? "bg-indigo-900 border-indigo-600 text-indigo-300" : "bg-gray-800 border-gray-600 text-gray-400"
          }`}
        >
          <ImageIcon className="w-3 h-3" />
          {imageFile ? imageFile.name.slice(0, 16) + "…" : "이미지 업로드"}
        </button>
        <input ref={imageRef} type="file" accept="image/*" className="hidden" onChange={(e) => { setImageFile(e.target.files?.[0] ?? null); setVideoFile(null); }} />

        <button
          type="button"
          onClick={() => videoRef.current?.click()}
          className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors ${
            videoFile ? "bg-indigo-900 border-indigo-600 text-indigo-300" : "bg-gray-800 border-gray-600 text-gray-400"
          }`}
        >
          <Video className="w-3 h-3" />
          {videoFile ? videoFile.name.slice(0, 16) + "…" : "영상 업로드"}
        </button>
        <input ref={videoRef} type="file" accept="video/*" className="hidden" onChange={(e) => { setVideoFile(e.target.files?.[0] ?? null); setImageFile(null); }} />
      </div>

      <button
        type="submit"
        disabled={loading || !request.trim()}
        className="w-full py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium transition-colors"
      >
        {loading ? "처리 중…" : "Agent 실행"}
      </button>
    </form>
  );
}
