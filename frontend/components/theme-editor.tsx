"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Settings, X, Upload, RotateCcw } from "lucide-react";
import { useTheme } from "@/lib/theme-context";
import { cn } from "@/lib/cn";

export default function ThemeEditor() {
  const { theme, updateTheme, resetTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const result = event.target?.result as string;
        updateTheme({ backgroundImage: result, backgroundType: "image" });
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <>
      {/* 打开按钮 */}
      <motion.button
        onClick={() => setIsOpen(true)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="fixed right-6 top-6 z-50 flex h-11 w-11 items-center justify-center rounded-full border border-white/20 bg-white/[0.08] shadow-[0_4px_16px_rgba(0,0,0,0.2),inset_0_1px_0_rgba(255,255,255,0.15)] backdrop-blur-xl transition-all hover:border-white/30 hover:bg-white/[0.12]"
      >
        <Settings className="h-5 w-5 text-white" />
      </motion.button>

      {/* 编辑器面板 */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* 遮罩 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 z-[100] bg-black/40 backdrop-blur-sm"
            />

            {/* 面板 */}
            <motion.div
              initial={{ x: 400, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 400, opacity: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed right-0 top-0 z-[101] h-screen w-[420px] border-l border-white/20 bg-[#1a1a1e]/95 shadow-[-8px_0_32px_rgba(0,0,0,0.3)] backdrop-blur-[80px]"
            >
              {/* 头部 */}
              <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
                <h2 className="text-[18px] font-semibold text-white">外观设置</h2>
                <div className="flex gap-2">
                  <button
                    onClick={resetTheme}
                    className="rounded-lg border border-white/10 bg-white/[0.05] p-2 text-white/60 transition-all hover:bg-white/[0.08] hover:text-white"
                  >
                    <RotateCcw className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="rounded-lg border border-white/10 bg-white/[0.05] p-2 text-white/60 transition-all hover:bg-white/[0.08] hover:text-white"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* 内容 */}
              <div className="h-[calc(100vh-73px)] overflow-y-auto px-6 py-6">
                <div className="space-y-8">
                  {/* 背景设置 */}
                  <Section title="背景">
                    <div className="space-y-4">
                      <div>
                        <label className="mb-2 block text-[13px] text-white/70">类型</label>
                        <div className="grid grid-cols-3 gap-2">
                          {(["gradient", "image", "solid"] as const).map((type) => (
                            <button
                              key={type}
                              onClick={() => updateTheme({ backgroundType: type })}
                              className={cn(
                                "rounded-lg border px-3 py-2 text-[12px] transition-all",
                                theme.backgroundType === type
                                  ? "border-[#0a84ff] bg-[#0a84ff]/20 text-white"
                                  : "border-white/10 bg-white/[0.03] text-white/50 hover:bg-white/[0.06]"
                              )}
                            >
                              {type === "gradient" ? "渐变" : type === "image" ? "图片" : "纯色"}
                            </button>
                          ))}
                        </div>
                      </div>

                      {theme.backgroundType === "image" && (
                        <div>
                          <label className="mb-2 block text-[13px] text-white/70">
                            上传背景图
                          </label>
                          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-white/20 bg-white/[0.03] px-4 py-6 text-[13px] text-white/60 transition-all hover:border-white/30 hover:bg-white/[0.06]">
                            <Upload className="h-4 w-4" />
                            <span>选择图片</span>
                            <input
                              type="file"
                              accept="image/*"
                              onChange={handleImageUpload}
                              className="hidden"
                            />
                          </label>
                          {theme.backgroundImage && (
                            <div className="mt-2 rounded-lg border border-white/10 p-2">
                              <img
                                src={theme.backgroundImage}
                                alt="Background"
                                className="h-20 w-full rounded object-cover"
                              />
                            </div>
                          )}
                        </div>
                      )}

                      {theme.backgroundType === "solid" && (
                        <div>
                          <label className="mb-2 block text-[13px] text-white/70">颜色</label>
                          <input
                            type="color"
                            value={theme.backgroundSolid}
                            onChange={(e) => updateTheme({ backgroundSolid: e.target.value })}
                            className="h-10 w-full cursor-pointer rounded-lg border border-white/10"
                          />
                        </div>
                      )}

                      <Slider
                        label="背景模糊"
                        value={theme.backgroundBlur}
                        onChange={(value) => updateTheme({ backgroundBlur: value })}
                        min={0}
                        max={20}
                        step={1}
                      />
                    </div>
                  </Section>

                  {/* 液态玻璃效果 */}
                  <Section title="液态玻璃效果">
                    <div className="space-y-4">
                      <Slider
                        label="透明度"
                        value={theme.glassOpacity}
                        onChange={(value) => updateTheme({ glassOpacity: value })}
                        min={0}
                        max={0.3}
                        step={0.01}
                      />
                      <Slider
                        label="模糊强度"
                        value={theme.glassBlur}
                        onChange={(value) => updateTheme({ glassBlur: value })}
                        min={20}
                        max={120}
                        step={5}
                      />
                      <Slider
                        label="边框透明度"
                        value={theme.glassBorder}
                        onChange={(value) => updateTheme({ glassBorder: value })}
                        min={0}
                        max={0.4}
                        step={0.01}
                      />
                      <Toggle
                        label="高光反射"
                        checked={theme.glassReflection}
                        onChange={(checked) => updateTheme({ glassReflection: checked })}
                      />
                    </div>
                  </Section>

                  {/* 侧边栏 */}
                  <Section title="侧边栏">
                    <div className="space-y-4">
                      <Slider
                        label="宽度"
                        value={theme.sidebarWidth}
                        onChange={(value) => updateTheme({ sidebarWidth: value })}
                        min={200}
                        max={400}
                        step={10}
                      />
                      <Slider
                        label="透明度"
                        value={theme.sidebarOpacity}
                        onChange={(value) => updateTheme({ sidebarOpacity: value })}
                        min={0}
                        max={0.2}
                        step={0.01}
                      />
                    </div>
                  </Section>

                  {/* 消息气泡 */}
                  <Section title="消息气泡">
                    <div className="space-y-4">
                      <Slider
                        label="圆角大小"
                        value={theme.bubbleRadius}
                        onChange={(value) => updateTheme({ bubbleRadius: value })}
                        min={8}
                        max={32}
                        step={2}
                      />
                      <div>
                        <label className="mb-2 block text-[13px] text-white/70">
                          用户消息颜色
                        </label>
                        <input
                          type="color"
                          value={theme.bubbleUserColor}
                          onChange={(e) => updateTheme({ bubbleUserColor: e.target.value })}
                          className="h-10 w-full cursor-pointer rounded-lg border border-white/10"
                        />
                      </div>
                    </div>
                  </Section>

                  {/* 字体 */}
                  <Section title="字体">
                    <div className="space-y-4">
                      <Slider
                        label="字号"
                        value={theme.fontSize}
                        onChange={(value) => updateTheme({ fontSize: value })}
                        min={12}
                        max={20}
                        step={1}
                      />
                      <Slider
                        label="行高"
                        value={theme.lineHeight}
                        onChange={(value) => updateTheme({ lineHeight: value })}
                        min={1.2}
                        max={2}
                        step={0.05}
                      />
                    </div>
                  </Section>

                  {/* 动画 */}
                  <Section title="动画">
                    <div className="space-y-4">
                      <Toggle
                        label="启用动画"
                        checked={theme.enableAnimations}
                        onChange={(checked) => updateTheme({ enableAnimations: checked })}
                      />
                      {theme.enableAnimations && (
                        <Slider
                          label="动画速度"
                          value={theme.animationSpeed}
                          onChange={(value) => updateTheme({ animationSpeed: value })}
                          min={0.5}
                          max={2}
                          step={0.1}
                        />
                      )}
                    </div>
                  </Section>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-4 text-[14px] font-semibold text-white">{title}</h3>
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">{children}</div>
    </div>
  );
}

function Slider({
  label,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step: number;
}) {
  return (
    <div>
      <div className="mb-2 flex justify-between text-[13px]">
        <span className="text-white/70">{label}</span>
        <span className="text-white">{value.toFixed(step < 1 ? 2 : 0)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-white/10 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[#0a84ff] [&::-webkit-slider-thumb]:shadow-[0_2px_8px_rgba(10,132,255,0.4)]"
      />
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[13px] text-white/70">{label}</span>
      <button
        onClick={() => onChange(!checked)}
        className={cn(
          "relative h-6 w-11 rounded-full transition-all",
          checked ? "bg-[#0a84ff]" : "bg-white/10"
        )}
      >
        <motion.div
          className="absolute top-1 h-4 w-4 rounded-full bg-white shadow-md"
          animate={{ x: checked ? 24 : 4 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        />
      </button>
    </div>
  );
}
