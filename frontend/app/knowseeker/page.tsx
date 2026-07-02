"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
    Search,
    Send,
    Upload,
    Trash2,
    FileText,
    Loader2,
    Brain,
    ChevronDown,
    ChevronUp,
    Sparkles,
    Bot,
    User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const API_BASE = "http://localhost:8000";

interface Document {
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

const iconMap: Record<string, { icon: string; color: string }> = {
    analyze: { icon: "📋", color: "text-blue-500" },
    retrieve: { icon: "🔍", color: "text-violet-500" },
    evaluate: { icon: "📊", color: "text-amber-500" },
    reformulate: { icon: "🔄", color: "text-cyan-500" },
    generate: { icon: "📝", color: "text-green-500" },
};

export default function KnowSeekerPage() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expandedThinking, setExpandedThinking] = useState<
        Record<number, boolean>
    >({});
    const fileInputRef = useRef<HTMLInputElement>(null);
    const chatEndRef = useRef<HTMLDivElement>(null);

    const fetchDocuments = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/documents`);
            if (res.ok) {
                const data = await res.json();
                setDocuments(data);
            }
        } catch {
            // Backend not available yet
        }
    }, []);

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const res = await fetch(`${API_BASE}/api/documents/upload`, {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Upload failed");
            }

            await fetchDocuments();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Upload failed");
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    const handleDelete = async (docId: string) => {
        try {
            const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
                method: "DELETE",
            });
            if (res.ok) {
                await fetchDocuments();
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Delete failed");
        }
    };

    const handleSend = async () => {
        const question = input.trim();
        if (!question || loading) return;

        setInput("");
        setError(null);

        const userMsg: ChatMessage = { role: "user", content: question };
        setMessages((prev) => [...prev, userMsg]);
        setLoading(true);

        try {
            const res = await fetch(`${API_BASE}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question }),
            });

            if (!res.ok) {
                throw new Error("Chat request failed");
            }

            const data = await res.json();

            const assistantMsg: ChatMessage = {
                role: "assistant",
                content: data.answer || "（未能生成回答）",
                thinking_trace: data.thinking_trace || [],
                citations: data.citations || [],
            };

            setMessages((prev) => [...prev, assistantMsg]);
        } catch (err) {
            const errorMsg: ChatMessage = {
                role: "assistant",
                content: `请求失败：${err instanceof Error ? err.message : "未知错误"}`,
            };
            setMessages((prev) => [...prev, errorMsg]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const toggleThinking = (idx: number) => {
        setExpandedThinking((prev) => ({ ...prev, [idx]: !prev[idx] }));
    };

    return (
        <div className="flex h-[calc(100vh-3.5rem)]">
            {/* Left Sidebar - Document Management */}
            <aside className="hidden lg:flex w-72 flex-col border-r bg-sidebar-background/50 backdrop-blur-sm">
                <div className="p-4 border-b">
                    <h2 className="text-sm font-semibold flex items-center gap-2">
                        <FileText className="h-4 w-4 text-primary" />
                        知识库文档
                    </h2>
                    <p className="text-xs text-muted-foreground mt-1">
                        上传文档以构建 RAG 知识库
                    </p>
                </div>

                <div className="p-3">
                    <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        onChange={handleUpload}
                        accept=".pdf,.txt,.md,.docx,.csv,.json,.xml"
                    />
                    <Button
                        variant="outline"
                        className="w-full gap-2 border-dashed"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                    >
                        {uploading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Upload className="h-4 w-4" />
                        )}
                        {uploading ? "上传中..." : "上传文档"}
                    </Button>
                    <p className="text-xs text-muted-foreground mt-2 text-center">
                        支持 PDF, TXT, MD, DOCX
                    </p>
                </div>

                <Separator />

                <ScrollArea className="flex-1 px-3 pb-3">
                    {documents.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted mb-3">
                                <FileText className="h-5 w-5 text-muted-foreground" />
                            </div>
                            <p className="text-sm text-muted-foreground">
                                暂无文档
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">
                                上传后即可开始提问
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-2 pt-2">
                            {documents.map((doc) => (
                                <div
                                    key={doc.id || doc.doc_id}
                                    className="group flex items-start justify-between rounded-lg border bg-card p-3 text-sm transition-colors hover:bg-accent/50"
                                >
                                    <div className="flex items-start gap-2 min-w-0 flex-1">
                                        <FileText className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                                        <div className="min-w-0">
                                            <p className="font-medium truncate text-sm">
                                                {doc.file_name}
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                {doc.chunks_count} 个片段
                                            </p>
                                        </div>
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-7 w-7 text-muted-foreground hover:text-destructive shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                                        onClick={() => handleDelete(doc.doc_id)}
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    )}
                </ScrollArea>
            </aside>

            {/* Main Chat Area */}
            <div className="flex flex-1 flex-col">
                {/* Header */}
                <div className="flex items-center gap-2 border-b px-4 py-3 bg-background/80 backdrop-blur-sm">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/15 to-blue-500/15 ring-1 ring-violet-500/20">
                        <Brain className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                    </div>
                    <h1 className="text-lg font-semibold">KnowSeeker</h1>
                    <Badge variant="secondary" className="ml-1 text-xs gap-1">
                        <Sparkles className="h-3 w-3" />
                        Agentic RAG
                    </Badge>
                </div>

                {/* Chat Messages */}
                <ScrollArea className="flex-1 scrollbar-thin">
                    {messages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-center py-16 px-4">
                            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/10 to-blue-500/10 ring-1 ring-violet-500/15 mb-4">
                                <Search className="h-8 w-8 text-violet-500/70" />
                            </div>
                            <h2 className="text-xl font-semibold mb-2">
                                Agentic RAG 知识助手
                            </h2>
                            <p className="text-muted-foreground max-w-md text-sm leading-relaxed">
                                上传文档后即可开始提问。AI Agent
                                会自主分析问题、制定检索策略并生成精准回答，
                                支持多轮检索和引用溯源。
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-6 py-4 px-4 max-w-3xl mx-auto">
                            {messages.map((msg, idx) => (
                                <div
                                    key={idx}
                                    className={cn(
                                        "flex gap-3 animate-fade-in-up",
                                        msg.role === "user"
                                            ? "justify-end"
                                            : "justify-start",
                                    )}
                                >
                                    {/* Avatar */}
                                    {msg.role === "assistant" && (
                                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 text-white">
                                            <Bot className="h-4 w-4" />
                                        </div>
                                    )}

                                    <div
                                        className={cn(
                                            "max-w-[80%] rounded-2xl px-4 py-3",
                                            msg.role === "user"
                                                ? "bg-primary text-primary-foreground rounded-br-md"
                                                : "bg-muted rounded-bl-md",
                                        )}
                                    >
                                        <div className="text-sm whitespace-pre-wrap leading-relaxed">
                                            {msg.content}
                                        </div>

                                        {/* Thinking Process - Timeline */}
                                        {msg.role === "assistant" &&
                                            msg.thinking_trace &&
                                            msg.thinking_trace.length > 0 && (
                                                <div className="mt-3 border-t pt-3">
                                                    <button
                                                        className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                                                        onClick={() =>
                                                            toggleThinking(idx)
                                                        }
                                                    >
                                                        {expandedThinking[
                                                            idx
                                                        ] ? (
                                                            <ChevronUp className="h-3 w-3" />
                                                        ) : (
                                                            <ChevronDown className="h-3 w-3" />
                                                        )}
                                                        <Brain className="h-3 w-3" />
                                                        思考过程 ({
                                                            msg.thinking_trace
                                                                .length
                                                        }{" "}
                                                        步)
                                                    </button>
                                                    {expandedThinking[idx] && (
                                                        <div className="mt-3 space-y-0">
                                                            {msg.thinking_trace.map(
                                                                (step, si) => {
                                                                    const meta =
                                                                        iconMap[
                                                                            step
                                                                                .step
                                                                        ] ||
                                                                        {
                                                                            icon: "🤖",
                                                                            color: "text-muted-foreground",
                                                                        };
                                                                    const isLast =
                                                                        si ===
                                                                        msg
                                                                            .thinking_trace!
                                                                            .length -
                                                                            1;
                                                                    return (
                                                                        <div
                                                                            key={
                                                                                si
                                                                            }
                                                                            className="flex gap-3"
                                                                        >
                                                                            {/* Timeline line + dot */}
                                                                            <div className="flex flex-col items-center">
                                                                                <div
                                                                                    className={cn(
                                                                                        "flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs",
                                                                                        meta.color,
                                                                                    )}
                                                                                >
                                                                                    {
                                                                                        meta.icon
                                                                                    }
                                                                                </div>
                                                                                {!isLast && (
                                                                                    <div className="w-px flex-1 bg-border min-h-[20px]" />
                                                                                )}
                                                                            </div>
                                                                            {/* Content */}
                                                                            <div className="pb-3 flex-1">
                                                                                <p className="text-xs font-medium">
                                                                                    {
                                                                                        step.content
                                                                                    }
                                                                                </p>
                                                                                {step.detail && (
                                                                                    <p className="text-xs text-muted-foreground mt-0.5">
                                                                                        {
                                                                                            step.detail
                                                                                        }
                                                                                    </p>
                                                                                )}
                                                                            </div>
                                                                        </div>
                                                                    );
                                                                },
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                        {/* Citations */}
                                        {msg.role === "assistant" &&
                                            msg.citations &&
                                            msg.citations.length > 0 && (
                                                <div className="mt-3 border-t pt-3">
                                                    <p className="text-xs font-medium text-muted-foreground mb-1.5">
                                                        引用来源
                                                    </p>
                                                    <div className="flex flex-wrap gap-1.5">
                                                        {msg.citations.map(
                                                            (c, ci) => (
                                                                <Badge
                                                                    key={ci}
                                                                    variant="outline"
                                                                    className="text-xs gap-1"
                                                                >
                                                                    <FileText className="h-3 w-3" />
                                                                    {c.doc_name}
                                                                </Badge>
                                                            ),
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                    </div>

                                    {/* User avatar */}
                                    {msg.role === "user" && (
                                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
                                            <User className="h-4 w-4 text-muted-foreground" />
                                        </div>
                                    )}
                                </div>
                            ))}
                            {loading && (
                                <div className="flex items-center gap-2 text-sm text-muted-foreground pl-11">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Agent 正在思考...
                                </div>
                            )}
                            <div ref={chatEndRef} />
                        </div>
                    )}
                </ScrollArea>

                {/* Error */}
                {error && (
                    <div className="mx-4 mb-2 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-2 text-sm text-destructive">
                        {error}
                        <button
                            className="ml-2 underline"
                            onClick={() => setError(null)}
                        >
                            关闭
                        </button>
                    </div>
                )}

                {/* Input Area */}
                <div className="border-t p-4">
                    <div className="flex gap-2 max-w-3xl mx-auto">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="请输入您的问题... (Enter 发送)"
                            disabled={loading}
                            className="flex-1"
                        />
                        <Button
                            onClick={handleSend}
                            disabled={loading || !input.trim()}
                            size="icon"
                            className="h-10 w-10"
                        >
                            {loading ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="h-4 w-4" />
                            )}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
