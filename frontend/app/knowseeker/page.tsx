"use client";

import * as React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Brain,
  FileText,
  FileUp,
  Lightbulb,
  Loader2,
  MessageSquare,
  Send,
  Sparkles,
  Trash2,
  Upload,
  User,
} from "lucide-react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "sonner";

const API_BASE = "http://localhost:8000/api";

interface DocumentItem {
  id: string;
  doc_id: string;
  file_name: string;
  chunks_count: number;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  thinking_trace?: { step: string; content: string; detail?: string }[];
  citations?: { doc_name: string; content?: string }[];
}

const iconMap: Record<string, { icon: string; color: string; label: string }> = {
  analyze: { icon: "📋", color: "text-blue-500", label: "问题分析" },
  retrieve: { icon: "🔍", color: "text-violet-500", label: "检索知识" },
  evaluate: { icon: "📊", color: "text-amber-500", label: "评估结果" },
  reformulate: { icon: "🔄", color: "text-cyan-500", label: "重写查询" },
  generate: { icon: "📝", color: "text-green-500", label: "生成回答" },
};

const SUGGESTIONS = [
  "总结我的文档要点",
  "文档涵盖了哪些主要主题？",
  "查找某个特定术语的相关信息",
];

export default function KnowSeekerPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isFetchingDocs, setIsFetchingDocs] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadDocuments = useCallback(async () => {
    setIsFetchingDocs(true);
    try {
      const res = await fetch(`${API_BASE}/documents`);
      if (!res.ok) throw new Error("加载文档失败");
      const data: DocumentItem[] = await res.json();
      setDocuments(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsFetchingDocs(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setUploadProgress(0);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = (ev) => {
          if (ev.lengthComputable) {
            setUploadProgress(Math.round((ev.loaded / ev.total) * 100));
          }
        };
        xhr.onload = () =>
          xhr.status >= 200 && xhr.status < 300
            ? resolve()
            : reject(new Error("上传失败"));
        xhr.onerror = () => reject(new Error("上传失败"));
        xhr.open("POST", `${API_BASE}/documents/upload`);
        xhr.send(formData);
      });
      toast.success("文档上传成功", { description: file.name });
      await loadDocuments();
    } catch (err) {
      toast.error("上传失败", {
        description: err instanceof Error ? err.message : "请重试",
      });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("删除失败");
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
      toast.success("文档已删除");
    } catch (err) {
      toast.error("删除文档失败", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  };

  const handleSend = async (text?: string) => {
    const question = (text ?? input).trim();
    if (!question || isLoading) return;
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error("获取回答失败");
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer ?? "",
          thinking_trace: data.thinking_trace,
          citations: data.citations,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "发生错误");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
        {/* ===== 侧边栏：文档管理 ===== */}
        <aside className="flex w-80 shrink-0 flex-col border-r bg-card">
          <div className="flex flex-col gap-3 p-4">
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 text-primary-foreground shadow-sm">
                <Brain className="size-5" />
              </div>
              <div className="flex flex-col">
                <span className="text-base font-semibold leading-tight">
                  KnowSeeker
                </span>
                <span className="text-xs text-muted-foreground">
                  Agentic RAG 知识助手
                </span>
              </div>
            </div>
          </div>
          <Separator />
          <div className="flex flex-col gap-3 p-4">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileChange}
              accept=".pdf,.txt,.md,.docx,.csv"
            />
            <Button
              onClick={handleUploadClick}
              disabled={isUploading}
              className="w-full"
            >
              {isUploading ? (
                <>
                  <Loader2 data-icon="inline-start" className="animate-spin" />
                  上传中…
                </>
              ) : (
                <>
                  <Upload data-icon="inline-start" />
                  上传文档
                </>
              )}
            </Button>
            {isUploading && (
              <div className="flex flex-col gap-1.5">
                <Progress value={uploadProgress} />
                <span className="text-xs text-muted-foreground">
                  已上传 {uploadProgress}%
                </span>
              </div>
            )}
          </div>
          <Separator />
          <div className="flex items-center justify-between px-4 py-3">
            <span className="text-sm font-medium">文档列表</span>
            <Badge variant="secondary">{documents.length}</Badge>
          </div>
          <ScrollArea className="min-h-0 flex-1">
            <div className="flex flex-col gap-2 px-4 pb-4">
              {isFetchingDocs ? (
                <div className="flex flex-col gap-2">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 rounded-lg border p-3"
                    >
                      <Skeleton className="size-8 rounded-md" />
                      <div className="flex flex-1 flex-col gap-2">
                        <Skeleton className="h-3 w-3/4" />
                        <Skeleton className="h-2.5 w-1/3" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : documents.length === 0 ? (
                <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-6 text-center">
                  <div className="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
                    <FileUp className="size-5" />
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium">暂无文档</span>
                    <span className="text-xs text-muted-foreground">
                      上传文件即可开始
                    </span>
                  </div>
                </div>
              ) : (
                documents.map((doc) => (
                  <div
                    key={doc.doc_id}
                    className="group flex items-center gap-3 rounded-lg border bg-background p-3 transition-colors hover:bg-accent"
                  >
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                      <FileText className="size-4" />
                    </div>
                    <div className="flex min-w-0 flex-1 flex-col gap-1">
                      <span
                        className="truncate text-sm font-medium"
                        title={doc.file_name}
                      >
                        {doc.file_name}
                      </span>
                      <Badge
                        variant="secondary"
                        className="w-fit text-xs font-normal"
                      >
                        {doc.chunks_count} 个分块
                      </Badge>
                    </div>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-7 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:text-destructive"
                          onClick={() => handleDelete(doc.doc_id)}
                        >
                          <Trash2 />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>删除文档</TooltipContent>
                    </Tooltip>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </aside>

        {/* ===== 主区：聊天 ===== */}
        <main className="flex min-h-0 flex-1 flex-col">
          <header className="flex h-14 shrink-0 items-center gap-2 border-b px-6">
            <MessageSquare className="size-5 text-muted-foreground" />
            <span className="font-semibold">知识问答助手</span>
            <Badge variant="outline" className="ml-auto gap-1">
              <Sparkles className="size-3" />
              Agentic RAG
            </Badge>
          </header>

          <div className="flex min-h-0 flex-1 flex-col">
            {messages.length === 0 && !error ? (
              <div className="flex flex-1 items-center justify-center p-6">
                <Card className="w-full max-w-md shadow-sm">
                  <CardHeader className="items-center text-center">
                    <div className="flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-blue-500 text-primary-foreground shadow-lg">
                      <Brain className="size-8" />
                    </div>
                    <CardTitle className="text-2xl">向 KnowSeeker 提问</CardTitle>
                    <CardDescription>
                      在左侧上传文档，然后提出任何问题。
                      KnowSeeker 会自主检索、评估并综合答案 ——
                      附带透明的思考过程和来源引用。
                    </CardDescription>
                  </CardHeader>
                  <CardFooter className="flex flex-col items-stretch gap-2">
                    <span className="self-start text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      试试这些问题
                    </span>
                    {SUGGESTIONS.map((s) => (
                      <Button
                        key={s}
                        variant="outline"
                        className="w-full justify-start"
                        onClick={() => handleSend(s)}
                      >
                        <Lightbulb data-icon="inline-start" />
                        {s}
                      </Button>
                    ))}
                  </CardFooter>
                </Card>
              </div>
            ) : (
              <ScrollArea className="min-h-0 flex-1">
                <div className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
                  {messages.map((msg, i) => (
                    <MessageBubble key={i} message={msg} />
                  ))}
                  {isLoading && <LoadingBubble />}
                  {error && (
                    <Alert variant="destructive">
                      <AlertCircle className="size-4" />
                      <AlertTitle>出现错误</AlertTitle>
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>
            )}
          </div>

          {/* ===== 输入区 ===== */}
          <div className="shrink-0 border-t p-4">
            <div className="mx-auto flex max-w-3xl flex-col gap-2">
              <div className="flex items-end gap-2 rounded-xl border bg-card p-2 focus-within:ring-2 focus-within:ring-ring">
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="输入你想了解的问题…"
                  className="max-h-40 min-h-[28px] flex-1 resize-none border-0 bg-transparent p-1.5 text-sm shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
                  rows={1}
                />
                <Button
                  size="icon"
                  onClick={() => handleSend()}
                  disabled={!input.trim() || isLoading}
                  className="size-9 shrink-0"
                >
                  {isLoading ? (
                    <Loader2 className="animate-spin" />
                  ) : (
                    <Send />
                  )}
                </Button>
              </div>
              <p className="text-center text-xs text-muted-foreground">
                按{" "}
                <kbd className="rounded border bg-muted px-1 font-sans text-[10px]">
                  Enter
                </kbd>{" "}
                发送 ·{" "}
                <kbd className="rounded border bg-muted px-1 font-sans text-[10px]">
                  Shift
                </kbd>
                +
                <kbd className="rounded border bg-muted px-1 font-sans text-[10px]">
                  Enter
                </kbd>{" "}
                换行
              </p>
            </div>
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <Avatar className="size-8 shrink-0">
        {isUser ? (
          <AvatarFallback className="bg-muted text-muted-foreground">
            <User className="size-4" />
          </AvatarFallback>
        ) : (
          <AvatarFallback className="bg-gradient-to-br from-violet-500 to-blue-500 text-primary-foreground">
            <Brain className="size-4" />
          </AvatarFallback>
        )}
      </Avatar>
      <div
        className={`flex max-w-[80%] flex-col gap-2 ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        <div
          className={
            isUser
              ? "rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground"
              : "rounded-2xl rounded-bl-sm bg-muted px-4 py-2.5 text-sm"
          }
        >
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>
        {!isUser &&
          message.thinking_trace &&
          message.thinking_trace.length > 0 && (
            <ThinkingTrace trace={message.thinking_trace} />
          )}
        {!isUser && message.citations && message.citations.length > 0 && (
          <Citations citations={message.citations} />
        )}
      </div>
    </div>
  );
}

function ThinkingTrace({
  trace,
}: {
  trace: { step: string; content: string; detail?: string }[];
}) {
  return (
    <div className="w-full rounded-lg border bg-background">
      <Accordion type="single" collapsible>
        <AccordionItem value="thinking" className="border-b-0">
          <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-violet-500" />
              <span className="font-medium">思考过程</span>
              <Badge variant="secondary" className="text-xs font-normal">
                {trace.length} 步
              </Badge>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-3 pb-3 pt-0">
            <div className="flex flex-col gap-1">
              {trace.map((step, i) => {
                const meta = iconMap[step.step] ?? {
                  icon: "•",
                  color: "text-muted-foreground",
                  label: step.step,
                };
                const isLast = i === trace.length - 1;
                return (
                  <div key={i} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div
                        className={`flex size-7 items-center justify-center rounded-full bg-muted text-sm ${meta.color}`}
                      >
                        {meta.icon}
                      </div>
                      {!isLast && <div className="w-px flex-1 bg-border" />}
                    </div>
                    <div className="flex flex-1 flex-col gap-1 pb-2">
                      <span className="text-sm font-medium">{meta.label}</span>
                      <p className="text-sm leading-relaxed text-muted-foreground">
                        {step.content}
                      </p>
                      {step.detail && (
                        <div className="rounded-md bg-muted/60 p-2 text-xs text-muted-foreground">
                          {step.detail}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}

function Citations({
  citations,
}: {
  citations: { doc_name: string; content?: string }[];
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-muted-foreground">来源引用</span>
      <div className="flex flex-wrap gap-1.5">
        {citations.map((c, i) => (
          <Tooltip key={i}>
            <TooltipTrigger asChild>
              <Badge variant="secondary" className="gap-1 font-normal">
                <FileText className="size-3" />
                {c.doc_name}
              </Badge>
            </TooltipTrigger>
            {c.content && (
              <TooltipContent className="max-w-xs">{c.content}</TooltipContent>
            )}
          </Tooltip>
        ))}
      </div>
    </div>
  );
}

function LoadingBubble() {
  return (
    <div className="flex gap-3">
      <Avatar className="size-8 shrink-0">
        <AvatarFallback className="bg-gradient-to-br from-violet-500 to-blue-500 text-primary-foreground">
          <Brain className="size-4" />
        </AvatarFallback>
      </Avatar>
      <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-muted px-4 py-3">
        <Loader2 className="size-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">思考中…</span>
      </div>
    </div>
  );
}
