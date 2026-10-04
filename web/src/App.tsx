import { useEffect, useState } from "react";
import AddPersonaModal from "./components/AddPersonaModal";
import ChatLog from "./components/ChatLog";
import Composer from "./components/Composer";
import Stage from "./components/Stage";
import Toasts from "./components/Toasts";
import TopBar from "./components/TopBar";
import { useRoom } from "./store";

export default function App() {
  const init = useRoom((s) => s.init);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    void init();
  }, [init]);

  return (
    <div className="flex h-full flex-col bg-ink-900 text-fog-100">
      <TopBar onAdd={() => setAdding(true)} />
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <Stage onAdd={() => setAdding(true)} />
        <aside className="flex h-[42vh] min-h-0 flex-col border-t border-white/5 bg-ink-950/60 lg:h-auto lg:w-[380px] lg:border-l lg:border-t-0 xl:w-[420px]">
          <div className="flex items-center justify-between px-4 py-2.5">
            <span className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-fog-400">transcript</span>
            <ClearButton />
          </div>
          <ChatLog />
          <Composer />
        </aside>
      </div>
      <AddPersonaModal open={adding} onClose={() => setAdding(false)} />
      <Toasts />
    </div>
  );
}

function ClearButton() {
  const control = useRoom((s) => s.control);
  const count = useRoom((s) => s.messages.length);
  if (!count) return null;
  return (
    <button onClick={() => void control("clear")} className="font-mono text-[10.5px] uppercase tracking-wider text-fog-400 transition hover:text-fog-100" title="Clear the transcript">
      clear
    </button>
  );
}
