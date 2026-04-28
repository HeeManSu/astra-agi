import { useState } from "react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  setInputValue,
  selectCurrentMessages,
} from "@/store/slices/chatSlice";
import { Switch } from "@/components/ui/switch";
import { Zap } from "lucide-react";
import { useChatStream } from "@/hooks/useChatStream";
import { useAutoScroll } from "@/hooks/useAutoScroll";
import { MessageList } from "./MessageList";
import { ChatComposer } from "./ChatComposer";

function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center bg-background">
      <div className="text-center">
        <img
          src="/logo.svg"
          alt="Astra Logo"
          className="h-16 w-16 mx-auto invert"
        />
        <h2 className="mt-4 text-xl font-semibold text-foreground">
          Welcome to Astra Playground
        </h2>
        <p className="mt-2 text-muted-foreground">
          Select an agent or team from the sidebar to start chatting
        </p>
      </div>
    </div>
  );
}

interface ModeToggleProps {
  streamMode: boolean;
  onChange: (next: boolean) => void;
}

function ModeToggle({ streamMode, onChange }: ModeToggleProps) {
  return (
    <div className="h-14 border-b border-border flex items-center justify-end px-4">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Invoke</span>
        <Switch
          checked={streamMode}
          onCheckedChange={onChange}
          className="data-[state=checked]:bg-primary"
        />
        <span className="text-xs text-muted-foreground flex items-center gap-1">
          <Zap className="h-3 w-3" />
          Stream
        </span>
      </div>
    </div>
  );
}

function ChatArea() {
  const dispatch = useAppDispatch();
  const selectedItem = useAppSelector((state) => state.app.selectedItem);
  const { isStreaming, streamingContent, inputValue } = useAppSelector(
    (state) => state.chat,
  );
  const messages = useAppSelector(selectCurrentMessages);

  const [streamMode, setStreamMode] = useState(true);
  const { send } = useChatStream();
  const scrollRef = useAutoScroll<HTMLDivElement>([messages, streamingContent]);

  const handleSubmit = (): void => {
    const text = inputValue;
    dispatch(setInputValue(""));
    void send({ text, streamMode });
  };

  if (!selectedItem) {
    return <EmptyState />;
  }

  return (
    <div className="flex-1 flex flex-col bg-background">
      <ModeToggle streamMode={streamMode} onChange={setStreamMode} />
      <MessageList
        ref={scrollRef}
        messages={messages}
        isStreaming={isStreaming}
      />
      <ChatComposer
        value={inputValue}
        onChange={(v) => dispatch(setInputValue(v))}
        onSubmit={handleSubmit}
        isStreaming={isStreaming}
        focusKey={selectedItem.id}
      />
    </div>
  );
}

export default ChatArea;
