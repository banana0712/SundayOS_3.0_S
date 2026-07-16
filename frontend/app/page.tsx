import ChatInterface from "@/components/chat-interface";
import ThemeEditor from "@/components/theme-editor";

export default function Home() {
  return (
    <>
      {/* 液态玻璃水滴层 */}
      <div className="fixed inset-0 z-[2] pointer-events-none">
        <div className="water-drop"></div>
        <div className="water-drop"></div>
        <div className="water-drop"></div>
        <div className="water-drop"></div>
      </div>
      <ChatInterface />
      <ThemeEditor />
    </>
  );
}
