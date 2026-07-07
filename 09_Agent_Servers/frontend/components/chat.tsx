"use client";

import { useState } from "react";
import { useStream } from "@langchain/react";
import { Cat, Check, Copy, FileText, Search, Wrench } from "lucide-react";

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageActions,
  MessageAction,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolOutput,
} from "@/components/ai-elements/tool";
import { getMessageText, toolLabel } from "@/lib/messages";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

type StreamMessage = ReturnType<typeof useStream>["messages"][number];

const SUGGESTIONS = [
  "How often should I deworm my cat?",
  "What vaccinations do kittens need?",
  "What are signs of feline dehydration?",
];

function toolIcon(name?: string) {
  if (name === "retrieve_information") return <FileText className="size-4" />;
  if (name?.startsWith("tavily")) return <Search className="size-4" />;
  return <Wrench className="size-4" />;
}

export function Chat({ assistantId }: { assistantId: string }) {
  const stream = useStream({ apiUrl: API_URL, assistantId });
  const { messages, isLoading, error } = stream;

  const [input, setInput] = useState("");

  const send = (text: string) => {
    const content = text.trim();
    if (!content || isLoading) return;
    stream.submit({ messages: [{ type: "human", content }] });
    setInput("");
  };

  const onSubmit = (message: PromptInputMessage) => {
    send(message.text ?? "");
  };

  const status = isLoading ? "submitted" : error != null ? "error" : "ready";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <Conversation>
        <ConversationContent className="mx-auto w-full max-w-3xl">
          {messages.length === 0 ? (
            <ConversationEmptyState
              icon={
                <div className="flex size-12 items-center justify-center rounded-full bg-muted">
                  <Cat className="size-6 text-muted-foreground" />
                </div>
              }
              title="Ask the cat health agent"
              description="Streams from your LangGraph deployment via a secure proxy."
            >
              <div className="flex size-12 items-center justify-center rounded-full bg-muted">
                <Cat className="size-6 text-muted-foreground" />
              </div>
              <div className="space-y-1">
                <h3 className="text-lg font-medium">Ask the cat health agent</h3>
                <p className="text-sm text-muted-foreground">
                  Streams from your LangGraph deployment via a secure proxy.
                </p>
              </div>
              <Suggestions className="mt-2 justify-center">
                {SUGGESTIONS.map((s) => (
                  <Suggestion key={s} suggestion={s} onClick={send} />
                ))}
              </Suggestions>
            </ConversationEmptyState>
          ) : (
            messages.map((message, i) => (
              <MessageRow key={message.id ?? i} message={message} />
            ))
          )}

          {isLoading && <ThinkingRow />}

          {error != null && (
            <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error instanceof Error ? error.message : "Something went wrong."}
            </div>
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <div className="border-t bg-background">
        <div className="mx-auto w-full max-w-3xl px-4 py-3">
          <PromptInput onSubmit={onSubmit}>
            <PromptInputBody>
              <PromptInputTextarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Message the cat health agent..."
                disabled={isLoading}
                autoFocus
              />
            </PromptInputBody>
            <PromptInputFooter>
              <PromptInputTools />
              <PromptInputSubmit
                status={status}
                disabled={isLoading || input.trim().length === 0}
              />
            </PromptInputFooter>
          </PromptInput>
        </div>
      </div>
    </div>
  );
}

function MessageRow({ message }: { message: StreamMessage }) {
  const isTool = message.type === "tool";
  const text = getMessageText(message.content);

  if (isTool) {
    const name = message.name ?? "tool";
    return (
      <Tool>
        <ToolHeader
          type={`tool-${name}`}
          state="output-available"
          title={toolLabel(name)}
        />
        <ToolContent>
          <ToolOutput output={text} errorText={undefined} />
        </ToolContent>
      </Tool>
    );
  }

  const isHuman = message.type === "human";
  const toolCalls =
    message.type === "ai"
      ? (message as unknown as {
          tool_calls?: Array<{ name?: string; id?: string }>;
        }).tool_calls ?? []
      : [];

  return (
    <Message from={isHuman ? "user" : "assistant"}>
      <MessageContent>
        {toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {toolCalls.map((tc, idx) => (
              <span
                key={tc.id ?? idx}
                className="inline-flex items-center gap-1.5 rounded-full border bg-muted/60 px-2.5 py-1 text-xs font-medium text-muted-foreground"
              >
                {toolIcon(tc.name)}
                {toolLabel(tc.name)}
              </span>
            ))}
          </div>
        )}
        {text && <MessageResponse>{text}</MessageResponse>}
      </MessageContent>

      {!isHuman && text && (
        <MessageActions>
          <CopyAction text={text} />
        </MessageActions>
      )}
    </Message>
  );
}

function CopyAction({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const onCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <MessageAction tooltip={copied ? "Copied!" : "Copy"} onClick={onCopy}>
      {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
    </MessageAction>
  );
}

function ThinkingRow() {
  return (
    <Message from="assistant">
      <MessageContent>
        <div className="flex items-center gap-1.5 py-1 text-sm text-muted-foreground">
          <span className="size-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.3s]" />
          <span className="size-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.15s]" />
          <span className="size-1.5 animate-bounce rounded-full bg-current" />
        </div>
      </MessageContent>
    </Message>
  );
}
