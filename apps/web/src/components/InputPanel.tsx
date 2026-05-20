import { MapPin, Mic, MonitorSmartphone, Upload } from "lucide-react";
import { useRef, useState } from "react";
import type { AgentMode, ContextRequest, DeviceInfo, GpsContext } from "@/types/agent";

const DEFAULT_DEVICES: DeviceInfo[] = [
  {
    device_id: "light-001",
    name: "거실 조명",
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
  {
    label: "안전 경보",
    request: "지금 건너도 안전한지 알려줘",
    gps: {
      latitude: 37.5665,
      longitude: 126.978,
      location_type: "crosswalk",
      place_name: "광화문 사거리",
    },
    videoPath: "/sample_videos/safety_alert_01.mp4",
    imagePath: "/sample_images/safety_alert_01.png",
  },
  {
    label: "기기 제어",
    request: "거실 조명 꺼줘",
    gps: null,
    videoPath: null,
    imagePath: "/sample_images/device_control_01.png",
  },
  {
    label: "장면 인식",
    request: "여기 무엇이 보이는지 설명해줘",
    gps: null,
    videoPath: "/sample_videos/scene_assistant_01.mp4",
    imagePath: "/sample_images/scene_assistant_01.png",
  },
  {
    label: "맥락 기억",
    request: "아까 본 카페가 어디였는지 알려줘",
    gps: {
      latitude: 37.57,
      longitude: 126.982,
      location_type: "street",
      place_name: "서울 시청 앞",
    },
    videoPath: null,
    imagePath: "/sample_images/context_memory_cafe_01.png",
  },
  {
    label: "라벨 인식",
    request: "약 라벨을 읽고 복용법을 알려줘",
    gps: null,
    videoPath: null,
    imagePath: "/sample_images/label_reader_medicine_01.png",
  },
];

type MediaType = "image" | "video" | null;

interface Props {
  onSubmit: (ctx: ContextRequest, image?: File, video?: File) => void;
  loading: boolean;
}

const CONTROL_BUTTON_BASE =
  "flex min-h-[44px] min-w-0 items-center justify-center gap-1.5 rounded-[14px] border px-3 py-2.5 text-center text-xs transition-all";

export default function InputPanel({ onSubmit, loading }: Props) {
  const [request, setRequest] = useState("");
  const [mode, setMode] = useState<AgentMode>("optimized");
  const [gps, setGps] = useState<GpsContext | null>(null);
  const [useDevices, setUseDevices] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [mediaPreview, setMediaPreview] = useState<string | null>(null);
  const [mediaType, setMediaType] = useState<MediaType>(null);
  const [mediaLoading, setMediaLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function clearMedia() {
    setImageFile(null);
    setVideoFile(null);
    setMediaPreview(null);
    setMediaType(null);
  }

  function setImageMedia(file: File, url: string) {
    setImageFile(file);
    setVideoFile(null);
    setMediaPreview(url);
    setMediaType("image");
  }

  function setVideoMedia(file: File, url: string) {
    setVideoFile(file);
    setImageFile(null);
    setMediaPreview(url);
    setMediaType("video");
  }

  async function applyScenario(s: (typeof QUICK_SCENARIOS)[number]) {
    setRequest(s.request);
    setGps(s.gps ?? null);
    setUseDevices(s.label === "기기 제어");
    clearMedia();

    // Prefer video when available, fall back to image.
    if (s.videoPath) {
      setMediaLoading(true);
      try {
        const res = await fetch(s.videoPath);
        if (res.ok) {
          const blob = await res.blob();
          const filename = s.videoPath.split("/").pop() ?? "video.mp4";
          const file = new File([blob], filename, { type: blob.type || "video/mp4" });
          setVideoMedia(file, URL.createObjectURL(blob));
          return;
        }
      } catch {
        // Fall through to image.
      } finally {
        setMediaLoading(false);
      }
    }

    if (s.imagePath) {
      setMediaLoading(true);
      try {
        const res = await fetch(s.imagePath);
        const blob = await res.blob();
        const filename = s.imagePath.split("/").pop() ?? "image.png";
        const file = new File([blob], filename, { type: blob.type });
        setImageMedia(file, URL.createObjectURL(blob));
      } catch {
        // Ignore missing sample media in local demo environments.
      } finally {
        setMediaLoading(false);
      }
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    if (file.type.startsWith("video/")) {
      setVideoMedia(file, url);
    } else {
      setImageMedia(file, url);
    }
    e.target.value = "";
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!request.trim()) return;

    onSubmit(
      {
        user_request: request,
        gps,
        nearby_devices: useDevices ? DEFAULT_DEVICES : [],
        mode,
      },
      imageFile ?? undefined,
      videoFile ?? undefined,
    );
  }

  return (
    <form onSubmit={handleSubmit} className="telemetry-card reveal-up rounded-[24px] p-5 sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <Mic className="h-4 w-4 shrink-0 text-[var(--signal)]" />
          <h2 className="display-face text-lg font-bold uppercase text-white">시나리오 입력</h2>
        </div>
        <span className="rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-3 py-1 text-[11px] uppercase tracking-[0.12em] text-[var(--text-faint)]">
          {loading ? "실행 중" : "준비"}
        </span>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5">
        {QUICK_SCENARIOS.map((scenario) => (
          <button
            key={scenario.label}
            type="button"
            onClick={() => void applyScenario(scenario)}
            className="min-w-0 rounded-[16px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] px-3.5 py-3 text-left transition-all hover:-translate-y-0.5 hover:border-[var(--signal)] hover:bg-[rgba(125,249,208,0.08)]"
          >
            <p className="button-copy button-copy-strong display-face text-[13px] font-bold text-white sm:text-sm">
              {scenario.label}
            </p>
            <p className="button-copy mt-1 text-[11px] text-[var(--text-faint)]">{scenario.request}</p>
          </button>
        ))}
      </div>

      <div className="mt-4">
        <input
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          placeholder="직접 요청을 입력하세요"
          className="w-full rounded-[16px] border border-[var(--line)] bg-[rgba(3,9,14,0.72)] px-4 py-3 text-sm text-white placeholder:text-[var(--text-faint)] focus:border-[var(--signal)] focus:outline-none"
        />
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-4">
        <div className="grid grid-cols-2 gap-2 sm:col-span-2">
          {(["optimized", "baseline"] as AgentMode[]).map((currentMode) => (
            <button
              key={currentMode}
              type="button"
              onClick={() => setMode(currentMode)}
              className={`${CONTROL_BUTTON_BASE} ${
                mode === currentMode
                  ? "border-[var(--signal)] bg-[rgba(125,249,208,0.12)] text-[var(--signal)]"
                  : "border-[var(--line)] bg-[rgba(3,9,14,0.58)] text-[var(--text-dim)]"
              }`}
            >
              <span className="display-face block whitespace-nowrap text-[11px] uppercase tracking-[0.03em] sm:text-[12px]">
                {currentMode}
              </span>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() =>
            setGps(
              gps
                ? null
                : {
                    latitude: 37.5665,
                    longitude: 126.978,
                    location_type: "crosswalk",
                    place_name: "광화문 사거리",
                  },
            )
          }
          className={`${CONTROL_BUTTON_BASE} ${
            gps
              ? "border-[rgba(255,200,111,0.45)] bg-[rgba(255,200,111,0.10)] text-[var(--amber)]"
              : "border-[var(--line)] bg-[rgba(3,9,14,0.58)] text-[var(--text-dim)]"
          }`}
        >
          <MapPin className="h-3.5 w-3.5 shrink-0" />
          <span className="min-w-0 truncate whitespace-nowrap text-[10px] sm:text-[11px]">
            {gps ? gps.place_name : "GPS 켜기"}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setUseDevices(!useDevices)}
          className={`${CONTROL_BUTTON_BASE} ${
            useDevices
              ? "border-[rgba(139,184,255,0.45)] bg-[rgba(139,184,255,0.10)] text-[var(--accent)]"
              : "border-[var(--line)] bg-[rgba(3,9,14,0.58)] text-[var(--text-dim)]"
          }`}
        >
          <MonitorSmartphone className="h-3.5 w-3.5 shrink-0" />
          <span className="min-w-0 truncate whitespace-nowrap text-[10px] sm:text-[11px]">
            {useDevices ? `기기 ${DEFAULT_DEVICES.length}개 사용` : "기기 켜기"}
          </span>
        </button>
      </div>

      {mediaLoading && (
        <div className="mt-3 flex items-center gap-2 rounded-[14px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] px-4 py-3 text-xs text-[var(--text-dim)]">
          <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--signal)]" />
          샘플 미디어를 불러오는 중입니다.
        </div>
      )}

      {mediaPreview && !mediaLoading && (
        <div className="mt-3 overflow-hidden rounded-[16px] border border-[rgba(125,249,208,0.3)] bg-[rgba(125,249,208,0.04)]">
          {mediaType === "video" ? (
            <video
              src={mediaPreview}
              controls
              className="max-h-48 w-full object-cover"
            />
          ) : (
            <img src={mediaPreview} alt="payload preview" className="max-h-48 w-full object-cover" />
          )}
          <div className="flex items-center justify-between gap-2 px-3 py-2">
            <div className="flex min-w-0 items-center gap-2">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--signal)]" />
              <span className="truncate text-[11px] text-[var(--signal)]">
                {(mediaType === "video" ? videoFile?.name : imageFile?.name) ?? ""}
              </span>
            </div>
            <span className="shrink-0 rounded-full border border-[var(--line)] px-2 py-0.5 text-[10px] uppercase tracking-widest text-[var(--text-faint)]">
              {mediaType === "video" ? "video" : "image"}
            </span>
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,video/mp4,video/quicktime,video/webm,video/avi"
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className={`${CONTROL_BUTTON_BASE} flex-shrink-0 border-[var(--line)] bg-[rgba(3,9,14,0.58)] text-[var(--text-dim)] hover:border-[var(--signal)] hover:text-[var(--signal)]`}
          title="이미지 또는 영상 직접 업로드"
        >
          <Upload className="h-3.5 w-3.5 shrink-0" />
          <span className="whitespace-nowrap text-[10px] sm:text-[11px]">미디어 업로드</span>
        </button>

        <button
          type="submit"
          disabled={loading || !request.trim()}
          className="display-face flex-1 rounded-[18px] border border-[var(--signal)] bg-[linear-gradient(90deg,rgba(125,249,208,0.16),rgba(139,184,255,0.14))] px-4 py-3.5 text-center text-sm font-bold text-white transition-all hover:-translate-y-0.5 disabled:border-[var(--line)] disabled:bg-[rgba(255,255,255,0.04)] disabled:text-[var(--text-faint)]"
        >
          <span className="button-pill block uppercase">{loading ? "실행 중" : "에이전트 실행"}</span>
        </button>
      </div>
    </form>
  );
}
