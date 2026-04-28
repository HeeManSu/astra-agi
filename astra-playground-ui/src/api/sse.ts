/**
 * Shared SSE reader loop. The runtime's `/agents/{id}/stream` and
 * `/teams/{id}/stream` endpoints emit `data: <json>\n\n` lines terminated by
 * `data: [DONE]`. We parse each line through `safeParseSseEvent`, which
 * tolerates the canonical and legacy event shapes.
 */

import type { StreamCallbacks } from "@/types/sse";
import { safeParseSseEvent } from "@/api/schemas";

const DONE_SENTINEL = "[DONE]";
const DATA_PREFIX = "data: ";

export async function consumeSseStream(
  response: Response,
  { onChunk, onDone, onError }: StreamCallbacks,
): Promise<void> {
  if (!response.body) {
    onError(new Error("Response has no body"));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        onDone();
        return;
      }

      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith(DATA_PREFIX)) continue;
        const data = line.slice(DATA_PREFIX.length).trim();

        if (data === DONE_SENTINEL) {
          onDone();
          return;
        }

        const event = safeParseSseEvent(data);
        if (event) {
          onChunk(event);
        } else if (data) {
          console.warn("Unparseable SSE event payload:", data);
        }
      }
    }
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)));
  }
}
