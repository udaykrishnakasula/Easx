import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sliders,
  RotateCcw,
  Copy,
  Check,
  X,
  Maximize2,
  Minimize2,
  Move,
  Eye,
  Settings2,
  Sparkles,
} from "lucide-react";

export const DEFAULT_VIDEO_CONFIG = {
  posX: 2, // 2%
  posY: 3, // 3%
  objectFit: "cover", // cover, contain, fill, none
  scale: 1,
  offsetX: 0, // px
  offsetY: 0, // px
  opacity: 100, // %
};

const STORAGE_KEY = "easyx_hero_video_config_v2";

export function useVideoPositionConfig() {
  const [config, setConfig] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        return { ...DEFAULT_VIDEO_CONFIG, ...JSON.parse(saved) };
      }
    } catch {
      // fallback
    }
    return DEFAULT_VIDEO_CONFIG;
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    } catch {
      // ignore
    }
  }, [config]);

  const resetConfig = () => {
    setConfig(DEFAULT_VIDEO_CONFIG);
  };

  return { config, setConfig, resetConfig };
}

const PRESETS = [
  { label: "Optimal Custom (2% 3%)", posX: 2, posY: 3, scale: 1, fit: "cover" },
  { label: "Right Center", posX: 100, posY: 50, scale: 1, fit: "cover" },
  { label: "Center Center", posX: 50, posY: 50, scale: 1, fit: "cover" },
  { label: "Right Top", posX: 100, posY: 20, scale: 1, fit: "cover" },
  { label: "Right Bottom", posX: 100, posY: 80, scale: 1, fit: "cover" },
  { label: "Left Center", posX: 0, posY: 50, scale: 1, fit: "cover" },
  { label: "Zoomed Coin Focus", posX: 90, posY: 45, scale: 1.35, fit: "cover" },
  { label: "Wide View (Contain)", posX: 2, posY: 3, scale: 1, fit: "contain" },
];

const GRID_POSITIONS = [
  { name: "TL", x: 0, y: 0, title: "Top Left" },
  { name: "TC", x: 50, y: 0, title: "Top Center" },
  { name: "TR", x: 100, y: 0, title: "Top Right" },
  { name: "CL", x: 0, y: 50, title: "Center Left" },
  { name: "CC", x: 50, y: 50, title: "Center" },
  { name: "CR", x: 100, y: 50, title: "Center Right (Default)" },
  { name: "BL", x: 0, y: 100, title: "Bottom Left" },
  { name: "BC", x: 50, y: 100, title: "Bottom Center" },
  { name: "BR", x: 100, y: 100, title: "Bottom Right" },
];

