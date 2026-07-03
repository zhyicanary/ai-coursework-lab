"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";

// ── 类型定义 ──────────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  thinking_trace?: { step: string; content: string; detail?: string }[];
  citations?: { doc_name: string; content?: string }[];
}

interface KnowSeekerContextType {
  messages: ChatMessage[];
  isLoading: boolean;
  progress: number; // 0..1
  error: string | null;
  sendMessage: (question: string) => Promise<string>; // 返回 taskId
  restoreTask: (taskId: string) => Promise<void>; // 轮询已有任务
  appendAssistantMessage: (msg: ChatMessage) => void; // 轮询结果写入
  setError: (err: string | null) => void;
  setLoading: (v: boolean) => void;
  setProgress: (v: number) => void;
  clearChat: () => void;
}

const API_BASE = "http://localhost:8000/api";

// ── Context ───────────────────────────────────────────────

const KnowSeekerContext = createContext<KnowSeekerContextType | null>(null);

export function KnowSeekerProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const pollingRef = useRef(false);

  const appendAssistantMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setProgress(0);
    setError(null);
  }, []);

  const sendMessage = useCallback(async (question: string) => {
    // 取消上一次请求
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setError(null);
    setProgress(0);
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error("提交失败");
      const data = await res.json();
      return data.taskId as string;
    } catch (err) {
      if ((err as Error).name === "AbortError") return "";
      setError(err instanceof Error ? err.message : "发生错误");
      setIsLoading(false);
      return "";
    }
  }, []);

  const restoreTask = useCallback(async (taskId: string) => {
    if (pollingRef.current) return; // 已在轮询
    pollingRef.current = true;
    setError(null);
    setIsLoading(true);
    setProgress(0);

    try {
      while (true) {
        const res = await fetch(`${API_BASE}/chat/${taskId}`);
        if (!res.ok) throw new Error("任务不存在");
        const task = await res.json();

        if (task.status === "completed") {
          setMessages((prev) => {
            // 如果用户消息丢了（刷新后），从后端返回的 question 重建
            const hasUserMsg = prev.some((m) => m.role === "user");
            const msgs = hasUserMsg
              ? [...prev]
              : [...prev, { role: "user" as const, content: task.question ?? "" }];
            msgs.push({
              role: "assistant",
              content: task.answer ?? "",
              thinking_trace: task.thinking_trace,
              citations: task.citations,
            });
            return msgs;
          });
          setProgress(1);
          setIsLoading(false);
          return;
        }

        if (task.status === "error") {
          setError(task.error ?? "任务执行失败");
          setProgress(1);
          setIsLoading(false);
          return;
        }

        // 还在处理中
        setProgress(task.progress ?? 0.3);
        await new Promise((r) => setTimeout(r, 1000));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "恢复任务失败");
      setIsLoading(false);
    } finally {
      pollingRef.current = false;
    }
  }, []);

  return (
    <KnowSeekerContext.Provider
      value={{
        messages,
        isLoading,
        progress,
        error,
        sendMessage,
        restoreTask,
        appendAssistantMessage,
        setError,
        setLoading: setIsLoading,
        setProgress,
        clearChat,
      }}
    >
      {children}
    </KnowSeekerContext.Provider>
  );
}

export function useKnowSeeker() {
  const ctx = useContext(KnowSeekerContext);
  if (!ctx) throw new Error("useKnowSeeker 必须在 KnowSeekerProvider 内使用");
  return ctx;
}
