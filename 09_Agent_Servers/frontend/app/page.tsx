"use client";

import { Cat } from "lucide-react";

import { Chat } from "@/components/chat";

const ASSISTANT_ID = "simple_agent";

export default function Page() {
  return (
    <main className="flex h-dvh flex-col">
      <header className="border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex w-full max-w-3xl items-center gap-3 px-4 py-3">
          <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <Cat className="size-5" />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-semibold">Cat Health Agent</p>
            <p className="text-xs text-muted-foreground">LangGraph + Next.js</p>
          </div>
        </div>
      </header>

      <Chat assistantId={ASSISTANT_ID} />
    </main>
  );
}
