import { forwardRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Message } from "@/types/domain";
import { MessageItem } from "./MessageItem";

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
}

export const MessageList = forwardRef<HTMLDivElement, MessageListProps>(
  ({ messages, isStreaming }, ref) => {
    return (
      <ScrollArea className="flex-1 p-4" ref={ref}>
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground">How can I help you today?</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <MessageItem
                key={message.id || index}
                message={message}
                isStreaming={isStreaming}
                isLast={index === messages.length - 1}
              />
            ))
          )}
        </div>
      </ScrollArea>
    );
  },
);
MessageList.displayName = "MessageList";