export default function VideoPositionControls({ config, setConfig, onReset }) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState("position"); // position | transform | presets

  const cssString = `object-fit: ${config.objectFit};
object-position: ${config.posX}% ${config.posY}%;
transform: scale(${config.scale}) translate(${config.offsetX}px, ${config.offsetY}px);
opacity: ${config.opacity / 100};`;

  const copyCSS = () => {
    navigator.clipboard.writeText(cssString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2200);
  };

  return (
    <>
      {/* Floating Quick Trigger Button */}
      <div className="video-adjust-trigger-container" data-testid="video-adjust-trigger-wrap">
        <motion.button
          onClick={() => setIsOpen((prev) => !prev)}
          className={`video-adjust-trigger-btn ${isOpen ? "active" : ""}`}
          title="Adjust Background Video Position & Scale"
          data-testid="video-adjust-toggle-btn"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Sliders size={16} className="text-purple-300" />
          <span className="text-xs font-medium tracking-wide">Adjust Video Position</span>
          <span className="video-adjust-badge">
            {config.posX}% {config.posY}%
          </span>
        </motion.button>
      </div>

      {/* Slide-out / Modal Floating Control Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="video-adjust-panel"
            data-testid="video-adjust-panel"
            initial={{ opacity: 0, scale: 0.92, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 20 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
          >
            {/* Header */}
            <div className="video-adjust-panel__header">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-400/30">
                  <Move size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white tracking-wide">
                    Background Video Position
                  </h3>
                  <p className="text-[11px] text-purple-200/70">
                    Real-time alignment & viewport controls
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={onReset}
                  className="p-1.5 text-purple-200/60 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                  title="Reset to default (Right Center)"
                  data-testid="video-adjust-reset-btn"
                >
                  <RotateCcw size={14} />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 text-purple-200/60 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                  title="Close panel"
                  data-testid="video-adjust-close-btn"
                >
                  <X size={15} />
                </button>
              </div>
            </div>

            {/* Quick 3x3 Placement Grid */}
            <div className="video-adjust-panel__section">
              <div className="flex justify-between items-center mb-2">
                <span className="text-[11px] font-medium text-purple-200 uppercase tracking-wider">
                  Quick Anchor Grid
                </span>
                <span className="text-[11px] text-purple-300 font-mono">
                  {config.posX}% X / {config.posY}% Y
                </span>
              </div>
              <div className="grid grid-cols-3 gap-1.5 p-2 rounded-xl bg-black/40 border border-purple-500/20">
                {GRID_POSITIONS.map((pos) => {
                  const isSelected =
                    Math.abs(config.posX - pos.x) < 8 && Math.abs(config.posY - pos.y) < 8;
                  return (
                    <button
                      key={pos.name}
                      onClick={() =>
                        setConfig((prev) => ({
                          ...prev,
                          posX: pos.x,
                          posY: pos.y,
                        }))
                      }
                      title={pos.title}
                      className={`h-7 rounded-lg text-[10px] font-semibold transition-all flex items-center justify-center ${
                        isSelected
                          ? "bg-purple-600 text-white shadow-lg shadow-purple-600/40 border border-purple-400"
                          : "bg-white/5 text-purple-200/70 hover:bg-white/15 hover:text-white"
                      }`}
                    >
                      {pos.name}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Sliders */}
            <div className="video-adjust-panel__section space-y-3">
              {/* Horizontal Position (X) */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-purple-200/90 font-medium">Horizontal Position (X)</span>
                  <span className="text-purple-300 font-mono text-[11px]">
                    {config.posX}% {config.posX === 100 ? "(Right)" : config.posX === 0 ? "(Left)" : config.posX === 50 ? "(Center)" : ""}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={config.posX}
                  onChange={(e) =>
                    setConfig((prev) => ({ ...prev, posX: Number(e.target.value) }))
                  }
                  className="w-full accent-purple-500 bg-white/10 h-1.5 rounded-lg cursor-pointer"
                  data-testid="slider-pos-x"
                />
                <div className="flex justify-between text-[10px] text-purple-300/40 mt-0.5">
                  <span>Left (0%)</span>
                  <span>Center (50%)</span>
                  <span>Right (100%)</span>
                </div>
              </div>

              {/* Vertical Position (Y) */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-purple-200/90 font-medium">Vertical Position (Y)</span>
                  <span className="text-purple-300 font-mono text-[11px]">
                    {config.posY}% {config.posY === 50 ? "(Center)" : config.posY === 0 ? "(Top)" : config.posY === 100 ? "(Bottom)" : ""}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={config.posY}
                  onChange={(e) =>
                    setConfig((prev) => ({ ...prev, posY: Number(e.target.value) }))
                  }
                  className="w-full accent-purple-500 bg-white/10 h-1.5 rounded-lg cursor-pointer"
                  data-testid="slider-pos-y"
                />
                <div className="flex justify-between text-[10px] text-purple-300/40 mt-0.5">
                  <span>Top (0%)</span>
                  <span>Center (50%)</span>
                  <span>Bottom (100%)</span>
                </div>
              </div>

              {/* Scale / Zoom */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-purple-200/90 font-medium">Scale / Zoom</span>
                  <span className="text-purple-300 font-mono text-[11px]">{config.scale}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.2"
                  step="0.05"
                  value={config.scale}
                  onChange={(e) =>
                    setConfig((prev) => ({ ...prev, scale: Number(e.target.value) }))
                  }
                  className="w-full accent-purple-500 bg-white/10 h-1.5 rounded-lg cursor-pointer"
                  data-testid="slider-scale"
                />
                <div className="flex justify-between text-[10px] text-purple-300/40 mt-0.5">
                  <span>0.5x (Fit)</span>
                  <span>1.0x (Standard)</span>
                  <span>2.2x (Close-up)</span>
                </div>
              </div>

              {/* Object Fit Mode */}
              <div>
                <span className="text-[11px] font-medium text-purple-200 block mb-1.5">
                  Object Fit Mode
                </span>
                <div className="grid grid-cols-4 gap-1">
                  {["cover", "contain", "fill", "none"].map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setConfig((prev) => ({ ...prev, objectFit: mode }))}
                      className={`py-1 text-[10px] font-medium capitalize rounded-md transition-all ${
                        config.objectFit === mode
                          ? "bg-purple-600 text-white font-semibold"
                          : "bg-white/5 text-purple-200/70 hover:bg-white/10 hover:text-white"
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Presets List */}
            <div className="video-adjust-panel__section">
              <span className="text-[11px] font-medium text-purple-200 uppercase tracking-wider block mb-1.5">
                Saved Presets
              </span>
              <div className="flex flex-wrap gap-1.5">
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    onClick={() =>
                      setConfig((prev) => ({
                        ...prev,
                        posX: p.posX,
                        posY: p.posY,
                        scale: p.scale,
                        objectFit: p.fit,
                      }))
                    }
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-white/5 hover:bg-purple-500/20 text-purple-200 hover:text-white border border-purple-500/20 transition-all"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Generated CSS & Action Footer */}
            <div className="video-adjust-panel__footer">
              <div className="bg-black/60 rounded-lg p-2 font-mono text-[10px] text-purple-200/90 border border-purple-500/20 mb-2 overflow-x-auto select-all">
                <code>{`object-position: ${config.posX}% ${config.posY}%; object-fit: ${config.objectFit}; transform: scale(${config.scale});`}</code>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={copyCSS}
                  className="flex-1 py-1.5 px-3 rounded-lg bg-purple-600/90 hover:bg-purple-600 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-all shadow-md shadow-purple-900/40"
                  data-testid="copy-video-css-btn"
                >
                  {copied ? (
                    <>
                      <Check size={13} className="text-emerald-300" />
                      <span>CSS Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy size={13} />
                      <span>Copy CSS Snippet</span>
                    </>
                  )}
                </button>
                <button
                  onClick={onReset}
                  className="py-1.5 px-3 rounded-lg bg-white/5 hover:bg-white/10 text-purple-200 text-xs font-medium transition-all"
                >
                  Reset
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
